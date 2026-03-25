"""Tests for scripts/validate.py — sprite validation, groupDistribution, sprite dir, and curated model."""

import json
from pathlib import Path

from scripts.validate import (
    validate_point_tile,
    validate_cluster_tile,
    validate_detail,
    validate_sprites_dir,
    validate_curated_final,
)


# ---------------------------------------------------------------------------
# Point tile sprite validation
# ---------------------------------------------------------------------------


def test_point_tile_requires_sprite(tmp_path):
    """When require_sprite=True, points missing 'sprite' should produce errors."""
    tile = {
        "zoom": 4, "x": 0, "y": 0,
        "points": [{"id": "1", "lat": 10.0, "lng": 20.0, "name": "Test"}],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(tile))
    errors = validate_point_tile(p, require_sprite=True)
    assert any("sprite" in str(e) for e in errors)


def test_point_tile_no_sprite_required_by_default(tmp_path):
    """Default (require_sprite=False) should NOT complain about missing sprite."""
    tile = {
        "zoom": 4, "x": 0, "y": 0,
        "points": [{"id": "1", "lat": 10.0, "lng": 20.0, "name": "Test"}],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(tile))
    errors = validate_point_tile(p)
    assert not any("sprite" in str(e) for e in errors)


def test_point_tile_sprite_present_no_error(tmp_path):
    """When require_sprite=True and sprite IS present, no sprite error."""
    tile = {
        "zoom": 4, "x": 0, "y": 0,
        "points": [{"id": "1", "lat": 10.0, "lng": 20.0, "name": "Test", "sprite": "shark_generic.svg"}],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(tile))
    errors = validate_point_tile(p, require_sprite=True)
    assert not any("sprite" in str(e) for e in errors)


def test_point_tile_sprite_null_is_error(tmp_path):
    """sprite=null should still be flagged when require_sprite=True."""
    tile = {
        "zoom": 4, "x": 0, "y": 0,
        "points": [{"id": "1", "lat": 10.0, "lng": 20.0, "name": "Test", "sprite": None}],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(tile))
    errors = validate_point_tile(p, require_sprite=True)
    assert any("sprite" in str(e) for e in errors)


# ---------------------------------------------------------------------------
# Cluster tile sprite + groupDistribution validation
# ---------------------------------------------------------------------------


def test_cluster_tile_requires_sprite_on_topitems(tmp_path):
    """When require_sprite=True, topItems missing 'sprite' should produce errors."""
    tile = {
        "zoom": 1, "x": 0, "y": 0,
        "clusters": [{
            "lat": 10.0, "lng": 20.0, "count": 5,
            "topItems": [{"id": "1", "name": "Test"}],
            "groupDistribution": {"shark": 3, "ray": 2},
        }],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(tile))
    errors = validate_cluster_tile(p, require_sprite=True)
    assert any("sprite" in str(e) for e in errors)


def test_cluster_tile_requires_group_distribution(tmp_path):
    """When require_sprite=True, clusters missing groupDistribution should error."""
    tile = {
        "zoom": 1, "x": 0, "y": 0,
        "clusters": [{
            "lat": 10.0, "lng": 20.0, "count": 5,
        }],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(tile))
    errors = validate_cluster_tile(p, require_sprite=True)
    assert any("groupDistribution" in str(e) for e in errors)


def test_cluster_tile_no_sprite_required_by_default(tmp_path):
    """Default (require_sprite=False) should NOT complain about missing sprite/groupDistribution."""
    tile = {
        "zoom": 1, "x": 0, "y": 0,
        "clusters": [{"lat": 10.0, "lng": 20.0, "count": 5}],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(tile))
    errors = validate_cluster_tile(p)
    assert not any("sprite" in str(e) for e in errors)
    assert not any("groupDistribution" in str(e) for e in errors)


