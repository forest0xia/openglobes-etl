# CLAUDE.md — Instructions for AI agents working on this repo

## What is this?
Data pipeline for OpenGlobes (openglobes.com) — a series of 3D globe visualizations.
This repo downloads bulk datasets and processes them into static JSON tile files.
Output is consumed by globe frontend repos (openglobes-aquatic, openglobes-dino, etc.).

## CRITICAL RULE: BULK DOWNLOADS ONLY

NEVER paginate through search APIs. Every data source offers a bulk download.
Total API calls across all globes should be ~10. Rate limiting is a non-issue.

## Data sources and download methods

| Globe | Source | Method | Rate Limit |
|-------|--------|--------|------------|
| Aquatic (metadata) | FishBase | `duckdb.read_parquet('https://fishbase.ropensci.org/fishbase/species.parquet')` | None — one HTTP GET for entire DB |
| Dino | PBDB | `paleobiodb.org/data1.2/occs/list.csv?base_name=Dinosauria&show=coords&limit=all` | None — 1 GET |
| Volcano | Smithsonian GVP | Download Excel from volcano.si.edu | Manual download |
| Quake | USGS | `earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=1900-01-01&minmagnitude=6` | None — public |
| Meteor | NASA | `data.nasa.gov/resource/gh4g-9sfh.csv?$limit=50000` | None — public domain |
| Shipwreck | NOAA AWOIS | Bulk CSV download | None — public domain |
| Bird | GBIF (includes eBird) | Async Download API: 1 POST → wait → download ZIP | 1 request |
| Satellite | CelesTrak | Bulk TLE file, updated daily | None |
| Aquatic | OBIS | S3 Parquet export from `s3://obis-products/` (`aws s3 cp --no-sign-request`) | None — public bucket |
| Aquatic | GBIF | Async Download API: 1 POST → wait → download ZIP | 1 request |
| Aquatic | FishBase | Same parquet reads as above | None |

## Workflow per globe
1. Download raw data → save to `data/raw/{globe}/` → commit (never re-download)
2. Clean: remove records without coordinates, deduplicate
3. Enrich: join tables where needed (e.g., FishBase species + ecology + comnames)
4. Split into spatial tiles using `scripts/tile_splitter.py`
5. Generate per-item detail JSON files
6. Generate master index.json with filter facets
7. Validate with `scripts/validate.py`

## Output format
See docs/DATA_CONTRACTS.md for exact schemas.
Output goes to: `output/{globe}/tiles/`, `output/{globe}/species/`, `output/{globe}/index.json`

## How globe repos consume output
Each globe repo (openglobes-aquatic, openglobes-dino, etc.) references this data:
- **Local dev:** symlink `data → ../openglobes-etl/output/{globe}`
- **CI (GitHub Actions):** workflow clones this repo and copies `output/{globe}` into the globe repo's `data/` directory before building
- The output/ directory IS committed to this repo so CI can clone and copy without re-running the pipeline
- Globe repos .gitignore their data/ directory

## Session continuity
- Save raw downloads to `data/raw/` and COMMIT them
- Next session: check if raw files exist. If yes, skip download.
- Update `.agent-state/data-pipeline.md` after every session

## Tech
- Python 3.11+
- duckdb (for parquet reads)
- pandas (for data processing)
- requests (for API calls)
- No heavy ML frameworks needed
