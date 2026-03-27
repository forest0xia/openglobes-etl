"""Merge curation/aquatic/selected.json with ETL species metadata into output/aquatic/final.json."""
import json
import math
import random
from collections import defaultdict
from pathlib import Path

from scripts.aquatic_groups import classify_group, classify_body_type

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


def resolve_sprite(species: dict, manifest: dict, taxonomy: dict) -> str:
    """Resolve sprite filename for a curated species using taxonomy classification."""
    sprites = manifest.get("sprites", {})
    group_fb = manifest.get("groupFallbacks", {})
    bt_fb = manifest.get("bodyTypeFallbacks", {})
    sci_name = species.get("name", "").strip().lower()

    # 1. Exact scientific name match in manifest
    for entry in sprites.values():
        if (entry.get("scientificName") or "").strip().lower() == sci_name:
            return entry["file"]

    # 2. Genus match
    genus = sci_name.split()[0] if " " in sci_name else ""
    if genus:
        for entry in sprites.values():
            if (entry.get("scientificName") or "").strip().lower() == genus:
                return entry["file"]

    # 3. Classify into group using taxonomy, then use group fallback
    group = classify_group(
        class_name=taxonomy.get("class", ""),
        order=taxonomy.get("order", ""),
        family=taxonomy.get("family", ""),
        phylum=taxonomy.get("phylum", ""),
    )
    if group in group_fb:
        return group_fb[group]

    # 4. Body type fallback
    body_type = classify_body_type(group)
    if body_type in bt_fb:
        return bt_fb[body_type]

    return bt_fb.get("fusiform", "sp-atlantic_cod.png")


def load_taxonomy_from_obis() -> dict:
    """Build scientific_name -> {family, order, class, phylum} from OBIS parquet."""
    obis_path = ROOT / "data" / "raw" / "aquatic" / "obis_occurrences.parquet"
    if not obis_path.exists():
        return {}
    try:
        import duckdb
        df = duckdb.sql(f"""
            SELECT DISTINCT scientific_name, family, "order", class, phylum
            FROM read_parquet('{obis_path}')
            WHERE scientific_name IS NOT NULL
        """).df()
        lookup = {}
        for _, row in df.iterrows():
            sn = str(row["scientific_name"]).strip().lower()
            if sn:
                lookup[sn] = {
                    "family": str(row.get("family", "") or ""),
                    "order": str(row.get("order", "") or ""),
                    "class": str(row.get("class", "") or ""),
                    "phylum": str(row.get("phylum", "") or ""),
                }
        return lookup
    except Exception as e:
        print(f"  WARNING: Could not load OBIS taxonomy: {e}")
        return {}


def jitter_overlapping_spots(species_list: list, radius_deg: float = 0.8, cluster_threshold: float = 0.3):
    """Spread apart viewing spots that share nearly-identical coordinates.

    Collects all viewing spots across all species, clusters those within
    cluster_threshold degrees, then distributes them in a uniform circle
    of radius_deg around the cluster centroid.  Uses a fixed seed for
    reproducibility.

    Args:
        species_list: The full species list (mutated in-place).
        radius_deg: Max jitter radius in degrees (~0.8° ≈ 90 km at equator).
        cluster_threshold: Spots within this distance are grouped together.
    """
    rng = random.Random(42)  # fixed seed for reproducibility

    # Collect all spots with back-references for mutation
    all_spots = []  # (lat, lng, species_idx, spot_idx)
    for si, sp in enumerate(species_list):
        for vi, vs in enumerate(sp.get("viewingSpots", [])):
            all_spots.append((vs["lat"], vs["lng"], si, vi))

    # Simple greedy clustering: group spots within threshold
    used = set()
    clusters = []
    for i, (lat1, lng1, si1, vi1) in enumerate(all_spots):
        if i in used:
            continue
        cluster = [i]
        used.add(i)
        for j, (lat2, lng2, si2, vi2) in enumerate(all_spots):
            if j in used:
                continue
            if abs(lat1 - lat2) < cluster_threshold and abs(lng1 - lng2) < cluster_threshold:
                cluster.append(j)
                used.add(j)
        if len(cluster) > 1:
            clusters.append(cluster)

    # Spread each cluster
    jittered_count = 0
    for cluster in clusters:
        n = len(cluster)
        # Centroid
        avg_lat = sum(all_spots[i][0] for i in cluster) / n
        avg_lng = sum(all_spots[i][1] for i in cluster) / n

        # Scale radius by cluster size — larger clusters spread more
        scaled_radius = radius_deg * min(1.0, 0.3 + 0.05 * n)

        # Place spots uniformly in a circle using sunflower pattern
        # (more uniform than pure random, avoids re-overlapping)
        golden_angle = math.pi * (3 - math.sqrt(5))
        indices = list(range(n))
        rng.shuffle(indices)  # randomize assignment to avoid bias

        for rank, ci in enumerate(indices):
            spot_idx_in_all = cluster[ci]
            _, _, si, vi = all_spots[spot_idx_in_all]

            # Sunflower spiral placement
            r = scaled_radius * math.sqrt((rank + 0.5) / n)
            theta = golden_angle * rank + rng.uniform(-0.3, 0.3)

            dlat = r * math.cos(theta)
            dlng = r * math.sin(theta) / max(math.cos(math.radians(avg_lat)), 0.1)

            spot = species_list[si]["viewingSpots"][vi]
            spot["lat"] = round(avg_lat + dlat, 4)
            spot["lng"] = round(avg_lng + dlng, 4)
            jittered_count += 1

    print(f"  Jittered {jittered_count} spots across {len(clusters)} clusters")


def merge():
    """Merge curation + ETL data into final output."""
    selected = json.loads((CURATION_DIR / "selected.json").read_text())
    hotspots = json.loads((CURATION_DIR / "hotspots.json").read_text())
    crosswalk = load_crosswalk()
    manifest = load_sprite_manifest()

    print("Loading taxonomy from OBIS...")
    taxonomy_lookup = load_taxonomy_from_obis()
    print(f"  {len(taxonomy_lookup)} species with taxonomy")

    final = []
    for species in selected:
        aphia_id = species.get("aphiaId")
        sci_name = species.get("name", "")
        entry = {
            # Curation fields
            "aphiaId": aphia_id,
            "tier": species.get("tier"),
            "name": sci_name,
            "nameZh": species.get("nameZh"),
            "tagline": species.get("tagline"),
            "viewingSpots": species.get("viewingSpots", []),
            "display": species.get("display"),
        }

        # ETL enrichment from crosswalk
        if aphia_id and aphia_id in crosswalk:
            cw = crosswalk[aphia_id]
            entry["scientificName"] = cw.get("scientificName", sci_name)
            fb_code = cw.get("fishbaseSpecCode")
            if fb_code and fb_code == fb_code:  # not NaN
                entry["fishbaseSpecCode"] = int(fb_code)
        else:
            entry["scientificName"] = sci_name

        # Taxonomy lookup and group classification
        taxonomy = taxonomy_lookup.get(sci_name.strip().lower(), {})
        group = classify_group(
            class_name=taxonomy.get("class", ""),
            order=taxonomy.get("order", ""),
            family=taxonomy.get("family", ""),
            phylum=taxonomy.get("phylum", ""),
        )
        entry["group"] = group
        entry["bodyType"] = classify_body_type(group)

        # Sprite resolution using taxonomy
        entry["sprite"] = resolve_sprite(species, manifest, taxonomy)

        final.append(entry)

    # Jitter overlapping coordinates so they don't pile up on the globe
    print("Spreading overlapping viewing spots...")
    jitter_overlapping_spots(final)

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
