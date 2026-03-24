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
        elif svg_path.stat().st_size > 3072:
            errors.append(ValidationError(str(svg_path), f"SVG too large: {svg_path.stat().st_size}B > 3KB"))

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


def validate_globe(globe: str) -> list[ValidationError]:
    globe_dir = OUTPUT_ROOT / globe
    if not globe_dir.exists():
        return [ValidationError(str(globe_dir), "Output directory does not exist")]

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
