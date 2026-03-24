# scripts/aquatic_etl.py
"""Aquatic globe ETL — OBIS + GBIF occurrences, FishBase metadata, sprite integration."""
import os
import subprocess
import sys
import json
import argparse
import time
import zipfile
from pathlib import Path
from datetime import date

import requests

import pandas as pd
import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "aquatic"
OUTPUT_DIR = ROOT / "output" / "aquatic"

# OBIS S3 bucket (public, no auth needed)
OBIS_S3_PATH = "s3://obis-products/exports/obis_20230726.parquet"


def download_obis():
    """Query OBIS parquet on S3 via DuckDB, pre-deduplicate to one point per species per z7 tile."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "obis_occurrences.parquet"
    if out.exists():
        print(f"  OBIS data already exists at {out}, skipping")
        return
    print("Querying OBIS from S3 (filter + deduplicate to z7 tiles in SQL)...")
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET s3_region='us-east-1'")
    # Pre-aggregate: one point per species per z7 tile — much faster than pandas groupby
    # z7 tile has 128 tiles on each axis, each ~1.4° lat × 2.8° lng
    con.execute(f"""
        COPY (
            SELECT
                aphia_id,
                ROUND(AVG(lat), 4) as lat,
                ROUND(AVG(lng), 4) as lng,
                FIRST(scientific_name) as scientific_name,
                FIRST(class) as class,
                FIRST("order") as "order",
                FIRST(family) as family,
                FIRST(phylum) as phylum
            FROM (
                SELECT
                    AphiaID as aphia_id,
                    decimalLatitude as lat,
                    decimalLongitude as lng,
                    scientificName as scientific_name,
                    class,
                    "order",
                    family,
                    phylum,
                    -- z7 tile assignment in SQL
                    FLOOR((lng + 180.0) / 360.0 * 128) AS tile_x,
                    FLOOR((1.0 - LN(TAN(RADIANS(LEAST(GREATEST(lat, -85), 85))) +
                           1.0 / COS(RADIANS(LEAST(GREATEST(lat, -85), 85)))) / PI()) / 2.0 * 128) AS tile_y
                FROM read_parquet('{OBIS_S3_PATH}')
                WHERE decimalLatitude IS NOT NULL
                  AND decimalLongitude IS NOT NULL
                  AND AphiaID IS NOT NULL
                  AND (coordinateUncertaintyInMeters < 50000 OR coordinateUncertaintyInMeters IS NULL)
                  AND dropped = false
                  AND absence = false
            ) filtered
            GROUP BY aphia_id, tile_x, tile_y
        ) TO '{out}' (FORMAT 'parquet', COMPRESSION 'zstd')
    """)
    row_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{out}')").fetchone()[0]
    species_count = con.execute(f"SELECT COUNT(DISTINCT aphia_id) FROM read_parquet('{out}')").fetchone()[0]
    print(f"  OBIS data saved to {out} ({row_count:,} points, {species_count:,} species)")


GBIF_API = "https://api.gbif.org/v1"
# Aquatic phyla/classes to include
GBIF_TAXON_KEYS = [
    44,    # Chordata (fish, mammals, reptiles)
    52,    # Mollusca
    54,    # Arthropoda (crustaceans)
    43,    # Cnidaria
    48,    # Echinodermata
    105,   # Porifera
]


def download_gbif():
    """Download GBIF occurrences via async download API. One POST + one GET."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "gbif_occurrences.csv"
    if out.exists():
        print(f"  GBIF data already exists at {out}, skipping")
        return

    # Check for existing download key
    key_file = RAW_DIR / "gbif_download_key.txt"
    if key_file.exists():
        download_key = key_file.read_text().strip()
        print(f"  Resuming GBIF download {download_key}")
    else:
        # Submit download request
        # NOTE: Requires GBIF account credentials in env vars GBIF_USER / GBIF_PWD
        user = os.environ.get("GBIF_USER", "")
        pwd = os.environ.get("GBIF_PWD", "")
        if not user or not pwd:
            print("ERROR: Set GBIF_USER and GBIF_PWD environment variables")
            print("Register at https://www.gbif.org/user/profile")
            sys.exit(1)

        payload = {
            "creator": user,
            "notification_address": [],
            "format": "SIMPLE_CSV",
            "predicate": {
                "type": "and",
                "predicates": [
                    {"type": "equals", "key": "HAS_COORDINATE", "value": "true"},
                    {"type": "equals", "key": "HAS_GEOSPATIAL_ISSUE", "value": "false"},
                    {"type": "in", "key": "TAXON_KEY", "values": [str(k) for k in GBIF_TAXON_KEYS]},
                    {"type": "equals", "key": "OCCURRENCE_STATUS", "value": "PRESENT"},
                ]
            }
        }
        resp = requests.post(
            f"{GBIF_API}/occurrence/download/request",
            json=payload,
            auth=(user, pwd),
            timeout=60,
        )
        resp.raise_for_status()
        download_key = resp.text
        key_file.write_text(download_key)
        print(f"  GBIF download submitted: {download_key}")

    # Poll until ready
    while True:
        resp = requests.get(f"{GBIF_API}/occurrence/download/{download_key}", timeout=30)
        status = resp.json().get("status", "")
        if status == "SUCCEEDED":
            break
        elif status in ("FAILED", "CANCELLED", "KILLED"):
            print(f"ERROR: GBIF download {status}")
            sys.exit(1)
        print(f"  GBIF download status: {status}, waiting 30s...")
        time.sleep(30)

    # Download ZIP
    zip_path = RAW_DIR / "gbif_download.zip"
    print("  Downloading GBIF ZIP...")
    resp = requests.get(
        f"{GBIF_API}/occurrence/download/request/{download_key}",
        stream=True, timeout=600,
    )
    with open(zip_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    # Extract CSV
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = [n for n in zf.namelist() if n.endswith(".csv")][0]
        with zf.open(csv_name) as src, open(out, "wb") as dst:
            dst.write(src.read())
    zip_path.unlink()
    key_file.unlink()
    print(f"  GBIF data saved to {out}")


# ---------------------------------------------------------------------------
# Task 4: Taxonomic Normalization & ID Crosswalk
# ---------------------------------------------------------------------------

import math
import numpy as np

from scripts.tile_splitter import lat_lng_to_tile


def _vectorized_tile_xy(lat: pd.Series, lng: pd.Series, zoom: int):
    """Compute tile (x, y) for arrays of lat/lng at a given zoom level.

    Equivalent to calling lat_lng_to_tile per-row but ~100x faster on large
    DataFrames because it operates on whole numpy arrays.
    """
    n = 2 ** zoom
    x = ((lng.to_numpy() + 180.0) / 360.0 * n).astype(int)
    lat_rad = np.radians(lat.to_numpy())
    y = ((1.0 - np.arcsinh(np.tan(lat_rad)) / np.pi) / 2.0 * n).astype(int)
    x = np.clip(x, 0, n - 1)
    y = np.clip(y, 0, n - 1)
    return x, y


def merge_occurrences(obis_df: pd.DataFrame, gbif_df: pd.DataFrame) -> pd.DataFrame:
    """Merge OBIS + GBIF occurrences, deduplicate to one point per species per z7 tile."""
    # Standardize columns
    combined = pd.concat([obis_df, gbif_df], ignore_index=True)

    # Quality filters
    combined = combined.dropna(subset=["lat", "lng", "aphia_id"])
    combined = combined[
        (combined["lat"].between(-90, 90)) &
        (combined["lng"].between(-180, 180))
    ]

    if combined.empty:
        return combined

    # Ensure numeric dtypes (concat with empty DF can produce object dtype)
    combined["lat"] = pd.to_numeric(combined["lat"], errors="coerce")
    combined["lng"] = pd.to_numeric(combined["lng"], errors="coerce")
    combined["aphia_id"] = pd.to_numeric(combined["aphia_id"], errors="coerce")
    combined = combined.dropna(subset=["lat", "lng", "aphia_id"])

    if combined.empty:
        return combined

    # Assign z7 tile for deduplication (vectorized)
    tile_x, tile_y = _vectorized_tile_xy(combined["lat"], combined["lng"], zoom=7)
    combined = combined.copy()
    combined["_tile_x"] = tile_x
    combined["_tile_y"] = tile_y

    # Deduplicate: one point per species per z7 tile (centroid)
    grouped = combined.groupby(["aphia_id", "_tile_x", "_tile_y"])
    deduped = grouped.agg({
        "lat": "mean",
        "lng": "mean",
        "scientific_name": "first",
        "class": "first",
        "order": "first",
        "family": "first",
        "phylum": "first",
    }).reset_index()

    deduped = deduped.drop(columns=["_tile_x", "_tile_y"])
    deduped["lat"] = deduped["lat"].round(4)
    deduped["lng"] = deduped["lng"].round(4)
    return deduped


def build_id_crosswalk(df: pd.DataFrame) -> dict:
    """Build aphiaId -> metadata crosswalk from merged DataFrame."""
    crosswalk = {}
    for _, row in df.drop_duplicates(subset=["aphia_id"]).iterrows():
        aid = int(row["aphia_id"])
        crosswalk[aid] = {
            "scientificName": row.get("scientific_name", ""),
            "gbifKey": row.get("gbif_taxon_key"),
            "fishbaseSpecCode": row.get("fishbase_spec_code"),
        }
    return crosswalk


# ---------------------------------------------------------------------------
# Task 5: FishBase Metadata Enrichment
# ---------------------------------------------------------------------------


def _derive_water_type(row) -> str:
    """Classify water type from FishBase Fresh/Brack/Saltwater columns."""
    parts = []
    if row.get("Fresh") == 1:
        parts.append("Freshwater")
    if row.get("Brack") == 1:
        parts.append("Brackish")
    if row.get("Saltwater") == 1:
        parts.append("Saltwater")
    if not parts:
        return "Unknown"
    if len(parts) == 1:
        return parts[0]
    if "Brackish" in parts:
        return "Brackish"
    return parts[0]


def _load_chinese_names() -> pd.DataFrame:
    """Load Mandarin Chinese common names from FishBase comnames, decode HTML entities."""
    import html as html_mod
    import re
    path = ROOT / "data" / "raw" / "fishbase" / "comnames.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["fishbase_spec_code", "name_zh"])
    cn = pd.read_parquet(path)
    cn = cn[cn["Language"] == "Mandarin Chinese"].copy()
    cn["decoded"] = cn["ComName"].apply(lambda x: html_mod.unescape(str(x)) if pd.notna(x) else "")
    # Keep only entries with actual CJK characters
    cn["has_cjk"] = cn["decoded"].apply(lambda x: bool(re.search(r"[\u4e00-\u9fff]", x)))
    cn = cn[cn["has_cjk"]]
    cn["fishbase_spec_code"] = pd.to_numeric(cn["SpecCode"], errors="coerce")
    cn = cn.dropna(subset=["fishbase_spec_code"])
    cn["fishbase_spec_code"] = cn["fishbase_spec_code"].astype(int)
    cn = cn.drop_duplicates(subset=["fishbase_spec_code"], keep="first")
    return cn[["fishbase_spec_code", "decoded"]].rename(columns={"decoded": "name_zh"})


def enrich_with_fishbase(occurrences: pd.DataFrame, fishbase_species: pd.DataFrame) -> pd.DataFrame:
    """Left-join FishBase metadata onto occurrences by scientific name."""
    fb = fishbase_species.copy()

    # Build scientific_name from Genus + Species if those columns exist,
    # otherwise assume scientific_name is already present
    if "Genus" in fb.columns and "Species" in fb.columns:
        fb["scientific_name"] = fb["Genus"].fillna("") + " " + fb["Species"].fillna("")
        fb["scientific_name"] = fb["scientific_name"].str.strip()

    fb = fb.rename(columns={
        "FBname": "common_name",
        "SpecCode": "fishbase_spec_code",
        "Vulnerability": "vulnerability",
        "DepthRangeDeep": "depth_max",
        "Length": "max_length_cm",
        "Weight": "max_weight_kg",
    })
    fb["thumb"] = fb["PicPreferredName"].apply(
        lambda x: f"tn_{x}" if pd.notna(x) else None
    )
    fb["water_type"] = fb.apply(_derive_water_type, axis=1)

    keep_cols = ["scientific_name", "common_name", "fishbase_spec_code", "thumb",
                 "vulnerability", "depth_max", "water_type", "max_length_cm", "max_weight_kg"]
    fb = fb[keep_cols].drop_duplicates(subset=["scientific_name"], keep="first")

    result = occurrences.merge(fb, on="scientific_name", how="left")
    # Fill common name from scientific name if no FishBase match
    result["common_name"] = result["common_name"].fillna(result["scientific_name"])

    # Chinese names
    zh_names = _load_chinese_names()
    if len(zh_names) > 0:
        result["fishbase_spec_code"] = pd.to_numeric(result["fishbase_spec_code"], errors="coerce")
        result = result.merge(zh_names, on="fishbase_spec_code", how="left")
        zh_count = result["name_zh"].notna().sum()
        print(f"  Chinese names matched: {zh_count:,} points ({result['name_zh'].notna().mean()*100:.0f}%)")
    else:
        result["name_zh"] = None

    return result


# ---------------------------------------------------------------------------
# Task 6: Group Classification Integration
# ---------------------------------------------------------------------------

from scripts.aquatic_groups import classify_group, classify_body_type, classify_body_group
from scripts.tile_splitter import split_tiles
from scripts.build_sprite_manifest import resolve_sprite, build_sprite_indices


def apply_classifications(df: pd.DataFrame) -> pd.DataFrame:
    """Add group, body_type, body_group columns based on taxonomy."""
    df = df.copy()
    df["group"] = df.apply(
        lambda r: classify_group(
            class_name=r.get("class", ""),
            order=r.get("order", ""),
            family=r.get("family", ""),
            phylum=r.get("phylum", ""),
        ), axis=1
    )
    df["body_type"] = df["group"].apply(classify_body_type)
    df["body_group"] = df["group"].apply(classify_body_group)
    return df


# ---------------------------------------------------------------------------
# Task 10: Tile + Species + Index Generation
# ---------------------------------------------------------------------------


def resolve_sprites_on_df(df: pd.DataFrame, manifest: dict) -> pd.DataFrame:
    """Add pre-resolved sprite filename to every row using vectorized lookups."""
    df = df.copy()
    idx = build_sprite_indices(manifest)

    # 1. Try exact scientific name match
    sci_col = df["scientific_name"].str.strip().str.lower() if "scientific_name" in df.columns else pd.Series("", index=df.index)
    df["sprite"] = sci_col.map(idx["sci_name"])

    # 2. Try genus-level match for unresolved
    missing = df["sprite"].isna()
    if missing.any():
        genus = sci_col[missing].str.split().str[0]
        df.loc[missing, "sprite"] = genus.map(idx["sci_name"])

    # 3. Group fallback for remaining
    missing = df["sprite"].isna()
    if missing.any():
        group_col = df.loc[missing, "group"] if "group" in df.columns else pd.Series("other", index=df.loc[missing].index)
        df.loc[missing, "sprite"] = group_col.map(idx["group"])

    # 4. Body type fallback for remaining
    missing = df["sprite"].isna()
    if missing.any():
        bt_col = df.loc[missing, "body_type"] if "body_type" in df.columns else pd.Series("fusiform", index=df.loc[missing].index)
        df.loc[missing, "sprite"] = bt_col.map(idx["body_type"])

    # 5. Ultimate fallback
    df["sprite"] = df["sprite"].fillna(idx["default"])

    resolved_exact = (~sci_col.map(idx["sci_name"]).isna()).sum()
    print(f"  Sprite resolution: {resolved_exact} exact, {len(df) - df['sprite'].isna().sum()} total resolved out of {len(df)}")
    return df


def generate_species_details(df: pd.DataFrame, output_dir: Path):
    """Generate one JSON detail file per unique species."""
    species_dir = output_dir / "species"
    species_dir.mkdir(parents=True, exist_ok=True)

    detail_df = df.drop_duplicates(subset=["id"], keep="first")
    count = 0
    for _, row in detail_df.iterrows():
        name_zh = row.get("name_zh")
        if pd.isna(name_zh):
            name_zh = None

        detail = {
            "id": str(row["id"]),
            "name": row.get("name") or row.get("scientific_name", ""),
            "nameZh": name_zh,
            "scientificName": row.get("scientific_name", ""),
            "family": row.get("family"),
            "description": row.get("description"),
            "descriptionZh": row.get("description_zh"),
            "sprite": row.get("sprite"),
            "group": row.get("group"),
            "bodyType": row.get("body_type"),
            "bodyGroup": row.get("body_group"),
            "metadata": {
                "habitat": row.get("water_type"),
                "depth": f"0-{int(row['depth_max'])} m" if pd.notna(row.get("depth_max")) else None,
                "maxLength": f"{int(row['max_length_cm'])} cm" if pd.notna(row.get("max_length_cm")) else None,
                "maxWeight": f"{row['max_weight_kg']:.1f} kg" if pd.notna(row.get("max_weight_kg")) else None,
                "rarity": {1: "Common", 2: "Uncommon", 3: "Rare", 4: "Legendary"}.get(row.get("rarity")),
                "vulnerability": row.get("vulnerability"),
            },
            "images": [],
            "links": [],
            "attribution": "OBIS, GBIF, FishBase (CC-BY-NC)",
        }
        # Add FishBase image if available
        thumb = row.get("thumb")
        if pd.notna(thumb) and thumb:
            pic_name = thumb.replace("tn_", "")
            detail["images"].append({
                "thumbnail": f"https://www.fishbase.se/images/thumbnails/jpg/{thumb}",
                "image": f"https://www.fishbase.se/images/species/{pic_name}",
            })

        # Strip None values from metadata
        detail["metadata"] = {k: v for k, v in detail["metadata"].items() if v is not None}

        out_path = species_dir / f"{row['id']}.json"
        out_path.write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")
        count += 1

    print(f"  Generated {count} species detail files")


def generate_index(df: pd.DataFrame, output_dir: Path):
    """Generate index.json for the aquatic globe."""
    index = {
        "globeId": "aquatic",
        "version": "1.0.0",
        "totalItems": len(df),
        "lastUpdated": date.today().isoformat(),
        "tileZoomRange": [0, 7],
        "filters": [
            {
                "key": "waterType",
                "label": "Water Type",
                "type": "chips",
                "options": sorted(df["water_type"].dropna().unique().tolist()),
            },
            {
                "key": "bodyGroup",
                "label": "Animal Type",
                "type": "chips",
                "options": sorted(df["body_group"].dropna().unique().tolist()),
            },
            {
                "key": "rarity",
                "label": "Rarity",
                "type": "chips",
                "options": ["Common", "Uncommon", "Rare", "Legendary"],
            },
        ],
        "attribution": [
            {"name": "OBIS", "license": "CC-BY 4.0", "url": "https://obis.org"},
            {"name": "GBIF", "license": "CC0/CC-BY 4.0", "url": "https://www.gbif.org"},
            {"name": "FishBase", "license": "CC-BY-NC 4.0", "url": "https://www.fishbase.se"},
        ],
    }
    out = output_dir / "index.json"
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Index written: {index['totalItems']} total items")


def run_process():
    """Run the full processing pipeline (assumes downloads are done)."""
    print("=== Aquatic ETL: Processing ===")

    # 1. Load OBIS (already filtered + deduped to z7 tiles by download_obis)
    print("Loading OBIS data...")
    obis_path = RAW_DIR / "obis_occurrences.parquet"
    con = duckdb.connect()
    obis_df = con.execute(f"SELECT * FROM read_parquet('{obis_path}')").df()
    print(f"  OBIS: {len(obis_df):,} points")

    # 2. Load GBIF (optional — may not be ready yet)
    gbif_path = RAW_DIR / "gbif_occurrences.csv"
    if gbif_path.exists():
        print("Loading GBIF data...")
        gbif_raw = pd.read_csv(gbif_path, sep="\t", usecols=[
            "decimalLatitude", "decimalLongitude", "speciesKey",
            "species", "class", "order", "family", "phylum",
        ], low_memory=False)
        gbif_df = gbif_raw.rename(columns={
            "decimalLatitude": "lat",
            "decimalLongitude": "lng",
            "speciesKey": "gbif_taxon_key",
            "species": "scientific_name",
        })
        # Map GBIF species to AphiaID via scientific name join with OBIS
        obis_name_to_aphia = obis_df.drop_duplicates(subset=["scientific_name"])[
            ["scientific_name", "aphia_id"]
        ]
        gbif_df = gbif_df.merge(obis_name_to_aphia, on="scientific_name", how="left")
        # For species not in OBIS, use "gbif-{taxonKey}" as fallback ID
        mask = gbif_df["aphia_id"].isna()
        gbif_df.loc[mask, "aphia_id"] = gbif_df.loc[mask, "gbif_taxon_key"].apply(
            lambda k: f"gbif-{int(k)}" if pd.notna(k) else None
        )
        gbif_df = gbif_df.dropna(subset=["aphia_id"])
        print(f"  GBIF: {len(gbif_df)} records (after AphiaID mapping)")
    else:
        print("  GBIF data not yet available, proceeding with OBIS only")
        gbif_df = pd.DataFrame(columns=obis_df.columns)

    # 3. Merge (OBIS is already deduped; just concat GBIF if present)
    print("Merging OBIS + GBIF...")
    if len(gbif_df) > 0:
        merged = merge_occurrences(obis_df, gbif_df)
    else:
        merged = obis_df.copy()
    print(f"  Merged: {len(merged):,} unique points")

    # 4. Load FishBase metadata
    print("Loading FishBase metadata...")
    fishbase_species = duckdb.sql(f"""
        SELECT * FROM read_parquet('{ROOT}/data/raw/fishbase/species.parquet')
    """).df()

    # 5. Enrich
    print("Enriching with FishBase metadata...")
    enriched = enrich_with_fishbase(merged, fishbase_species)

    # 6. Classify
    print("Applying taxonomy classifications...")
    enriched = apply_classifications(enriched)

    # 7. Prepare DataFrame for tiling — rename to camelCase for output JSON
    enriched["id"] = enriched["aphia_id"].astype(str)
    enriched["name"] = enriched["common_name"]
    enriched["nameZh"] = enriched.get("name_zh")
    enriched["waterType"] = enriched.get("water_type", "Unknown")
    enriched["bodyGroup"] = enriched["body_group"]
    enriched["bodyType"] = enriched["body_type"]
    enriched["rarity"] = enriched.get("rarity", 1)  # default Common
    # Size in cm (numeric, for sorting cluster representatives)
    enriched["size"] = pd.to_numeric(enriched.get("max_length_cm"), errors="coerce").fillna(0).astype(int)

    # 8. Load sprite manifest and resolve sprites
    print("Resolving sprites...")
    manifest_path = OUTPUT_DIR / "sprites" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        enriched = resolve_sprites_on_df(enriched, manifest)
    else:
        print("  WARNING: No sprite manifest found, using sp-atlantic_cod.png for all")
        enriched["sprite"] = "sp-atlantic_cod.png"

    # 9. Generate tiles
    print("Generating tiles...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tile_stats = split_tiles(
        enriched,
        OUTPUT_DIR,
        filter_agg_keys=["waterType", "bodyGroup"],
        top_items_fields=["id", "name", "nameZh", "thumb", "sprite", "group", "size"],
        point_fields=["id", "lat", "lng", "name", "nameZh", "thumb", "sprite",
                       "group", "rarity", "waterType", "size", "precision"],
        group_distribution_key="group",
    )
    print(f"  Tiles: {tile_stats}")

    # 10. Generate species details
    print("Generating species details...")
    generate_species_details(enriched, OUTPUT_DIR)

    # 11. Generate index
    print("Generating index...")
    generate_index(enriched, OUTPUT_DIR)

    # 12. Save crosswalk
    print("Saving ID crosswalk...")
    crosswalk = build_id_crosswalk(enriched)
    crosswalk_path = RAW_DIR / "id_crosswalk.json"
    crosswalk_path.write_text(json.dumps(crosswalk, ensure_ascii=False, indent=2))

    print("=== Done ===")


def main():
    parser = argparse.ArgumentParser(description="Aquatic globe ETL")
    parser.add_argument("--download", action="store_true", help="Download only")
    parser.add_argument("--process", action="store_true", help="Process only")
    args = parser.parse_args()

    if args.download:
        download_obis()
        download_gbif()
    elif args.process:
        run_process()
    else:
        download_obis()
        download_gbif()
        run_process()


if __name__ == "__main__":
    main()
