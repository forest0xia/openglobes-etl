"""Volcano Globe ETL — Smithsonian GVP Holocene volcano list."""

import json
import sys
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
from lxml import etree

sys.path.insert(0, str(Path(__file__).parent))
from tile_splitter import split_tiles

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "volcano"
OUTPUT_DIR = ROOT / "output" / "volcano"
URL = "https://volcano.si.edu/database/list_volcano_holocene_excel.cfm"


def download():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "holocene.xml"
    if out.exists():
        print("  holocene.xml already exists, skipping")
        return
    print("  Downloading GVP Holocene volcano list...")
    r = requests.get(URL, timeout=60)
    r.raise_for_status()
    out.write_bytes(r.content)
    print(f"    -> {len(r.content) / 1024:.0f} KB")


def parse_xml() -> pd.DataFrame:
    """Parse Office SpreadsheetML XML into DataFrame."""
    data = (RAW_DIR / "holocene.xml").read_bytes()
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(data, parser)
    ns = "urn:schemas-microsoft-com:office:spreadsheet"
    rows = root.findall(f".//{{{ns}}}Row")

    def row_vals(row):
        return [
            (d.text.strip() if d is not None and d.text else "")
            for cell in row.findall(f"{{{ns}}}Cell")
            for d in [cell.find(f"{{{ns}}}Data")]
        ]

    headers = row_vals(rows[1])  # Row 0 is title, row 1 is header
    records = [dict(zip(headers, row_vals(r))) for r in rows[2:]]
    return pd.DataFrame(records)


def process():
    print("  Parsing XML...")
    df = parse_xml()
    print(f"  Raw: {len(df)} volcanoes")

    df["lat"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["lng"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df = df.dropna(subset=["lat", "lng"])

    df["id"] = df["Volcano Number"]
    df["name"] = df["Volcano Name"]
    df["type"] = df["Primary Volcano Type"]
    df["elevation"] = pd.to_numeric(df["Elevation (m)"], errors="coerce").fillna(0).astype(int)
    df["lastEruption"] = df["Last Known Eruption"]
    df["country"] = df["Country"]
    df["region"] = df["Volcanic Region"]
    df["thumb"] = ""
    print(f"  With coordinates: {len(df)}")

    # Tiles
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    split_tiles(
        df=df, output_dir=OUTPUT_DIR,
        filter_agg_keys=["type"],
        top_items_fields=["id", "name", "thumb"],
        point_fields=["id", "name", "type", "elevation", "lastEruption", "country"],
    )

    # Detail files
    species_dir = OUTPUT_DIR / "species"
    species_dir.mkdir(exist_ok=True)
    for _, row in df.iterrows():
        detail = {
            "id": row["id"], "name": row["name"],
            "scientificName": row["type"],
            "metadata": {"elevation": f"{row['elevation']} m", "lastEruption": row["lastEruption"],
                         "country": row["country"], "region": row["region"],
                         "tectonics": row.get("Tectonic Setting", ""), "rock": row.get("Dominant Rock Type", "")},
            "images": [], "links": [{"label": "GVP", "url": f"https://volcano.si.edu/volcano.cfm?vn={row['id']}"}],
            "attribution": "Smithsonian GVP (CC-BY-NC)",
        }
        (species_dir / f"{row['id']}.json").write_text(json.dumps(detail, ensure_ascii=False))

    # Index
    index = {
        "globeId": "volcano", "version": "1.0.0", "totalItems": len(df),
        "lastUpdated": date.today().isoformat(), "tileZoomRange": [0, 7],
        "filters": [{"key": "type", "label": "Type", "type": "chips",
                     "options": sorted(df["type"].dropna().unique().tolist())}],
        "attribution": [{"name": "Smithsonian GVP", "license": "CC-BY-NC", "url": "https://volcano.si.edu"}],
    }
    (OUTPUT_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    print(f"  Done: {len(df)} volcanoes, index + details written")


if __name__ == "__main__":
    print("\n=== Volcano ETL ===")
    download()
    process()
