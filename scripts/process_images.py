"""
Download FishBase thumbnails and remove backgrounds using rembg (U2-Net).

Downloads species photos from FishBase, removes backgrounds locally using
the U2-Net model via rembg, and saves transparent WebP images.

Usage:
    python scripts/process_images.py                # Process all
    python scripts/process_images.py --limit 100    # Process batch of 100
    python scripts/process_images.py --skip-download # Only process already-downloaded images
"""

import argparse
import json
import sys
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "fishbase"
CACHE_DIR = ROOT / ".cache" / "fish"
RAW_IMG_DIR = CACHE_DIR / "images_raw"
OUTPUT_DIR = ROOT / "output" / "fish" / "thumbs"

FISHBASE_THUMB = "https://www.fishbase.se/images/thumbnails/jpg/tn_{}"
FISHBASE_IMG = "https://www.fishbase.se/images/species/{}"


def get_species_with_pics() -> list[dict]:
    """Find all species with FishBase photos."""
    sp = pd.read_parquet(RAW_DIR / "species.parquet")
    sp["SpecCode"] = pd.to_numeric(sp["SpecCode"], errors="coerce")
    sp = sp.dropna(subset=["SpecCode", "PicPreferredName"])
    sp["SpecCode"] = sp["SpecCode"].astype(int)
    return [
        {"speccode": int(row["SpecCode"]), "pic": row["PicPreferredName"]}
        for _, row in sp.iterrows()
    ]


def download_images(species_list: list[dict], limit: int | None = None):
    """Download raw images from FishBase."""
    RAW_IMG_DIR.mkdir(parents=True, exist_ok=True)

    to_download = [
        s for s in species_list
        if not (RAW_IMG_DIR / f"{s['speccode']}.jpg").exists()
    ]
    if limit:
        to_download = to_download[:limit]

    print(f"  Downloading {len(to_download)} images (skipping {len(species_list) - len(to_download)} cached)...")

    downloaded = 0
    errors = 0
    for i, sp in enumerate(to_download):
        url = FISHBASE_IMG.format(sp["pic"])
        out_path = RAW_IMG_DIR / f"{sp['speccode']}.jpg"
        try:
            r = requests.get(url, timeout=15, verify=False)
            if r.status_code == 200 and len(r.content) > 1000:
                out_path.write_bytes(r.content)
                downloaded += 1
            else:
                errors += 1
        except requests.RequestException:
            errors += 1

        if (i + 1) % 100 == 0:
            print(f"    [{i+1}/{len(to_download)}] downloaded={downloaded}, errors={errors}")

    print(f"  Download complete: {downloaded} new, {errors} errors")


def process_backgrounds(limit: int | None = None):
    """Remove backgrounds using rembg and save as WebP."""
    try:
        from rembg import remove
        from PIL import Image
    except ImportError:
        print("ERROR: rembg and Pillow required. Install with:")
        print("  pip install rembg pillow")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(RAW_IMG_DIR.glob("*.jpg"))
    to_process = [
        f for f in raw_files
        if not (OUTPUT_DIR / f"{f.stem}.webp").exists()
    ]
    if limit:
        to_process = to_process[:limit]

    print(f"  Processing {len(to_process)} images (skipping {len(raw_files) - len(to_process)} cached)...")

    processed = 0
    errors = 0
    for i, img_path in enumerate(to_process):
        try:
            input_img = Image.open(img_path)
            output_img = remove(input_img)
            out_path = OUTPUT_DIR / f"{img_path.stem}.webp"
            output_img.save(str(out_path), "WEBP", quality=85)
            processed += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"    Error processing {img_path.name}: {e}")

        if (i + 1) % 50 == 0:
            print(f"    [{i+1}/{len(to_process)}] processed={processed}, errors={errors}")

    print(f"  Background removal complete: {processed} processed, {errors} errors")


def main():
    parser = argparse.ArgumentParser(description="Download and process fish images")
    parser.add_argument("--limit", type=int, help="Max images to process")
    parser.add_argument("--skip-download", action="store_true", help="Skip download, process existing only")
    args = parser.parse_args()

    species = get_species_with_pics()
    print(f"\n=== Process Images ===")
    print(f"  Species with FishBase photos: {len(species)}")

    if not args.skip_download:
        print("\n--- Step 1: Download ---")
        download_images(species, args.limit)

    print("\n--- Step 2: Remove backgrounds ---")
    process_backgrounds(args.limit)


if __name__ == "__main__":
    main()
