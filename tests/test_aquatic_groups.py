# tests/test_aquatic_groups.py
from scripts.aquatic_groups import classify_group, classify_body_type, GROUPS, BODY_TYPES

def test_shark_classified():
    assert classify_group(class_name="Elasmobranchii", order="Carcharhiniformes", family="Carcharhinidae") == "shark"

def test_orca_classified():
    assert classify_group(class_name="Mammalia", order="Cetacea", family="Delphinidae") == "dolphin"

def test_sea_turtle_classified():
    assert classify_group(class_name="Reptilia", order="Testudines", family="Cheloniidae") == "sea_turtle"

def test_octopus_classified():
    assert classify_group(class_name="Cephalopoda", order="Octopoda", family="Octopodidae") == "octopus_squid"

def test_jellyfish_classified():
    assert classify_group(class_name="Scyphozoa", order="Semaeostomeae", family="Ulmaridae") == "jellyfish"

def test_unknown_fallback():
    assert classify_group(class_name="Unknown", order="Unknown", family="Unknown") == "other"

def test_body_type_shark():
    assert classify_body_type("shark") == "fusiform"

def test_body_type_whale():
    assert classify_body_type("whale") == "cetacean"

def test_body_type_octopus():
    assert classify_body_type("octopus_squid") == "cephalopod"

def test_body_type_jellyfish():
    assert classify_body_type("jellyfish") == "jellyfish"

def test_body_type_unknown():
    assert classify_body_type("other") == "fusiform"  # default fallback

def test_body_group_fish():
    from scripts.aquatic_groups import classify_body_group
    assert classify_body_group("shark") == "fish"
    assert classify_body_group("whale") == "mammal"
    assert classify_body_group("octopus_squid") == "cephalopod"
    assert classify_body_group("jellyfish") == "cnidarian"
    assert classify_body_group("crab_lobster") == "crustacean"
    assert classify_body_group("sea_turtle") == "reptile"

def test_all_groups_have_body_type():
    for g in GROUPS:
        assert classify_body_type(g["id"]) in BODY_TYPES

def test_group_count():
    assert len(GROUPS) >= 50
