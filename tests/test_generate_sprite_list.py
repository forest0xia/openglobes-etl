# tests/test_generate_sprite_list.py
import pandas as pd
from scripts.generate_sprite_list import curate_sprite_list


def test_curate_produces_500():
    # Mock enriched DataFrame with many species
    rows = []
    for i in range(1000):
        rows.append({"aphia_id": i, "scientific_name": f"Species {i}",
                      "group": f"group_{i % 20}", "body_type": "fusiform"})
    df = pd.DataFrame(rows)
    result = curate_sprite_list(df, target=500)
    assert len(result) == 500


def test_curate_ensures_group_coverage():
    rows = []
    # 990 from group_a, 10 from group_b
    for i in range(990):
        rows.append({"aphia_id": i, "scientific_name": f"Sp {i}",
                      "group": "group_a", "body_type": "fusiform"})
    for i in range(990, 1000):
        rows.append({"aphia_id": i, "scientific_name": f"Sp {i}",
                      "group": "group_b", "body_type": "cetacean"})
    df = pd.DataFrame(rows)
    result = curate_sprite_list(df, target=100, min_per_group=5)
    group_b_count = sum(1 for r in result if r["group"] == "group_b")
    assert group_b_count >= 5  # minimum coverage guaranteed


def test_curate_returns_list_of_dicts():
    """Each item should be a dict with expected keys."""
    rows = [{"aphia_id": i, "scientific_name": f"Species {i}",
             "group": "reef_fish", "body_type": "fusiform"} for i in range(10)]
    df = pd.DataFrame(rows)
    result = curate_sprite_list(df, target=5)
    assert isinstance(result, list)
    assert len(result) == 5
    for item in result:
        assert isinstance(item, dict)
        assert "id" in item
        assert "scientificName" in item
        assert "group" in item
        assert "bodyType" in item
        assert "occurrences" in item


def test_curate_id_is_string():
    """IDs should be string type for JSON compatibility."""
    rows = [{"aphia_id": 42, "scientific_name": "Test sp",
             "group": "reef_fish", "body_type": "fusiform"}]
    df = pd.DataFrame(rows)
    result = curate_sprite_list(df, target=1)
    assert result[0]["id"] == "42"
    assert isinstance(result[0]["id"], str)


def test_curate_fewer_species_than_target():
    """If fewer species exist than target, return all available."""
    rows = [{"aphia_id": i, "scientific_name": f"Species {i}",
             "group": "reef_fish", "body_type": "fusiform"} for i in range(3)]
    df = pd.DataFrame(rows)
    result = curate_sprite_list(df, target=500)
    assert len(result) == 3


def test_curate_min_per_group_exceeds_group_size():
    """If a group has fewer than min_per_group, use all of them."""
    rows = []
    for i in range(50):
        rows.append({"aphia_id": i, "scientific_name": f"Sp {i}",
                      "group": "big_group", "body_type": "fusiform"})
    for i in range(50, 52):
        rows.append({"aphia_id": i, "scientific_name": f"Sp {i}",
                      "group": "small_group", "body_type": "flatfish"})
    df = pd.DataFrame(rows)
    result = curate_sprite_list(df, target=20, min_per_group=5)
    small_count = sum(1 for r in result if r["group"] == "small_group")
    # small_group only has 2 species, so we get both
    assert small_count == 2


def test_curate_no_duplicates():
    """Result should contain no duplicate species IDs."""
    rows = []
    # Duplicate aphia_ids (multiple occurrences of same species)
    for i in range(100):
        rows.append({"aphia_id": i % 50, "scientific_name": f"Species {i % 50}",
                      "group": f"group_{i % 5}", "body_type": "fusiform"})
    df = pd.DataFrame(rows)
    result = curate_sprite_list(df, target=30)
    ids = [r["id"] for r in result]
    assert len(ids) == len(set(ids))


def test_curate_sorted_by_occurrence():
    """Phase 2 fill should prefer species with more occurrences."""
    rows = []
    # Species 0 appears 10 times, Species 1 appears 1 time - both in same group
    for _ in range(10):
        rows.append({"aphia_id": 0, "scientific_name": "Common sp",
                      "group": "reef_fish", "body_type": "fusiform"})
    rows.append({"aphia_id": 1, "scientific_name": "Rare sp",
                  "group": "reef_fish", "body_type": "fusiform"})
    df = pd.DataFrame(rows)
    result = curate_sprite_list(df, target=2, min_per_group=0)
    # Most common species should be first
    assert result[0]["scientificName"] == "Common sp"
    assert result[0]["occurrences"] == 10
