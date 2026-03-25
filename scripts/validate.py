"""
Validate output files against DATA_CONTRACTS.md schemas.

Usage:
    python scripts/validate.py fish          # Validate fish globe output
    python scripts/validate.py --all         # Validate all globes
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = ROOT / "output"

CLUSTER_ZOOM_MIN = 0
CLUSTER_ZOOM_MAX = 3
POINT_ZOOM_MIN = 4
POINT_ZOOM_MAX = 7
MAX_CLUSTER_TILE_KB = 5
MAX_POINT_TILE_KB = 30
MAX_DETAIL_KB = 3
MAX_POINTS_PER_TILE = 200


class ValidationError:
    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message

    def __str__(self):
        return f"  {self.path}: {self.message}"


def validate_cluster_tile(path: Path, require_sprite: bool = False) -> list[ValidationError]:
    errors = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [ValidationError(str(path), f"Invalid JSON: {e}")]

    size_kb = path.stat().st_size / 1024
    if size_kb > MAX_CLUSTER_TILE_KB:
        errors.append(ValidationError(str(path), f"Cluster tile too large: {size_kb:.1f}KB > {MAX_CLUSTER_TILE_KB}KB"))

    for key in ("zoom", "x", "y", "clusters"):
        if key not in data:
            errors.append(ValidationError(str(path), f"Missing required key: {key}"))

    if "clusters" in data:
        for i, cluster in enumerate(data["clusters"]):
            for ck in ("lat", "lng", "count"):
                if ck not in cluster:
                    errors.append(ValidationError(str(path), f"clusters[{i}] missing key: {ck}"))
            if "lat" in cluster and not -90 <= cluster["lat"] <= 90:
                errors.append(ValidationError(str(path), f"clusters[{i}] lat out of range: {cluster['lat']}"))
            if "lng" in cluster and not -180 <= cluster["lng"] <= 180:
                errors.append(ValidationError(str(path), f"clusters[{i}] lng out of range: {cluster['lng']}"))

            if require_sprite:
                for j, item in enumerate(cluster.get("topItems", [])):
                    if not item.get("sprite"):
                        errors.append(ValidationError(str(path), f"clusters[{i}].topItems[{j}] (id={item.get('id')}) missing sprite"))
                if "groupDistribution" not in cluster:
                    errors.append(ValidationError(str(path), f"clusters[{i}] missing groupDistribution"))

    return errors


def validate_point_tile(path: Path, require_sprite: bool = False) -> list[ValidationError]:
    errors = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [ValidationError(str(path), f"Invalid JSON: {e}")]

    size_kb = path.stat().st_size / 1024
    if size_kb > MAX_POINT_TILE_KB:
        errors.append(ValidationError(str(path), f"Point tile too large: {size_kb:.1f}KB > {MAX_POINT_TILE_KB}KB"))

    for key in ("zoom", "x", "y", "points"):
        if key not in data:
            errors.append(ValidationError(str(path), f"Missing required key: {key}"))

    if "points" in data:
        if len(data["points"]) > MAX_POINTS_PER_TILE:
            errors.append(ValidationError(str(path), f"Too many points: {len(data['points'])} > {MAX_POINTS_PER_TILE}"))
        for i, pt in enumerate(data["points"]):
            for pk in ("lat", "lng", "id", "name"):
                if pk not in pt:
                    errors.append(ValidationError(str(path), f"points[{i}] missing key: {pk}"))
            if "lat" in pt and not -90 <= pt["lat"] <= 90:
                errors.append(ValidationError(str(path), f"points[{i}] lat out of range: {pt['lat']}"))
            if "lng" in pt and not -180 <= pt["lng"] <= 180:
                errors.append(ValidationError(str(path), f"points[{i}] lng out of range: {pt['lng']}"))
            if require_sprite and not pt.get("sprite"):
                errors.append(ValidationError(str(path), f"points[{i}] (id={pt.get('id')}) missing sprite"))

    return errors


def validate_detail(path: Path, require_sprite: bool = False) -> list[ValidationError]:
    errors = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [ValidationError(str(path), f"Invalid JSON: {e}")]

    size_kb = path.stat().st_size / 1024
    if size_kb > MAX_DETAIL_KB:
        errors.append(ValidationError(str(path), f"Detail file too large: {size_kb:.1f}KB > {MAX_DETAIL_KB}KB"))

    for key in ("id", "name", "scientificName"):
        if key not in data:
            errors.append(ValidationError(str(path), f"Missing required key: {key}"))

    if require_sprite:
        for key in ("sprite", "group", "bodyType", "bodyGroup"):
            if not data.get(key):
                errors.append(ValidationError(str(path), f"Missing required sprite field: {key}"))

    return errors


def validate_index(path: Path) -> list[ValidationError]:
    errors = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [ValidationError(str(path), f"Invalid JSON: {e}")]

    for key in ("globeId", "version", "totalItems", "lastUpdated", "tileZoomRange", "filters", "attribution"):
        if key not in data:
            errors.append(ValidationError(str(path), f"Missing required key: {key}"))

    if "totalItems" in data and data["totalItems"] == 0:
        errors.append(ValidationError(str(path), "totalItems is 0"))

    return errors


def validate_sprites_dir(globe_dir: Path) -> list[ValidationError]:
    """Validate sprites directory: manifest exists, all referenced files exist, SVGs valid."""
    errors = []
    sprites_dir = globe_dir / "sprites"
    manifest_path = sprites_dir / "manifest.json"
    if not manifest_path.exists():
        errors.append(ValidationError(str(manifest_path), "Missing manifest.json"))
        return errors

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        return [ValidationError(str(manifest_path), f"Invalid JSON: {e}")]

    # Check all sprite files exist and are within size limit
    for sid, sdata in manifest.get("sprites", {}).items():
        svg_path = sprites_dir / sdata["file"]
        if not svg_path.exists():
            errors.append(ValidationError(str(svg_path), f"Missing sprite file for {sid}"))
        elif svg_path.stat().st_size > 512 * 1024:
            errors.append(ValidationError(str(svg_path), f"Sprite too large: {svg_path.stat().st_size}B > 512KB"))

    # Check group fallback files exist
    for gid, filename in manifest.get("groupFallbacks", {}).items():
        if not (sprites_dir / filename).exists():
            errors.append(ValidationError(str(sprites_dir / filename), f"Missing group fallback for {gid}"))

    # Check body type fallback files exist
    for bt, filename in manifest.get("bodyTypeFallbacks", {}).items():
        if not (sprites_dir / filename).exists():
            errors.append(ValidationError(str(sprites_dir / filename), f"Missing body type fallback for {bt}"))

    return errors


# Globes that require sprite validation
SPRITE_GLOBES = {"aquatic"}

# Globes that use curated final.json instead of tiles
CURATED_GLOBES = {"aquatic"}

EXPECTED_TIERS = {"star": 50, "ecosystem": 80, "surprise": 70}
TIER_TOLERANCE = 5  # allow +/- from expected count


def validate_curated_final(globe_dir: Path) -> list[ValidationError]:
    """Validate curated final.json + hotspots.json for aquatic globe."""
    errors = []

    # --- final.json ---
    final_path = globe_dir / "final.json"
    if not final_path.exists():
        return [ValidationError(str(final_path), "final.json missing")]

    try:
        species = json.loads(final_path.read_text())
    except json.JSONDecodeError as e:
        return [ValidationError(str(final_path), f"Invalid JSON: {e}")]

    if not isinstance(species, list):
        return [ValidationError(str(final_path), "final.json must be an array")]

    print(f"  Species count: {len(species)}")

    # Tier distribution
    from collections import Counter
    tiers = Counter(s.get("tier") for s in species)
    for tier, expected in EXPECTED_TIERS.items():
        actual = tiers.get(tier, 0)
        print(f"  {tier}: {actual} (expected ~{expected})")
        if abs(actual - expected) > TIER_TOLERANCE:
            errors.append(ValidationError(str(final_path),
                f"Tier '{tier}' count {actual} deviates from expected ~{expected}"))

    # Per-species checks
    aphia_ids = set()
    no_spots = []
    no_name_zh = []
    no_tagline = []
    no_sprite = []
    for i, s in enumerate(species):
        # Required fields
        for key in ("aphiaId", "name", "tier", "viewingSpots", "display"):
            if key not in s:
                errors.append(ValidationError(str(final_path), f"species[{i}] ({s.get('name','?')}) missing key: {key}"))

        # AphiaID uniqueness
        aid = s.get("aphiaId")
        if aid:
            if aid in aphia_ids:
                errors.append(ValidationError(str(final_path), f"Duplicate aphiaId: {aid}"))
            aphia_ids.add(aid)

        # Viewing spots
        spots = s.get("viewingSpots", [])
        if not spots:
            no_spots.append(s.get("name", f"[{i}]"))
        for j, spot in enumerate(spots):
            for sk in ("name", "country", "lat", "lng", "season", "reliability", "activity"):
                if sk not in spot:
                    errors.append(ValidationError(str(final_path),
                        f"species[{i}].viewingSpots[{j}] missing key: {sk}"))
            if "lat" in spot and not -90 <= spot["lat"] <= 90:
                errors.append(ValidationError(str(final_path),
                    f"species[{i}].viewingSpots[{j}] lat out of range: {spot['lat']}"))
            if "lng" in spot and not -180 <= spot["lng"] <= 180:
                errors.append(ValidationError(str(final_path),
                    f"species[{i}].viewingSpots[{j}] lng out of range: {spot['lng']}"))

        # Optional but tracked
        if not s.get("nameZh"):
            no_name_zh.append(s.get("name", f"[{i}]"))
        if not s.get("tagline"):
            no_tagline.append(s.get("name", f"[{i}]"))
        if not s.get("sprite"):
            no_sprite.append(s.get("name", f"[{i}]"))

    if no_spots:
        errors.append(ValidationError(str(final_path), f"{len(no_spots)} species with 0 viewingSpots"))
    if no_sprite:
        errors.append(ValidationError(str(final_path), f"{len(no_sprite)} species with no sprite"))

    # Warnings (not errors)
    if no_name_zh:
        print(f"  WARNING: {len(no_name_zh)} species missing nameZh")
    if no_tagline:
        print(f"  WARNING: {len(no_tagline)} species missing tagline")

    total_spots = sum(len(s.get("viewingSpots", [])) for s in species)
    print(f"  Total viewing spots: {total_spots}")

    # --- hotspots.json ---
    hotspots_path = globe_dir / "hotspots.json"
    if not hotspots_path.exists():
        errors.append(ValidationError(str(hotspots_path), "hotspots.json missing"))
    else:
        try:
            hotspots = json.loads(hotspots_path.read_text())
        except json.JSONDecodeError as e:
            errors.append(ValidationError(str(hotspots_path), f"Invalid JSON: {e}"))
            hotspots = []

        print(f"  Hotspots: {len(hotspots)}")

        # Check each hotspot has minimum species coverage
        hotspot_ids = {h["id"]: h for h in hotspots}
        hotspot_counts = Counter()
        for s in species:
            for spot in s.get("viewingSpots", []):
                hid = spot.get("hotspotId")
                if hid:
                    hotspot_counts[hid] += 1

        for h in hotspots:
            hid = h["id"]
            count = hotspot_counts.get(hid, 0)
            min_req = h.get("minSpeciesCount", 1)
            if count < min_req:
                errors.append(ValidationError(str(hotspots_path),
                    f"Hotspot '{hid}' has {count} species (minimum: {min_req})"))

        # Check for hotspotIds that don't exist in hotspots.json
        for s in species:
            for spot in s.get("viewingSpots", []):
                hid = spot.get("hotspotId")
                if hid and hid not in hotspot_ids:
                    errors.append(ValidationError(str(final_path),
                        f"Species '{s.get('name')}' references unknown hotspotId: {hid}"))

    # --- sprites ---
    errors.extend(validate_sprites_dir(globe_dir))

    return errors


def validate_globe(globe: str) -> list[ValidationError]:
    globe_dir = OUTPUT_ROOT / globe
    if not globe_dir.exists():
        return [ValidationError(str(globe_dir), "Output directory does not exist")]

    # Curated globes use final.json instead of tiles
    if globe in CURATED_GLOBES:
        return validate_curated_final(globe_dir)

    require_sprite = globe in SPRITE_GLOBES
    errors = []
    tiles_dir = globe_dir / "tiles"

    # Validate cluster tiles
    for z in range(CLUSTER_ZOOM_MIN, CLUSTER_ZOOM_MAX + 1):
        zoom_dir = tiles_dir / f"z{z}"
        if not zoom_dir.exists():
            errors.append(ValidationError(str(zoom_dir), "Cluster zoom directory missing"))
            continue
        for f in zoom_dir.glob("*.json"):
            errors.extend(validate_cluster_tile(f, require_sprite=require_sprite))

    # Validate point tiles
    for z in range(POINT_ZOOM_MIN, POINT_ZOOM_MAX + 1):
        zoom_dir = tiles_dir / f"z{z}"
        if not zoom_dir.exists():
            errors.append(ValidationError(str(zoom_dir), "Point zoom directory missing"))
            continue
        for f in zoom_dir.glob("*.json"):
            errors.extend(validate_point_tile(f, require_sprite=require_sprite))

    # Validate detail files
    species_dir = globe_dir / "species"
    if species_dir.exists():
        for f in list(species_dir.glob("*.json"))[:100]:  # Sample 100
            errors.extend(validate_detail(f, require_sprite=require_sprite))
    else:
        errors.append(ValidationError(str(species_dir), "Species directory missing"))

    # Validate index
    index_path = globe_dir / "index.json"
    if index_path.exists():
        errors.extend(validate_index(index_path))
    else:
        errors.append(ValidationError(str(index_path), "index.json missing"))

    # Validate sprites directory (only for globes that require sprites)
    if require_sprite:
        errors.extend(validate_sprites_dir(globe_dir))

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate globe output files")
    parser.add_argument("globe", nargs="?", help="Globe name to validate (e.g., fish)")
    parser.add_argument("--all", action="store_true", help="Validate all globes")
    args = parser.parse_args()

    if args.all:
        globes = [d.name for d in OUTPUT_ROOT.iterdir() if d.is_dir()]
    elif args.globe:
        globes = [args.globe]
    else:
        parser.print_help()
        sys.exit(1)

    total_errors = 0
    for globe in globes:
        print(f"\nValidating {globe}...")
        errors = validate_globe(globe)
        if errors:
            print(f"  {len(errors)} error(s):")
            for e in errors[:20]:
                print(e)
            if len(errors) > 20:
                print(f"  ... and {len(errors) - 20} more")
        else:
            print("  All valid!")
        total_errors += len(errors)

    if total_errors:
        print(f"\n{total_errors} total error(s)")
        sys.exit(1)
    else:
        print("\nAll validations passed!")


if __name__ == "__main__":
    main()
