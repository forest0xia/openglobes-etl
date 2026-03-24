# tests/test_sprite_manifest.py
from scripts.build_sprite_manifest import build_manifest, resolve_sprite


def test_resolve_sprite_exact_match():
    manifest = {
        "sprites": {"123": {"file": "sp-123.svg"}},
        "groupFallbacks": {"shark": "grp-shark.svg"},
        "bodyTypeFallbacks": {"fusiform": "fb-fusiform.svg"},
    }
    assert resolve_sprite("123", "shark", "fusiform", manifest) == "sp-123.svg"


def test_resolve_sprite_group_fallback():
    manifest = {
        "sprites": {},
        "groupFallbacks": {"shark": "grp-shark.svg"},
        "bodyTypeFallbacks": {"fusiform": "fb-fusiform.svg"},
    }
    assert resolve_sprite("999", "shark", "fusiform", manifest) == "grp-shark.svg"


def test_resolve_sprite_body_type_fallback():
    manifest = {
        "sprites": {},
        "groupFallbacks": {},
        "bodyTypeFallbacks": {"fusiform": "fb-fusiform.svg"},
    }
    assert resolve_sprite("999", "unknown_group", "fusiform", manifest) == "fb-fusiform.svg"


def test_resolve_sprite_ultimate_fallback():
    manifest = {
        "sprites": {},
        "groupFallbacks": {},
        "bodyTypeFallbacks": {"fusiform": "fb-fusiform.svg"},
    }
    assert resolve_sprite("999", "unknown", "unknown", manifest) == "fb-fusiform.svg"


def test_build_manifest_structure():
    sprites_dir_files = ["sp-123.svg", "grp-shark.svg", "fb-fusiform.svg"]
    species_data = {
        "123": {"name": "Great White", "scientificName": "Carcharodon carcharias",
                "group": "shark", "bodyType": "fusiform", "bodyGroup": "fish", "license": "CC0"}
    }
    group_fallbacks = {"shark": "grp-shark.svg"}
    body_type_fallbacks = {"fusiform": "fb-fusiform.svg"}

    manifest = build_manifest(species_data, group_fallbacks, body_type_fallbacks)
    assert manifest["version"] == "1.0.0"
    assert "123" in manifest["sprites"]
    assert manifest["sprites"]["123"]["file"] == "sp-123.svg"
    assert manifest["groupFallbacks"]["shark"] == "grp-shark.svg"
    assert "glowDefaults" in manifest
