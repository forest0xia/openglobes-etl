# Data Contracts — Output Schema for All Globes

All output files must conform to these schemas. Validated by `scripts/validate.py`.

## Directory structure per globe

### Standard globes (dino, quake, meteor, volcano)
```
output/{globe}/
├── tiles/
│   ├── z0/0_0.json         # Zoom 0: whole world, 1 file
│   ├── z1/{x}_{y}.json     # Zoom 1: 4 files
│   ├── z2/{x}_{y}.json     # Zoom 2: 16 files
│   ├── z3/{x}_{y}.json     # Zoom 3: 64 files (max cluster level)
│   ├── z4/{x}_{y}.json     # Zoom 4+: individual points
│   └── ...up to z7
├── species/                  # Or items/ — one file per entity
│   ├── {id}.json
│   └── ...
└── index.json               # Master index
```

### Aquatic globe (curated model)

The aquatic globe uses a curated 200-species model with `final.json` instead of tiles:

```
output/aquatic/
├── final.json                       # 200 curated species with viewing spots
├── hotspots.json                    # 25 hotspot locations
├── sprites/
│   ├── manifest.json                # Full sprite index + fallback chain
│   ├── sp-{speciesId}.png           # 179 curated species images
│   ├── grp-{group}.png             # group fallbacks
│   └── fb-{bodyType}.png           # body-type fallbacks
└── migration_routes.json            # Marine migration routes
```

## Aquatic: final.json (curated model)

Array of 200 curated species, each with viewing spots and metadata.

```json
[
  {
    "aphiaId": 137090,
    "tier": "star",
    "name": "Balaenoptera musculus",
    "nameZh": "蓝鲸",
    "scientificName": "Balaenoptera musculus",
    "tagline": {
      "en": "The largest animal ever to live on Earth",
      "zh": "地球上有史以来最大的动物"
    },
    "sprite": "sp-blue_whale.png",
    "display": { "scale": 1.2, "animation": "swim" },
    "viewingSpots": [
      {
        "hotspotId": "monterey_bay",
        "name": "Monterey Bay",
        "country": "US",
        "lat": 36.8,
        "lng": -121.9,
        "season": "Jul-Oct",
        "reliability": "high",
        "activity": "whale_watching"
      }
    ]
  }
]
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `aphiaId` | number | Yes | WoRMS AphiaID, unique per species |
| `tier` | string | Yes | One of: "star", "ecosystem", "surprise" |
| `name` | string | Yes | Scientific name |
| `nameZh` | string | No | Chinese common name |
| `scientificName` | string | Yes | Scientific name (from crosswalk or curation) |
| `tagline` | object | No | `{en, zh}` short description |
| `sprite` | string | Yes | Pre-resolved sprite filename |
| `display` | object | Yes | Frontend display hints (scale, animation) |
| `viewingSpots` | array | Yes | Real-world locations to see this species |
| `viewingSpots[].hotspotId` | string | No | Reference to hotspots.json |
| `viewingSpots[].name` | string | Yes | Location name |
| `viewingSpots[].country` | string | Yes | ISO 3166-1 alpha-2 country code |
| `viewingSpots[].lat` | number | Yes | Latitude (-90 to 90) |
| `viewingSpots[].lng` | number | Yes | Longitude (-180 to 180) |
| `viewingSpots[].season` | string | Yes | Best season (e.g., "Jul-Oct", "year-round") |
| `viewingSpots[].reliability` | string | Yes | "high", "medium", or "low" |
| `viewingSpots[].activity` | string | Yes | Activity type (e.g., "diving", "whale_watching") |

## Aquatic: hotspots.json

Array of 25 hotspot locations referenced by `viewingSpots[].hotspotId`.

```json
[
  {
    "id": "great_barrier_reef",
    "name": { "en": "Great Barrier Reef", "zh": "大堡礁" },
    "country": "AU",
    "lat": -18.29,
    "lng": 147.70,
    "type": "coral_reef",
    "minSpeciesCount": 5
  }
]
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique hotspot ID, referenced by viewingSpots |
| `name` | object | Yes | `{en, zh}` display name |
| `country` | string | Yes | ISO 3166-1 alpha-2 country code |
| `lat` | number | Yes | Latitude (-90 to 90) |
| `lng` | number | Yes | Longitude (-180 to 180) |
| `type` | string | Yes | Location type (e.g., "coral_reef", "open_ocean", "kelp_forest") |
| `minSpeciesCount` | number | Yes | Minimum species expected at this hotspot |

---

## Tile-based schemas (dino, quake, meteor, volcano)

The following schemas apply to tile-based globes. The aquatic globe no longer uses tiles — see final.json and hotspots.json above.

