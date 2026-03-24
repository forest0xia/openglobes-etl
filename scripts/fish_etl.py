"""
Fish Globe ETL pipeline.

Downloads FishBase parquet tables, cleans/merges them, assigns coordinates
from GBIF occurrences, splits into spatial tiles, and generates detail files.

Usage:
    python scripts/fish_etl.py                # Run full pipeline
    python scripts/fish_etl.py --download     # Download raw data only
    python scripts/fish_etl.py --process      # Process existing raw data only
"""

import argparse
import gzip
import json
import os
import sys
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import requests

# Add scripts dir to path for tile_splitter import
sys.path.insert(0, str(Path(__file__).parent))
from tile_splitter import split_tiles

# --- Config ---

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "fishbase"
OUTPUT_DIR = ROOT / "output" / "fish"

FISHBASE_RELEASE = "https://github.com/ropensci/rfishbase/releases/download/fb-21.06"
TABLES = ["species", "ecology", "comnames", "country", "stocks", "faoareas", "countref"]

# Rarity tiers based on number of GBIF occurrences
RARITY_THRESHOLDS = {
    "Legendary": 10,
    "Rare": 100,
    "Uncommon": 1000,
    # Everything else is "Common"
}


# --- Download ---


def download_fishbase():
    """Download FishBase tables from rfishbase GitHub releases (tsv.gz), save as parquet."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

    for table in TABLES:
        out_path = RAW_DIR / f"{table}.parquet"
        if out_path.exists():
            print(f"  {table}.parquet already exists, skipping")
            continue

        url = f"{FISHBASE_RELEASE}/{table}.tsv.gz"
        print(f"  Downloading {table}.tsv.gz ...")
        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            # Decompress gzip, parse TSV with pandas, save as parquet
            tsv_bytes = gzip.decompress(resp.content)
            df = pd.read_csv(
                pd.io.common.BytesIO(tsv_bytes),
                sep="\t",
                on_bad_lines="skip",
                engine="python",
            )
            df.to_parquet(out_path, index=False)
            print(f"    -> {len(df):,} rows ({len(resp.content) / 1024 / 1024:.1f} MB)")
        except Exception as e:
            print(f"    ERROR downloading {table}: {e}")
            if out_path.exists():
                out_path.unlink()
            raise

    con.close()
    print("FishBase download complete.")


# --- Process ---


def load_raw_tables() -> dict[str, pd.DataFrame]:
    """Load raw parquet files into DataFrames."""
    tables = {}
    con = duckdb.connect()
    for table in TABLES:
        path = RAW_DIR / f"{table}.parquet"
        if not path.exists():
            print(f"  WARNING: {table}.parquet not found, skipping")
            continue
        tables[table] = con.execute(f"SELECT * FROM read_parquet('{path}')").fetchdf()
        print(f"  Loaded {table}: {len(tables[table]):,} rows")
    con.close()
    return tables


def clean_and_merge(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Merge FishBase tables into a single enriched species DataFrame.
    """
    species = tables["species"].copy()

    # Keep only valid species with a numeric SpecCode
    species["SpecCode"] = pd.to_numeric(species["SpecCode"], errors="coerce")
    species = species.dropna(subset=["SpecCode"])
    species["SpecCode"] = species["SpecCode"].astype(int)

    # --- Merge ecology ---
    if "ecology" in tables:
        eco = tables["ecology"].copy()
        eco["SpecCode"] = pd.to_numeric(eco["SpecCode"], errors="coerce")
        eco = eco.dropna(subset=["SpecCode"])
        eco["SpecCode"] = eco["SpecCode"].astype(int)
        # Keep relevant ecology columns
        eco_cols = ["SpecCode"]
        for col in ["Herbivory2", "FeedingType", "DietTroph", "FoodTroph"]:
            if col in eco.columns:
                eco_cols.append(col)
        eco = eco[eco_cols].drop_duplicates(subset=["SpecCode"], keep="first")
        species = species.merge(eco, on="SpecCode", how="left")

    # --- Merge common names (English + Chinese) ---
    if "comnames" in tables:
        cn = tables["comnames"].copy()
        cn["SpecCode"] = pd.to_numeric(cn["SpecCode"], errors="coerce")
        cn = cn.dropna(subset=["SpecCode"])
        cn["SpecCode"] = cn["SpecCode"].astype(int)

        # English common name (prefer ComName where Language == 'English')
        en_names = (
            cn[cn["Language"] == "English"]
            .drop_duplicates(subset=["SpecCode"], keep="first")[["SpecCode", "ComName"]]
            .rename(columns={"ComName": "commonNameEn"})
        )
        species = species.merge(en_names, on="SpecCode", how="left")

        # Chinese common name
        zh_names = (
            cn[cn["Language"] == "Mandarin Chinese"]
            .drop_duplicates(subset=["SpecCode"], keep="first")[["SpecCode", "ComName"]]
            .rename(columns={"ComName": "commonNameZh"})
        )
        species = species.merge(zh_names, on="SpecCode", how="left")

    print(f"  Merged species table: {len(species):,} rows")
    return species


