# Aquatic Globe: Sprite System & Data Pipeline Redesign

## Overview

Evolve the fish globe into a full **aquatic life globe** (`openglobes-aquatic`) covering fish, marine mammals, reptiles, cephalopods, crustaceans, cnidarians, echinoderms, and more. Replace dot-based visualization with glowing neon-outline SVG sprites. Upgrade the data pipeline from FishBase-only coordinates to OBIS+GBIF occurrence data with FishBase metadata enrichment.

## Decisions

| Decision | Choice |
|----------|--------|
| Visual style | Glowing neon outlines (D) — outline SVGs with glow applied at render time |
| Points (z4+) | Individual species sprite per point |
| Clusters (z0-z3) | Scattered swarm of tiny sprite outlines |
| Curated species count | 500 selected by popularity/recognition |
| Fallback chain | Species → group (~50) → body-type (~10) |
| Image sourcing | Multi-source fetch script, persist locally, curate best |
| Coordinate data | OBIS + GBIF bulk downloads (hybrid with FishBase for metadata) |
| Globe scope | All aquatic life (marine + freshwater) |
| Naming | `aquatic` — `output/aquatic/`, `openglobes-aquatic` |
| Illustration sourcing | Source clean outlines from multiple databases, apply glow in frontend code |
| Frontend transition | Out of scope for ETL — frontend concern |

## 1. Data Pipeline Architecture

### Three data layers

| Layer | Source | Provides | Method |
|-------|--------|----------|--------|
| Occurrences | OBIS bulk export | Where things are (lat/lng + taxon) | 1 bulk download |
| Occurrences | GBIF async download | Additional occurrences, freshwater/terrestrial coverage | 1 async job |
| Metadata | FishBase parquets | Species attributes (diet, rarity, habitat, images) | Existing parquet reads |

### Unified species ID scheme

**Canonical ID: WoRMS AphiaID** — the World Register of Marine Species identifier. Chosen because:
- OBIS is built on WoRMS (every OBIS record has an AphiaID)
- GBIF maintains a WoRMS-to-taxonKey mapping
- FishBase SpecCodes can be mapped to AphiaID via WoRMS API or the `taxize` crosswalk

All output files (species details, tiles, sprites, manifest) use AphiaID as the primary key. A mapping table `data/raw/aquatic/id_crosswalk.json` records: `{ aphiaId → { gbifKey, fishbaseSpecCode, scientificName } }` for traceability.

For freshwater-only species not in WoRMS, use GBIF taxonKey prefixed with `gbif-` (e.g., `"gbif-12345"`) to avoid collisions.

### Processing flow

1. Download OBIS + GBIF bulk data → `data/raw/aquatic/`
2. Deduplicate occurrences across both sources (same species at ~same location)
3. Taxonomic normalization — map all taxon keys to WoRMS AphiaID via crosswalk
4. Enrich with FishBase metadata where available (join via crosswalk on SpecCode)
5. For non-fish species (orcas, octopus, turtles, etc.) — use OBIS/GBIF metadata fields as fallback enrichment
6. Tile, generate species detail files, index — same pipeline structure as current fish ETL
7. Output to `output/aquatic/`

### Bulk download rule

Per project rules: BULK DOWNLOADS ONLY. Total API calls ~3-4:
- OBIS: Full Parquet export via S3 (`s3://obis-products/` — public bucket, no auth). Download with `aws s3 cp --no-sign-request`. ~40GB compressed. Filter to records with coordinates post-download.
- GBIF: 1 async download job (POST → poll → download ZIP). Filter: `hasCoordinate=true`, `isInCluster=false`, taxon keys for aquatic phyla.
- FishBase: existing parquet reads (~7 HTTP GETs)

### Scale considerations

OBIS has 100M+ occurrence records. Downsampling strategy:
- **Deduplication level:** One point per species per z7 tile (finest zoom). Use centroid of all occurrences of that species within the tile.
- **Target:** ~200K-500K unique points in the final DataFrame (vs. 116K in current fish globe)
- **When:** Deduplication happens after merging OBIS+GBIF, before tiling
- **Quality filter:** Discard records with coordinate uncertainty >50km, flagged as fossils, or missing taxonomic resolution below family level

## 2. Sprite System

### 500 curated species

Selected by global recognition across all aquatic taxa:

- **Fish:** clownfish, great white shark, manta ray, seahorse, pufferfish, tuna, salmon, anglerfish, swordfish, etc.
- **Marine mammals:** orca, humpback whale, dolphin, seal, sea otter, walrus, manatee, etc.
- **Reptiles:** sea turtle (multiple species), sea snake
- **Cephalopods:** octopus, squid, nautilus, cuttlefish
- **Crustaceans:** lobster, crab, shrimp, krill
- **Cnidarians:** jellyfish, coral (as group icon), sea anemone
- **Echinoderms:** starfish, sea urchin, sea cucumber
- **Mollusks:** clam, mussel, sea snail, nudibranch

### ~50 search groups

Keep existing 36 fish groups, add:
- whale, dolphin, seal/sea lion, sea turtle, octopus/squid, jellyfish, crab/lobster, starfish, coral, sea urchin, shrimp, clam/mussel, sea snail, sponge, etc.

