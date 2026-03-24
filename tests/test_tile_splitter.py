import json
import pandas as pd
from pathlib import Path
from scripts.tile_splitter import split_tiles


def test_cluster_tiles_have_group_distribution(tmp_path):
    df = pd.DataFrame({
        "id": ["1", "2", "3", "4", "5"],
        "lat": [10.0, 10.1, 10.2, 10.3, 10.4],
        "lng": [20.0, 20.1, 20.2, 20.3, 20.4],
        "name": ["A", "B", "C", "D", "E"],
        "group": ["shark", "shark", "tuna", "jellyfish", "tuna"],
        "waterType": ["Saltwater"] * 5,
    })
    split_tiles(
        df, tmp_path,
        filter_agg_keys=["waterType"],
        top_items_fields=["id", "name"],
        point_fields=["id", "lat", "lng", "name", "group"],
        group_distribution_key="group",
    )
    # Read a z0 cluster tile
    z0 = tmp_path / "tiles" / "z0" / "0_0.json"
    assert z0.exists()
    data = json.loads(z0.read_text())
    cluster = data["clusters"][0]
    assert "groupDistribution" in cluster
    # Should be list of {group, count} sorted by count desc
    gd = cluster["groupDistribution"]
    assert isinstance(gd, list)
    assert all("group" in g and "count" in g for g in gd)
    # Verify counts: shark=2, tuna=2, jellyfish=1
    counts = {g["group"]: g["count"] for g in gd}
    assert counts["shark"] == 2
    assert counts["tuna"] == 2
    assert counts["jellyfish"] == 1


def test_split_tiles_without_group_distribution(tmp_path):
    """Backward compatibility: no group_distribution_key means no groupDistribution field."""
    df = pd.DataFrame({
        "id": ["1", "2", "3"],
        "lat": [10.0, 10.1, 10.2],
        "lng": [20.0, 20.1, 20.2],
        "name": ["A", "B", "C"],
        "waterType": ["Saltwater"] * 3,
    })
    split_tiles(
        df, tmp_path,
        filter_agg_keys=["waterType"],
        top_items_fields=["id", "name"],
        point_fields=["id", "lat", "lng", "name"],
    )
    z0 = tmp_path / "tiles" / "z0" / "0_0.json"
    assert z0.exists()
    data = json.loads(z0.read_text())
    cluster = data["clusters"][0]
    assert "groupDistribution" not in cluster
