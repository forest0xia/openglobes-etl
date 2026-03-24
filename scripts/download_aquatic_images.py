#!/usr/bin/env python3
"""
Download full-body images for aquatic species.

Sources (in priority order):
  1. FishBase — species already have URLs in their detail JSON
  2. GBIF Occurrence API — CC-licensed photos via species name lookup
  3. iNaturalist — high-quality community photos

Output structure:
  .cache/aquatic/images/fishbase/{species_id}.jpg    — raw FishBase downloads
  .cache/aquatic/images/gbif/{species_id}.jpg        — GBIF downloads
  .cache/aquatic/images/inat/{species_id}.jpg        — iNaturalist downloads

Usage:
  python scripts/download_aquatic_images.py                     # download all
  python scripts/download_aquatic_images.py --source fishbase    # FishBase only
  python scripts/download_aquatic_images.py --source gbif        # GBIF fallback only
  python scripts/download_aquatic_images.py --limit 500          # limit count
  python scripts/download_aquatic_images.py --dry-run            # just count
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parent.parent
SPECIES_DIR = ROOT / "output" / "aquatic" / "species"
CACHE_DIR = ROOT / ".cache" / "aquatic" / "images"

FISHBASE_DIR = CACHE_DIR / "fishbase"
GBIF_DIR = CACHE_DIR / "gbif"
INAT_DIR = CACHE_DIR / "inat"

# Rate limiting
GBIF_DELAY = 0.5   # seconds between GBIF API calls
INAT_DELAY = 1.0   # seconds between iNat API calls

HEADERS = {
    "User-Agent": "OpenGlobes/1.0 (aquatic species image downloader; https://openglobes.com)"
}


def load_species_files():
    """Load all species detail JSONs."""
    species = []
    for f in sorted(SPECIES_DIR.iterdir()):
        if not f.suffix == ".json":
            continue
        try:
            data = json.loads(f.read_text())
            species.append(data)
        except Exception:
            continue
    return species


def download_file(url: str, dest: Path, timeout: int = 30) -> bool:
    """Download a URL to a file. Returns True on success."""
    if dest.exists() and dest.stat().st_size > 1000:
        return True  # already downloaded
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            data = resp.read()
            if len(data) < 500:
                return False  # too small, probably an error page
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return True
    except Exception:
        return False


def download_fishbase(species_list: list, limit: int = 0, dry_run: bool = False):
    """Download images from FishBase URLs already in species data."""
    FISHBASE_DIR.mkdir(parents=True, exist_ok=True)

    to_download = []
    for sp in species_list:
        images = sp.get("images", [])
        if not images:
            continue
        sid = sp["id"]
        dest = FISHBASE_DIR / f"{sid}.jpg"
        if dest.exists() and dest.stat().st_size > 1000:
            continue
        url = images[0].get("image", "")
        if not url:
            continue
        to_download.append((sid, url, dest))

    if limit > 0:
        to_download = to_download[:limit]

    print(f"[FishBase] {len(to_download)} images to download")
    if dry_run:
        return

    success = 0
    failed = 0

    def do_download(item):
        sid, url, dest = item
        return sid, download_file(url, dest)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(do_download, item): item for item in to_download}
        for i, future in enumerate(as_completed(futures)):
            sid, ok = future.result()
            if ok:
                success += 1
            else:
                failed += 1
            if (i + 1) % 100 == 0:
                print(f"  [{i+1}/{len(to_download)}] ok={success} fail={failed}")

    print(f"[FishBase] Done: {success} downloaded, {failed} failed")


def download_gbif(species_list: list, limit: int = 0, dry_run: bool = False):
    """Download CC-licensed images from GBIF for species without FishBase photos."""
    GBIF_DIR.mkdir(parents=True, exist_ok=True)

    # Find species without any downloaded image
    already = set()
    for d in [FISHBASE_DIR, GBIF_DIR, INAT_DIR]:
        if d.exists():
            for f in d.iterdir():
                if f.stat().st_size > 1000:
                    already.add(f.stem)

    to_fetch = []
    for sp in species_list:
        sid = sp["id"]
        if sid in already:
            continue
        sci_name = sp.get("scientificName", "")
        if not sci_name:
            continue
        to_fetch.append((sid, sci_name))

    if limit > 0:
        to_fetch = to_fetch[:limit]

    print(f"[GBIF] {len(to_fetch)} species to search")
    if dry_run:
        return

    success = 0
    failed = 0

    for i, (sid, sci_name) in enumerate(to_fetch):
        dest = GBIF_DIR / f"{sid}.jpg"
        if dest.exists() and dest.stat().st_size > 1000:
            success += 1
            continue

        try:
            # Step 1: Find GBIF taxon key
            match_url = f"https://api.gbif.org/v1/species/match?name={urllib.request.quote(sci_name)}&strict=true"
            req = urllib.request.Request(match_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                match = json.loads(resp.read())

            taxon_key = match.get("usageKey")
            if not taxon_key:
                failed += 1
                time.sleep(GBIF_DELAY)
                continue

            # Step 2: Search for occurrence with image
            occ_url = (
                f"https://api.gbif.org/v1/occurrence/search"
                f"?taxonKey={taxon_key}&mediaType=StillImage&limit=5"
            )
            req = urllib.request.Request(occ_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                occ = json.loads(resp.read())

            # Find first usable image URL
            img_url = None
            for result in occ.get("results", []):
                for media in result.get("media", []):
                    if media.get("type") == "StillImage" and media.get("identifier"):
                        img_url = media["identifier"]
                        break
                if img_url:
                    break

            if img_url and download_file(img_url, dest):
                success += 1
            else:
                failed += 1

        except Exception:
            failed += 1

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(to_fetch)}] ok={success} fail={failed}")

        time.sleep(GBIF_DELAY)

    print(f"[GBIF] Done: {success} downloaded, {failed} failed")


def download_inat(species_list: list, limit: int = 0, dry_run: bool = False):
    """Download images from iNaturalist for species still missing photos."""
    INAT_DIR.mkdir(parents=True, exist_ok=True)

    already = set()
    for d in [FISHBASE_DIR, GBIF_DIR, INAT_DIR]:
        if d.exists():
            for f in d.iterdir():
                if f.stat().st_size > 1000:
                    already.add(f.stem)

    to_fetch = []
    for sp in species_list:
        sid = sp["id"]
        if sid in already:
            continue
        sci_name = sp.get("scientificName", "")
        if not sci_name:
            continue
        to_fetch.append((sid, sci_name))

    if limit > 0:
        to_fetch = to_fetch[:limit]

    print(f"[iNaturalist] {len(to_fetch)} species to search")
    if dry_run:
        return

    success = 0
    failed = 0

    for i, (sid, sci_name) in enumerate(to_fetch):
        dest = INAT_DIR / f"{sid}.jpg"
        if dest.exists() and dest.stat().st_size > 1000:
            success += 1
            continue

        try:
            search_url = (
                f"https://api.inaturalist.org/v1/taxa"
                f"?q={urllib.request.quote(sci_name)}&per_page=1&is_active=true"
            )
            req = urllib.request.Request(search_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            results = data.get("results", [])
            if not results:
                failed += 1
                time.sleep(INAT_DELAY)
                continue

            taxon = results[0]
            photo_url = None

            # Try default photo first
            default_photo = taxon.get("default_photo", {})
            if default_photo:
                # Get medium size (500px)
                photo_url = default_photo.get("medium_url") or default_photo.get("url")

            # Try taxon_photos
            if not photo_url:
                for tp in taxon.get("taxon_photos", [])[:3]:
                    p = tp.get("photo", {})
                    photo_url = p.get("medium_url") or p.get("url")
                    if photo_url:
                        break

            if photo_url and download_file(photo_url, dest):
                success += 1
            else:
                failed += 1

        except Exception:
            failed += 1

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(to_fetch)}] ok={success} fail={failed}")

        time.sleep(INAT_DELAY)

    print(f"[iNaturalist] Done: {success} downloaded, {failed} failed")


def print_stats():
    """Print current download stats."""
    for name, d in [("FishBase", FISHBASE_DIR), ("GBIF", GBIF_DIR), ("iNaturalist", INAT_DIR)]:
        if d.exists():
            files = [f for f in d.iterdir() if f.stat().st_size > 1000]
            print(f"  {name}: {len(files)} images")
        else:
            print(f"  {name}: 0 images")


def main():
    parser = argparse.ArgumentParser(description="Download aquatic species images")
    parser.add_argument("--source", choices=["fishbase", "gbif", "inat", "all"], default="all")
    parser.add_argument("--limit", type=int, default=0, help="Max images to download (0=all)")
    parser.add_argument("--dry-run", action="store_true", help="Just count, don't download")
    parser.add_argument("--stats", action="store_true", help="Show current download stats")
    args = parser.parse_args()

    if args.stats:
        print_stats()
        return

    print("Loading species data...")
    species = load_species_files()
    print(f"Loaded {len(species)} species")

    if args.source in ("fishbase", "all"):
        download_fishbase(species, args.limit, args.dry_run)

    if args.source in ("gbif", "all"):
        download_gbif(species, args.limit, args.dry_run)

    if args.source in ("inat", "all"):
        download_inat(species, args.limit, args.dry_run)

    print("\nCurrent stats:")
    print_stats()


if __name__ == "__main__":
    main()
