# tests/test_aquatic_etl.py
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd

from scripts.aquatic_etl import download_obis, download_gbif, RAW_DIR
from scripts.aquatic_etl import merge_occurrences, build_id_crosswalk, enrich_with_fishbase
from scripts.aquatic_etl import apply_classifications

def test_download_obis_skips_if_exists(tmp_path):
    """download_obis should skip if parquet already exists."""
    fake_file = tmp_path / "obis_occurrences.parquet"
    fake_file.write_text("exists")
    with patch("scripts.aquatic_etl.RAW_DIR", tmp_path):
        download_obis()  # should not raise, should skip
    assert fake_file.read_text() == "exists"  # unchanged

def test_raw_dir_is_aquatic():
    assert "aquatic" in str(RAW_DIR)

def test_download_gbif_skips_if_exists(tmp_path):
    fake_file = tmp_path / "gbif_occurrences.csv"
    fake_file.write_text("exists")
    with patch("scripts.aquatic_etl.RAW_DIR", tmp_path):
        download_gbif()
    assert fake_file.read_text() == "exists"


def test_merge_deduplicates():
    """Same species at same z7 tile should deduplicate to one point."""
    obis = pd.DataFrame({
        "aphia_id": [123, 123, 456],
        "lat": [47.6, 47.601, 10.0],  # first two are same z7 tile
        "lng": [-122.3, -122.301, 20.0],
        "scientific_name": ["Orcinus orca", "Orcinus orca", "Thunnus thynnus"],
        "class": ["Mammalia", "Mammalia", "Actinopterygii"],
        "order": ["Cetacea", "Cetacea", "Scombriformes"],
        "family": ["Delphinidae", "Delphinidae", "Scombridae"],
        "phylum": ["Chordata", "Chordata", "Chordata"],
    })
    gbif = pd.DataFrame({
        "aphia_id": [123, 789],
        "lat": [47.602, 35.0],
        "lng": [-122.302, 139.0],
        "scientific_name": ["Orcinus orca", "Chelonia mydas"],
        "class": ["Mammalia", "Reptilia"],
        "order": ["Cetacea", "Testudines"],
        "family": ["Delphinidae", "Cheloniidae"],
        "phylum": ["Chordata", "Chordata"],
    })
    merged = merge_occurrences(obis, gbif)
    # Orcas near Seattle should dedup to ~1 point at z7
    orca_points = merged[merged["aphia_id"] == 123]
    assert len(orca_points) <= 2  # deduped from 3 to ~1-2


def test_merge_filters_invalid_coords():
    """merge_occurrences should drop rows with out-of-range lat/lng or NaN."""
    obis = pd.DataFrame({
        "aphia_id": [100, 200, 300],
        "lat": [91.0, float("nan"), 10.0],
        "lng": [0.0, 0.0, 20.0],
        "scientific_name": ["A", "B", "C"],
        "class": ["X", "X", "X"],
        "order": ["X", "X", "X"],
        "family": ["X", "X", "X"],
        "phylum": ["X", "X", "X"],
    })
    gbif = pd.DataFrame(columns=obis.columns)
    merged = merge_occurrences(obis, gbif)
    assert len(merged) == 1
    assert merged.iloc[0]["aphia_id"] == 300


def test_merge_rounds_coords():
    """Merged lat/lng should be rounded to 4 decimal places."""
    obis = pd.DataFrame({
        "aphia_id": [100],
        "lat": [10.123456789],
        "lng": [20.987654321],
        "scientific_name": ["A"],
        "class": ["X"],
        "order": ["X"],
        "family": ["X"],
        "phylum": ["X"],
    })
    gbif = pd.DataFrame(columns=obis.columns)
    merged = merge_occurrences(obis, gbif)
    assert merged.iloc[0]["lat"] == 10.1235
    assert merged.iloc[0]["lng"] == 20.9877


def test_build_crosswalk():
    df = pd.DataFrame({
        "aphia_id": [123, 456],
        "scientific_name": ["Orcinus orca", "Thunnus thynnus"],
    })
    crosswalk = build_id_crosswalk(df)
    assert 123 in crosswalk
    assert crosswalk[123]["scientificName"] == "Orcinus orca"
    assert 456 in crosswalk
    assert crosswalk[456]["scientificName"] == "Thunnus thynnus"


def test_build_crosswalk_deduplicates():
    """build_id_crosswalk should keep only one entry per aphia_id."""
    df = pd.DataFrame({
        "aphia_id": [123, 123, 456],
        "scientific_name": ["Orcinus orca", "Orcinus orca", "Thunnus thynnus"],
    })
    crosswalk = build_id_crosswalk(df)
    assert len(crosswalk) == 2


def test_enrich_adds_fishbase_metadata():
    occurrences = pd.DataFrame({
        "aphia_id": [123, 456],
        "lat": [47.6, 10.0],
        "lng": [-122.3, 20.0],
        "scientific_name": ["Thunnus thynnus", "Chelonia mydas"],
        "class": ["Actinopterygii", "Reptilia"],
        "order": ["Scombriformes", "Testudines"],
        "family": ["Scombridae", "Cheloniidae"],
        "phylum": ["Chordata", "Chordata"],
    })
    fishbase = pd.DataFrame({
        "scientific_name": ["Thunnus thynnus"],
        "SpecCode": [147],
        "FBname": ["Atlantic bluefin tuna"],
        "PicPreferredName": ["Ththyn_u0.jpg"],
        "Vulnerability": [74.0],
        "DepthRangeDeep": [985],
        "Fresh": [0], "Brack": [0], "Saltwater": [1],
    })
    result = enrich_with_fishbase(occurrences, fishbase)
    tuna = result[result["aphia_id"] == 123].iloc[0]
    assert tuna["common_name"] == "Atlantic bluefin tuna"
    assert tuna["thumb"] == "tn_Ththyn_u0.jpg"
    # Non-fish species should have null fishbase fields
    turtle = result[result["aphia_id"] == 456].iloc[0]
    assert pd.isna(turtle.get("thumb")) or turtle.get("thumb") is None