## Cluster tile (z0-z3)
Max file size: 5KB
```json
{
  "zoom": 0,
  "x": 0,
  "y": 0,
  "clusters": [
    {
      "lat": 35.6,
      "lng": 139.7,
      "count": 482,
      "topItems": [
        {"id": "123", "name": "Common Carp", "thumb": "123.webp"}
      ],
      "filterAggs": {
        "waterType": {"Freshwater": 300, "Saltwater": 182}
      }
    }
  ]
}
```

### Aquatic cluster tile (DEPRECATED — aquatic now uses final.json)

> **Note**: The aquatic globe no longer uses tile-based output. These schemas are retained for reference only.

Clusters span z0-z5 for the aquatic globe. Tiles at z4-z5 contain both `clusters` and `points` arrays (overlap zone).

Each `topItems` entry gains `sprite` and `group`. A new `groupDistribution` field lists the top 5 groups by count.

```json
{
  "zoom": 2,
  "x": 1,
  "y": 1,
  "clusters": [
    {
      "lat": 35.6,
      "lng": 139.7,
      "count": 482,
      "topItems": [
        {
          "id": "100",
          "name": "Bigscale mackerel",
          "thumb": "Gamel_u5.jpg",
          "sprite": "sp-100.png",
          "group": "tuna_mackerel"
        }
      ],
      "groupDistribution": [
        {"group": "shark", "count": 12},
        {"group": "tuna_mackerel", "count": 8},
        {"group": "jellyfish", "count": 3}
      ],
      "filterAggs": {
        "waterType": {"Freshwater": 300, "Saltwater": 182}
      }
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `topItems[].sprite` | string | Yes | Pre-resolved sprite filename, never null |
| `topItems[].group` | string | Yes | Search group key (e.g., "shark", "octopus") |
| `groupDistribution` | array | Yes | Top 5 groups with counts for swarm rendering |
| `groupDistribution[].group` | string | Yes | Group key matching search_index.json |
| `groupDistribution[].count` | number | Yes | Number of species in this group within the cluster |

## Point tile (z4+)
Max file size: 30KB. Max 200 points per tile.
```json
{
  "zoom": 4,
  "x": 8,
  "y": 5,
  "points": [
    {
      "id": "123",
      "lat": 35.6895,
      "lng": 139.6917,
      "name": "Common Carp",
      "nameZh": "鲤鱼",
      "thumb": "123.webp",
      "rarity": 1,
      "waterType": "Freshwater"
    }
  ]
}
```
Note: point objects include enough fields for filtering client-side.
Theme-specific fields (rarity, era, magnitude, etc.) vary by globe.

### Aquatic point tile (DEPRECATED — aquatic now uses final.json)

> **Note**: The aquatic globe no longer uses tile-based output. These schemas are retained for reference only.

Each point gains `sprite` and `group` fields alongside existing fields.

```json
{
  "zoom": 5,
  "x": 16,
  "y": 10,
  "points": [
    {
      "id": "123",
      "lat": 35.6895,
      "lng": 139.6917,
      "name": "Common Carp",
      "nameZh": "鲤鱼",
      "thumb": "123.webp",
      "sprite": "sp-123.png",
      "group": "carp_minnow",
      "rarity": 1,
      "waterType": "Freshwater",
      "precision": 4
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sprite` | string | Yes | Pre-resolved sprite filename for globe marker icon, never null |
| `group` | string | Yes | Search group key for filtering |

`thumb` is retained for photo-based popups/hover cards. `sprite` is for the globe marker icon. They serve different purposes.

## Detail file (per item)
Max file size: 3KB (text only, images are URLs)
```json
{
  "id": "123",
  "name": "Common Carp",
  "nameZh": "鲤鱼",
  "scientificName": "Cyprinus carpio",
  "family": "Cyprinidae",
  "description": "One of the most widely distributed freshwater fish...",
  "descriptionZh": "鲤鱼是世界上分布最广泛的淡水鱼之一...",
  "metadata": {
    "maxLength": "120 cm",
    "maxWeight": "40 kg",
    "lifespan": "20-47 years",
    "habitat": "Freshwater",
    "depth": "0-20 m",
    "diet": "Omnivore",
    "rarity": "Common"
  },
  "images": [],
  "links": [
    {"label": "FishBase", "url": "https://www.fishbase.se/summary/123"},
    {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Common_carp"}
  ],
  "attribution": "FishBase (CC-BY-NC), GBIF"
}
```

### Aquatic detail file (DEPRECATED — aquatic now uses final.json)

> **Note**: The aquatic globe no longer generates per-species detail files. These schemas are retained for reference only.

All existing fields are retained. New fields added for the sprite system and taxonomic classification:

```json
{
  "id": "123",
  "name": "Common Carp",
  "nameZh": "鲤鱼",
  "scientificName": "Cyprinus carpio",
  "family": "Cyprinidae",
  "description": "One of the most widely distributed freshwater fish...",
  "descriptionZh": "鲤鱼是世界上分布最广泛的淡水鱼之一...",
  "sprite": "sp-123.png",
  "group": "carp_minnow",
  "bodyType": "fusiform",
  "bodyGroup": "fish",
  "metadata": {
    "maxLength": "120 cm",
    "maxWeight": "40 kg",
    "lifespan": "20-47 years",
    "habitat": "Freshwater",
    "depth": "0-20 m",
    "diet": "Omnivore",
    "rarity": "Common"
  },
  "images": [],
  "links": [
    {"label": "FishBase", "url": "https://www.fishbase.se/summary/123"},
    {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Common_carp"}
  ],
  "attribution": "FishBase (CC-BY-NC), GBIF, OBIS"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sprite` | string | Yes | sprite filename for species outline, never null |
| `group` | string | Yes | Search group key (e.g., "shark", "octopus", "carp_minnow") |
| `bodyType` | string | Yes | One of ~10 body types: fusiform, flat, elongated, deep-bodied, seahorse, globular, cetacean, crustacean, cephalopod, jellyfish |
| `bodyGroup` | string | Yes | Broad visual classification for color tinting: fish, mammal, reptile, cephalopod, crustacean, cnidarian, echinoderm, mollusk, other |

Note: `bodyGroup` represents visual grouping, not strict taxonomy. Cephalopods are taxonomically mollusks but visually distinct, so they get their own bodyGroup.

Note: `nameZh` is available for fish (from FishBase). For non-fish taxa it will be null unless a Chinese name mapping is sourced separately.

## Sprite manifest

`output/aquatic/sprites/manifest.json` — indexes all sprites and defines the fallback chain.

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
  "note": "Fallback chain: sprites[speciesId] -> groupFallbacks[group] -> bodyTypeFallbacks[bodyType]. Resolved at ETL time -- frontend uses pre-resolved sprite field on each point/topItem."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Manifest schema version |
| `glowDefaults` | object | Suggested glow effect parameters for frontend |
| `bodyTypes` | array | All valid body type values |
| `sprites` | object | Keyed by species ID; one entry per curated species (~500) |
| `sprites[].file` | string | sprite filename (e.g., "sp-123.png") |
| `sprites[].group` | string | Search group key |
| `sprites[].bodyType` | string | Body type for fallback resolution |
| `sprites[].bodyGroup` | string | Visual classification for color tinting |
| `sprites[].license` | string | License of the source illustration |
| `groupFallbacks` | object | Group key to sprite filename (~50 entries) |
| `bodyTypeFallbacks` | object | Body type to sprite filename (~10 entries) |
| `totalSprites` | number | Total SVG files (species + group + body-type fallbacks) |

### Fallback chain

```
species sprite (500) -> group fallback (~50) -> body-type fallback (~10)
```

Merge-time pre-resolves the chain so every `sprite` field on every species in final.json is a valid filename. The frontend never walks the chain.

## Sprite format spec

All sprites in `output/aquatic/sprites/final/` are transparent PNG images:

| Property | Requirement |
|----------|-------------|
| Format | PNG with alpha transparency |
| Background | Transparent (no background color) |
| Style | Photorealistic, side profile, vivid natural colors |
| Orientation | Side-view, typically facing left |

Naming convention:
- `sp-{speciesId}.png` — curated species (179 files)
- `sp-{commonName}.png` — replacement sprites with common names

## Master index (tile-based globes only)

Used by tile-based globes (dino, quake, meteor, volcano). The aquatic globe does not use index.json.

```json
{
  "globeId": "dino",
  "version": "1.0.0",
  "totalItems": 22930,
  "lastUpdated": "2026-03-19",
  "tileZoomRange": [0, 7],
  "filters": [
    {"key": "era", "label": "Era", "type": "chips", "options": ["Triassic", "Jurassic", "Cretaceous"]}
  ],
  "attribution": [
    {"name": "PBDB", "license": "CC-BY 4.0", "url": "https://paleobiodb.org"}
  ]
}
```

## Tile coordinate system
Standard web mercator (slippy map) tile numbering:
- Zoom N has 2^N x 2^N tiles
- Tile (x, y) at zoom z covers a specific lat/lng bounding box
- Use scripts/tile_splitter.py to compute tile assignments from lat/lng points
