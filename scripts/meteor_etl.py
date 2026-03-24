"""Meteor Globe ETL — NASA Meteorite Landings."""

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from tile_splitter import split_tiles

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "meteor"
OUTPUT_DIR = ROOT / "output" / "meteor"
URL = "https://data.nasa.gov/docs/legacy/meteorite_landings/Meteorite_Landings.csv"


def download():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "meteorites.csv"
    if out.exists():
        print("  meteorites.csv already exists, skipping")
        return
    print("  Downloading NASA Meteorite Landings...")
    r = requests.get(URL, timeout=60)
    r.raise_for_status()
    out.write_bytes(r.content)
    lines = r.text.count("\n")
    print(f"    -> {lines} rows ({len(r.content) / 1024 / 1024:.1f} MB)")


def process():
    df = pd.read_csv(RAW_DIR / "meteorites.csv")
    print(f"  Raw: {len(df)} meteorites")

    df["lat"] = pd.to_numeric(df["reclat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["reclong"], errors="coerce")
    df = df.dropna(subset=["lat", "lng"])
    df = df[(df["lat"] != 0) | (df["lng"] != 0)]  # drop (0,0) entries

    df["id"] = df["id"].astype(int).astype(str)
    df["mass"] = pd.to_numeric(df["mass (g)"], errors="coerce")
    df["year"] = pd.to_datetime(df["year"], errors="coerce").dt.year
    df["name"] = df["name"]
    df["fall"] = df["fall"]  # "Fell" or "Found"
    df["recclass"] = df["recclass"]
    df["thumb"] = ""

    # Mass category for filtering
    df["massRange"] = pd.cut(
        df["mass"].fillna(0),
        bins=[0, 100, 1000, 10000, 100000, float("inf")],
        labels=["<100g", "100g-1kg", "1-10kg", "10-100kg", ">100kg"],
    )
    print(f"  With coordinates: {len(df)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    split_tiles(
        df=df, output_dir=OUTPUT_DIR,
        filter_agg_keys=["fall", "massRange"],
        top_items_fields=["id", "name", "thumb"],
        point_fields=["id", "name", "fall", "recclass", "massRange"],
    )

    # Detail files
    species_dir = OUTPUT_DIR / "species"
    species_dir.mkdir(exist_ok=True)
    for _, row in df.iterrows():
        mass_str = f"{row['mass']:.0f} g" if pd.notna(row["mass"]) else None
        detail = {
            "id": row["id"], "name": row["name"], "scientificName": row["recclass"],
            "metadata": {"mass": mass_str, "year": int(row["year"]) if pd.notna(row["year"]) else None,
                         "class": row["recclass"], "fall": row["fall"]},
            "images": [], "links": [{"label": "Meteoritical Bulletin",
                                     "url": f"https://www.lpi.usra.edu/meteor/metbull.php?sea={row['name']}"}],
            "attribution": "NASA Open Data Portal (Public Domain)",
        }
        detail["metadata"] = {k: v for k, v in detail["metadata"].items() if v is not None}
        (species_dir / f"{row['id']}.json").write_text(json.dumps(detail, ensure_ascii=False))

    # Index
    index = {
        "globeId": "meteor", "version": "1.0.0", "totalItems": len(df),
        "lastUpdated": date.today().isoformat(), "tileZoomRange": [0, 7],
        "filters": [
            {"key": "fall", "label": "Discovery", "type": "chips", "options": ["Fell", "Found"]},
            {"key": "massRange", "label": "Mass", "type": "chips",
             "options": ["<100g", "100g-1kg", "1-10kg", "10-100kg", ">100kg"]},
        ],
        "attribution": [{"name": "NASA", "license": "Public Domain", "url": "https://data.nasa.gov"}],
    }
    (OUTPUT_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    print(f"  Done: {len(df)} meteorites, index + details written")


if __name__ == "__main__":
    print("\n=== Meteor ETL ===")
    download()
    process()