def test_cluster_tile_sprite_present_no_error(tmp_path):
    """When require_sprite=True and all topItems have sprite, no sprite error."""
    tile = {
        "zoom": 1, "x": 0, "y": 0,
        "clusters": [{
            "lat": 10.0, "lng": 20.0, "count": 5,
            "topItems": [{"id": "1", "name": "Test", "sprite": "orca.svg"}],
            "groupDistribution": {"dolphin": 5},
        }],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(tile))
    errors = validate_cluster_tile(p, require_sprite=True)
    assert not any("sprite" in str(e) for e in errors)
    assert not any("groupDistribution" in str(e) for e in errors)


# ---------------------------------------------------------------------------
# Detail file sprite validation
# ---------------------------------------------------------------------------


def test_detail_requires_sprite_fields(tmp_path):
    """When require_sprite=True, detail files need sprite, group, bodyType, bodyGroup."""
    detail = {"id": "123", "name": "Test Fish", "scientificName": "Testus fishus"}
    p = tmp_path / "123.json"
    p.write_text(json.dumps(detail))
    errors = validate_detail(p, require_sprite=True)
    assert any("sprite" in str(e) for e in errors)
    assert any("group" in str(e) for e in errors)
    assert any("bodyType" in str(e) for e in errors)
    assert any("bodyGroup" in str(e) for e in errors)


def test_detail_no_sprite_required_by_default(tmp_path):
    """Default should NOT require sprite fields."""
    detail = {"id": "123", "name": "Test Fish", "scientificName": "Testus fishus"}
    p = tmp_path / "123.json"
    p.write_text(json.dumps(detail))
    errors = validate_detail(p)
    assert not any("sprite" in str(e) for e in errors)
    assert not any("group" in str(e) for e in errors)
    assert not any("bodyType" in str(e) for e in errors)
    assert not any("bodyGroup" in str(e) for e in errors)


def test_detail_sprite_fields_present_no_error(tmp_path):
    """When all sprite fields present, no errors."""
    detail = {
        "id": "123", "name": "Test Fish", "scientificName": "Testus fishus",
        "sprite": "shark_generic.svg", "group": "shark",
        "bodyType": "fusiform", "bodyGroup": "fish",
    }
    p = tmp_path / "123.json"
    p.write_text(json.dumps(detail))
    errors = validate_detail(p, require_sprite=True)
    assert not any("sprite" in str(e) for e in errors)
    assert not any("group" in str(e) for e in errors)
    assert not any("bodyType" in str(e) for e in errors)
    assert not any("bodyGroup" in str(e) for e in errors)


# ---------------------------------------------------------------------------
# Sprites directory validation
# ---------------------------------------------------------------------------


def test_validate_sprites_dir_missing_manifest(tmp_path):
    """Missing manifest.json should produce an error."""
    sprites_dir = tmp_path / "sprites"
    sprites_dir.mkdir()
    errors = validate_sprites_dir(tmp_path)
    assert any("manifest.json" in str(e) for e in errors)


def test_validate_sprites_dir_missing_sprite_file(tmp_path):
    """Manifest referencing a non-existent SVG should produce an error."""
    sprites_dir = tmp_path / "sprites"
    sprites_dir.mkdir()
    manifest = {
        "sprites": {
            "orca": {"file": "orca.svg", "group": "dolphin", "bodyType": "cetacean"},
        },
        "groupFallbacks": {},
        "bodyTypeFallbacks": {},
    }
    (sprites_dir / "manifest.json").write_text(json.dumps(manifest))
    errors = validate_sprites_dir(tmp_path)
    assert any("Missing sprite file" in str(e) for e in errors)


def test_validate_sprites_dir_oversized_svg(tmp_path):
    """SVG larger than 3KB should produce an error."""
    sprites_dir = tmp_path / "sprites"
    sprites_dir.mkdir()
    manifest = {
        "sprites": {
            "orca": {"file": "orca.svg", "group": "dolphin", "bodyType": "cetacean"},
        },
        "groupFallbacks": {},
        "bodyTypeFallbacks": {},
    }
    (sprites_dir / "manifest.json").write_text(json.dumps(manifest))
    # Create an oversized SVG (>3072 bytes)
    (sprites_dir / "orca.svg").write_text("x" * 4000)
    errors = validate_sprites_dir(tmp_path)
    assert any("SVG too large" in str(e) for e in errors)