### ~10 body-type fallbacks

| Body type | Covers |
|-----------|--------|
| fusiform | tuna, salmon, barracuda |
| flat | ray, flounder, skate |
| elongated | eel, sea snake, pipefish |
| deep-bodied | angelfish, sunfish, butterflyfish |
| seahorse | seahorse, sea dragon |
| globular | pufferfish, boxfish |
| cetacean | whale, dolphin, porpoise |
| crustacean | crab, lobster, shrimp |
| cephalopod | octopus, squid, nautilus |
| jellyfish | jellyfish, man-o-war |

### Fallback chain

```
species sprite (500) → group fallback (~50) → body-type fallback (~10)
```

ETL pre-resolves the chain. Every point and cluster topItem ships with a final `sprite` filename — it is never null. The ETL guarantees resolution to at least a body-type fallback. Frontend never walks the chain.

## 3. Image Sourcing Pipeline

### Script: `scripts/fetch_aquatic_sprites.py`

**Step 1 — Curate the 500 list:**
- Rank species across all taxa by OBIS/GBIF occurrence count + recognition factor
- Ensure every search group has at least 5-10 representatives
- Output `data/raw/aquatic/sprite_species_list.json`

**Step 2 — Fetch from multiple sources:**

| Source | Coverage | License | Method |
|--------|----------|---------|--------|
| Phylopic | Broad taxonomy, silhouettes | CC0/CC-BY | REST API by scientific name |
| FishBase line art | Fish only | CC-BY-NC | Scrape from species pages |
| OBIS/GBIF media | Broad | Varies per record | Media URLs from occurrence metadata |
| Wikimedia Commons | Broad, inconsistent | Mixed (check per file) | API search by scientific name |
| NOAA/govt illustrations | US commercial species | Public domain | Bulk scrape |

**Step 3 — Persist raw downloads:**
- `data/raw/aquatic/sprites/{source}/{speciesId}.*`
- One subfolder per source for comparison
- Never re-download existing files

**Step 4 — Normalize to clean outlines:**
- Target viewBox: `0 0 100 60` (landscape, consistent aspect ratio)
- Target stroke width: 1.5 (unitless, scales with viewBox)
- Strip all fills, set `fill="none"`, normalize stroke to single color (`#fff` — frontend applies glow color)
- Side-view orientation (facing left) — flip horizontally if needed
- For raster-only sources (GBIF photos): auto-trace with potrace/svgtrace to generate outline SVGs, flag for manual review
- Output to `output/aquatic/sprites/`
- Each SVG should be <3KB

**Step 5 — Generate group fallbacks (~50):**
- Pick best-quality outline from most common species per group

**Step 6 — Generate body-type fallbacks (~10):**
- Hand-selected from best available outlines

**Auto-pick priority:** Phylopic CC0 → FishBase → NOAA → Wikimedia → GBIF media

**Manual override:** `data/raw/aquatic/sprite_overrides.json` for cases where auto-pick is bad.

**Automation:** Scripts should batch-process and parallelize where possible to handle 500 species × 5 sources efficiently.

## 4. Sprite Manifest Schema

`output/aquatic/sprites/manifest.json`:

```json
{
  "version": "1.0.0",
  "glowDefaults": {
    "color": "#00E5FF",
    "blur": "4px",
    "note": "Apply via CSS filter: drop-shadow(0 0 {blur} {color})"
  },
  "bodyTypes": [
    "fusiform", "flat", "elongated", "deep-bodied", "seahorse",
    "globular", "cetacean", "crustacean", "cephalopod", "jellyfish"
  ],
  "sprites": {
    "<speciesId>": {
      "file": "sp-<speciesId>.svg",
      "name": "Common name",
      "scientificName": "Genus species",
      "group": "group_key",
      "bodyType": "fusiform",
      "bodyGroup": "fish",
      "license": "CC0"
    }
  },
  "groupFallbacks": {
    "shark": "grp-shark.svg",
    "whale": "grp-whale.svg"
  },
  "bodyTypeFallbacks": {
    "fusiform": "fb-fusiform.svg",
    "cetacean": "fb-cetacean.svg"
  },
  "totalSprites": 560,
  "note": "Fallback chain: sprites[speciesId] → groupFallbacks[group] → bodyTypeFallbacks[bodyType]. Resolved at ETL time — frontend uses pre-resolved sprite field on each point/topItem."
}
```

## 5. Tile & Species Format Changes

### Species detail files (`output/aquatic/species/{id}.json`)

All existing fields retained (`name`, `nameZh`, `scientificName`, `family`, `description`, `metadata`, `images`, `links`, `attribution`). New fields added:
- `sprite` — filename of species' outline SVG (always resolved, never null)
- `group` — search group key (e.g., "shark", "octopus")
- `bodyType` — one of ~10 body types
- `bodyGroup` — broad visual classification for color tinting: "fish", "mammal", "reptile", "cephalopod", "crustacean", "cnidarian", "echinoderm", "mollusk", "other"

