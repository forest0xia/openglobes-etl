"""
Fetch CC-BY image URLs from GBIF/iNaturalist for fish species without FishBase photos.

Searches GBIF occurrence API for StillImage media with CC-BY license,
stores URLs in a cache file. Does NOT download actual images.

Usage:
    python scripts/fetch_images.py --limit 100   # Fetch up to 100 species
    python scripts/fetch_images.py               # Fetch all missing
    python scripts/fetch_images.py --apply        # Apply cached URLs to detail JSONs
"""

import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
CACHE_PATH = RAW_DIR / "image_urls.json"
SPECIES_DIR = ROOT / "output" / "fish" / "species"

GBIF_SEARCH = "https://api.gbif.org/v1/occurrence/search"
GBIF_SPECIES_MATCH = "https://api.gbif.org/v1/species/match"


def load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache: dict):
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False))


def get_gbif_taxon_key(scientific_name: str) -> int | None:
    """Match a scientific name to a GBIF taxon key."""
    try:
        r = requests.get(GBIF_SPECIES_MATCH, params={"name": scientific_name}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("matchType") != "NONE" and data.get("usageKey"):
                return data["usageKey"]
    except requests.RequestException:
        pass
    return None


def search_gbif_image(taxon_key: int) -> dict | None:
    """Search GBIF for a CC-BY licensed image for a taxon."""
    try:
        r = requests.get(GBIF_SEARCH, params={
            "taxonKey": taxon_key,
            "mediaType": "StillImage",
            "limit": 1,
            "license": "CC_BY_4_0",
        }, timeout=10)
        if r.status_code != 200:
            return None
        results = r.json().get("results", [])
        if not results:
            return None
        for media in results[0].get("media", []):
            if media.get("identifier"):
                return {
                    "image": media["identifier"],
                    "thumbnail": media.get("identifier", ""),
                    "license": media.get("license", "CC BY 4.0"),
                    "creator": media.get("creator", ""),
                    "source": "GBIF/iNaturalist",
                }
    except requests.RequestException:
        pass
    return None


def find_missing_species() -> list[dict]:
    """Find species detail files that have no images."""
    missing = []
    for f in SPECIES_DIR.glob("*.json"):
        data = json.loads(f.read_text())
        if not data.get("images"):
            missing.append({
                "id": data["id"],
                "scientificName": data.get("scientificName", ""),
                "name": data.get("name", ""),
            })
    return missing


def fetch(limit: int | None = None):
    """Fetch image URLs for species without photos."""
    cache = load_cache()
    missing = find_missing_species()
    print(f"Species without images: {len(missing)}")

    # Filter out already-cached (including explicit "not found" markers)
    to_fetch = [s for s in missing if s["id"] not in cache]
    if limit:
        to_fetch = to_fetch[:limit]
    print(f"To fetch: {len(to_fetch)} (cached: {len(cache)})")

    found = 0
    for i, sp in enumerate(to_fetch):
        sci_name = sp["scientificName"]
        sp_id = sp["id"]

        # Step 1: resolve taxon key
        taxon_key = get_gbif_taxon_key(sci_name)
        if not taxon_key:
            cache[sp_id] = None  # Mark as not found
            if (i + 1) % 50 == 0:
                save_cache(cache)
            time.sleep(0.5)
            continue

        # Step 2: search for image
        result = search_gbif_image(taxon_key)
        if result:
            cache[sp_id] = result
            found += 1
            print(f"  [{i+1}/{len(to_fetch)}] {sci_name}: found")
        else:
            cache[sp_id] = None
            if (i + 1) % 100 == 0:
                print(f"  [{i+1}/{len(to_fetch)}] progress...")

        # Rate limit: ~1 req/sec (2 requests per species)
        time.sleep(1.0)

        # Periodic save
        if (i + 1) % 50 == 0:
            save_cache(cache)

    save_cache(cache)
    print(f"\nDone. Found images for {found}/{len(to_fetch)} species.")
    print(f"Cache total: {sum(1 for v in cache.values() if v is not None)} with images, "
          f"{sum(1 for v in cache.values() if v is None)} not found")


def apply_to_details():
    """Apply cached image URLs to species detail JSON files."""
    cache = load_cache()
    updated = 0

    for f in SPECIES_DIR.glob("*.json"):
        data = json.loads(f.read_text())
        sp_id = data["id"]

        if data.get("images"):
            continue  # Already has images

        if sp_id in cache and cache[sp_id] is not None:
            img = cache[sp_id]
            data["images"] = [
                {"thumbnail": img["thumbnail"], "image": img["image"]},
            ]
            f.write_text(json.dumps(data, ensure_ascii=False))
            updated += 1

    print(f"Updated {updated} species detail files with GBIF images.")


def main():
    parser = argparse.ArgumentParser(description="Fetch image URLs for fish species")
    parser.add_argument("--limit", type=int, help="Max species to fetch")
    parser.add_argument("--apply", action="store_true", help="Apply cached URLs to detail JSONs")
    args = parser.parse_args()

    if args.apply:
        apply_to_details()
    else:
        fetch(args.limit)
        apply_to_details()


if __name__ == "__main__":
    main()
