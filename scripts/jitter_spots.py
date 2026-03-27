"""Standalone script to jitter overlapping viewing spots in final.json.

Reads output/aquatic/final.json, spreads apart clustered coordinates,
and writes it back. Does not require OBIS parquet or re-running the full merge.

Usage:
    python scripts/jitter_spots.py
"""
import json
from pathlib import Path

from scripts.merge_curated import jitter_overlapping_spots

ROOT = Path(__file__).resolve().parent.parent
FINAL_PATH = ROOT / "output" / "aquatic" / "final.json"


def main():
    species_list = json.loads(FINAL_PATH.read_text())
    print(f"Loaded {len(species_list)} species from {FINAL_PATH.name}")

    total_spots = sum(len(s.get("viewingSpots", [])) for s in species_list)
    print(f"Total viewing spots: {total_spots}")

    jitter_overlapping_spots(species_list)

    FINAL_PATH.write_text(
        json.dumps(species_list, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Written back to {FINAL_PATH}")


if __name__ == "__main__":
    main()