def derive_water_type(row) -> str:
    """Derive water type from FishBase Fresh/Brack/Saltwater columns."""
    fresh = row.get("Fresh", -1)
    brack = row.get("Brack", -1)
    saltw = row.get("Saltwater", -1)
    if fresh == 1 and saltw == 1:
        return "Brackish"
    if fresh == 1:
        return "Freshwater"
    if saltw == 1:
        return "Saltwater"
    if brack == 1:
        return "Brackish"
    return "Unknown"


def assign_rarity(occurrence_count: int) -> str:
    """Assign rarity tier based on GBIF occurrence count."""
    for tier, threshold in RARITY_THRESHOLDS.items():
        if occurrence_count <= threshold:
            return tier
    return "Common"


RARITY_INT = {"Common": 1, "Uncommon": 2, "Rare": 3, "Legendary": 4}


def _build_stocks_coords(stocks: pd.DataFrame) -> pd.DataFrame:
    """Build SpecCode → (lat, lng, EnvTemp, Resilience) from stocks bounding boxes."""
    st = stocks.copy()
    st["SpecCode"] = pd.to_numeric(st["SpecCode"], errors="coerce")
    st = st.dropna(subset=["SpecCode"])
    st["SpecCode"] = st["SpecCode"].astype(int)

    keep = ["SpecCode", "Northernmost", "NorthSouthN", "Southermost", "NorthSouthS",
            "Westernmost", "WestEastW", "Easternmost", "WestEastE", "EnvTemp", "Resilience"]
    st = st[[c for c in keep if c in st.columns]].copy()
    st = st.dropna(subset=["Northernmost", "Southermost", "Westernmost", "Easternmost"])
    st = st.drop_duplicates(subset=["SpecCode"], keep="first")

    for c in ["Northernmost", "Southermost", "Westernmost", "Easternmost"]:
        st[c] = pd.to_numeric(st[c], errors="coerce")
    st = st.dropna(subset=["Northernmost", "Southermost", "Westernmost", "Easternmost"])

    st["lat"] = (
        (st["Northernmost"] * st["NorthSouthN"].map({"N": 1, "S": -1}).fillna(1)
         + st["Southermost"] * st["NorthSouthS"].map({"N": 1, "S": -1}).fillna(1)) / 2
    ).round(4)
    st["lng"] = (
        (st["Westernmost"] * st["WestEastW"].map({"E": 1, "W": -1}).fillna(1)
         + st["Easternmost"] * st["WestEastE"].map({"E": 1, "W": -1}).fillna(1)) / 2
    ).round(4)

    out_cols = ["SpecCode", "lat", "lng"]
    for c in ["EnvTemp", "Resilience"]:
        if c in st.columns:
            out_cols.append(c)
    return st[out_cols]


