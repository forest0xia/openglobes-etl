# scripts/build_sprite_manifest.py
"""Generate sprite manifest.json with pre-resolved fallback chain."""
import json
from pathlib import Path

from scripts.aquatic_groups import BODY_TYPES, GROUPS

ROOT = Path(__file__).resolve().parent.parent
SPRITE_OUTPUT_DIR = ROOT / "output" / "aquatic" / "sprites"


def build_sprite_indices(manifest: dict) -> dict:
    """Pre-build lookup indices from manifest for fast vectorized resolution.

    Returns dict with:
      - sci_name: {lowercase_name: sprite_file}  (exact + genus prefix)
      - group: {group_key: sprite_file}
      - body_type: {body_type: sprite_file}
      - default: fallback sprite file
    """
    sci_name_idx = {}
    group_idx = dict(manifest.get("groupFallbacks", {}))
    body_type_idx = dict(manifest.get("bodyTypeFallbacks", {}))

    for _key, entry in manifest.get("sprites", {}).items():
        sname = (entry.get("scientificName") or "").strip().lower()
        if sname:
            sci_name_idx[sname] = entry["file"]
        # Also populate group/body_type from sprites if not already in fallbacks
        g = entry.get("group", "")
        if g and g not in group_idx:
            group_idx[g] = entry["file"]
        bt = entry.get("bodyType", "")
        if bt and bt not in body_type_idx:
            body_type_idx[bt] = entry["file"]

    default = body_type_idx.get("fusiform", "sp-atlantic_cod.png")
    return {"sci_name": sci_name_idx, "group": group_idx,
            "body_type": body_type_idx, "default": default}


def resolve_sprite(species_id: str, group: str, body_type: str, manifest: dict,
                   scientific_name: str = "") -> str:
    """Walk the fallback chain and return the resolved sprite filename.

    Tries: exact scientific name -> genus prefix -> group fallback -> body_type fallback.
    """
    sprites = manifest.get("sprites", {})
    # 1. Exact scientific name match
    sci_lower = scientific_name.strip().lower() if scientific_name else ""
    if sci_lower:
        for entry in sprites.values():
            if (entry.get("scientificName") or "").strip().lower() == sci_lower:
                return entry["file"]
        # 1b. Genus-level match (first word of scientific name)
        genus = sci_lower.split()[0] if " " in sci_lower else ""
        if genus:
            for entry in sprites.values():
                if (entry.get("scientificName") or "").strip().lower() == genus:
                    return entry["file"]
    # 2. Group fallback
    if group in manifest.get("groupFallbacks", {}):
        return manifest["groupFallbacks"][group]
    # Try group from sprites directly
    for entry in sprites.values():
        if entry.get("group") == group:
            return entry["file"]
    # 3. Body type fallback
    if body_type in manifest.get("bodyTypeFallbacks", {}):
        return manifest["bodyTypeFallbacks"][body_type]
    for entry in sprites.values():
        if entry.get("bodyType") == body_type:
            return entry["file"]
    # 4. Ultimate fallback
    return manifest.get("bodyTypeFallbacks", {}).get("fusiform", "sp-atlantic_cod.png")


def build_manifest(species_data: dict, group_fallbacks: dict,
                   body_type_fallbacks: dict) -> dict:
    """Build the full manifest.json structure."""
    sprites = {}
    for sid, data in species_data.items():
        sprites[sid] = {
            "file": f"sp-{sid}.png",
            "name": data.get("name", ""),
            "scientificName": data.get("scientificName", ""),
            "group": data.get("group", "other"),
            "bodyType": data.get("bodyType", "fusiform"),
            "bodyGroup": data.get("bodyGroup", "other"),
            "license": data.get("license", "unknown"),
        }

    total = len(sprites) + len(group_fallbacks) + len(body_type_fallbacks)

    return {
        "version": "1.0.0",
        "glowDefaults": {
            "color": "#00E5FF",
            "blur": "4px",
            "note": "Apply via CSS filter: drop-shadow(0 0 {blur} {color})",
        },
        "bodyTypes": BODY_TYPES,
        "sprites": sprites,
        "groupFallbacks": group_fallbacks,
        "bodyTypeFallbacks": body_type_fallbacks,
        "totalSprites": total,
        "note": "Fallback chain: sprites[speciesId] -> groupFallbacks[group] -> bodyTypeFallbacks[bodyType]. Resolved at ETL time.",
    }


def write_manifest(manifest: dict):
    """Write manifest.json to output directory."""
    SPRITE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = SPRITE_OUTPUT_DIR / "manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Manifest written to {out} ({manifest['totalSprites']} sprites)")


def main():
    """CLI: build manifest from normalized sprites and species data.

    If an existing manifest.json exists, preserves its sprite metadata (group, bodyType, etc.)
    and only adds/removes entries based on actual sp-*.png files present on disk.
    """
    sprites_dir = SPRITE_OUTPUT_DIR
    final_dir = SPRITE_OUTPUT_DIR / "final"
    search_dir = final_dir if final_dir.exists() else sprites_dir
    manifest_path = SPRITE_OUTPUT_DIR / "manifest.json"

    # Load existing manifest to preserve curated metadata
    existing_sprites = {}
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text())
        existing_sprites = existing.get("sprites", {})

    # Scan for all sp-*.png files on disk
    species_data = {}
    for sprite_file in sorted(search_dir.glob("sp-*.png")):
        key = sprite_file.stem.replace("sp-", "")
        if key in existing_sprites:
            # Preserve existing curated metadata
            e = existing_sprites[key]
            species_data[key] = {
                "name": e.get("name", key.replace("_", " ").title()),
                "scientificName": e.get("scientificName", ""),
                "group": e.get("group", "other"),
                "bodyType": e.get("bodyType", "fusiform"),
                "bodyGroup": e.get("bodyGroup", "other"),
                "license": e.get("license", "generated"),
            }
        else:
            # New sprite not in existing manifest
            readable_name = key.replace("_", " ").title()
            species_data[key] = {
                "name": readable_name,
                "scientificName": readable_name,
                "group": "other",
                "bodyType": "fusiform",
                "bodyGroup": "other",
                "license": "generated",
            }

    # Build group fallbacks: prefer grp-* files, else first species sprite per group
    group_fallbacks = {}
    for f in list(search_dir.glob("grp-*.png")) + list(search_dir.glob("grp-*.svg")):
        group_fallbacks[f.stem.replace("grp-", "")] = f.name
    for sid, data in species_data.items():
        g = data.get("group", "")
        if g and g not in group_fallbacks:
            group_fallbacks[g] = f"sp-{sid}.png"

    # Build body type fallbacks: prefer fb-* files, else first species sprite per body type
    body_type_fallbacks = {}
    for f in list(search_dir.glob("fb-*.png")) + list(search_dir.glob("fb-*.svg")):
        body_type_fallbacks[f.stem.replace("fb-", "")] = f.name
    for sid, data in species_data.items():
        bt = data.get("bodyType", "")
        if bt and bt not in body_type_fallbacks:
            body_type_fallbacks[bt] = f"sp-{sid}.png"

    manifest = build_manifest(species_data, group_fallbacks, body_type_fallbacks)
    write_manifest(manifest)


if __name__ == "__main__":
    main()