def test_enrich_with_genus_species_columns():
    """enrich_with_fishbase should build scientific_name from Genus+Species columns."""
    occurrences = pd.DataFrame({
        "aphia_id": [123],
        "lat": [47.6],
        "lng": [-122.3],
        "scientific_name": ["Thunnus thynnus"],
        "class": ["Actinopterygii"],
        "order": ["Scombriformes"],
        "family": ["Scombridae"],
        "phylum": ["Chordata"],
    })
    fishbase = pd.DataFrame({
        "Genus": ["Thunnus"],
        "Species": ["thynnus"],
        "SpecCode": [147],
        "FBname": ["Atlantic bluefin tuna"],
        "PicPreferredName": ["Ththyn_u0.jpg"],
        "Vulnerability": [74.0],
        "DepthRangeDeep": [985],
        "Fresh": [0], "Brack": [0], "Saltwater": [1],
    })
    result = enrich_with_fishbase(occurrences, fishbase)
    tuna = result[result["aphia_id"] == 123].iloc[0]
    assert tuna["common_name"] == "Atlantic bluefin tuna"
    assert tuna["water_type"] == "Saltwater"


def test_derive_water_type_brackish():
    """Brackish should win when multiple water types are true."""
    from scripts.aquatic_etl import _derive_water_type
    row = {"Fresh": 1, "Brack": 1, "Saltwater": 0}
    assert _derive_water_type(row) == "Brackish"


def test_derive_water_type_unknown():
    """All zeros should return Unknown."""
    from scripts.aquatic_etl import _derive_water_type
    row = {"Fresh": 0, "Brack": 0, "Saltwater": 0}
    assert _derive_water_type(row) == "Unknown"


def test_enrich_fills_common_name_for_non_fish():
    """Non-fish species without FishBase match should get scientific_name as common_name."""
    occurrences = pd.DataFrame({
        "aphia_id": [456],
        "lat": [10.0],
        "lng": [20.0],
        "scientific_name": ["Chelonia mydas"],
        "class": ["Reptilia"],
        "order": ["Testudines"],
        "family": ["Cheloniidae"],
        "phylum": ["Chordata"],
    })
    fishbase = pd.DataFrame({
        "scientific_name": ["Thunnus thynnus"],
        "SpecCode": [147],
        "FBname": ["Atlantic bluefin tuna"],
        "PicPreferredName": ["Ththyn_u0.jpg"],
        "Vulnerability": [74.0],
        "DepthRangeDeep": [985],
        "Fresh": [0], "Brack": [0], "Saltwater": [1],
    })
    result = enrich_with_fishbase(occurrences, fishbase)
    turtle = result.iloc[0]
    assert turtle["common_name"] == "Chelonia mydas"


def test_apply_classifications():
    df = pd.DataFrame({
        "aphia_id": [123, 456, 789],
        "scientific_name": ["Orcinus orca", "Thunnus thynnus", "Aurelia aurita"],
        "class": ["Mammalia", "Actinopterygii", "Scyphozoa"],
        "order": ["Cetacea", "Scombriformes", "Semaeostomeae"],
        "family": ["Delphinidae", "Scombridae", "Ulmaridae"],
        "phylum": ["Chordata", "Chordata", "Cnidaria"],
    })
    result = apply_classifications(df)
    assert result.iloc[0]["group"] == "dolphin"
    assert result.iloc[0]["body_type"] == "cetacean"
    assert result.iloc[0]["body_group"] == "mammal"
    assert result.iloc[1]["group"] == "tuna_mackerel"
    assert result.iloc[2]["group"] == "jellyfish"
    assert result.iloc[2]["body_group"] == "cnidarian"


import json
from scripts.aquatic_etl import generate_species_details

def test_generate_species_detail_has_sprite(tmp_path):
    df = pd.DataFrame({
        "id": ["123", "123"],
        "lat": [47.6, 48.0],
        "lng": [-122.3, -122.5],
        "name": ["Orca", "Orca"],
        "scientific_name": ["Orcinus orca", "Orcinus orca"],
        "group": ["dolphin", "dolphin"],
        "body_type": ["cetacean", "cetacean"],
        "body_group": ["mammal", "mammal"],
        "sprite": ["sp-123.svg", "sp-123.svg"],
        "thumb": [None, None],
        "water_type": ["Saltwater", "Saltwater"],
        "rarity": [3, 3],
    })
    generate_species_details(df, tmp_path)
    detail = json.loads((tmp_path / "species" / "123.json").read_text())
    assert detail["sprite"] == "sp-123.svg"
    assert detail["group"] == "dolphin"
    assert detail["bodyType"] == "cetacean"
    assert detail["bodyGroup"] == "mammal"