def _build_country_coords(country: pd.DataFrame) -> pd.DataFrame:
    """Build SpecCode → [(lat, lng)] from country table + country centroids."""
    country_centroids = json.loads(
        (RAW_DIR / "country_centroids.json").read_text()
    )
    cn = country.copy()
    cn["SpecCode"] = pd.to_numeric(cn["SpecCode"], errors="coerce")
    cn = cn.dropna(subset=["SpecCode"])
    cn["SpecCode"] = cn["SpecCode"].astype(int)
    cn = cn[["SpecCode", "C_Code"]].drop_duplicates()

    rows = []
    for _, r in cn.iterrows():
        cc = str(r["C_Code"]).strip()
        if cc in country_centroids:
            c = country_centroids[cc]
            rows.append({"SpecCode": r["SpecCode"], "lat": c["lat"], "lng": c["lng"]})
    return pd.DataFrame(rows)


def _build_fao_coords(faoareas: pd.DataFrame) -> pd.DataFrame:
    """Build SpecCode → [(lat, lng)] from FAO area table + FAO centroids."""
    fao_centroids = json.loads(
        (RAW_DIR / "fao_centroids.json").read_text()
    )
    fa = faoareas.copy()
    fa["SpecCode"] = pd.to_numeric(fa["SpecCode"], errors="coerce")
    fa = fa.dropna(subset=["SpecCode"])
    fa["SpecCode"] = fa["SpecCode"].astype(int)
    fa = fa[["SpecCode", "AreaCode"]].drop_duplicates()

    rows = []
    for _, r in fa.iterrows():
        ac = str(int(r["AreaCode"])) if pd.notna(r["AreaCode"]) else ""
        if ac in fao_centroids:
            c = fao_centroids[ac]
            rows.append({"SpecCode": r["SpecCode"], "lat": c["lat"], "lng": c["lng"]})
    return pd.DataFrame(rows)