Note: `bodyGroup` replaces the previously discussed `taxonType`. Named `bodyGroup` because cephalopods are taxonomically mollusks but visually distinct — this field represents visual grouping, not strict taxonomy.

Note on `nameZh`: FishBase provides Chinese common names for fish. For non-fish taxa, `nameZh` will be null unless a Chinese name mapping is sourced separately (future enhancement).

### Point tiles (z4+)

All existing fields retained (`id`, `lat`, `lng`, `name`, `nameZh`, `thumb`, `rarity`, `waterType`, `precision`). New fields added:
- `sprite` — pre-resolved SVG filename (never null)
- `group` — search group key

`thumb` is kept for photo-based popups/hover cards. `sprite` is for the globe marker icon. They serve different purposes.

### Cluster tiles (z0-z5)

Note: Clusters span z0-z5, not z0-z3. Tiles at z4-z5 contain both `clusters` and `points` arrays (overlap zone). This matches the existing tile_splitter.py behavior.

- `topItems[]` gains `sprite` and `group` fields per item (alongside existing `thumb`)
- New `groupDistribution` — top 5 groups with counts:

```json
"groupDistribution": [
  {"group": "shark", "count": 12},
  {"group": "tuna_mackerel", "count": 8},
  {"group": "jellyfish", "count": 3}
]
```

Example cluster topItem:
```json
{
  "id": "100",
  "name": "Bigscale mackerel",
  "thumb": "Gamel_u5.jpg",
  "sprite": "sp-100.svg",
  "group": "tuna_mackerel"
}
```

## 6. Frontend Handoff Spec (for openglobes-aquatic)

### Assets delivered by ETL

- `data/sprites/*.svg` — ~560 SVG files (500 species + ~50 group + ~10 body-type fallbacks)
- `data/sprites/manifest.json` — full index with fallback chain
- All SVGs: outline-only, no fill, consistent stroke width, normalized viewBox

### Rendering contract

**Glow effect:** Apply via CSS/WebGL at render time. Default: `drop-shadow(0 0 4px #00E5FF)`. Manifest includes `glowDefaults` but frontend owns the final effect.

**Points (z4+):** Each point has a `sprite` field. Load SVG, render at ~24-48px.

**Clusters (z0-z5) — Scattered swarm:**
- Use `topItems[].sprite` to pick which outlines appear
- Use `count` to determine density: e.g., `min(count / 50, 12)` visible sprites
- Use `groupDistribution` to vary the shapes in the swarm
- Scatter positions: randomize with seed from tile coords for deterministic layout
- At z4-z5 (overlap zone): render both individual points and cluster swarms

**Fallback:** ETL guarantees every `sprite` field is non-null. No frontend fallback logic needed.

**Photo thumbnails:** `thumb` field is retained on points and topItems for popup/hover cards showing actual photos. `sprite` is the globe marker; `thumb` is the detail view.

**Color variation (optional):** Tint by `bodyGroup`:
- Cyan (#00E5FF) — fish (default)
- Purple — cephalopods
- Green — reptiles
- Pink — cnidarians
- Warm white — mammals

### What the frontend does NOT need to do

- Walk the fallback chain (ETL pre-resolved)
- Fetch from external image sources (all assets local)
- Parse metadata to determine body type (already computed)
- Handle data source differences (OBIS vs GBIF normalized by ETL)

## 7. Output Directory Structure

```
output/aquatic/
├── tiles/
│   ├── z0-z3/{x}_{y}.json          # Cluster tiles with swarm data
│   └── z4-z7/{x}_{y}.json          # Point tiles with sprite refs
├── species/
│   └── {id}.json                    # Detail files with sprite/group/bodyType
├── sprites/
│   ├── manifest.json                # Full sprite index + fallback chain
│   ├── sp-{speciesId}.svg            # 500 curated species outlines
│   ├── grp-{group}.svg              # ~50 group fallbacks
│   └── fb-{bodyType}.svg            # ~10 body-type fallbacks
├── index.json                       # Master index with expanded filters
├── search_index.json                # Expanded to ~50 groups
└── migration_routes.json            # Keep existing, expand to marine mammals
```

## 8. Validation Updates

`scripts/validate.py` must be updated to check:
- Point tiles: `sprite` field present and non-null on every point
- Point tiles: `group` field present
- Cluster tiles: `topItems[].sprite` present and non-null
- Cluster tiles: `groupDistribution` array present with valid group keys
- Sprites directory: every `sprite` filename referenced in tiles exists as a file
- Manifest: all group keys in tiles exist in `groupFallbacks`
- Manifest: all body types in tiles exist in `bodyTypeFallbacks`
- SVG files: valid XML, viewBox present, <3KB each
- Species detail files: `sprite`, `group`, `bodyType`, `bodyGroup` fields present

## 9. Migration from Fish to Aquatic

- Current `output/fish/` continues to work until `output/aquatic/` is ready
- `openglobes-fish` repo either renames to `openglobes-aquatic` or a new repo is created
- CLAUDE.md updated with new data sources and methods
- DATA_CONTRACTS.md updated with new fields and sprite format
