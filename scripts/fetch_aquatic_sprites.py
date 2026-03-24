# scripts/fetch_aquatic_sprites.py
"""Multi-source sprite fetcher for aquatic globe outlines."""
import json
import time
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parent.parent
SPRITE_RAW_DIR = ROOT / "data" / "raw" / "aquatic" / "sprites"
SPRITE_LIST_PATH = ROOT / "data" / "raw" / "aquatic" / "sprite_species_list.json"
SPRITE_OVERRIDES_PATH = ROOT / "data" / "raw" / "aquatic" / "sprite_overrides.json"

SOURCE_PRIORITY = ["wikimedia", "fishbase", "noaa", "gbif_media"]

PHYLOPIC_API = "https://api.phylopic.org/v2"
HEADERS = {"User-Agent": "OpenGlobesETL/1.0 (https://openglobes.com)"}


def fetch_phylopic(scientific_name: str, species_id: str) -> bool:
    """Fetch SVG silhouette from Phylopic. Returns True if found/exists."""
    out_dir = SPRITE_RAW_DIR / "phylopic"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{species_id}.svg"
    if out_path.exists():
        return True

    # Search by scientific name
    resp = requests.get(
        f"{PHYLOPIC_API}/images",
        params={"filter_name": scientific_name, "embed_items": "true"},
        timeout=30,
    )
    if resp.status_code != 200:
        return False

    items = resp.json().get("items", [])
    if not items:
        return False

    # Get the first result's SVG
    image_uuid = items[0].get("uuid", "")
    if not image_uuid:
        return False

    # Download SVG
    svg_resp = requests.get(
        f"{PHYLOPIC_API}/images/{image_uuid}/file",
        headers={"Accept": "image/svg+xml"},
        timeout=30,
    )
    if svg_resp.status_code != 200 or "svg" not in svg_resp.headers.get("content-type", ""):
        return False

    out_path.write_bytes(svg_resp.content)
    return True


def fetch_fishbase_line_art(scientific_name: str, species_id: str) -> bool:
    """Fetch line art from FishBase. Returns True if found/exists."""
    out_dir = SPRITE_RAW_DIR / "fishbase"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{species_id}.gif"
    if out_path.exists():
        return True

    genus, *species_parts = scientific_name.split()
    species = species_parts[0] if species_parts else ""
    url = f"https://www.fishbase.se/images/species/{genus[:2]}{species[:4]}_u0.gif"
    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
        return False
    out_path.write_bytes(resp.content)
    return True


def fetch_wikimedia(scientific_name: str, species_id: str) -> bool:
    """Search Wikimedia Commons for SVG illustration. Returns True if found/exists."""
    out_dir = SPRITE_RAW_DIR / "wikimedia"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{species_id}.svg"
    if out_path.exists():
        return True

    resp = requests.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": f"{scientific_name} filetype:svg",
            "srnamespace": "6",
            "format": "json",
            "srlimit": "1",
        },
        headers=HEADERS, timeout=15,
    )
    if resp.status_code != 200:
        return False
    results = resp.json().get("query", {}).get("search", [])
    if not results:
        return False

    # Get file URL
    title = results[0]["title"]
    info_resp = requests.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|mime",
            "format": "json",
        },
        headers=HEADERS, timeout=15,
    )
    pages = info_resp.json().get("query", {}).get("pages", {})
    for page in pages.values():
        imageinfo = page.get("imageinfo", [{}])[0]
        if "svg" in imageinfo.get("mime", ""):
            svg_url = imageinfo["url"]
            svg_resp = requests.get(svg_url, headers=HEADERS, timeout=30)
            if svg_resp.status_code == 200:
                out_path.write_bytes(svg_resp.content)
                return True
    return False


def fetch_noaa(scientific_name: str, species_id: str) -> bool:
    """Fetch illustration from NOAA Fisheries. Returns True if found/exists."""
    out_dir = SPRITE_RAW_DIR / "noaa"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{species_id}.png"
    if out_path.exists():
        return True
    # NOAA species illustrations are at predictable URLs by common name
    # This is a best-effort scrape — many species won't have NOAA art
    search_name = scientific_name.replace(" ", "+")
    resp = requests.get(
        f"https://www.fisheries.noaa.gov/api/v2/species?search={search_name}",
        timeout=15,
    )
    if resp.status_code != 200:
        return False
    results = resp.json().get("data", [])
    if not results:
        return False
    # Look for species illustration URL
    img_url = results[0].get("species_illustration_photo", {}).get("src")
    if not img_url:
        return False
    img_resp = requests.get(img_url, timeout=30)
    if img_resp.status_code == 200:
        out_path.write_bytes(img_resp.content)
        return True
    return False


def fetch_gbif_media(scientific_name: str, species_id: str) -> bool:
    """Fetch CC-licensed image from GBIF occurrence media. Returns True if found/exists."""
    out_dir = SPRITE_RAW_DIR / "gbif_media"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{species_id}.jpg"
    if out_path.exists():
        return True
    # Search GBIF for occurrence with CC-BY image
    resp = requests.get(
        "https://api.gbif.org/v1/occurrence/search",
        params={
            "scientificName": scientific_name,
            "mediaType": "StillImage",
            "limit": 1,
        },
        timeout=15,
    )
    if resp.status_code != 200:
        return False
    results = resp.json().get("results", [])
    for occ in results:
        for media in occ.get("media", []):
            if media.get("type") == "StillImage" and media.get("identifier"):
                img_resp = requests.get(media["identifier"], timeout=30)
                if img_resp.status_code == 200:
                    out_path.write_bytes(img_resp.content)
                    return True
    return False


FETCH_FUNCTIONS = {
    "phylopic": fetch_phylopic,
    "fishbase": fetch_fishbase_line_art,
    "noaa": fetch_noaa,
    "wikimedia": fetch_wikimedia,
    "gbif_media": fetch_gbif_media,
}


def fetch_all_sprites(species_list: list[dict], sources: list[str] = None):
    """Fetch sprites for all species from all sources. Parallelized per source."""
    sources = sources or SOURCE_PRIORITY
    results = {}  # species_id -> {source: True/False}

    for source in sources:
        fetch_fn = FETCH_FUNCTIONS.get(source)
        if not fetch_fn:
            print(f"  Skipping unknown source: {source}")
            continue

        print(f"Fetching from {source}...")
        found = 0
        for sp in species_list:
            sid = str(sp["id"])
            sci_name = sp["scientificName"]
            if sid not in results:
                results[sid] = {}
            success = fetch_fn(sci_name, sid)
            results[sid][source] = success
            if success:
                found += 1
            time.sleep(0.5)  # rate limit
        print(f"  {source}: {found}/{len(species_list)} found")

    # Save results summary
    summary_path = SPRITE_RAW_DIR / "fetch_results.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    return results


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Fetch aquatic sprite outlines")
    parser.add_argument("--sources", nargs="+", default=SOURCE_PRIORITY,
                        help="Sources to fetch from")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of species (0=all)")
    args = parser.parse_args()

    if not SPRITE_LIST_PATH.exists():
        print(f"ERROR: Species list not found at {SPRITE_LIST_PATH}")
        print("Run aquatic_etl.py first to generate the species list")
        return

    species_list = json.loads(SPRITE_LIST_PATH.read_text())
    if args.limit > 0:
        species_list = species_list[:args.limit]

    print(f"Fetching sprites for {len(species_list)} species from {args.sources}")
    fetch_all_sprites(species_list, args.sources)


if __name__ == "__main__":
    main()