def test_validate_sprites_dir_valid(tmp_path):
    """Valid manifest + existing files = no errors."""
    sprites_dir = tmp_path / "sprites"
    sprites_dir.mkdir()
    manifest = {
        "sprites": {
            "orca": {"file": "orca.svg", "group": "dolphin", "bodyType": "cetacean"},
        },
        "groupFallbacks": {"dolphin": "dolphin_generic.svg"},
        "bodyTypeFallbacks": {"cetacean": "cetacean_fallback.svg"},
    }
    (sprites_dir / "manifest.json").write_text(json.dumps(manifest))
    (sprites_dir / "orca.svg").write_text('<svg viewBox="0 0 100 100"></svg>')
    (sprites_dir / "dolphin_generic.svg").write_text('<svg viewBox="0 0 100 100"></svg>')
    (sprites_dir / "cetacean_fallback.svg").write_text('<svg viewBox="0 0 100 100"></svg>')
    errors = validate_sprites_dir(tmp_path)
    assert len(errors) == 0


def test_validate_sprites_dir_missing_group_fallback(tmp_path):
    """Missing group fallback file should produce an error."""
    sprites_dir = tmp_path / "sprites"
    sprites_dir.mkdir()
    manifest = {
        "sprites": {},
        "groupFallbacks": {"shark": "shark_generic.svg"},
        "bodyTypeFallbacks": {},
    }
    (sprites_dir / "manifest.json").write_text(json.dumps(manifest))
    errors = validate_sprites_dir(tmp_path)
    assert any("Missing group fallback" in str(e) for e in errors)


def test_validate_sprites_dir_missing_body_type_fallback(tmp_path):
    """Missing body type fallback file should produce an error."""
    sprites_dir = tmp_path / "sprites"
    sprites_dir.mkdir()
    manifest = {
        "sprites": {},
        "groupFallbacks": {},
        "bodyTypeFallbacks": {"fusiform": "fusiform_fallback.svg"},
    }
    (sprites_dir / "manifest.json").write_text(json.dumps(manifest))
    errors = validate_sprites_dir(tmp_path)
    assert any("Missing body type fallback" in str(e) for e in errors)


# ---------------------------------------------------------------------------
# Backward compatibility: existing fish validation still works
# ---------------------------------------------------------------------------


def test_existing_point_tile_validation_still_works(tmp_path):
    """Standard point tile without sprite fields should pass when require_sprite=False."""
    tile = {
        "zoom": 4, "x": 0, "y": 0,
        "points": [
            {"id": "1", "lat": 10.0, "lng": 20.0, "name": "Clownfish"},
            {"id": "2", "lat": -10.0, "lng": -20.0, "name": "Tuna"},
        ],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(tile))
    errors = validate_point_tile(p)
    assert len(errors) == 0


def test_existing_cluster_tile_validation_still_works(tmp_path):
    """Standard cluster tile without sprite fields should pass when require_sprite=False."""
    tile = {
        "zoom": 1, "x": 0, "y": 0,
        "clusters": [
            {"lat": 10.0, "lng": 20.0, "count": 42},
        ],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(tile))
    errors = validate_cluster_tile(p)
    assert len(errors) == 0


def test_existing_detail_validation_still_works(tmp_path):
    """Standard detail file without sprite fields should pass when require_sprite=False."""
    detail = {"id": "123", "name": "Test Fish", "scientificName": "Testus fishus"}
    p = tmp_path / "123.json"
    p.write_text(json.dumps(detail))
    errors = validate_detail(p)
    assert len(errors) == 0


# ---------------------------------------------------------------------------
# Curated final.json validation (aquatic globe)
# ---------------------------------------------------------------------------


