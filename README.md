# openglobes-etl

Data pipelines for [OpenGlobes](https://openglobes.com). Downloads bulk datasets and processes them into static JSON tile files for 3D globe visualizations.

## Globes

| Globe | Script | Source | Records | Tiles | License |
|-------|--------|--------|---------|-------|---------|
| Aquatic | `aquatic_etl.py` | OBIS + GBIF + FishBase | 172K species / 2.6M points | 15,491 | CC-BY / CC-BY-NC |
| Dino | `dino_etl.py` | Paleobiology Database | 22,930 fossil occurrences | 1,584 | CC-BY |
| Quake | `quake_etl.py` | USGS FDSN | 14,431 M6+ earthquakes (since 1900) | 2,540 | Public domain |
| Meteor | `meteor_etl.py` | NASA Open Data | 32,187 meteorite landings | 1,933 | Public domain |
| Volcano | `volcano_etl.py` | Smithsonian GVP | 1,222 Holocene volcanoes | 912 | CC-BY-NC |

## Architecture

```
data/raw/{globe}/          Raw downloads (parquet, CSV, GeoJSON, XML)
output/{globe}/
  tiles/z{0-7}/*.json      Spatial tiles (slippy map quadtree)
  species/*.json            Per-item detail files
  index.json                Master index with filter definitions
  search_index.json         Group-based search index (aquatic)
  sprites/                  Species marker icons (aquatic)
    manifest.json           Sprite index + fallback chain
    sp-{name}.png           179 photorealistic transparent PNGs
scripts/
  tile_splitter.py          Generic spatial tiler (shared by all globes)
  validate.py               Schema validator for all output
  {globe}_etl.py            Per-globe ETL pipeline
  aquatic_groups.py         53 aquatic group taxonomy classifier
  build_sprite_manifest.py  Sprite manifest builder with fallback chain
  build_aquatic_search_index.py  Group-based search index
```

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install duckdb pandas requests pyarrow lxml

# Run any globe pipeline (downloads + processes + validates)
python -m scripts.aquatic_etl           # Downloads OBIS/GBIF, then processes
python -m scripts.aquatic_etl --process # Process only (skip downloads)
python -m scripts.dino_etl
python -m scripts.quake_etl
python -m scripts.meteor_etl
python -m scripts.volcano_etl

# Validate all output
python scripts/validate.py --all

# Aquatic-specific
python -m scripts.build_sprite_manifest          # Rebuild sprite manifest
python -m scripts.build_aquatic_search_index      # Rebuild search index
```

All downloads are idempotent — raw files are cached in `data/raw/` and skipped if they already exist.

## Tile System

Standard slippy map (web mercator) tiling:

- **z0-z3**: Cluster tiles. Each cluster has a centroid, count, top items, and filter aggregations. Large clusters are subdivided spatially to avoid mega-clusters.
- **z4-z5**: Overlap zone (aquatic only). Tiles contain both clusters and individual points.
- **z4-z7**: Point tiles. Individual items with enough fields for client-side filtering. Capped at 200 points per tile to stay under 30KB.

Tile coordinates follow `z{zoom}/{x}_{y}.json` naming. See `docs/DATA_CONTRACTS.md` for exact schemas.

## Aquatic Globe

The aquatic globe is the most complex pipeline, covering all marine and freshwater life:

**Data sources**: OBIS (116M records, deduped to 2.6M via DuckDB S3 query), GBIF occurrences, FishBase metadata enrichment.

**Taxonomy**: 53 groups (shark, whale, dolphin, jellyfish, coral, etc.), 10 body types (fusiform, flat, elongated, cetacean, etc.), 9 body groups for visual classification.

**Sprites**: 179 photorealistic transparent PNG icons for globe markers. Each species resolves to a sprite via a 3-tier fallback chain: species sprite (179) -> group fallback (53) -> body-type fallback (10). Resolution happens at ETL time — the frontend just renders the pre-resolved `sprite` field.

**Enriched metadata** per species:
- Basic: name, scientific name, family, max length, max weight, lifespan
- Ecology: water type, depth, diet, trophic level
- Classification: group, body type, body group, rarity
- Conservation: vulnerability score
- Localization: English and Chinese common names (fish only via FishBase)

**Search index** (`search_index.json`): 53 aquatic groups mapped to species IDs for instant client-side search.

## Data Sources

| Globe | Method | API Calls |
|-------|--------|-----------|
| Aquatic (OBIS) | DuckDB S3 Parquet query (`s3://obis-products/`) | 1 GET |
| Aquatic (GBIF) | Async Download API (1 POST -> poll -> download ZIP) | 1 request |
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
