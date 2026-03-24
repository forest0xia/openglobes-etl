# scripts/build_aquatic_search_index.py
"""Build search index for aquatic globe with ~50 groups."""
import json
from pathlib import Path
from collections import defaultdict

from scripts.aquatic_groups import GROUPS

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output" / "aquatic"

# Build label lookup from GROUPS
_GROUP_LABELS = {g["id"]: g["label"] for g in GROUPS}
_GROUP_LABELS["other"] = "Other"


def build_search_index(df) -> dict:
    """Build search index from classified DataFrame."""
    groups = defaultdict(lambda: {"label": "", "specIds": []})
    by_spec_id = {}

    for _, row in df.drop_duplicates(subset=["id"]).iterrows():
        gid = row.get("group", "other")
        sid = str(row["id"])
        groups[gid]["label"] = _GROUP_LABELS.get(gid, gid.replace("_", " ").title())
        groups[gid]["specIds"].append(sid)
        by_spec_id[sid] = gid

    # Sort specIds within each group
    for g in groups.values():
        g["specIds"].sort()

    return {
        "groups": dict(sorted(groups.items())),
        "bySpecId": dict(sorted(by_spec_id.items())),
    }


def main():
    import pandas as pd
    species_dir = OUTPUT_DIR / "species"
    if not species_dir.exists():
        print("ERROR: Run aquatic_etl.py first")
        return

    records = []
    for f in species_dir.glob("*.json"):
        data = json.loads(f.read_text())
        records.append({"id": data["id"], "group": data.get("group", "other"),
                        "scientific_name": data.get("scientificName", "")})

    df = pd.DataFrame(records)
    index = build_search_index(df)

    out = OUTPUT_DIR / "search_index.json"
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    total_species = sum(len(g["specIds"]) for g in index["groups"].values())
    print(f"  Search index: {len(index['groups'])} groups, {total_species} species")


if __name__ == "__main__":
    main()
