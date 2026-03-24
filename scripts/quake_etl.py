"""Quake Globe ETL — USGS M6+ earthquakes since 1900."""

import json
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from tile_splitter import split_tiles

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "quake"
OUTPUT_DIR = ROOT / "output" / "quake"
URL = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=1900-01-01&minmagnitude=6"


def download():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "quakes.geojson"
    if out.exists():
        print("  quakes.geojson already exists, skipping")
        return
    print("  Downloading USGS M6+ earthquakes...")
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    out.write_bytes(r.content)
    feats = r.json()["features"]
    print(f"    -> {len(feats)} earthquakes ({len(r.content) / 1024 / 1024:.1f} MB)")


def process():
    data = json.loads((RAW_DIR / "quakes.geojson").read_text())
    rows = []
    for f in data["features"]:
        p = f["properties"]
        coords = f["geometry"]["coordinates"]
        ts = p.get("time")
        dt = datetime.fromtimestamp(ts / 1000, tz=None).strftime("%Y-%m-%d") if ts else None
        depth = coords[2] if len(coords) > 2 and coords[2] is not None else 0
        rows.append({
            "id": f.get("id", ""),
            "lat": coords[1],
            "lng": coords[0],
            "depth": round(depth, 1),
            "mag": round(p.get("mag", 0), 1),
            "name": p.get("place", "Unknown"),
            "date": dt,
            "tsunami": bool(p.get("tsunami")),
            "thumb": "",
        })

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["lat", "lng"])

    # Magnitude bucket for filtering
    df["magRange"] = pd.cut(df["mag"], bins=[0, 6.5, 7, 7.5, 8, 10],
                            labels=["6.0-6.4", "6.5-6.9", "7.0-7.4", "7.5-7.9", "8.0+"])
    print(f"  Loaded {len(df)} earthquakes")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    split_tiles(
        df=df, output_dir=OUTPUT_DIR,
        filter_agg_keys=["magRange"],
        top_items_fields=["id", "name", "thumb"],
        point_fields=["id", "name", "mag", "depth", "date", "magRange"],
    )

    # Detail files
    species_dir = OUTPUT_DIR / "species"
    species_dir.mkdir(exist_ok=True)
    for _, row in df.iterrows():
        detail = {
            "id": row["id"], "name": row["name"], "scientificName": f"M{row['mag']}",
            "metadata": {"magnitude": row["mag"], "depth": f"{row['depth']} km",
                         "date": row["date"], "tsunami": "Yes" if row["tsunami"] else "No"},
            "images": [],
            "links": [{"label": "USGS", "url": f"https://earthquake.usgs.gov/earthquakes/eventpage/{row['id']}"}],
            "attribution": "USGS Earthquake Hazards Program",
        }
        (species_dir / f"{row['id']}.json").write_text(json.dumps(detail, ensure_ascii=False))

    # Index
    index = {
        "globeId": "quake", "version": "1.0.0", "totalItems": len(df),
        "lastUpdated": date.today().isoformat(), "tileZoomRange": [0, 7],
        "filters": [
            {"key": "magRange", "label": "Magnitude", "type": "chips",
             "options": ["6.0-6.4", "6.5-6.9", "7.0-7.4", "7.5-7.9", "8.0+"]},
            {"key": "depth", "label": "Depth", "type": "range", "min": 0, "max": 700, "unit": "km"},
        ],
        "attribution": [{"name": "USGS", "license": "Public Domain", "url": "https://earthquake.usgs.gov"}],
    }
    (OUTPUT_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    print(f"  Done: {len(df)} quakes, index + details written")


if __name__ == "__main__":
    print("\n=== Quake ETL ===")
    download()
    process()
