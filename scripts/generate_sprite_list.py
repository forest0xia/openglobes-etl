"""Curate the ranked list of species for sprite generation."""
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "data" / "raw" / "aquatic" / "sprite_species_list.json"


def curate_sprite_list(df, target=500, min_per_group=5):
    """Rank species by occurrence count, ensure group coverage."""
    # Count occurrences per species
    species_counts = df.groupby("aphia_id").agg(
        count=("aphia_id", "size"),
        scientific_name=("scientific_name", "first"),
        group=("group", "first"),
        body_type=("body_type", "first"),
    ).reset_index().sort_values("count", ascending=False)

    selected = []
    selected_ids = set()

    # Phase 1: Ensure minimum per group
    for group_id, group_df in species_counts.groupby("group"):
        top_in_group = group_df.head(min_per_group)
        for _, row in top_in_group.iterrows():
            if row["aphia_id"] not in selected_ids:
                selected.append({
                    "id": str(int(row["aphia_id"])) if isinstance(row["aphia_id"], (int, float)) else str(row["aphia_id"]),
                    "scientificName": row["scientific_name"],
                    "group": row["group"],
                    "bodyType": row["body_type"],
                    "occurrences": int(row["count"]),
                })
                selected_ids.add(row["aphia_id"])

    # Phase 2: Fill remaining slots by global occurrence rank
    for _, row in species_counts.iterrows():
        if len(selected) >= target:
            break
        if row["aphia_id"] not in selected_ids:
            selected.append({
                "id": str(int(row["aphia_id"])) if isinstance(row["aphia_id"], (int, float)) else str(row["aphia_id"]),
                "scientificName": row["scientific_name"],
                "group": row["group"],
                "bodyType": row["body_type"],
                "occurrences": int(row["count"]),
            })
            selected_ids.add(row["aphia_id"])

    return selected[:target]


def main():
    import pandas as pd
    species_dir = ROOT / "output" / "aquatic" / "species"
    if not species_dir.exists():
        print("ERROR: Run aquatic_etl.py first")
        return
    # Load all species to count occurrences from tiles
    records = []
    for f in species_dir.glob("*.json"):
        data = json.loads(f.read_text())
        records.append(data)
    df = pd.DataFrame(records).rename(columns={"id": "aphia_id", "scientificName": "scientific_name",
                                                 "bodyType": "body_type"})
    result = curate_sprite_list(df, target=500)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Curated {len(result)} species for sprite generation -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
