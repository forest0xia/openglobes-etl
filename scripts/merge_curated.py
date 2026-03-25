"""Merge curation/aquatic/selected.json with ETL species metadata into output/aquatic/final.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURATION_DIR = ROOT / "curation" / "aquatic"
OUTPUT_DIR = ROOT / "output" / "aquatic"
CROSSWALK_PATH = ROOT / "data" / "raw" / "aquatic" / "id_crosswalk.json"
MANIFEST_PATH = OUTPUT_DIR / "sprites" / "manifest.json"


def load_crosswalk() -> dict:
    """Load aphiaId -> metadata crosswalk."""
    if not CROSSWALK_PATH.exists():
        return {}
    raw = json.loads(CROSSWALK_PATH.read_text())
    return {int(k): v for k, v in raw.items()}


def load_sprite_manifest() -> dict:
    """Load sprite manifest and build group -> sprite lookup."""
    if not MANIFEST_PATH.exists():
        return {}
    return json.loads(MANIFEST_PATH.read_text())


def resolve_sprite(species: dict, manifest: dict) -> str:
    """Resolve sprite filename for a curated species."""
    sprites = manifest.get("sprites", {})
    sci_name = species.get("name", "").strip().lower()

    # 1. Exact scientific name match
    for entry in sprites.values():
        if (entry.get("scientificName") or "").strip().lower() == sci_name:
            return entry["file"]

    # 2. Genus match
    genus = sci_name.split()[0] if " " in sci_name else ""
    if genus:
        for entry in sprites.values():
            if (entry.get("scientificName") or "").strip().lower() == genus:
                return entry["file"]

    # 3. Group fallback (derive group from crosswalk if possible)
    group_fb = manifest.get("groupFallbacks", {})
    # We don't have group on the curated species yet, so fall back to body type
    bt_fb = manifest.get("bodyTypeFallbacks", {})

    return group_fb.get("other", bt_fb.get("fusiform", "sp-atlantic_cod.png"))


def merge():
    """Merge curation + ETL data into final output."""
    selected = json.loads((CURATION_DIR / "selected.json").read_text())
    hotspots = json.loads((CURATION_DIR / "hotspots.json").read_text())
    crosswalk = load_crosswalk()
    manifest = load_sprite_manifest()

    final = []
    for species in selected:
        aphia_id = species.get("aphiaId")
        entry = {
            # Curation fields
            "aphiaId": aphia_id,
            "tier": species.get("tier"),
            "name": species.get("name"),
            "nameZh": species.get("nameZh"),
            "tagline": species.get("tagline"),
            "viewingSpots": species.get("viewingSpots", []),
            "display": species.get("display"),
        }

        # ETL enrichment from crosswalk
        if aphia_id and aphia_id in crosswalk:
            cw = crosswalk[aphia_id]
            entry["scientificName"] = cw.get("scientificName", species.get("name"))
            fb_code = cw.get("fishbaseSpecCode")
            if fb_code and fb_code == fb_code:  # not NaN
                entry["fishbaseSpecCode"] = int(fb_code)
        else:
            entry["scientificName"] = species.get("name")

        # Sprite resolution
        entry["sprite"] = resolve_sprite(species, manifest)

        final.append(entry)

    # Write final output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "final.json"
    out_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write hotspots alongside
    hotspots_out = OUTPUT_DIR / "hotspots.json"
    hotspots_out.write_text(json.dumps(hotspots, ensure_ascii=False, indent=2), encoding="utf-8")

    # Stats
    with_spots = sum(1 for s in final if s.get("viewingSpots"))
    total_spots = sum(len(s.get("viewingSpots", [])) for s in final)
    with_sprite = sum(1 for s in final if s.get("sprite", "").startswith("sp-"))
    print(f"Merged {len(final)} species -> {out_path}")
    print(f"  {with_spots} with viewingSpots ({total_spots} total spots)")
    print(f"  {with_sprite} with specific sprites")
    print(f"  Hotspots written -> {hotspots_out}")


if __name__ == "__main__":
    merge()
