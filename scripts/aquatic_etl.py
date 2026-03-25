# scripts/aquatic_etl.py
"""Aquatic globe ETL — downloads OBIS/GBIF occurrences and FishBase metadata.

This script generates INTERMEDIATE data (crosswalk, enriched metadata) that is
consumed by scripts/merge_curated.py, NOT final output. The aquatic globe uses
a curated 200-species model; see curation/aquatic/selected.json and
scripts/merge_curated.py for the final pipeline.
"""
import os
import sys
import json
import argparse
import time
import zipfile
from pathlib import Path

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


def run_process():
    """Build intermediate crosswalk + metadata from raw downloads.

    This does NOT produce final output. Run scripts/merge_curated.py after
    this to merge curation data with the crosswalk into output/aquatic/final.json.
    """
    print("=== Aquatic ETL: Processing (intermediate data for merge_curated.py) ===")

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

    # 7. Save crosswalk (consumed by merge_curated.py)
    print("Saving ID crosswalk...")
    crosswalk = build_id_crosswalk(enriched)
    crosswalk_path = RAW_DIR / "id_crosswalk.json"
    crosswalk_path.write_text(json.dumps(crosswalk, ensure_ascii=False, indent=2))

    print(f"  Crosswalk: {len(crosswalk)} species")
    print("=== Done — run 'python -m scripts.merge_curated' to produce final output ===")


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
