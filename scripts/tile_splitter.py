"""
Generic quadtree spatial tiler for OpenGlobes.
Assigns lat/lng points to slippy-map tiles, producing cluster tiles (z0-z3)
and point tiles (z4-z7).

Cluster tiles separate species by water type and cap cluster sizes to avoid
mega-clusters. Large groups are subdivided into smaller spatial clusters.
"""

import json
import math
import os
from pathlib import Path

import pandas as pd

# Zoom levels — clusters extend through z5 for smooth transitions
CLUSTER_ZOOM_MIN = 0
CLUSTER_ZOOM_MAX = 5
POINT_ZOOM_MIN = 4
POINT_ZOOM_MAX = 7
MAX_POINTS_PER_TILE = 120

# Max species per cluster at each zoom level. If exceeded, subdivide.
MAX_CLUSTER_SIZE = {0: 5000, 1: 2000, 2: 500, 3: 100, 4: 30, 5: 10}

# Top items per cluster
TOP_ITEMS_COUNT = 10


def lat_lng_to_tile(lat: float, lng: float, zoom: int) -> tuple[int, int]:
    """Convert lat/lng to tile coordinates at given zoom level."""
    n = 2 ** zoom
    x = int((lng + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    x = max(0, min(n - 1, x))
    y = max(0, min(n - 1, y))
    return x, y


def tile_to_bbox(x: int, y: int, zoom: int) -> dict:
    """Get bounding box for a tile."""
    n = 2 ** zoom
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return {"north": north, "south": south, "east": east, "west": west}


def _make_cluster(group: pd.DataFrame, top_items_fields: list[str], filter_agg_keys: list[str], group_distribution_key: str | None = None) -> dict:
    """Build a single cluster dict from a group of points."""
    cluster = {
        "lat": round(group["lat"].mean(), 2),
        "lng": round(group["lng"].mean(), 2),
        "count": len(group),
    }

    # Top items — distinct species, up to TOP_ITEMS_COUNT
    seen_ids = set()
    top_items = []
    for _, row in group.iterrows():
        item_id = str(row.get("id", ""))
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        item = {}
        for k in top_items_fields:
            if k in row and pd.notna(row[k]):
                item[k] = row[k]
        top_items.append(item)
        if len(top_items) >= TOP_ITEMS_COUNT:
            break
    cluster["topItems"] = top_items

    # Filter aggregations
    if filter_agg_keys:
        aggs = {}
        for key in filter_agg_keys:
            if key in group.columns:
                aggs[key] = group[key].value_counts().to_dict()
        cluster["filterAggs"] = aggs

    # Group distribution — top-5 group counts for this cluster
    if group_distribution_key and group_distribution_key in group.columns:
        dist = group[group_distribution_key].value_counts().head(5)
        cluster["groupDistribution"] = [
            {"group": g, "count": int(c)} for g, c in dist.items()
        ]

    return cluster


def _subdivide_group(
    group: pd.DataFrame,
    max_size: int,
    top_items_fields: list[str],
    filter_agg_keys: list[str],
    group_distribution_key: str | None = None,
    depth: int = 0,
) -> list[dict]:
    """
    Recursively subdivide a group of points into clusters until each is
    under max_size. Uses grid bisection on the larger axis.
    """
    if len(group) <= max_size or depth > 8:
        return [_make_cluster(group, top_items_fields, filter_agg_keys, group_distribution_key)]

    # Split on the wider geographic axis
    lat_range = group["lat"].max() - group["lat"].min()
    lng_range = group["lng"].max() - group["lng"].min()

    # Try spatial bisection first
    clusters = []
    split_worked = False

    if lat_range > 0.001 or lng_range > 0.001:
        if lat_range >= lng_range:
            mid = group["lat"].median()
            parts = [sub for _, sub in group.groupby(group["lat"] <= mid) if len(sub) > 0]
        else:
            mid = group["lng"].median()
            parts = [sub for _, sub in group.groupby(group["lng"] <= mid) if len(sub) > 0]

        # Only use spatial split if it actually divides the group
        if len(parts) == 2 and len(parts[0]) < len(group) and len(parts[1]) < len(group):
            split_worked = True
            for sub in parts:
                clusters.extend(_subdivide_group(sub, max_size, top_items_fields, filter_agg_keys, group_distribution_key, depth + 1))

    # If spatial split failed (all points at same location), chunk alphabetically
    if not split_worked:
        sorted_group = group.sort_values("name" if "name" in group.columns else "id")
        chunk_size = max(max_size, 1)
        for i in range(0, len(sorted_group), chunk_size):
            chunk = sorted_group.iloc[i:i + chunk_size]
            clusters.append(_make_cluster(chunk, top_items_fields, filter_agg_keys, group_distribution_key))

    return clusters


def build_cluster_tiles(
    df: pd.DataFrame,
    zoom: int,
    filter_agg_keys: list[str],
    top_items_fields: list[str],
    output_dir: Path,
    group_distribution_key: str | None = None,
) -> int:
    """
    Build cluster tiles at a given zoom level.
    Separates species by water type, then spatially clusters within each type.
    Large clusters are subdivided to stay under MAX_CLUSTER_SIZE.
    Returns number of tiles written.
    """
    df = df.copy()
    tiles = df.apply(lambda r: lat_lng_to_tile(r["lat"], r["lng"], zoom), axis=1)
    df["_tile_x"] = [t[0] for t in tiles]
    df["_tile_y"] = [t[1] for t in tiles]

    zoom_dir = output_dir / f"z{zoom}"
    zoom_dir.mkdir(parents=True, exist_ok=True)

    max_size = MAX_CLUSTER_SIZE.get(zoom, 500)
    water_type_col = "waterType" if "waterType" in df.columns else None

    count = 0
    for (tx, ty), tile_group in df.groupby(["_tile_x", "_tile_y"]):
        all_clusters = []

        if water_type_col:
            # Separate clustering per water type
            for wt, wt_group in tile_group.groupby(water_type_col):
                clusters = _subdivide_group(wt_group, max_size, top_items_fields, filter_agg_keys, group_distribution_key)
                all_clusters.extend(clusters)
        else:
            all_clusters = _subdivide_group(tile_group, max_size, top_items_fields, filter_agg_keys, group_distribution_key)

        tile_data = {
            "zoom": zoom,
            "x": int(tx),
            "y": int(ty),
            "clusters": all_clusters,
        }

        out_path = zoom_dir / f"{int(tx)}_{int(ty)}.json"
        out_path.write_text(json.dumps(tile_data, ensure_ascii=False), encoding="utf-8")
        count += 1

    return count


def build_point_tiles(
    df: pd.DataFrame,
    zoom: int,
    point_fields: list[str],
    output_dir: Path,
) -> int:
    """
    Build point tiles at a given zoom level.
    If a cluster tile already exists for this zoom/tile, merges points into it.
    Returns number of tiles written.
    """
    df = df.copy()
    tiles = df.apply(lambda r: lat_lng_to_tile(r["lat"], r["lng"], zoom), axis=1)
    df["_tile_x"] = [t[0] for t in tiles]
    df["_tile_y"] = [t[1] for t in tiles]

    zoom_dir = output_dir / f"z{zoom}"
    zoom_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for (tx, ty), group in df.groupby(["_tile_x", "_tile_y"]):
        subset = group.head(MAX_POINTS_PER_TILE)

        points = []
        for _, row in subset.iterrows():
            point = {"lat": round(row["lat"], 4), "lng": round(row["lng"], 4)}
            for f in point_fields:
                if f in row and pd.notna(row[f]):
                    val = row[f]
                    point[f] = int(val) if isinstance(val, (int, float)) and f == "rarity" else val
            points.append(point)

        out_path = zoom_dir / f"{int(tx)}_{int(ty)}.json"

        # If cluster tile already exists (z4-z5 overlap), merge points into it
        if out_path.exists():
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            existing["points"] = points
            out_path.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
        else:
            tile_data = {
                "zoom": zoom,
                "x": int(tx),
                "y": int(ty),
                "points": points,
            }
            out_path.write_text(json.dumps(tile_data, ensure_ascii=False), encoding="utf-8")
        count += 1

    return count


def split_tiles(
    df: pd.DataFrame,
    output_dir: str | Path,
    filter_agg_keys: list[str],
    top_items_fields: list[str],
    point_fields: list[str],
    group_distribution_key: str | None = None,
) -> dict:
    """
    Main entry point. Takes a DataFrame with lat/lng columns and produces
    all tile files.
    """
    output_dir = Path(output_dir)
    tiles_dir = output_dir / "tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)

    # Filter out rows missing coordinates
    df = df.dropna(subset=["lat", "lng"])
    df = df[(df["lat"].between(-90, 90)) & (df["lng"].between(-180, 180))]

    stats = {}

    # Cluster tiles (z0-z3)
    for z in range(CLUSTER_ZOOM_MIN, CLUSTER_ZOOM_MAX + 1):
        n = build_cluster_tiles(df, z, filter_agg_keys, top_items_fields, tiles_dir, group_distribution_key)
        stats[f"z{z}"] = n
        print(f"  z{z}: {n} cluster tiles")

    # Point tiles (z4-z7)
    for z in range(POINT_ZOOM_MIN, POINT_ZOOM_MAX + 1):
        n = build_point_tiles(df, z, point_fields, tiles_dir)
        stats[f"z{z}"] = n
        print(f"  z{z}: {n} point tiles")

    return stats
