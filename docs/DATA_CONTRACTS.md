# Data Contracts — Output Schema for All Globes

All tile files must conform to these schemas. Validated by `scripts/validate.py`.

## Directory structure per globe
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

### Aquatic globe directory structure

The aquatic globe extends the standard layout with a `sprites/` directory:

```
output/aquatic/
├── tiles/
│   ├── z0-z3/{x}_{y}.json          # Cluster tiles with swarm data
│   └── z4-z7/{x}_{y}.json          # Point tiles with sprite refs
├── species/
│   └── {id}.json                    # Detail files with sprite/group/bodyType
├── sprites/
│   ├── manifest.json                # Full sprite index + fallback chain
│   ├── sp-{speciesId}.png           # 179 curated species images
│   ├── grp-{group}.png             # group fallbacks
│   └── fb-{bodyType}.png           # body-type fallbacks
├── index.json                       # Master index with expanded filters
├── search_index.json                # ~50 groups
└── migration_routes.json            # Marine migration routes
```

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

### Aquatic cluster tile (z0-z5)

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

### Aquatic point tile (z4+)

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

### Aquatic detail file

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

ETL pre-resolves the chain so every `sprite` field on every point and topItem is a valid filename. The frontend never walks the chain.

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

## Master index
```json
{
  "globeId": "aquatic",
  "version": "1.0.0",
  "totalItems": 35000,
  "lastUpdated": "2026-03-19",
  "tileZoomRange": [0, 7],
  "filters": [
    {"key": "waterType", "label": "Water Type", "type": "chips", "options": ["Freshwater", "Saltwater", "Brackish"]},
    {"key": "depth", "label": "Depth", "type": "range", "min": 0, "max": 8000, "unit": "m"},
    {"key": "rarity", "label": "Rarity", "type": "chips", "options": ["Common", "Uncommon", "Rare", "Legendary"]}
  ],
  "attribution": [
    {"name": "FishBase", "license": "CC-BY-NC 4.0", "url": "https://www.fishbase.se"},
    {"name": "GBIF", "license": "CC0/CC-BY 4.0", "url": "https://www.gbif.org"}
  ]
}
```

## Tile coordinate system
Standard web mercator (slippy map) tile numbering:
- Zoom N has 2^N x 2^N tiles
- Tile (x, y) at zoom z covers a specific lat/lng bounding box
- Use scripts/tile_splitter.py to compute tile assignments from lat/lng points
