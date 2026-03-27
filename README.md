# openglobes-etl

Data pipelines for [OpenGlobes](https://openglobes.com). Downloads bulk datasets and processes them into static JSON files for 3D globe visualizations.

## Globes

| Globe | Script | Source | Records | Output | License |
|-------|--------|--------|---------|--------|---------|
| Aquatic | `merge_curated.py` | Curated + FishBase + OBIS | 214 species / 726 viewing spots | `final.json` + `hotspots.json` | CC-BY / CC-BY-NC |
| Dino | `dino_etl.py` | Paleobiology Database | 22,930 fossil occurrences | 1,584 tiles | CC-BY |
| Quake | `quake_etl.py` | USGS FDSN | 14,431 M6+ earthquakes (since 1900) | 2,540 tiles | Public domain |
| Meteor | `meteor_etl.py` | NASA Open Data | 32,187 meteorite landings | 1,933 tiles | Public domain |
| Volcano | `volcano_etl.py` | Smithsonian GVP | 1,222 Holocene volcanoes | 912 tiles | CC-BY-NC |

## Architecture

```
curation/aquatic/
  selected.json             214 curated species with viewing spots
  hotspots.json             25 diving/viewing hotspot locations
data/raw/{globe}/           Raw downloads (parquet, CSV, GeoJSON, XML)
output/aquatic/
  final.json                Merged curated species (214) + ETL metadata
  hotspots.json             25 hotspot locations
  migration_routes.json     80 marine migration routes
  sprites/                  Species marker icons
    manifest.json           Sprite index + fallback chain
    sp-{name}.png           450 photorealistic transparent PNGs (64px height)
    spritesheet-0.webp      Sprite atlas (all sprites packed, ~3 MB)
    spritesheet-0.png       Sprite atlas PNG fallback (~8 MB)
    spritesheet.json        Atlas coordinate manifest
output/{globe}/             (dino, quake, meteor, volcano)
  tiles/z{0-7}/*.json       Spatial tiles (slippy map quadtree)
  species/*.json             Per-item detail files
  index.json                 Master index with filter definitions
scripts/
  merge_curated.py          Merges curation + ETL metadata -> final.json (includes coordinate jittering)
  aquatic_etl.py            OBIS/FishBase download + enrichment (intermediate data)
  tile_splitter.py          Generic spatial tiler (dino, quake, meteor, volcano)
  validate.py               Schema validator for all output
  {globe}_etl.py            Per-globe ETL pipeline
  aquatic_groups.py         53 aquatic group taxonomy classifier
  build_sprite_manifest.py  Sprite manifest builder with fallback chain
  crop_and_pack_sprites.py  Crops text labels, normalizes height, builds sprite sheets
  cut_migration_sprites.py  Cuts 2x2 ChatGPT composites into individual migration sprites
  jitter_spots.py           Standalone coordinate jitter (spreads overlapping viewing spots)
```

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install duckdb pandas requests pyarrow lxml

# Aquatic globe (curated model)
python -m scripts.aquatic_etl --download  # Download OBIS/FishBase raw data
python -m scripts.aquatic_etl --process   # Build crosswalk + metadata (intermediate)
python -m scripts.merge_curated            # Merge curation -> output/aquatic/final.json

# Other globe pipelines (tile-based)
python -m scripts.dino_etl
python -m scripts.quake_etl
python -m scripts.meteor_etl
python -m scripts.volcano_etl

# Validate all output
python scripts/validate.py --all

# Aquatic-specific
python -m scripts.build_sprite_manifest   # Rebuild sprite manifest
```

All downloads are idempotent — raw files are cached in `data/raw/` and skipped if they already exist.

## Tile System (dino, quake, meteor, volcano)

Standard slippy map (web mercator) tiling:

- **z0-z3**: Cluster tiles. Each cluster has a centroid, count, top items, and filter aggregations.
- **z4-z7**: Point tiles. Individual items with enough fields for client-side filtering. Capped at 200 points per tile to stay under 30KB.

Tile coordinates follow `z{zoom}/{x}_{y}.json` naming. See `docs/DATA_CONTRACTS.md` for exact schemas.

## Aquatic Globe

The aquatic globe uses a curated 214-species model instead of bulk tile-based output.

**Pipeline**: Hand-curated species list (`curation/aquatic/selected.json`) is merged with ETL-derived metadata (crosswalk, FishBase enrichment) via `scripts/merge_curated.py` to produce `output/aquatic/final.json`. Overlapping viewing-spot coordinates are automatically jittered apart during the merge.

**214 curated species** across 3 tiers:
- **Star** (~51): Iconic species (blue whale, great white shark, manta ray)
- **Ecosystem** (~86): Ecologically important species (coral, kelp, sea urchin)
- **Surprise** (~77): Unusual or lesser-known species (frogfish, nudibranch, vampire squid)

**726 viewing spots**: Real-world diving/snorkeling/whale-watching locations linked to species and 25 hotspots.

**80 migration routes**: Classic marine migration paths (salmon, tuna, eels, sharks, etc.) with waypoints.

**Sprites**: 450 photorealistic transparent PNG icons for globe markers, packed into a single sprite sheet (`spritesheet-0.webp`, ~3 MB) with a coordinate manifest (`spritesheet.json`). Individual PNGs also available. Text labels auto-cropped, all normalized to 64px height. Each species resolves to a sprite via a 3-tier fallback chain: species sprite (450) -> group fallback (53) -> body-type fallback (10). Resolution happens at merge time.

**Taxonomy**: 53 groups (shark, whale, dolphin, jellyfish, coral, etc.), 10 body types, 9 body groups for visual classification.

## Data Sources

| Globe | Method | API Calls |
|-------|--------|-----------|
| Aquatic (OBIS) | DuckDB S3 Parquet query (`s3://obis-products/`) | 1 GET |
| Aquatic (metadata) | FishBase rfishbase Parquet files | 7 GETs |
| Dino | PBDB bulk CSV (`/data1.2/occs/list.csv?limit=all`) | 1 GET |
| Quake | USGS FDSN GeoJSON query | 1 GET |
| Meteor | NASA legacy CSV endpoint | 1 GET |
| Volcano | Smithsonian GVP XML spreadsheet | 1 GET |

Total API calls across all globes: ~12. No pagination, no rate limiting concerns.

## Output

Copy `output/{globe}/` to the respective frontend repo's data directory:
- [openglobes-aquatic](https://github.com/forest0xia/openglobes-aquatic)
- [openglobes-dino](https://github.com/forest0xia/openglobes-dino)
- etc.

## License

Code: AGPL-3.0. Output data inherits the license of its source — see [LICENSES.md](LICENSES.md) for details.