def _make_curated_species(aphia_id, name, tier="star", spots=None):
    """Helper to build a minimal valid curated species entry."""
    if spots is None:
        spots = [{
            "name": "Test Reef", "country": "US", "lat": 25.0, "lng": -80.0,
            "season": "year-round", "reliability": "high", "activity": "diving",
        }]
    return {
        "aphiaId": aphia_id,
        "name": name,
        "tier": tier,
        "viewingSpots": spots,
        "display": {"scale": 1.0},
        "sprite": f"sp-{aphia_id}.png",
    }


def _write_curated_output(tmp_path, species_list, hotspots=None):
    """Write final.json, hotspots.json, and a minimal sprites dir."""
    globe_dir = tmp_path / "aquatic"
    globe_dir.mkdir(parents=True, exist_ok=True)
    (globe_dir / "final.json").write_text(json.dumps(species_list))
    if hotspots is None:
        hotspots = []
    (globe_dir / "hotspots.json").write_text(json.dumps(hotspots))
    # Minimal sprites dir with manifest
    sprites_dir = globe_dir / "sprites"
    sprites_dir.mkdir()
    manifest = {"sprites": {}, "groupFallbacks": {}, "bodyTypeFallbacks": {}}
    (sprites_dir / "manifest.json").write_text(json.dumps(manifest))
    return globe_dir


def test_curated_final_valid(tmp_path):
    """A valid curated final.json should produce no errors (beyond tier count deviations)."""
    species = []
    for i in range(50):
        species.append(_make_curated_species(i, f"Star {i}", "star"))
    for i in range(50, 130):
        species.append(_make_curated_species(i, f"Eco {i}", "ecosystem"))
    for i in range(130, 200):
        species.append(_make_curated_species(i, f"Surprise {i}", "surprise"))
    globe_dir = _write_curated_output(tmp_path, species)
    errors = validate_curated_final(globe_dir)
    assert len(errors) == 0, f"Unexpected errors: {errors}"


def test_curated_final_missing_required_fields(tmp_path):
    """Species missing required fields should produce errors."""
    species = [{"name": "Incomplete"}]  # missing aphiaId, tier, viewingSpots, display
    globe_dir = _write_curated_output(tmp_path, species)
    errors = validate_curated_final(globe_dir)
    error_msgs = [str(e) for e in errors]
    assert any("aphiaId" in m for m in error_msgs)
    assert any("tier" in m for m in error_msgs)
    assert any("display" in m for m in error_msgs)


def test_curated_final_duplicate_aphia_id(tmp_path):
    """Duplicate aphiaIds should produce an error."""
    species = [
        _make_curated_species(100, "Species A"),
        _make_curated_species(100, "Species B"),
    ]
    globe_dir = _write_curated_output(tmp_path, species)
    errors = validate_curated_final(globe_dir)
    assert any("Duplicate aphiaId" in str(e) for e in errors)


def test_curated_final_spot_lat_out_of_range(tmp_path):
    """Viewing spots with lat > 90 should error."""
    bad_spot = [{
        "name": "Bad Spot", "country": "US", "lat": 95.0, "lng": 0.0,
        "season": "year-round", "reliability": "high", "activity": "diving",
    }]
    species = [_make_curated_species(1, "Test", spots=bad_spot)]
    globe_dir = _write_curated_output(tmp_path, species)
    errors = validate_curated_final(globe_dir)
    assert any("lat out of range" in str(e) for e in errors)


def test_curated_final_missing_final_json(tmp_path):
    """Missing final.json should produce an error."""
    globe_dir = tmp_path / "aquatic"
    globe_dir.mkdir(parents=True)
    errors = validate_curated_final(globe_dir)
    assert any("final.json missing" in str(e) for e in errors)


def test_curated_final_missing_hotspots_json(tmp_path):
    """Missing hotspots.json should produce an error."""
    species = [_make_curated_species(1, "Test")]
    globe_dir = tmp_path / "aquatic"
    globe_dir.mkdir(parents=True)
    (globe_dir / "final.json").write_text(json.dumps(species))
    # No hotspots.json, no sprites dir
    errors = validate_curated_final(globe_dir)
    assert any("hotspots.json missing" in str(e) for e in errors)