def build_enriched_df(species: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Build the final DataFrame ready for tiling.
    Coordinate fallthrough: stocks bbox → country centroid → FAO area centroid.
    Species with multiple countries get one point per country.
    """
    df = species.copy()

    # --- Resolve coordinates with fallthrough ---
    stocks_coords = _build_stocks_coords(tables["stocks"])
    stocks_specs = set(stocks_coords["SpecCode"].unique())
    stocks_coords["precision"] = "exact"
    print(f"    Tier 1 (stocks bbox): {len(stocks_specs)} species")

    country_coords = _build_country_coords(tables["country"])
    # Only use country coords for species NOT in stocks
    country_coords = country_coords[~country_coords["SpecCode"].isin(stocks_specs)]
    country_specs = set(country_coords["SpecCode"].unique())
    country_coords["precision"] = "country"
    print(f"    Tier 2 (country centroid): {len(country_specs)} species")

    fao_coords = pd.DataFrame()
    if "faoareas" in tables:
        fao_coords = _build_fao_coords(tables["faoareas"])
        covered = stocks_specs | country_specs
        fao_coords = fao_coords[~fao_coords["SpecCode"].isin(covered)]
        fao_specs = set(fao_coords["SpecCode"].unique())
        fao_coords["precision"] = "fao_area"
        print(f"    Tier 3 (FAO area centroid): {len(fao_specs)} species")

    all_coords = pd.concat([stocks_coords, country_coords, fao_coords], ignore_index=True)
    all_coords = all_coords[(all_coords["lat"].between(-90, 90)) & (all_coords["lng"].between(-180, 180))]

    # Merge: one row per (SpecCode, lat, lng) — multi-country species get multiple rows
    merge_cols = ["SpecCode", "lat", "lng", "precision"]
    for c in ["EnvTemp", "Resilience"]:
        if c in all_coords.columns:
            merge_cols.append(c)
    df = df.merge(all_coords[merge_cols], on="SpecCode", how="inner")
    print(f"    Total points after merge: {len(df):,} ({df['SpecCode'].nunique():,} unique species)")

    # --- Enrich fields ---
    df["waterType"] = df.apply(derive_water_type, axis=1)
    df["name"] = df["commonNameEn"].fillna(df["Genus"] + " " + df["Species"])
    df["nameZh"] = df.get("commonNameZh", pd.Series(dtype=str))
    df["scientificName"] = df["Genus"] + " " + df["Species"]
    df["id"] = df["SpecCode"].astype(str)
    df["family"] = df.get("Family", pd.Series(dtype=str))
    df["rarity"] = 1
    df["rarityLabel"] = "Common"
    df["depth"] = df["DepthRangeDeep"].fillna(0).astype(int) if "DepthRangeDeep" in df.columns else 0

    # Photo filename (short for tiles, full URLs in detail files)
    if "PicPreferredName" in df.columns:
        df["pic"] = df["PicPreferredName"]
        df["thumb"] = df["pic"].fillna("")  # Just filename in tiles
    else:
        df["pic"] = None
        df["thumb"] = ""

    print(f"  Enriched DataFrame: {len(df):,} points, {df['SpecCode'].nunique():,} species")
    return df


def _val(row, col):
    """Return string value or None if missing."""
    v = row.get(col)
    return str(v) if pd.notna(v) and str(v).strip() else None


def generate_species_details(df: pd.DataFrame, output_dir: Path):
    """Generate per-species detail JSON files (one per unique SpecCode)."""
    species_dir = output_dir / "species"
    species_dir.mkdir(parents=True, exist_ok=True)

    # Deduplicate: one detail file per species, prefer "exact" precision row
    precision_order = {"exact": 0, "country": 1, "fao_area": 2}
    df_sorted = df.copy()
    df_sorted["_prec_rank"] = df_sorted["precision"].map(precision_order).fillna(3)
    detail_df = df_sorted.sort_values("_prec_rank").drop_duplicates(subset=["id"], keep="first")

    count = 0
    for _, row in detail_df.iterrows():
        detail = {
            "id": row["id"],
            "name": row["name"],
            "nameZh": row.get("nameZh", None) if pd.notna(row.get("nameZh")) else None,
            "scientificName": row["scientificName"],
            "family": row.get("family") if pd.notna(row.get("family")) else None,
            "description": None,  # To be filled by LLM or Wikipedia later
            "descriptionZh": None,
            "metadata": {
                "maxLength": f"{int(row['Length'])} cm" if pd.notna(row.get("Length")) else None,
                "maxWeight": f"{row['Weight']:.1f} kg" if pd.notna(row.get("Weight")) else None,
                "lifespan": f"{row['LongevityWild']:.0f} years" if pd.notna(row.get("LongevityWild")) else None,
                "habitat": row["waterType"],
                "depth": f"0-{row['depth']} m" if row["depth"] > 0 else None,
                "diet": _val(row, "FeedingType"),
                "rarity": row["rarityLabel"],
                "dangerous": _val(row, "Dangerous"),
                "gameFish": bool(int(row["GameFish"])) if pd.notna(row.get("GameFish")) and str(row["GameFish"]).strip() in ("0","1") else None,
                "aquarium": _val(row, "Aquarium"),
                "priceCategory": _val(row, "PriceCateg"),
                "vulnerability": round(float(row["Vulnerability"]), 1) if pd.notna(row.get("Vulnerability")) else None,
                "trophicLevel": round(float(row["DietTroph"]), 2) if pd.notna(row.get("DietTroph")) else None,
                "herbivory": _val(row, "Herbivory2"),
                "envTemp": _val(row, "EnvTemp"),
                "resilience": _val(row, "Resilience"),
            },
            "images": [],
            "links": [
                {"label": "FishBase", "url": f"https://www.fishbase.se/summary/{row['id']}"},
            ],
        }

        # Add image URLs if PicPreferredName exists
        pic = row.get("pic")
        if pd.notna(pic) and pic:
            detail["images"] = [
                {"thumbnail": f"https://www.fishbase.se/images/thumbnails/jpg/tn_{pic}",
                 "image": f"https://www.fishbase.se/images/species/{pic}"},
            ]
            detail["links"].append(
                {"label": "Photos", "url": f"https://www.fishbase.se/photos/thumbnailssummary.php?ID={row['id']}"}
            )

        detail["attribution"] = "FishBase (CC-BY-NC)"

        # Strip None values from metadata
        detail["metadata"] = {k: v for k, v in detail["metadata"].items() if v is not None}

        out_path = species_dir / f"{row['id']}.json"
        out_path.write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")
        count += 1

    print(f"  Generated {count:,} species detail files")


def generate_index(df: pd.DataFrame, output_dir: Path):
    """Generate the master index.json."""
    depth_max = int(df["depth"].max()) if df["depth"].max() > 0 else 8000

    index = {
        "globeId": "fish",
        "version": "1.0.0",
        "totalItems": len(df),
        "lastUpdated": date.today().isoformat(),
        "tileZoomRange": [0, 7],
        "filters": [
            {
                "key": "waterType",
                "label": "Water Type",
                "type": "chips",
                "options": sorted(df["waterType"].unique().tolist()),
            },
            {
                "key": "depth",
                "label": "Depth",
                "type": "range",
                "min": 0,
                "max": depth_max,
                "unit": "m",
            },
            {
                "key": "rarity",
                "label": "Rarity",
                "type": "chips",
                "options": ["Common", "Uncommon", "Rare", "Legendary"],
            },
            {
                "key": "dangerous",
                "label": "Danger",
                "type": "chips",
                "options": sorted(df["Dangerous"].dropna().unique().tolist()) if "Dangerous" in df.columns else [],
            },
            {
                "key": "envTemp",
                "label": "Climate",
                "type": "chips",
                "options": sorted(df["EnvTemp"].dropna().unique().tolist()) if "EnvTemp" in df.columns else [],
            },
            {
                "key": "resilience",
                "label": "Resilience",
                "type": "chips",
                "options": ["High", "Medium", "Low", "Very low"],
            },
            {
                "key": "vulnerability",
                "label": "Vulnerability",
                "type": "range",
                "min": 0,
                "max": 100,
                "unit": "",
            },
        ],
        "attribution": [
            {"name": "FishBase", "license": "CC-BY-NC 4.0", "url": "https://www.fishbase.se"},
            {"name": "GBIF", "license": "CC0/CC-BY 4.0", "url": "https://www.gbif.org"},
        ],
    }

    out_path = output_dir / "index.json"
    out_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Generated index.json ({len(df):,} total items)")


# --- Main ---


def run_download():
    print("\n=== Step 1: Download FishBase data ===")
    download_fishbase()


def run_process():
    print("\n=== Step 2: Load raw tables ===")
    tables = load_raw_tables()
    if "species" not in tables:
        print("ERROR: species.parquet is required. Run with --download first.")
        sys.exit(1)

    print("\n=== Step 3: Clean and merge ===")
    species = clean_and_merge(tables)

    print("\n=== Step 4: Build enriched DataFrame ===")
    if "stocks" not in tables:
        print("ERROR: stocks.parquet is required. Run with --download first.")
        sys.exit(1)
    df = build_enriched_df(species, tables)

    print("\n=== Step 5: Generate tiles ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stats = split_tiles(
        df=df,
        output_dir=OUTPUT_DIR,
        filter_agg_keys=["waterType"],
        top_items_fields=["id", "name", "thumb"],
        point_fields=["id", "name", "nameZh", "thumb", "rarity", "waterType", "precision"],
    )

    print("\n=== Step 6: Generate species detail files ===")
    generate_species_details(df, OUTPUT_DIR)

    print("\n=== Step 7: Generate index.json ===")
    generate_index(df, OUTPUT_DIR)

    print(f"\n=== Done! Output in {OUTPUT_DIR} ===")
    print(f"  Tile stats: {stats}")


def main():
    parser = argparse.ArgumentParser(description="Fish Globe ETL pipeline")
    parser.add_argument("--download", action="store_true", help="Download raw data only")
    parser.add_argument("--process", action="store_true", help="Process existing raw data only")
    args = parser.parse_args()

    if args.download:
        run_download()
    elif args.process:
        run_process()
    else:
        run_download()
        run_process()


if __name__ == "__main__":
    main()
