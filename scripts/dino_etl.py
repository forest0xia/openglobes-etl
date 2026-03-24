"""Dino Globe ETL — Paleobiology Database (PBDB) dinosaur occurrences."""

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from tile_splitter import split_tiles

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "dino"
OUTPUT_DIR = ROOT / "output" / "dino"
URL = ("https://paleobiodb.org/data1.2/occs/list.csv"
       "?base_name=Dinosauria&show=coords,class,loc,time,strat&limit=all")

# Map PBDB order/class to display type
TYPE_MAP = {
    "Theropoda": "Theropod", "Sauropodomorpha": "Sauropod",
    "Ornithischia": "Ornithischian",
}
CLASS_TYPE = {"Reptilia": "Marine Reptile"}
# Orders that map to Pterosaur (technically archosaurs, often in Dinosauria queries)
PTEROSAUR_ORDERS = {"Pterosauria"}


def classify_type(row) -> str:
    order = str(row.get("order", "")).strip()
    cls = str(row.get("class", "")).strip()
    if order in PTEROSAUR_ORDERS:
        return "Pterosaur"
    if cls == "Aves":
        return "Other"  # Modern birds
    if order in TYPE_MAP:
        return TYPE_MAP[order]
    if cls in CLASS_TYPE:
        return CLASS_TYPE[cls]
    if cls == "Ornithischia":
        return "Ornithischian"
    if cls == "Saurischia":
        # Saurischia without a mapped order — check family hints
        return "Theropod"  # Most unclassified saurischians are theropods
    return "Other"


def era_from_age(max_ma: float) -> str:
    if max_ma >= 201.3:
        return "Triassic"
    if max_ma >= 145.0:
        return "Jurassic"
    return "Cretaceous"


def download():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "occurrences.csv"
    if out.exists():
        print("  occurrences.csv already exists, skipping")
        return
    print("  Downloading PBDB Dinosauria occurrences...")
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    out.write_bytes(r.content)
    print(f"    -> {r.text.count(chr(10))} rows ({len(r.content) / 1024 / 1024:.1f} MB)")


def process():
    df = pd.read_csv(RAW_DIR / "occurrences.csv")
    print(f"  Raw: {len(df)} occurrences")

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")
    df = df.dropna(subset=["lat", "lng"])

    # Exclude modern birds (Aves with max_ma < 66 = post-K/Pg)
    df["max_ma"] = pd.to_numeric(df["max_ma"], errors="coerce").fillna(0)
    df["min_ma"] = pd.to_numeric(df["min_ma"], errors="coerce").fillna(0)
    df = df[~((df["class"] == "Aves") & (df["max_ma"] < 66))].copy()
    print(f"  After excluding modern birds: {len(df)}")

    df["id"] = df["occurrence_no"].astype(str)
    df["name"] = df["accepted_name"].fillna(df["identified_name"])
    df["era"] = df["max_ma"].apply(era_from_age)
    df["early_age"] = df["max_ma"].round(1)
    df["late_age"] = df["min_ma"].round(1)
    df["type"] = df.apply(classify_type, axis=1)
    df["country"] = df["cc"].fillna("Unknown")
    df["formation"] = df.get("formation", pd.Series(dtype=str))
    df["thumb"] = ""

    # Deduplicate by accepted_name + collection for cleaner tiles
    print(f"  Types: {df['type'].value_counts().to_dict()}")
    print(f"  Eras: {df['era'].value_counts().to_dict()}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    split_tiles(
        df=df, output_dir=OUTPUT_DIR,
        filter_agg_keys=["era", "type"],
        top_items_fields=["id", "name", "thumb"],
        point_fields=["id", "name", "era", "type", "early_age", "late_age", "country"],
    )

    # Detail files
    species_dir = OUTPUT_DIR / "species"
    species_dir.mkdir(exist_ok=True)
    for _, row in df.iterrows():
        accepted = row["name"]
        wiki_name = accepted.replace(" ", "_")
        detail = {
            "id": row["id"], "name": accepted, "scientificName": accepted,
            "metadata": {
                "era": row["era"],
                "type": row["type"],
                "age": f"{row['early_age']}-{row['late_age']} Ma",
                "country": row["country"],
                "formation": row["formation"] if pd.notna(row.get("formation")) else None,
                "class": row.get("class", "") if pd.notna(row.get("class")) else None,
                "order": row.get("order", "") if pd.notna(row.get("order")) and row.get("order") != "NO_ORDER_SPECIFIED" else None,
                "family": row.get("family", "") if pd.notna(row.get("family")) and row.get("family") != "NO_FAMILY_SPECIFIED" else None,
            },
            "images": [],
            "links": [
                {"label": "PBDB", "url": f"https://paleobiodb.org/classic/basicTaxonInfo?taxon_no={row.get('accepted_no', '')}"},
                {"label": "Wikipedia", "url": f"https://en.wikipedia.org/wiki/{wiki_name}"},
            ],
            "attribution": "Paleobiology Database (CC-BY 4.0)",
        }
        detail["metadata"] = {k: v for k, v in detail["metadata"].items() if v is not None}
        (species_dir / f"{row['id']}.json").write_text(json.dumps(detail, ensure_ascii=False))

    # Index
    top_countries = df["country"].value_counts().head(20).index.tolist()
    index = {
        "globeId": "dino", "version": "1.0.0", "totalItems": len(df),
        "lastUpdated": date.today().isoformat(), "tileZoomRange": [0, 7],
        "filters": [
            {"key": "era", "label": "Era", "type": "chips",
             "options": ["Triassic", "Jurassic", "Cretaceous"]},
            {"key": "type", "label": "Type", "type": "chips",
             "options": ["Theropod", "Sauropod", "Ornithischian", "Marine Reptile", "Pterosaur", "Other"]},
            {"key": "early_age", "label": "Age (Ma)", "type": "range",
             "min": 0, "max": 252, "unit": "Ma"},
            {"key": "country", "label": "Country", "type": "chips",
             "options": top_countries},
        ],
        "attribution": [{"name": "Paleobiology Database", "license": "CC-BY 4.0", "url": "https://paleobiodb.org"}],
    }
    (OUTPUT_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    print(f"  Done: {len(df)} occurrences")


if __name__ == "__main__":
    print("\n=== Dino ETL ===")
    download()
    process()
