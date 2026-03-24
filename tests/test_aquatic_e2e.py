# tests/test_aquatic_e2e.py
"""End-to-end test: small mock dataset through full aquatic pipeline."""
import json

import pandas as pd
from pathlib import Path

from scripts.aquatic_etl import (
    merge_occurrences, enrich_with_fishbase, apply_classifications,
    resolve_sprites_on_df, generate_species_details, generate_index,
)
from scripts.tile_splitter import split_tiles
from scripts.build_sprite_manifest import build_manifest, resolve_sprite
from scripts.build_aquatic_search_index import build_search_index


def test_e2e_pipeline(tmp_path):
    """Full pipeline with 10 mock species produces valid output."""
    # Mock OBIS data — 10 records for 8 distinct species
    obis = pd.DataFrame({
        "aphia_id": [137094, 137094, 105838, 105838, 123456,
                     234567, 345678, 456789, 567890, 678901],
        "lat": [47.6, 48.0, 10.0, 11.0, 35.0,
                -33.0, 60.0, 25.0, -10.0, 55.0],
        "lng": [-122.3, -122.5, 20.0, 21.0, 139.0,
                151.0, -5.0, -80.0, 45.0, 10.0],
        "scientific_name": [
            "Orcinus orca", "Orcinus orca",
            "Chelonia mydas", "Chelonia mydas",
            "Thunnus thynnus", "Carcharodon carcharias",
            "Gadus morhua", "Octopus vulgaris",
            "Aurelia aurita", "Hippocampus hippocampus",
        ],
        "class": ["Mammalia", "Mammalia", "Reptilia", "Reptilia",
                  "Actinopterygii", "Elasmobranchii", "Actinopterygii",
                  "Cephalopoda", "Scyphozoa", "Actinopterygii"],
        "order": ["Cetacea", "Cetacea", "Testudines", "Testudines",
                  "Scombriformes", "Lamniformes", "Gadiformes",
                  "Octopoda", "Semaeostomeae", "Syngnathiformes"],
        "family": ["Delphinidae", "Delphinidae", "Cheloniidae", "Cheloniidae",
                   "Scombridae", "Lamnidae", "Gadidae",
                   "Octopodidae", "Ulmaridae", "Syngnathidae"],
        "phylum": ["Chordata"] * 10,
    })

    # Mock GBIF data — 2 records with valid aphia_ids to test the merge path
    gbif = pd.DataFrame({
        "aphia_id": [137094, 345678],
        "lat": [47.7, 59.5],
        "lng": [-122.4, -4.5],
        "scientific_name": ["Orcinus orca", "Gadus morhua"],
        "class": ["Mammalia", "Actinopterygii"],
        "order": ["Cetacea", "Gadiformes"],
        "family": ["Delphinidae", "Gadidae"],
        "phylum": ["Chordata", "Chordata"],
    })

    # 1. Merge — should deduplicate
    merged = merge_occurrences(obis, gbif)
    assert len(merged) >= 8, f"Expected >= 8 deduped points, got {len(merged)}"
    # GBIF records should be included (orca near Seattle, cod near UK)
    assert len(merged) <= 12, "Should be fewer than 12 after dedup"

    # 2. Enrich with FishBase (partial match — only tuna and cod)
    fishbase = pd.DataFrame({
        "Genus": ["Thunnus", "Gadus"],
        "Species": ["thynnus", "morhua"],
        "SpecCode": [147, 69],
        "FBname": ["Atlantic bluefin tuna", "Atlantic cod"],
        "PicPreferredName": ["Ththyn_u0.jpg", "Gamo_u0.jpg"],
        "Vulnerability": [74.0, 59.0],
        "DepthRangeDeep": [985, 600],
        "Fresh": [0, 0],
        "Brack": [0, 1],
        "Saltwater": [1, 1],
    })
    enriched = enrich_with_fishbase(merged, fishbase)
    assert "common_name" in enriched.columns
    # Tuna should have FishBase common name
    tuna_rows = enriched[enriched["scientific_name"] == "Thunnus thynnus"]
    if len(tuna_rows) > 0:
        assert tuna_rows.iloc[0]["common_name"] == "Atlantic bluefin tuna"
    # Non-fish species should fall back to scientific name as common_name
    jelly_rows = enriched[enriched["scientific_name"] == "Aurelia aurita"]
    if len(jelly_rows) > 0:
        assert jelly_rows.iloc[0]["common_name"] == "Aurelia aurita"

    # 3. Classify — check group assignments
    enriched = apply_classifications(enriched)
    assert "group" in enriched.columns
    assert "body_type" in enriched.columns
    assert "body_group" in enriched.columns
    groups_present = set(enriched["group"].values)
    assert "dolphin" in groups_present, f"Expected 'dolphin' in groups, got {groups_present}"
    assert "sea_turtle" in groups_present, f"Expected 'sea_turtle' in groups, got {groups_present}"
    assert "jellyfish" in groups_present, f"Expected 'jellyfish' in groups, got {groups_present}"
    assert "tuna_mackerel" in groups_present, f"Expected 'tuna_mackerel' in groups, got {groups_present}"
    assert "shark" in groups_present, f"Expected 'shark' in groups, got {groups_present}"
    assert "seahorse" in groups_present, f"Expected 'seahorse' in groups, got {groups_present}"

    # 4. Build mock sprite manifest with group + body type fallbacks
    manifest = build_manifest(
        species_data={},
        group_fallbacks={
            "dolphin": "grp-dolphin.svg",
            "shark": "grp-shark.svg",
            "sea_turtle": "grp-sea_turtle.svg",
        },
        body_type_fallbacks={
            "fusiform": "fb-fusiform.svg",
            "cetacean": "fb-cetacean.svg",
            "flat": "fb-flat.svg",
            "cephalopod": "fb-cephalopod.svg",
            "jellyfish": "fb-jellyfish.svg",
            "seahorse": "fb-seahorse.svg",
            "elongated": "fb-elongated.svg",
            "globular": "fb-globular.svg",
            "deep-bodied": "fb-deep-bodied.svg",
            "crustacean": "fb-crustacean.svg",
        },
    )

    # 5. Resolve sprites — every row must have a non-null sprite
    enriched["id"] = enriched["aphia_id"].astype(str)
    enriched["name"] = enriched["common_name"]
    enriched["rarity"] = 1
    enriched = resolve_sprites_on_df(enriched, manifest)
    assert enriched["sprite"].notna().all(), "All rows must have a resolved sprite"
    # Dolphin should get group fallback
    dolphin_rows = enriched[enriched["group"] == "dolphin"]
    if len(dolphin_rows) > 0:
        assert dolphin_rows.iloc[0]["sprite"] == "grp-dolphin.svg"

    # 6. Tile generation
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    enriched["waterType"] = enriched.get("water_type", pd.Series(["Saltwater"] * len(enriched)))
    enriched["bodyGroup"] = enriched["body_group"]
    enriched["bodyType"] = enriched["body_type"]
    enriched["nameZh"] = None
    enriched["thumb"] = enriched.get("thumb", pd.Series([None] * len(enriched)))
    enriched["precision"] = "exact"

    tile_stats = split_tiles(
        enriched, output_dir,
        filter_agg_keys=["waterType", "bodyGroup"],
        top_items_fields=["id", "name", "sprite", "group"],
        point_fields=["id", "lat", "lng", "name", "sprite", "group", "rarity", "waterType"],
        group_distribution_key="group",
    )

    # Verify tile output structure
    tiles_dir = output_dir / "tiles"
    assert tiles_dir.is_dir()
    assert (tiles_dir / "z0").is_dir()
    tile_files = list(tiles_dir.rglob("*.json"))
    assert len(tile_files) > 0, "Should have generated at least one tile"

    # Verify a cluster tile has expected structure
    z0_files = list((tiles_dir / "z0").glob("*.json"))
    assert len(z0_files) > 0
    sample_tile = json.loads(z0_files[0].read_text())
    assert "clusters" in sample_tile
    assert "zoom" in sample_tile
    assert sample_tile["zoom"] == 0

    # Verify a point tile (z7) has expected structure
    z7_dir = tiles_dir / "z7"
    if z7_dir.exists():
        z7_files = list(z7_dir.glob("*.json"))
        if z7_files:
            pt = json.loads(z7_files[0].read_text())
            assert "points" in pt
            # Points should have sprite field
            for p in pt["points"]:
                assert "sprite" in p, f"Point missing sprite field: {p}"

    # 7. Species detail files
    generate_species_details(enriched, output_dir)
    species_dir = output_dir / "species"
    assert species_dir.is_dir()
    species_files = list(species_dir.glob("*.json"))
    assert len(species_files) >= 8, f"Expected >= 8 species files, got {len(species_files)}"

    # Verify species detail structure
    sample_detail = json.loads(species_files[0].read_text())
    assert "sprite" in sample_detail
    assert "group" in sample_detail
    assert "bodyType" in sample_detail
    assert "bodyGroup" in sample_detail
    assert sample_detail["sprite"] is not None

    # 8. Index file
    generate_index(enriched, output_dir)
    index_path = output_dir / "index.json"
    assert index_path.exists()
    index = json.loads(index_path.read_text())
    assert index["globeId"] == "aquatic"
    assert index["totalItems"] > 0
    assert "filters" in index
    assert len(index["filters"]) >= 2

    # 9. Search index
    search_idx = build_search_index(enriched)
    assert "groups" in search_idx
    assert "bySpecId" in search_idx
    assert len(search_idx["groups"]) >= 5, (
        f"Expected >= 5 groups in search index, got {len(search_idx['groups'])}"
    )
    # Verify some expected groups are present
    assert "dolphin" in search_idx["groups"]
    assert "sea_turtle" in search_idx["groups"]
    assert "jellyfish" in search_idx["groups"]
    # Each group should have label and specIds
    for gid, gdata in search_idx["groups"].items():
        assert "label" in gdata, f"Group {gid} missing label"
        assert "specIds" in gdata, f"Group {gid} missing specIds"
        assert len(gdata["specIds"]) > 0, f"Group {gid} has no species"
