"""
Enrich species detail files with up to 3 photos from FishBase picturesmain table.

Sources (in priority order):
1. picturesmain.parquet — up to 3 photos per species, ranked by score/preferred
2. Existing GBIF cache (data/raw/image_urls.json) — fallback for species with no FishBase photos

Usage:
    python scripts/enrich_images.py              # Update all detail files
    python scripts/enrich_images.py --dry-run    # Show stats without writing
"""

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "fishbase"
SPECIES_DIR = ROOT / "output" / "fish" / "species"
GBIF_CACHE = ROOT / "data" / "raw" / "image_urls.json"

FB_THUMB = "https://www.fishbase.se/images/thumbnails/jpg/tn_{}"
FB_IMAGE = "https://www.fishbase.se/images/species/{}"
MAX_PHOTOS = 3


def load_photo_index() -> dict[int, list[str]]:
    """Build SpecCode -> [pic filenames] from picturesmain, best first."""
    df = pd.read_parquet(RAW_DIR / "picturesmain.parquet")
    df["SpecCode"] = pd.to_numeric(df["SpecCode"], errors="coerce")
    df = df.dropna(subset=["SpecCode", "PicName"])
    df["SpecCode"] = df["SpecCode"].astype(int)

    # Sort: preferred first, then by score descending
    df["_preferred"] = df["PicPreferred"].fillna(0).astype(float)
    df["_score"] = pd.to_numeric(df["Score"], errors="coerce").fillna(0)
    df = df.sort_values(["SpecCode", "_preferred", "_score"], ascending=[True, False, False])

    index = {}
    for spec, group in df.groupby("SpecCode"):
        pics = group["PicName"].tolist()[:MAX_PHOTOS]
        index[int(spec)] = pics
    return index


def load_gbif_cache() -> dict[str, dict]:
    if GBIF_CACHE.exists():
        return json.loads(GBIF_CACHE.read_text())
    return {}


def build_images_list(pics: list[str]) -> list[dict]:
    return [
        {"thumbnail": FB_THUMB.format(p), "image": FB_IMAGE.format(p)}
        for p in pics
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("Loading photo index from picturesmain...")
    photo_index = load_photo_index()
    print(f"  {len(photo_index)} species with FishBase photos")

    gbif_cache = load_gbif_cache()
    gbif_with_img = {k: v for k, v in gbif_cache.items() if v is not None}
    print(f"  {len(gbif_with_img)} species with GBIF fallback images")

    stats = {"updated": 0, "already_3": 0, "no_photos": 0, "added_gbif": 0}

    detail_files = list(SPECIES_DIR.glob("*.json"))
    print(f"  {len(detail_files)} detail files to process")

    for f in detail_files:
        data = json.loads(f.read_text())
        spec_id = int(data["id"])

        # Try FishBase picturesmain
        if spec_id in photo_index:
            pics = photo_index[spec_id]
            new_images = build_images_list(pics)

            if len(data.get("images", [])) >= MAX_PHOTOS:
                stats["already_3"] += 1
                continue

            data["images"] = new_images

            # Add photo page link if not present
            links = data.get("links", [])
            if not any("photos" in l.get("url", "").lower() for l in links):
                links.append({
                    "label": "Photos",
                    "url": f"https://www.fishbase.se/photos/thumbnailssummary.php?ID={spec_id}"
                })
                data["links"] = links

            if not args.dry_run:
                f.write_text(json.dumps(data, ensure_ascii=False))
            stats["updated"] += 1

        # GBIF fallback — only if no FishBase photos at all
        elif data["id"] in gbif_with_img:
            img = gbif_with_img[data["id"]]
            data["images"] = [{"thumbnail": img["image"], "image": img["image"]}]
            if not args.dry_run:
                f.write_text(json.dumps(data, ensure_ascii=False))
            stats["added_gbif"] += 1

        else:
            stats["no_photos"] += 1

    print(f"\nResults:")
    print(f"  Updated with FishBase photos: {stats['updated']}")
    print(f"  Already had 3+ photos: {stats['already_3']}")
    print(f"  Added GBIF fallback: {stats['added_gbif']}")
    print(f"  No photos available: {stats['no_photos']}")

    # Photo count distribution
    if not args.dry_run:
        counts = {1: 0, 2: 0, 3: 0}
        for f in detail_files[:5000]:
            n = len(json.loads(f.read_text()).get("images", []))
            if n in counts:
                counts[n] += 1
        print(f"\n  Photo distribution (sample): {counts}")


if __name__ == "__main__":
    main()
