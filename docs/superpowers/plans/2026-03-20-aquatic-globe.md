# Aquatic Globe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full aquatic life globe ETL that replaces the fish-only globe with OBIS+GBIF occurrence data, FishBase metadata enrichment, and 500+ SVG sprite outlines with glowing neon rendering.

**Architecture:** Three-layer hybrid pipeline — OBIS and GBIF provide occurrence coordinates (bulk downloads), FishBase provides species metadata (parquet reads). All species keyed by WoRMS AphiaID with crosswalk table. Output includes spatial tiles with pre-resolved sprite references, 560 SVG outline files, and a sprite manifest. tile_splitter.py is modified minimally to support `groupDistribution` on cluster tiles.

**Tech Stack:** Python 3.11+, pandas, duckdb (parquet reads), requests, boto3 (S3 for OBIS), aiohttp (parallel sprite fetching), svgpathtools (SVG normalization), potrace (raster→SVG tracing)

**Spec:** `docs/superpowers/specs/2026-03-20-aquatic-globe-sprites-design.md`

---

## File Structure

### New files to create:
| File | Responsibility |
|------|---------------|
| `scripts/aquatic_etl.py` | Main ETL orchestrator: download, clean, merge, enrich, tile, detail, index |
| `scripts/fetch_aquatic_sprites.py` | Multi-source sprite fetcher: Phylopic, FishBase, Wikimedia, NOAA, GBIF |
| `scripts/normalize_sprites.py` | SVG normalization: strip fills, standardize viewBox/stroke, raster→outline |
| `scripts/build_sprite_manifest.py` | Generate manifest.json with fallback chain resolution |
| `scripts/aquatic_groups.py` | Taxonomy group definitions (~50 groups) + body type mappings |
| `scripts/build_aquatic_search_index.py` | Search index for ~50 aquatic groups |
| `scripts/generate_sprite_list.py` | Curate the 500 species list ranked by occurrence count + recognition |
| `tests/test_aquatic_etl.py` | Tests for data pipeline |
| `tests/test_sprites.py` | Tests for sprite fetching + normalization |
| `tests/test_sprite_manifest.py` | Tests for manifest generation + fallback resolution |

### Files to modify:
| File | Change |
|------|--------|
| `scripts/validate.py` | Add sprite field validation, groupDistribution checks |
| `docs/DATA_CONTRACTS.md` | Add aquatic globe schemas, sprite fields |
| `CLAUDE.md` | Add OBIS/GBIF data source entries |

### Files to modify (minor):
| File | Change |
|------|--------|
| `scripts/tile_splitter.py` | Add optional `group_distribution_key` param to `_make_cluster` and `build_cluster_tiles` |

### Files unchanged (reused as-is):
| File | Why |
|------|-----|
| `scripts/fish_etl.py` | Kept for backward compatibility until aquatic is stable |

---

## Task 1: Aquatic Group Definitions & Body Type Mappings

**Files:**
- Create: `scripts/aquatic_groups.py`
- Test: `tests/test_aquatic_groups.py`

This is the taxonomy backbone. Every downstream task depends on these mappings.

- [ ] **Step 1: Write failing test for group classification**

```python
# tests/test_aquatic_groups.py
from scripts.aquatic_groups import classify_group, classify_body_type, GROUPS, BODY_TYPES

def test_shark_classified():
    assert classify_group(class_name="Elasmobranchii", order="Carcharhiniformes", family="Carcharhinidae") == "shark"

def test_orca_classified():
    assert classify_group(class_name="Mammalia", order="Cetacea", family="Delphinidae") == "dolphin"

def test_sea_turtle_classified():
    assert classify_group(class_name="Reptilia", order="Testudines", family="Cheloniidae") == "sea_turtle"

def test_octopus_classified():
    assert classify_group(class_name="Cephalopoda", order="Octopoda", family="Octopodidae") == "octopus_squid"

def test_jellyfish_classified():
    assert classify_group(class_name="Scyphozoa", order="Semaeostomeae", family="Ulmaridae") == "jellyfish"

def test_unknown_fallback():
    assert classify_group(class_name="Unknown", order="Unknown", family="Unknown") == "other"

def test_body_type_shark():
    assert classify_body_type("shark") == "fusiform"

def test_body_type_whale():
    assert classify_body_type("whale") == "cetacean"

def test_body_type_octopus():
    assert classify_body_type("octopus_squid") == "cephalopod"

def test_body_type_jellyfish():
    assert classify_body_type("jellyfish") == "jellyfish"

def test_body_type_unknown():
    assert classify_body_type("other") == "fusiform"  # default fallback

def test_body_group_fish():
    from scripts.aquatic_groups import classify_body_group
    assert classify_body_group("shark") == "fish"
    assert classify_body_group("whale") == "mammal"
    assert classify_body_group("octopus_squid") == "cephalopod"
    assert classify_body_group("jellyfish") == "cnidarian"
    assert classify_body_group("crab_lobster") == "crustacean"
    assert classify_body_group("sea_turtle") == "reptile"

def test_all_groups_have_body_type():
    for g in GROUPS:
        assert classify_body_type(g["id"]) in BODY_TYPES

def test_group_count():
    assert len(GROUPS) >= 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_groups.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement aquatic_groups.py**

```python
# scripts/aquatic_groups.py
"""Taxonomy group definitions and body type mappings for the aquatic globe."""

BODY_TYPES = [
    "fusiform", "flat", "elongated", "deep-bodied", "seahorse",
    "globular", "cetacean", "crustacean", "cephalopod", "jellyfish",
]

# Each group: id, label, match rules (class, order, family), body_type, body_group
GROUPS = [
    # --- Fish (from existing 36, condensed + expanded) ---
    {"id": "shark", "label": "Sharks", "class": "Elasmobranchii",
     "orders": ["Carcharhiniformes", "Lamniformes", "Squaliformes", "Orectolobiformes",
                "Hexanchiformes", "Pristiophoriformes", "Squatiniformes", "Heterodontiformes"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "ray", "label": "Rays & Skates", "class": "Elasmobranchii",
     "orders": ["Rajiformes", "Myliobatiformes", "Torpediniformes", "Rhinopristiformes"],
     "body_type": "flat", "body_group": "fish"},
    {"id": "eel", "label": "Eels", "orders": ["Anguilliformes"],
     "body_type": "elongated", "body_group": "fish"},
    {"id": "catfish", "label": "Catfish", "orders": ["Siluriformes"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "salmon_trout", "label": "Salmon & Trout", "families": ["Salmonidae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "tuna_mackerel", "label": "Tuna & Mackerel", "families": ["Scombridae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "seahorse", "label": "Seahorses & Pipefish", "families": ["Syngnathidae"],
     "body_type": "seahorse", "body_group": "fish"},
    {"id": "clownfish", "label": "Clownfish & Damselfish", "families": ["Pomacentridae"],
     "body_type": "deep-bodied", "body_group": "fish"},
    {"id": "pufferfish", "label": "Pufferfish", "families": ["Tetraodontidae", "Diodontidae"],
     "body_type": "globular", "body_group": "fish"},
    {"id": "angelfish", "label": "Angelfish", "families": ["Pomacanthidae"],
     "body_type": "deep-bodied", "body_group": "fish"},
    {"id": "grouper", "label": "Groupers", "families": ["Serranidae", "Epinephelidae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "wrasse", "label": "Wrasses", "families": ["Labridae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "carp_minnow", "label": "Carp & Minnow", "families": ["Cyprinidae", "Leuciscidae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "goby", "label": "Gobies", "families": ["Gobiidae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "cichlid", "label": "Cichlids", "families": ["Cichlidae"],
     "body_type": "deep-bodied", "body_group": "fish"},
    {"id": "butterflyfish", "label": "Butterflyfish", "families": ["Chaetodontidae"],
     "body_type": "deep-bodied", "body_group": "fish"},
    {"id": "parrotfish", "label": "Parrotfish", "families": ["Scaridae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "triggerfish", "label": "Triggerfish", "families": ["Balistidae"],
     "body_type": "deep-bodied", "body_group": "fish"},
    {"id": "surgeonfish", "label": "Surgeonfish & Tang", "families": ["Acanthuridae"],
     "body_type": "deep-bodied", "body_group": "fish"},
    {"id": "blenny", "label": "Blennies", "orders": ["Blenniiformes"],
     "body_type": "elongated", "body_group": "fish"},
    {"id": "scorpionfish", "label": "Scorpionfish & Lionfish", "families": ["Scorpaenidae"],
     "body_type": "globular", "body_group": "fish"},
    {"id": "flatfish", "label": "Flatfish", "orders": ["Pleuronectiformes"],
     "body_type": "flat", "body_group": "fish"},
    {"id": "cod", "label": "Cod & Haddock", "families": ["Gadidae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "herring", "label": "Herring & Sardine", "families": ["Clupeidae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "anchovy", "label": "Anchovies", "families": ["Engraulidae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "bass", "label": "Bass & Perch", "families": ["Moronidae", "Percidae", "Centrarchidae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "snapper", "label": "Snappers", "families": ["Lutjanidae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "barracuda", "label": "Barracuda", "families": ["Sphyraenidae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "swordfish", "label": "Swordfish & Marlin", "families": ["Xiphiidae", "Istiophoridae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "flying_fish", "label": "Flying Fish", "families": ["Exocoetidae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "anglerfish", "label": "Anglerfish", "orders": ["Lophiiformes"],
     "body_type": "globular", "body_group": "fish"},
    {"id": "piranha", "label": "Piranhas & Tetras", "families": ["Serrasalmidae", "Characidae"],
     "body_type": "deep-bodied", "body_group": "fish"},
    {"id": "sturgeon", "label": "Sturgeon", "families": ["Acipenseridae"],
     "body_type": "fusiform", "body_group": "fish"},
    {"id": "sunfish", "label": "Ocean Sunfish", "families": ["Molidae"],
     "body_type": "deep-bodied", "body_group": "fish"},
    {"id": "moray", "label": "Moray Eels", "families": ["Muraenidae"],
     "body_type": "elongated", "body_group": "fish"},
    {"id": "lamprey", "label": "Lampreys", "orders": ["Petromyzontiformes"],
     "body_type": "elongated", "body_group": "fish"},
    {"id": "hagfish", "label": "Hagfish", "class_only": "Myxini",
     "body_type": "elongated", "body_group": "fish"},
    {"id": "lungfish", "label": "Lungfish", "orders": ["Ceratodontiformes", "Lepidosireniformes"],
     "body_type": "elongated", "body_group": "fish"},
    {"id": "other_fish", "label": "Other Fish", "class_only": "Actinopterygii",
     "body_type": "fusiform", "body_group": "fish"},
    # --- Marine mammals ---
    {"id": "whale", "label": "Whales", "families": ["Balaenopteridae", "Balaenidae", "Physeteridae",
     "Eschrichtiidae", "Ziphiidae", "Kogiidae"],
     "body_type": "cetacean", "body_group": "mammal"},
    {"id": "dolphin", "label": "Dolphins & Porpoises", "families": ["Delphinidae", "Phocoenidae",
     "Platanistidae", "Iniidae", "Pontoporiidae"],
     "body_type": "cetacean", "body_group": "mammal"},
    {"id": "seal", "label": "Seals & Sea Lions", "families": ["Phocidae", "Otariidae", "Odobenidae"],
     "body_type": "cetacean", "body_group": "mammal"},
    {"id": "sea_otter", "label": "Sea Otters & Manatees",
     "families": ["Mustelidae", "Trichechidae", "Dugongidae"],
     "body_type": "cetacean", "body_group": "mammal"},
    # --- Reptiles ---
    {"id": "sea_turtle", "label": "Sea Turtles", "families": ["Cheloniidae", "Dermochelyidae"],
     "body_type": "flat", "body_group": "reptile"},
    {"id": "sea_snake", "label": "Sea Snakes", "families": ["Elapidae"],
     "orders": ["Squamata"], "body_type": "elongated", "body_group": "reptile"},
    # --- Cephalopods ---
    {"id": "octopus_squid", "label": "Octopus & Squid", "class_only": "Cephalopoda",
     "body_type": "cephalopod", "body_group": "cephalopod"},
    # --- Crustaceans ---
    {"id": "crab_lobster", "label": "Crabs & Lobsters",
     "orders": ["Decapoda"],
     "class_only": "Malacostraca",
     "body_type": "crustacean", "body_group": "crustacean"},
    {"id": "shrimp", "label": "Shrimp & Krill",
     "orders": ["Euphausiacea"],
     "body_type": "crustacean", "body_group": "crustacean"},
    # --- Cnidarians ---
    {"id": "jellyfish", "label": "Jellyfish",
     "class_only": "Scyphozoa",
     "body_type": "jellyfish", "body_group": "cnidarian"},
    {"id": "coral", "label": "Corals", "class_only": "Anthozoa",
     "body_type": "jellyfish", "body_group": "cnidarian"},
    # --- Echinoderms ---
    {"id": "starfish", "label": "Starfish & Sea Urchins", "phylum_only": "Echinodermata",
     "body_type": "flat", "body_group": "echinoderm"},
    # --- Mollusks (non-cephalopod) ---
    {"id": "clam_mussel", "label": "Clams, Mussels & Oysters", "class_only": "Bivalvia",
     "body_type": "flat", "body_group": "mollusk"},
    {"id": "sea_snail", "label": "Sea Snails & Nudibranchs", "class_only": "Gastropoda",
     "body_type": "globular", "body_group": "mollusk"},
    # --- Sponges ---
    {"id": "sponge", "label": "Sponges", "phylum_only": "Porifera",
     "body_type": "globular", "body_group": "other"},
]

# Lookup dicts built from GROUPS
_GROUP_BY_ID = {g["id"]: g for g in GROUPS}

_BODY_TYPE_MAP = {g["id"]: g["body_type"] for g in GROUPS}
_BODY_TYPE_MAP["other"] = "fusiform"  # default

_BODY_GROUP_MAP = {g["id"]: g["body_group"] for g in GROUPS}
_BODY_GROUP_MAP["other"] = "other"


def classify_group(class_name: str = "", order: str = "", family: str = "",
                   phylum: str = "") -> str:
    """Classify a species into a group based on taxonomy. Returns group id."""
    # Priority 1: family match (most specific)
    for g in GROUPS:
        if "families" in g and family in g["families"]:
            # If group also requires order/class, check those too
            if "orders" in g and order not in g["orders"]:
                continue
            if "class" in g and class_name != g["class"]:
                continue
            return g["id"]

    # Priority 2: order match
    for g in GROUPS:
        if "orders" in g and order in g["orders"] and "families" not in g:
            if "class" in g and class_name != g["class"]:
                continue
            return g["id"]

    # Priority 3: class_only match
    for g in GROUPS:
        if "class_only" in g and class_name == g["class_only"]:
            return g["id"]

    # Priority 4: phylum_only match
    for g in GROUPS:
        if "phylum_only" in g and phylum == g["phylum_only"]:
            return g["id"]

    # Priority 5: broad class match (e.g., other_fish catches remaining Actinopterygii)
    for g in GROUPS:
        if g.get("class_only") == class_name:
            return g["id"]

    return "other"


def classify_body_type(group_id: str) -> str:
    """Return body type for a group id."""
    return _BODY_TYPE_MAP.get(group_id, "fusiform")


def classify_body_group(group_id: str) -> str:
    """Return body group (visual classification) for a group id."""
    return _BODY_GROUP_MAP.get(group_id, "other")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_groups.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/aquatic_groups.py tests/test_aquatic_groups.py
git commit -m "feat(aquatic): add taxonomy group definitions and body type mappings"
```

---

## Task 2: OBIS Bulk Data Download

**Files:**
- Create: `scripts/aquatic_etl.py` (download section only)
- Test: `tests/test_aquatic_etl.py`

Downloads the OBIS full Parquet export from S3. This is ~40GB so the script must handle large files gracefully.

- [ ] **Step 1: Write failing test for OBIS download function signature**

```python
# tests/test_aquatic_etl.py
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from scripts.aquatic_etl import download_obis, RAW_DIR

def test_download_obis_skips_if_exists(tmp_path):
    """download_obis should skip if parquet already exists."""
    fake_file = tmp_path / "obis_occurrences.parquet"
    fake_file.write_text("exists")
    with patch("scripts.aquatic_etl.RAW_DIR", tmp_path):
        download_obis()  # should not raise, should skip
    assert fake_file.read_text() == "exists"  # unchanged

def test_raw_dir_is_aquatic():
    assert "aquatic" in str(RAW_DIR)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_etl.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement download_obis in aquatic_etl.py**

```python
# scripts/aquatic_etl.py
"""Aquatic globe ETL — OBIS + GBIF occurrences, FishBase metadata, sprite integration."""
import os
import subprocess
import sys
import json
import argparse
from pathlib import Path
from datetime import date

import pandas as pd
import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "aquatic"
OUTPUT_DIR = ROOT / "output" / "aquatic"

# OBIS S3 bucket (public, no auth needed)
OBIS_S3_PATH = "s3://obis-products/exports/obis_20240101.parquet"
# Adjust the date suffix to the latest available export


def download_obis():
    """Download OBIS full Parquet export from S3. ~40GB, one bulk download."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "obis_occurrences.parquet"
    if out.exists():
        print(f"  OBIS data already exists at {out}, skipping")
        return
    print("Downloading OBIS full export from S3 (this may take a while)...")
    # Use aws CLI with --no-sign-request for public bucket
    subprocess.run(
        ["aws", "s3", "cp", "--no-sign-request", OBIS_S3_PATH, str(out)],
        check=True,
    )
    print(f"  OBIS data saved to {out}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_etl.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/aquatic_etl.py tests/test_aquatic_etl.py
git commit -m "feat(aquatic): add OBIS bulk download from S3"
```

---

## Task 3: GBIF Async Bulk Download

**Files:**
- Modify: `scripts/aquatic_etl.py`
- Modify: `tests/test_aquatic_etl.py`

GBIF async download API: POST a download request, poll until ready, download ZIP.

- [ ] **Step 1: Write failing test**

```python
# tests/test_aquatic_etl.py (append)
from scripts.aquatic_etl import download_gbif

def test_download_gbif_skips_if_exists(tmp_path):
    fake_file = tmp_path / "gbif_occurrences.csv"
    fake_file.write_text("exists")
    with patch("scripts.aquatic_etl.RAW_DIR", tmp_path):
        download_gbif()
    assert fake_file.read_text() == "exists"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_etl.py::test_download_gbif_skips_if_exists -v`
Expected: FAIL

- [ ] **Step 3: Implement download_gbif**

```python
# Add to scripts/aquatic_etl.py
import requests
import time
import zipfile

GBIF_API = "https://api.gbif.org/v1"
# Aquatic phyla/classes to include
GBIF_TAXON_KEYS = [
    44,    # Chordata (fish, mammals, reptiles)
    52,    # Mollusca
    54,    # Arthropoda (crustaceans)
    43,    # Cnidaria
    48,    # Echinodermata
    105,   # Porifera
]


def download_gbif():
    """Download GBIF occurrences via async download API. One POST + one GET."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "gbif_occurrences.csv"
    if out.exists():
        print(f"  GBIF data already exists at {out}, skipping")
        return

    # Check for existing download key
    key_file = RAW_DIR / "gbif_download_key.txt"
    if key_file.exists():
        download_key = key_file.read_text().strip()
        print(f"  Resuming GBIF download {download_key}")
    else:
        # Submit download request
        # NOTE: Requires GBIF account credentials in env vars GBIF_USER / GBIF_PWD
        user = os.environ.get("GBIF_USER", "")
        pwd = os.environ.get("GBIF_PWD", "")
        if not user or not pwd:
            print("ERROR: Set GBIF_USER and GBIF_PWD environment variables")
            print("Register at https://www.gbif.org/user/profile")
            sys.exit(1)

        payload = {
            "creator": user,
            "notification_address": [],
            "format": "SIMPLE_CSV",
            "predicate": {
                "type": "and",
                "predicates": [
                    {"type": "equals", "key": "HAS_COORDINATE", "value": "true"},
                    {"type": "equals", "key": "HAS_GEOSPATIAL_ISSUE", "value": "false"},
                    {"type": "in", "key": "TAXON_KEY", "values": [str(k) for k in GBIF_TAXON_KEYS]},
                    {"type": "equals", "key": "OCCURRENCE_STATUS", "value": "PRESENT"},
                ]
            }
        }
        resp = requests.post(
            f"{GBIF_API}/occurrence/download/request",
            json=payload,
            auth=(user, pwd),
            timeout=60,
        )
        resp.raise_for_status()
        download_key = resp.text
        key_file.write_text(download_key)
        print(f"  GBIF download submitted: {download_key}")

    # Poll until ready
    while True:
        resp = requests.get(f"{GBIF_API}/occurrence/download/{download_key}", timeout=30)
        status = resp.json().get("status", "")
        if status == "SUCCEEDED":
            break
        elif status in ("FAILED", "CANCELLED", "KILLED"):
            print(f"ERROR: GBIF download {status}")
            sys.exit(1)
        print(f"  GBIF download status: {status}, waiting 30s...")
        time.sleep(30)

    # Download ZIP
    zip_path = RAW_DIR / "gbif_download.zip"
    print("  Downloading GBIF ZIP...")
    resp = requests.get(
        f"{GBIF_API}/occurrence/download/request/{download_key}",
        stream=True, timeout=600,
    )
    with open(zip_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    # Extract CSV
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = [n for n in zf.namelist() if n.endswith(".csv")][0]
        with zf.open(csv_name) as src, open(out, "wb") as dst:
            dst.write(src.read())
    zip_path.unlink()
    key_file.unlink()
    print(f"  GBIF data saved to {out}")
```

- [ ] **Step 4: Run tests**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_etl.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/aquatic_etl.py tests/test_aquatic_etl.py
git commit -m "feat(aquatic): add GBIF async bulk download"
```

---

## Task 4: Taxonomic Normalization & ID Crosswalk

**Files:**
- Modify: `scripts/aquatic_etl.py`
- Modify: `tests/test_aquatic_etl.py`

Build the WoRMS AphiaID crosswalk and merge OBIS+GBIF occurrences.

- [ ] **Step 1: Write failing test for merge + dedup**

```python
# tests/test_aquatic_etl.py (append)
import pandas as pd
from scripts.aquatic_etl import merge_occurrences, build_id_crosswalk

def test_merge_deduplicates():
    """Same species at same z7 tile should deduplicate to one point."""
    obis = pd.DataFrame({
        "aphia_id": [123, 123, 456],
        "lat": [47.6, 47.601, 10.0],  # first two are same z7 tile
        "lng": [-122.3, -122.301, 20.0],
        "scientific_name": ["Orcinus orca", "Orcinus orca", "Thunnus thynnus"],
        "class": ["Mammalia", "Mammalia", "Actinopterygii"],
        "order": ["Cetacea", "Cetacea", "Scombriformes"],
        "family": ["Delphinidae", "Delphinidae", "Scombridae"],
        "phylum": ["Chordata", "Chordata", "Chordata"],
    })
    gbif = pd.DataFrame({
        "aphia_id": [123, 789],
        "lat": [47.602, 35.0],
        "lng": [-122.302, 139.0],
        "scientific_name": ["Orcinus orca", "Chelonia mydas"],
        "class": ["Mammalia", "Reptilia"],
        "order": ["Cetacea", "Testudines"],
        "family": ["Delphinidae", "Cheloniidae"],
        "phylum": ["Chordata", "Chordata"],
    })
    merged = merge_occurrences(obis, gbif)
    # Orcas near Seattle should dedup to ~1 point at z7
    orca_points = merged[merged["aphia_id"] == 123]
    assert len(orca_points) <= 2  # deduped from 3 to ~1-2

def test_build_crosswalk():
    df = pd.DataFrame({
        "aphia_id": [123, 456],
        "scientific_name": ["Orcinus orca", "Thunnus thynnus"],
    })
    crosswalk = build_id_crosswalk(df)
    assert 123 in crosswalk
    assert crosswalk[123]["scientificName"] == "Orcinus orca"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_etl.py::test_merge_deduplicates -v`
Expected: FAIL

- [ ] **Step 3: Implement merge_occurrences and build_id_crosswalk**

```python
# Add to scripts/aquatic_etl.py
import math

from scripts.tile_splitter import lat_lng_to_tile

def merge_occurrences(obis_df: pd.DataFrame, gbif_df: pd.DataFrame) -> pd.DataFrame:
    """Merge OBIS + GBIF occurrences, deduplicate to one point per species per z7 tile."""
    # Standardize columns
    combined = pd.concat([obis_df, gbif_df], ignore_index=True)

    # Quality filters
    combined = combined.dropna(subset=["lat", "lng", "aphia_id"])
    combined = combined[
        (combined["lat"].between(-90, 90)) &
        (combined["lng"].between(-180, 180))
    ]

    # Assign z7 tile for deduplication
    combined["_tile_x"], combined["_tile_y"] = zip(
        *combined.apply(lambda r: lat_lng_to_tile(r["lat"], r["lng"], 7), axis=1)
    )

    # Deduplicate: one point per species per z7 tile (centroid)
    grouped = combined.groupby(["aphia_id", "_tile_x", "_tile_y"])
    deduped = grouped.agg({
        "lat": "mean",
        "lng": "mean",
        "scientific_name": "first",
        "class": "first",
        "order": "first",
        "family": "first",
        "phylum": "first",
    }).reset_index()

    deduped = deduped.drop(columns=["_tile_x", "_tile_y"])
    deduped["lat"] = deduped["lat"].round(4)
    deduped["lng"] = deduped["lng"].round(4)
    return deduped


def build_id_crosswalk(df: pd.DataFrame) -> dict:
    """Build aphiaId → metadata crosswalk from merged DataFrame."""
    crosswalk = {}
    for _, row in df.drop_duplicates(subset=["aphia_id"]).iterrows():
        aid = int(row["aphia_id"])
        crosswalk[aid] = {
            "scientificName": row.get("scientific_name", ""),
            "gbifKey": row.get("gbif_taxon_key"),
            "fishbaseSpecCode": row.get("fishbase_spec_code"),
        }
    return crosswalk
```

- [ ] **Step 4: Run tests**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_etl.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/aquatic_etl.py tests/test_aquatic_etl.py
git commit -m "feat(aquatic): add OBIS+GBIF merge with z7 tile deduplication"
```

---

## Task 5: FishBase Metadata Enrichment

**Files:**
- Modify: `scripts/aquatic_etl.py`
- Modify: `tests/test_aquatic_etl.py`

Join FishBase metadata (diet, habitat, images, etc.) onto occurrence data via scientific name.

- [ ] **Step 1: Write failing test**

```python
# tests/test_aquatic_etl.py (append)
from scripts.aquatic_etl import enrich_with_fishbase

def test_enrich_adds_fishbase_metadata():
    occurrences = pd.DataFrame({
        "aphia_id": [123, 456],
        "lat": [47.6, 10.0],
        "lng": [-122.3, 20.0],
        "scientific_name": ["Thunnus thynnus", "Chelonia mydas"],
        "class": ["Actinopterygii", "Reptilia"],
        "order": ["Scombriformes", "Testudines"],
        "family": ["Scombridae", "Cheloniidae"],
        "phylum": ["Chordata", "Chordata"],
    })
    fishbase = pd.DataFrame({
        "scientific_name": ["Thunnus thynnus"],
        "SpecCode": [147],
        "FBname": ["Atlantic bluefin tuna"],
        "PicPreferredName": ["Ththyn_u0.jpg"],
        "Vulnerability": [74.0],
        "DepthRangeDeep": [985],
        "Fresh": [0], "Brack": [0], "Saltwater": [1],
    })
    result = enrich_with_fishbase(occurrences, fishbase)
    tuna = result[result["aphia_id"] == 123].iloc[0]
    assert tuna["common_name"] == "Atlantic bluefin tuna"
    assert tuna["thumb"] == "tn_Ththyn_u0.jpg"
    # Non-fish species should have null fishbase fields
    turtle = result[result["aphia_id"] == 456].iloc[0]
    assert pd.isna(turtle.get("thumb")) or turtle.get("thumb") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_etl.py::test_enrich_adds_fishbase_metadata -v`
Expected: FAIL

- [ ] **Step 3: Implement enrich_with_fishbase**

```python
# Add to scripts/aquatic_etl.py

def enrich_with_fishbase(occurrences: pd.DataFrame, fishbase_species: pd.DataFrame) -> pd.DataFrame:
    """Left-join FishBase metadata onto occurrences by scientific name."""
    # Build FishBase lookup columns
    fb = fishbase_species.copy()
    fb["scientific_name"] = fb["Genus"].fillna("") + " " + fb["Species"].fillna("")
    fb["scientific_name"] = fb["scientific_name"].str.strip()
    fb = fb.rename(columns={
        "FBname": "common_name",
        "SpecCode": "fishbase_spec_code",
        "Vulnerability": "vulnerability",
        "DepthRangeDeep": "depth_max",
    })
    fb["thumb"] = fb["PicPreferredName"].apply(
        lambda x: f"tn_{x}" if pd.notna(x) else None
    )
    fb["water_type"] = fb.apply(_derive_water_type, axis=1)

    keep_cols = ["scientific_name", "common_name", "fishbase_spec_code", "thumb",
                 "vulnerability", "depth_max", "water_type"]
    fb = fb[keep_cols].drop_duplicates(subset=["scientific_name"], keep="first")

    result = occurrences.merge(fb, on="scientific_name", how="left")
    # Fill common name from scientific name if no FishBase match
    result["common_name"] = result["common_name"].fillna(result["scientific_name"])
    return result


def _derive_water_type(row) -> str:
    """Classify water type from FishBase Fresh/Brack/Saltwater columns."""
    parts = []
    if row.get("Fresh") == 1: parts.append("Freshwater")
    if row.get("Brack") == 1: parts.append("Brackish")
    if row.get("Saltwater") == 1: parts.append("Saltwater")
    if not parts: return "Unknown"
    if len(parts) == 1: return parts[0]
    if "Brackish" in parts: return "Brackish"
    return parts[0]
```

- [ ] **Step 4: Run tests**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_etl.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/aquatic_etl.py tests/test_aquatic_etl.py
git commit -m "feat(aquatic): add FishBase metadata enrichment via scientific name join"
```

---

## Task 6: Group Classification Integration

**Files:**
- Modify: `scripts/aquatic_etl.py`
- Modify: `tests/test_aquatic_etl.py`

Apply aquatic_groups.py classifications to the enriched DataFrame.

- [ ] **Step 1: Write failing test**

```python
# tests/test_aquatic_etl.py (append)
from scripts.aquatic_etl import apply_classifications

def test_apply_classifications():
    df = pd.DataFrame({
        "aphia_id": [123, 456, 789],
        "scientific_name": ["Orcinus orca", "Thunnus thynnus", "Aurelia aurita"],
        "class": ["Mammalia", "Actinopterygii", "Scyphozoa"],
        "order": ["Cetacea", "Scombriformes", "Semaeostomeae"],
        "family": ["Delphinidae", "Scombridae", "Ulmaridae"],
        "phylum": ["Chordata", "Chordata", "Cnidaria"],
    })
    result = apply_classifications(df)
    assert result.iloc[0]["group"] == "dolphin"
    assert result.iloc[0]["body_type"] == "cetacean"
    assert result.iloc[0]["body_group"] == "mammal"
    assert result.iloc[1]["group"] == "tuna_mackerel"
    assert result.iloc[2]["group"] == "jellyfish"
    assert result.iloc[2]["body_group"] == "cnidarian"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_etl.py::test_apply_classifications -v`
Expected: FAIL

- [ ] **Step 3: Implement**

```python
# Add to scripts/aquatic_etl.py
from scripts.aquatic_groups import classify_group, classify_body_type, classify_body_group

def apply_classifications(df: pd.DataFrame) -> pd.DataFrame:
    """Add group, body_type, body_group columns based on taxonomy."""
    df = df.copy()
    df["group"] = df.apply(
        lambda r: classify_group(
            class_name=r.get("class", ""),
            order=r.get("order", ""),
            family=r.get("family", ""),
            phylum=r.get("phylum", ""),
        ), axis=1
    )
    df["body_type"] = df["group"].apply(classify_body_type)
    df["body_group"] = df["group"].apply(classify_body_group)
    return df
```

- [ ] **Step 4: Run tests**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_etl.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/aquatic_etl.py tests/test_aquatic_etl.py
git commit -m "feat(aquatic): integrate taxonomy group classification into ETL"
```

---

## Task 6b: Add groupDistribution to tile_splitter.py

**Files:**
- Modify: `scripts/tile_splitter.py`
- Test: `tests/test_tile_splitter.py` (new)

Add optional `group_distribution_key` parameter so cluster tiles include top-5 group counts.

- [ ] **Step 1: Write failing test**

```python
# tests/test_tile_splitter.py
import json
import pandas as pd
from pathlib import Path
from scripts.tile_splitter import split_tiles

def test_cluster_tiles_have_group_distribution(tmp_path):
    df = pd.DataFrame({
        "id": ["1", "2", "3", "4", "5"],
        "lat": [10.0, 10.1, 10.2, 10.3, 10.4],
        "lng": [20.0, 20.1, 20.2, 20.3, 20.4],
        "name": ["A", "B", "C", "D", "E"],
        "group": ["shark", "shark", "tuna", "jellyfish", "tuna"],
        "waterType": ["Saltwater"] * 5,
    })
    split_tiles(
        df, tmp_path,
        filter_agg_keys=["waterType"],
        top_items_fields=["id", "name"],
        point_fields=["id", "lat", "lng", "name", "group"],
        group_distribution_key="group",
    )
    # Read a z0 cluster tile
    z0 = tmp_path / "tiles" / "z0" / "0_0.json"
    assert z0.exists()
    data = json.loads(z0.read_text())
    cluster = data["clusters"][0]
    assert "groupDistribution" in cluster
    # Should be list of {group, count} sorted by count desc
    gd = cluster["groupDistribution"]
    assert isinstance(gd, list)
    assert all("group" in g and "count" in g for g in gd)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_tile_splitter.py -v`
Expected: FAIL — `group_distribution_key` not accepted

- [ ] **Step 3: Modify tile_splitter.py**

Add `group_distribution_key=None` parameter to `_make_cluster`, `_subdivide_group`, `build_cluster_tiles`, and `split_tiles`. When set, add `groupDistribution` to each cluster:

In `_make_cluster`:
```python
def _make_cluster(group, top_items_fields, filter_agg_keys, group_distribution_key=None):
    # ... existing code ...
    cluster = { "lat": ..., "lng": ..., "count": ..., "topItems": ..., "filterAggs": ... }
    if group_distribution_key and group_distribution_key in group.columns:
        dist = group[group_distribution_key].value_counts().head(5)
        cluster["groupDistribution"] = [
            {"group": g, "count": int(c)} for g, c in dist.items()
        ]
    return cluster
```

Thread the parameter through `_subdivide_group` → `build_cluster_tiles` → `split_tiles`. Existing callers that don't pass it get the old behavior (no `groupDistribution`).

- [ ] **Step 4: Run tests**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_tile_splitter.py -v && python -m pytest tests/ -v`
Expected: All PASS (new test + existing fish tests unchanged)

- [ ] **Step 5: Commit**

```bash
git add scripts/tile_splitter.py tests/test_tile_splitter.py
git commit -m "feat(tiles): add optional groupDistribution to cluster tiles"
```

---

## Task 6c: Generate Curated 500 Species List

**Files:**
- Create: `scripts/generate_sprite_list.py`
- Test: `tests/test_generate_sprite_list.py`

Rank species by occurrence count and recognition, ensure group coverage, output `sprite_species_list.json`.

- [ ] **Step 1: Write failing test**

```python
# tests/test_generate_sprite_list.py
import pandas as pd
from scripts.generate_sprite_list import curate_sprite_list

def test_curate_produces_500():
    # Mock enriched DataFrame with many species
    rows = []
    for i in range(1000):
        rows.append({"aphia_id": i, "scientific_name": f"Species {i}",
                      "group": f"group_{i % 20}", "body_type": "fusiform"})
    df = pd.DataFrame(rows)
    result = curate_sprite_list(df, target=500)
    assert len(result) == 500

def test_curate_ensures_group_coverage():
    rows = []
    # 990 from group_a, 10 from group_b
    for i in range(990):
        rows.append({"aphia_id": i, "scientific_name": f"Sp {i}",
                      "group": "group_a", "body_type": "fusiform"})
    for i in range(990, 1000):
        rows.append({"aphia_id": i, "scientific_name": f"Sp {i}",
                      "group": "group_b", "body_type": "cetacean"})
    df = pd.DataFrame(rows)
    result = curate_sprite_list(df, target=100, min_per_group=5)
    group_b_count = sum(1 for r in result if r["group"] == "group_b")
    assert group_b_count >= 5  # minimum coverage guaranteed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_generate_sprite_list.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

```python
# scripts/generate_sprite_list.py
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
```

- [ ] **Step 4: Run tests**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_generate_sprite_list.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_sprite_list.py tests/test_generate_sprite_list.py
git commit -m "feat(aquatic): add curated sprite species list generator with group coverage"
```

---

## Task 7: Sprite Fetcher — Phylopic Source

**Files:**
- Create: `scripts/fetch_aquatic_sprites.py`
- Test: `tests/test_sprites.py`

Start with Phylopic as the primary CC0 source. Other sources follow as separate tasks.

- [ ] **Step 1: Write failing test**

```python
# tests/test_sprites.py
from pathlib import Path
from unittest.mock import patch, MagicMock
from scripts.fetch_aquatic_sprites import fetch_phylopic, SOURCE_PRIORITY

def test_source_priority_order():
    assert SOURCE_PRIORITY == ["phylopic", "fishbase", "noaa", "wikimedia", "gbif_media"]

def test_fetch_phylopic_skips_existing(tmp_path):
    existing = tmp_path / "phylopic" / "123.svg"
    existing.parent.mkdir(parents=True)
    existing.write_text("<svg/>")
    with patch("scripts.fetch_aquatic_sprites.SPRITE_RAW_DIR", tmp_path):
        result = fetch_phylopic("Orcinus orca", "123")
    assert result is True  # already exists

def test_fetch_phylopic_returns_false_on_not_found(tmp_path):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"items": []}
    with patch("scripts.fetch_aquatic_sprites.SPRITE_RAW_DIR", tmp_path), \
         patch("requests.get", return_value=mock_resp):
        result = fetch_phylopic("Nonexistent species", "999")
    assert result is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_sprites.py -v`
Expected: FAIL

- [ ] **Step 3: Implement fetch_aquatic_sprites.py with Phylopic**

```python
# scripts/fetch_aquatic_sprites.py
"""Multi-source sprite fetcher for aquatic globe outlines."""
import json
import time
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parent.parent
SPRITE_RAW_DIR = ROOT / "data" / "raw" / "aquatic" / "sprites"
SPRITE_LIST_PATH = ROOT / "data" / "raw" / "aquatic" / "sprite_species_list.json"
SPRITE_OVERRIDES_PATH = ROOT / "data" / "raw" / "aquatic" / "sprite_overrides.json"

SOURCE_PRIORITY = ["phylopic", "fishbase", "noaa", "wikimedia", "gbif_media"]

PHYLOPIC_API = "https://api.phylopic.org/v2"


def fetch_phylopic(scientific_name: str, species_id: str) -> bool:
    """Fetch SVG silhouette from Phylopic. Returns True if found/exists."""
    out_dir = SPRITE_RAW_DIR / "phylopic"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{species_id}.svg"
    if out_path.exists():
        return True

    # Search by scientific name
    resp = requests.get(
        f"{PHYLOPIC_API}/images",
        params={"filter_name": scientific_name, "embed_items": "true"},
        timeout=30,
    )
    if resp.status_code != 200:
        return False

    items = resp.json().get("items", [])
    if not items:
        return False

    # Get the first result's SVG
    image_uuid = items[0].get("uuid", "")
    if not image_uuid:
        return False

    # Download SVG
    svg_resp = requests.get(
        f"{PHYLOPIC_API}/images/{image_uuid}/file",
        headers={"Accept": "image/svg+xml"},
        timeout=30,
    )
    if svg_resp.status_code != 200 or "svg" not in svg_resp.headers.get("content-type", ""):
        return False

    out_path.write_bytes(svg_resp.content)
    return True


def fetch_fishbase_line_art(scientific_name: str, species_id: str) -> bool:
    """Fetch line art from FishBase. Returns True if found/exists."""
    out_dir = SPRITE_RAW_DIR / "fishbase"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{species_id}.gif"
    if out_path.exists():
        return True

    genus, *species_parts = scientific_name.split()
    species = species_parts[0] if species_parts else ""
    url = f"https://www.fishbase.se/images/species/{genus[:2]}{species[:4]}_u0.gif"
    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
        return False
    out_path.write_bytes(resp.content)
    return True


def fetch_wikimedia(scientific_name: str, species_id: str) -> bool:
    """Search Wikimedia Commons for SVG illustration. Returns True if found/exists."""
    out_dir = SPRITE_RAW_DIR / "wikimedia"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{species_id}.svg"
    if out_path.exists():
        return True

    resp = requests.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": f"{scientific_name} filetype:svg",
            "srnamespace": "6",
            "format": "json",
            "srlimit": "1",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        return False
    results = resp.json().get("query", {}).get("search", [])
    if not results:
        return False

    # Get file URL
    title = results[0]["title"]
    info_resp = requests.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|mime",
            "format": "json",
        },
        timeout=15,
    )
    pages = info_resp.json().get("query", {}).get("pages", {})
    for page in pages.values():
        imageinfo = page.get("imageinfo", [{}])[0]
        if "svg" in imageinfo.get("mime", ""):
            svg_url = imageinfo["url"]
            svg_resp = requests.get(svg_url, timeout=30)
            if svg_resp.status_code == 200:
                out_path.write_bytes(svg_resp.content)
                return True
    return False


def fetch_noaa(scientific_name: str, species_id: str) -> bool:
    """Fetch illustration from NOAA Fisheries. Returns True if found/exists."""
    out_dir = SPRITE_RAW_DIR / "noaa"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{species_id}.png"
    if out_path.exists():
        return True
    # NOAA species illustrations are at predictable URLs by common name
    # This is a best-effort scrape — many species won't have NOAA art
    search_name = scientific_name.replace(" ", "+")
    resp = requests.get(
        f"https://www.fisheries.noaa.gov/api/v2/species?search={search_name}",
        timeout=15,
    )
    if resp.status_code != 200:
        return False
    results = resp.json().get("data", [])
    if not results:
        return False
    # Look for species illustration URL
    img_url = results[0].get("species_illustration_photo", {}).get("src")
    if not img_url:
        return False
    img_resp = requests.get(img_url, timeout=30)
    if img_resp.status_code == 200:
        out_path.write_bytes(img_resp.content)
        return True
    return False


def fetch_gbif_media(scientific_name: str, species_id: str) -> bool:
    """Fetch CC-licensed image from GBIF occurrence media. Returns True if found/exists."""
    out_dir = SPRITE_RAW_DIR / "gbif_media"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{species_id}.jpg"
    if out_path.exists():
        return True
    # Search GBIF for occurrence with CC-BY image
    resp = requests.get(
        "https://api.gbif.org/v1/occurrence/search",
        params={
            "scientificName": scientific_name,
            "mediaType": "StillImage",
            "limit": 1,
        },
        timeout=15,
    )
    if resp.status_code != 200:
        return False
    results = resp.json().get("results", [])
    for occ in results:
        for media in occ.get("media", []):
            if media.get("type") == "StillImage" and media.get("identifier"):
                img_resp = requests.get(media["identifier"], timeout=30)
                if img_resp.status_code == 200:
                    out_path.write_bytes(img_resp.content)
                    return True
    return False


FETCH_FUNCTIONS = {
    "phylopic": fetch_phylopic,
    "fishbase": fetch_fishbase_line_art,
    "noaa": fetch_noaa,
    "wikimedia": fetch_wikimedia,
    "gbif_media": fetch_gbif_media,
}


def fetch_all_sprites(species_list: list[dict], sources: list[str] = None):
    """Fetch sprites for all species from all sources. Parallelized per source."""
    sources = sources or SOURCE_PRIORITY
    results = {}  # species_id -> {source: True/False}

    for source in sources:
        fetch_fn = FETCH_FUNCTIONS.get(source)
        if not fetch_fn:
            print(f"  Skipping unknown source: {source}")
            continue

        print(f"Fetching from {source}...")
        found = 0
        for sp in species_list:
            sid = str(sp["id"])
            sci_name = sp["scientificName"]
            if sid not in results:
                results[sid] = {}
            success = fetch_fn(sci_name, sid)
            results[sid][source] = success
            if success:
                found += 1
            time.sleep(0.5)  # rate limit
        print(f"  {source}: {found}/{len(species_list)} found")

    # Save results summary
    summary_path = SPRITE_RAW_DIR / "fetch_results.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    return results


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Fetch aquatic sprite outlines")
    parser.add_argument("--sources", nargs="+", default=SOURCE_PRIORITY,
                        help="Sources to fetch from")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of species (0=all)")
    args = parser.parse_args()

    if not SPRITE_LIST_PATH.exists():
        print(f"ERROR: Species list not found at {SPRITE_LIST_PATH}")
        print("Run aquatic_etl.py first to generate the species list")
        return

    species_list = json.loads(SPRITE_LIST_PATH.read_text())
    if args.limit > 0:
        species_list = species_list[:args.limit]

    print(f"Fetching sprites for {len(species_list)} species from {args.sources}")
    fetch_all_sprites(species_list, args.sources)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_sprites.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_aquatic_sprites.py tests/test_sprites.py
git commit -m "feat(aquatic): add multi-source sprite fetcher (Phylopic, FishBase, Wikimedia)"
```

---

## Task 8: SVG Normalization Pipeline

**Files:**
- Create: `scripts/normalize_sprites.py`
- Test: `tests/test_normalize_sprites.py`

Normalize raw SVGs to consistent outline format: viewBox 0 0 100 60, stroke 1.5, fill none, white stroke.

- [ ] **Step 1: Write failing test**

```python
# tests/test_normalize_sprites.py
from scripts.normalize_sprites import normalize_svg, is_valid_svg

def test_normalize_strips_fill():
    svg_in = '<svg viewBox="0 0 200 100"><path d="M0,0L10,10" fill="red" stroke="black"/></svg>'
    result = normalize_svg(svg_in)
    assert 'fill="none"' in result or "fill:none" in result
    assert 'fill="red"' not in result

def test_normalize_sets_viewbox():
    svg_in = '<svg viewBox="0 0 200 100"><path d="M0,0L10,10"/></svg>'
    result = normalize_svg(svg_in)
    assert 'viewBox="0 0 100 60"' in result

def test_normalize_sets_stroke_color():
    svg_in = '<svg viewBox="0 0 200 100"><path d="M0,0L10,10" stroke="blue"/></svg>'
    result = normalize_svg(svg_in)
    assert 'stroke="#fff"' in result or "stroke:#fff" in result

def test_is_valid_svg():
    assert is_valid_svg('<svg viewBox="0 0 100 60"><path d="M0,0"/></svg>')
    assert not is_valid_svg("not xml at all")
    assert not is_valid_svg('<div>not svg</div>')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_normalize_sprites.py -v`
Expected: FAIL

- [ ] **Step 3: Implement normalize_sprites.py**

```python
# scripts/normalize_sprites.py
"""Normalize raw SVGs to consistent outline format for globe sprites."""
import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPRITE_RAW_DIR = ROOT / "data" / "raw" / "aquatic" / "sprites"
SPRITE_OUTPUT_DIR = ROOT / "output" / "aquatic" / "sprites"

TARGET_VIEWBOX = "0 0 100 60"
TARGET_STROKE = "#fff"
TARGET_STROKE_WIDTH = "1.5"

# SVG namespace
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def is_valid_svg(content: str) -> bool:
    """Check if content is valid SVG XML."""
    try:
        root = ET.fromstring(content)
        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
        return tag == "svg"
    except ET.ParseError:
        return False


def normalize_svg(svg_content: str) -> str:
    """Normalize an SVG to outline format: standard viewBox, white stroke, no fill."""
    root = ET.fromstring(svg_content)

    # Set viewBox
    root.set("viewBox", TARGET_VIEWBOX)
    # Remove width/height to let viewBox control sizing
    for attr in ["width", "height"]:
        if attr in root.attrib:
            del root.attrib[attr]

    # Process all elements
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        # Strip fills on shape elements
        if tag in ("path", "circle", "ellipse", "rect", "polygon", "polyline", "line", "g"):
            elem.set("fill", "none")
            # Set stroke
            if tag != "g":
                elem.set("stroke", TARGET_STROKE)
                elem.set("stroke-width", TARGET_STROKE_WIDTH)

        # Clean inline styles
        style = elem.get("style", "")
        if style:
            # Remove fill colors, replace stroke colors
            style = re.sub(r"fill\s*:\s*[^;]+;?", "fill:none;", style)
            style = re.sub(r"stroke\s*:\s*[^;]+;?", f"stroke:{TARGET_STROKE};", style)
            elem.set("style", style)

    return ET.tostring(root, encoding="unicode")


def normalize_all(source_priority: list[str], species_ids: list[str],
                  overrides: dict = None):
    """Normalize best available SVG for each species. Returns manifest-ready dict."""
    SPRITE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    overrides = overrides or {}
    results = {}  # species_id -> output filename

    for sid in species_ids:
        # Check override first
        if sid in overrides:
            source = overrides[sid]["source"]
            src_file = SPRITE_RAW_DIR / source / overrides[sid]["file"]
            if src_file.exists():
                _normalize_and_write(src_file, f"sp-{sid}.svg")
                results[sid] = f"sp-{sid}.svg"
                continue

        # Walk source priority
        for source in source_priority:
            src_dir = SPRITE_RAW_DIR / source
            # Check for SVG or GIF (FishBase uses GIF line art)
            for ext in [".svg", ".gif", ".png"]:
                src_file = src_dir / f"{sid}{ext}"
                if src_file.exists():
                    if ext == ".svg":
                        _normalize_and_write(src_file, f"sp-{sid}.svg")
                    else:
                        _trace_and_write(src_file, f"sp-{sid}.svg")
                    results[sid] = f"sp-{sid}.svg"
                    break
            if sid in results:
                break

    return results


def _normalize_and_write(src: Path, out_name: str):
    """Read SVG, normalize, write to output."""
    content = src.read_text(encoding="utf-8", errors="ignore")
    if not is_valid_svg(content):
        print(f"  WARNING: Invalid SVG: {src}")
        return
    normalized = normalize_svg(content)
    out_path = SPRITE_OUTPUT_DIR / out_name
    out_path.write_text(normalized, encoding="utf-8")


def _trace_and_write(src: Path, out_name: str):
    """Convert raster image to SVG outline using potrace, then normalize."""
    import subprocess
    import tempfile

    # Convert to PBM first (potrace input format)
    with tempfile.NamedTemporaryFile(suffix=".pbm", delete=False) as pbm:
        pbm_path = pbm.name
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as svg:
        svg_path = svg.name

    try:
        # Use ImageMagick convert -> PBM, then potrace -> SVG
        subprocess.run(
            ["convert", str(src), "-threshold", "50%", pbm_path],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["potrace", pbm_path, "-s", "-o", svg_path],
            check=True, capture_output=True,
        )
        content = Path(svg_path).read_text()
        if is_valid_svg(content):
            normalized = normalize_svg(content)
            out_path = SPRITE_OUTPUT_DIR / out_name
            out_path.write_text(normalized, encoding="utf-8")
        else:
            print(f"  WARNING: potrace output invalid for {src}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  WARNING: Raster trace failed for {src}: {e}")
    finally:
        Path(pbm_path).unlink(missing_ok=True)
        Path(svg_path).unlink(missing_ok=True)


def main():
    """CLI: normalize all raw sprites using source priority."""
    overrides = {}
    if SPRITE_OVERRIDES_PATH.exists():
        overrides = json.loads(SPRITE_OVERRIDES_PATH.read_text())

    # Get species IDs from raw sprite directories
    species_ids = set()
    for source_dir in SPRITE_RAW_DIR.iterdir():
        if source_dir.is_dir():
            for f in source_dir.iterdir():
                species_ids.add(f.stem)

    source_priority = ["phylopic", "fishbase", "noaa", "wikimedia", "gbif_media"]
    results = normalize_all(source_priority, sorted(species_ids), overrides)
    print(f"Normalized {len(results)} sprites to {SPRITE_OUTPUT_DIR}")


SPRITE_OVERRIDES_PATH = ROOT / "data" / "raw" / "aquatic" / "sprite_overrides.json"

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_normalize_sprites.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/normalize_sprites.py tests/test_normalize_sprites.py
git commit -m "feat(aquatic): add SVG normalization pipeline with raster tracing fallback"
```

---

## Task 9: Sprite Manifest Generator

**Files:**
- Create: `scripts/build_sprite_manifest.py`
- Test: `tests/test_sprite_manifest.py`

Generate manifest.json with pre-resolved fallback chain.

- [ ] **Step 1: Write failing test**

```python
# tests/test_sprite_manifest.py
from scripts.build_sprite_manifest import build_manifest, resolve_sprite

def test_resolve_sprite_exact_match():
    manifest = {
        "sprites": {"123": {"file": "sp-123.svg"}},
        "groupFallbacks": {"shark": "grp-shark.svg"},
        "bodyTypeFallbacks": {"fusiform": "fb-fusiform.svg"},
    }
    assert resolve_sprite("123", "shark", "fusiform", manifest) == "sp-123.svg"

def test_resolve_sprite_group_fallback():
    manifest = {
        "sprites": {},
        "groupFallbacks": {"shark": "grp-shark.svg"},
        "bodyTypeFallbacks": {"fusiform": "fb-fusiform.svg"},
    }
    assert resolve_sprite("999", "shark", "fusiform", manifest) == "grp-shark.svg"

def test_resolve_sprite_body_type_fallback():
    manifest = {
        "sprites": {},
        "groupFallbacks": {},
        "bodyTypeFallbacks": {"fusiform": "fb-fusiform.svg"},
    }
    assert resolve_sprite("999", "unknown_group", "fusiform", manifest) == "fb-fusiform.svg"

def test_resolve_sprite_ultimate_fallback():
    manifest = {
        "sprites": {},
        "groupFallbacks": {},
        "bodyTypeFallbacks": {"fusiform": "fb-fusiform.svg"},
    }
    assert resolve_sprite("999", "unknown", "unknown", manifest) == "fb-fusiform.svg"

def test_build_manifest_structure():
    sprites_dir_files = ["sp-123.svg", "grp-shark.svg", "fb-fusiform.svg"]
    species_data = {
        "123": {"name": "Great White", "scientificName": "Carcharodon carcharias",
                "group": "shark", "bodyType": "fusiform", "bodyGroup": "fish", "license": "CC0"}
    }
    group_fallbacks = {"shark": "grp-shark.svg"}
    body_type_fallbacks = {"fusiform": "fb-fusiform.svg"}

    manifest = build_manifest(species_data, group_fallbacks, body_type_fallbacks)
    assert manifest["version"] == "1.0.0"
    assert "123" in manifest["sprites"]
    assert manifest["sprites"]["123"]["file"] == "sp-123.svg"
    assert manifest["groupFallbacks"]["shark"] == "grp-shark.svg"
    assert "glowDefaults" in manifest
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_sprite_manifest.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

```python
# scripts/build_sprite_manifest.py
"""Generate sprite manifest.json with pre-resolved fallback chain."""
import json
from pathlib import Path

from scripts.aquatic_groups import BODY_TYPES, GROUPS

ROOT = Path(__file__).resolve().parent.parent
SPRITE_OUTPUT_DIR = ROOT / "output" / "aquatic" / "sprites"


def resolve_sprite(species_id: str, group: str, body_type: str, manifest: dict) -> str:
    """Walk the fallback chain and return the resolved sprite filename."""
    # 1. Exact species match
    if species_id in manifest.get("sprites", {}):
        return manifest["sprites"][species_id]["file"]
    # 2. Group fallback
    if group in manifest.get("groupFallbacks", {}):
        return manifest["groupFallbacks"][group]
    # 3. Body type fallback
    if body_type in manifest.get("bodyTypeFallbacks", {}):
        return manifest["bodyTypeFallbacks"][body_type]
    # 4. Ultimate fallback: fusiform
    return manifest.get("bodyTypeFallbacks", {}).get("fusiform", "fb-fusiform.svg")


def build_manifest(species_data: dict, group_fallbacks: dict,
                   body_type_fallbacks: dict) -> dict:
    """Build the full manifest.json structure."""
    sprites = {}
    for sid, data in species_data.items():
        sprites[sid] = {
            "file": f"sp-{sid}.svg",
            "name": data.get("name", ""),
            "scientificName": data.get("scientificName", ""),
            "group": data.get("group", "other"),
            "bodyType": data.get("bodyType", "fusiform"),
            "bodyGroup": data.get("bodyGroup", "other"),
            "license": data.get("license", "unknown"),
        }

    total = len(sprites) + len(group_fallbacks) + len(body_type_fallbacks)

    return {
        "version": "1.0.0",
        "glowDefaults": {
            "color": "#00E5FF",
            "blur": "4px",
            "note": "Apply via CSS filter: drop-shadow(0 0 {blur} {color})",
        },
        "bodyTypes": BODY_TYPES,
        "sprites": sprites,
        "groupFallbacks": group_fallbacks,
        "bodyTypeFallbacks": body_type_fallbacks,
        "totalSprites": total,
        "note": "Fallback chain: sprites[speciesId] -> groupFallbacks[group] -> bodyTypeFallbacks[bodyType]. Resolved at ETL time.",
    }


def write_manifest(manifest: dict):
    """Write manifest.json to output directory."""
    SPRITE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = SPRITE_OUTPUT_DIR / "manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Manifest written to {out} ({manifest['totalSprites']} sprites)")


def main():
    """CLI: build manifest from normalized sprites and species data."""
    # Scan sprite output dir for sp-*.svg files
    species_data = {}
    sprites_dir = SPRITE_OUTPUT_DIR
    species_dir = ROOT / "output" / "aquatic" / "species"

    # Load species detail files for metadata
    if species_dir.exists():
        for f in species_dir.glob("*.json"):
            data = json.loads(f.read_text())
            sid = data["id"]
            if (sprites_dir / f"sp-{sid}.svg").exists():
                species_data[sid] = {
                    "name": data.get("name", ""),
                    "scientificName": data.get("scientificName", ""),
                    "group": data.get("group", "other"),
                    "bodyType": data.get("bodyType", "fusiform"),
                    "bodyGroup": data.get("bodyGroup", "other"),
                    "license": "unknown",
                }

    # Build group fallbacks from grp-*.svg files
    group_fallbacks = {}
    for f in sprites_dir.glob("grp-*.svg"):
        group_id = f.stem.replace("grp-", "")
        group_fallbacks[group_id] = f.name

    # Build body type fallbacks from fb-*.svg files
    body_type_fallbacks = {}
    for f in sprites_dir.glob("fb-*.svg"):
        bt = f.stem.replace("fb-", "")
        body_type_fallbacks[bt] = f.name

    manifest = build_manifest(species_data, group_fallbacks, body_type_fallbacks)
    write_manifest(manifest)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_sprite_manifest.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/build_sprite_manifest.py tests/test_sprite_manifest.py
git commit -m "feat(aquatic): add sprite manifest generator with fallback chain resolution"
```

---

## Task 10: Aquatic ETL Orchestrator — Tile + Species + Index Generation

**Files:**
- Modify: `scripts/aquatic_etl.py` (add tile/species/index generation + CLI)
- Modify: `tests/test_aquatic_etl.py`

Wire everything together: enriched DataFrame → tiles with sprite refs → species details → index.

- [ ] **Step 1: Write failing test for species detail generation**

```python
# tests/test_aquatic_etl.py (append)
from scripts.aquatic_etl import generate_species_details

def test_generate_species_detail_has_sprite(tmp_path):
    df = pd.DataFrame({
        "id": ["123", "123"],
        "lat": [47.6, 48.0],
        "lng": [-122.3, -122.5],
        "name": ["Orca", "Orca"],
        "scientific_name": ["Orcinus orca", "Orcinus orca"],
        "group": ["dolphin", "dolphin"],
        "body_type": ["cetacean", "cetacean"],
        "body_group": ["mammal", "mammal"],
        "sprite": ["sp-123.svg", "sp-123.svg"],
        "thumb": [None, None],
        "water_type": ["Saltwater", "Saltwater"],
        "rarity": [3, 3],
    })
    generate_species_details(df, tmp_path)
    detail = json.loads((tmp_path / "species" / "123.json").read_text())
    assert detail["sprite"] == "sp-123.svg"
    assert detail["group"] == "dolphin"
    assert detail["bodyType"] == "cetacean"
    assert detail["bodyGroup"] == "mammal"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_etl.py::test_generate_species_detail_has_sprite -v`
Expected: FAIL

- [ ] **Step 3: Implement generate_species_details, generate_index, and CLI**

```python
# Add to scripts/aquatic_etl.py
from scripts.tile_splitter import split_tiles
from scripts.build_sprite_manifest import resolve_sprite

def resolve_sprites_on_df(df: pd.DataFrame, manifest: dict) -> pd.DataFrame:
    """Add pre-resolved sprite filename to every row."""
    df = df.copy()
    df["sprite"] = df.apply(
        lambda r: resolve_sprite(
            str(r.get("id", r.get("aphia_id", ""))),
            r.get("group", "other"),
            r.get("body_type", "fusiform"),
            manifest,
        ), axis=1
    )
    return df


def generate_species_details(df: pd.DataFrame, output_dir: Path):
    """Generate one JSON detail file per unique species."""
    species_dir = output_dir / "species"
    species_dir.mkdir(parents=True, exist_ok=True)

    detail_df = df.drop_duplicates(subset=["id"], keep="first")
    count = 0
    for _, row in detail_df.iterrows():
        detail = {
            "id": str(row["id"]),
            "name": row.get("name") or row.get("scientific_name", ""),
            "nameZh": row.get("name_zh"),
            "scientificName": row.get("scientific_name", ""),
            "family": row.get("family"),
            "description": row.get("description"),
            "descriptionZh": row.get("description_zh"),
            "sprite": row.get("sprite"),
            "group": row.get("group"),
            "bodyType": row.get("body_type"),
            "bodyGroup": row.get("body_group"),
            "metadata": {
                "habitat": row.get("water_type"),
                "depth": f"0-{int(row['depth_max'])} m" if pd.notna(row.get("depth_max")) else None,
                "rarity": {1: "Common", 2: "Uncommon", 3: "Rare", 4: "Legendary"}.get(row.get("rarity")),
                "vulnerability": row.get("vulnerability"),
            },
            "images": [],
            "links": [],
            "attribution": "OBIS, GBIF, FishBase (CC-BY-NC)",
        }
        # Add FishBase image if available
        thumb = row.get("thumb")
        if pd.notna(thumb) and thumb:
            pic_name = thumb.replace("tn_", "")
            detail["images"].append({
                "thumbnail": f"https://www.fishbase.se/images/thumbnails/jpg/{thumb}",
                "image": f"https://www.fishbase.se/images/species/{pic_name}",
            })

        # Strip None values from metadata
        detail["metadata"] = {k: v for k, v in detail["metadata"].items() if v is not None}

        out_path = species_dir / f"{row['id']}.json"
        out_path.write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")
        count += 1

    print(f"  Generated {count} species detail files")


def generate_index(df: pd.DataFrame, output_dir: Path):
    """Generate index.json for the aquatic globe."""
    index = {
        "globeId": "aquatic",
        "version": "1.0.0",
        "totalItems": len(df),
        "lastUpdated": date.today().isoformat(),
        "tileZoomRange": [0, 7],
        "filters": [
            {
                "key": "waterType",
                "label": "Water Type",
                "type": "chips",
                "options": sorted(df["water_type"].dropna().unique().tolist()),
            },
            {
                "key": "bodyGroup",
                "label": "Animal Type",
                "type": "chips",
                "options": sorted(df["body_group"].dropna().unique().tolist()),
            },
            {
                "key": "rarity",
                "label": "Rarity",
                "type": "chips",
                "options": ["Common", "Uncommon", "Rare", "Legendary"],
            },
        ],
        "attribution": [
            {"name": "OBIS", "license": "CC-BY 4.0", "url": "https://obis.org"},
            {"name": "GBIF", "license": "CC0/CC-BY 4.0", "url": "https://www.gbif.org"},
            {"name": "FishBase", "license": "CC-BY-NC 4.0", "url": "https://www.fishbase.se"},
        ],
    }
    out = output_dir / "index.json"
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Index written: {index['totalItems']} total items")


def run_process():
    """Run the full processing pipeline (assumes downloads are done)."""
    print("=== Aquatic ETL: Processing ===")

    # 1. Load OBIS
    print("Loading OBIS data...")
    obis_path = RAW_DIR / "obis_occurrences.parquet"
    obis_df = duckdb.sql(f"""
        SELECT
            AphiaID as aphia_id,
            decimalLatitude as lat,
            decimalLongitude as lng,
            scientificName as scientific_name,
            class,
            "order",
            family,
            phylum
        FROM read_parquet('{obis_path}')
        WHERE decimalLatitude IS NOT NULL
          AND decimalLongitude IS NOT NULL
          AND AphiaID IS NOT NULL
          AND coordinateUncertaintyInMeters < 50000
    """).df()
    print(f"  OBIS: {len(obis_df)} records")

    # 2. Load GBIF
    print("Loading GBIF data...")
    gbif_path = RAW_DIR / "gbif_occurrences.csv"
    gbif_raw = pd.read_csv(gbif_path, sep="\t", usecols=[
        "decimalLatitude", "decimalLongitude", "speciesKey",
        "species", "class", "order", "family", "phylum",
    ], low_memory=False)
    gbif_df = gbif_raw.rename(columns={
        "decimalLatitude": "lat",
        "decimalLongitude": "lng",
        "speciesKey": "gbif_taxon_key",
        "species": "scientific_name",
    })
    # Map GBIF species to AphiaID via scientific name join with OBIS
    obis_name_to_aphia = obis_df.drop_duplicates(subset=["scientific_name"])[
        ["scientific_name", "aphia_id"]
    ]
    gbif_df = gbif_df.merge(obis_name_to_aphia, on="scientific_name", how="left")
    # For species not in OBIS, use "gbif-{taxonKey}" as fallback ID
    mask = gbif_df["aphia_id"].isna()
    gbif_df.loc[mask, "aphia_id"] = gbif_df.loc[mask, "gbif_taxon_key"].apply(
        lambda k: f"gbif-{int(k)}" if pd.notna(k) else None
    )
    gbif_df = gbif_df.dropna(subset=["aphia_id"])
    print(f"  GBIF: {len(gbif_df)} records (after AphiaID mapping)")

    # 3. Merge + deduplicate
    print("Merging OBIS + GBIF...")
    merged = merge_occurrences(obis_df, gbif_df)
    print(f"  Merged: {len(merged)} unique points")

    # 4. Load FishBase metadata
    print("Loading FishBase metadata...")
    fishbase_species = duckdb.sql(f"""
        SELECT * FROM read_parquet('{ROOT}/data/raw/fishbase/species.parquet')
    """).df()

    # 5. Enrich
    print("Enriching with FishBase metadata...")
    enriched = enrich_with_fishbase(merged, fishbase_species)

    # 6. Classify
    print("Applying taxonomy classifications...")
    enriched = apply_classifications(enriched)

    # 7. Prepare DataFrame for tiling — rename to camelCase for output JSON
    enriched["id"] = enriched["aphia_id"].astype(str)
    enriched["name"] = enriched["common_name"]
    enriched["nameZh"] = enriched.get("name_zh")
    enriched["waterType"] = enriched.get("water_type", "Unknown")
    enriched["bodyGroup"] = enriched["body_group"]
    enriched["bodyType"] = enriched["body_type"]
    enriched["rarity"] = enriched.get("rarity", 1)  # default Common

    # 8. Load sprite manifest and resolve sprites
    print("Resolving sprites...")
    manifest_path = OUTPUT_DIR / "sprites" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        enriched = resolve_sprites_on_df(enriched, manifest)
    else:
        print("  WARNING: No sprite manifest found, using fb-fusiform.svg for all")
        enriched["sprite"] = "fb-fusiform.svg"

    # 9. Generate tiles
    print("Generating tiles...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tile_stats = split_tiles(
        enriched,
        OUTPUT_DIR,
        filter_agg_keys=["waterType", "bodyGroup"],
        top_items_fields=["id", "name", "thumb", "sprite", "group"],
        point_fields=["id", "lat", "lng", "name", "nameZh", "thumb", "sprite",
                       "group", "rarity", "waterType", "precision"],
        group_distribution_key="group",
    )
    print(f"  Tiles: {tile_stats}")

    # 10. Generate species details
    print("Generating species details...")
    generate_species_details(enriched, OUTPUT_DIR)

    # 11. Generate index
    print("Generating index...")
    generate_index(enriched, OUTPUT_DIR)

    # 12. Save crosswalk
    print("Saving ID crosswalk...")
    crosswalk = build_id_crosswalk(enriched)
    crosswalk_path = RAW_DIR / "id_crosswalk.json"
    crosswalk_path.write_text(json.dumps(crosswalk, ensure_ascii=False, indent=2))

    print("=== Done ===")


def main():
    parser = argparse.ArgumentParser(description="Aquatic globe ETL")
    parser.add_argument("--download", action="store_true", help="Download only")
    parser.add_argument("--process", action="store_true", help="Process only")
    args = parser.parse_args()

    if args.download:
        download_obis()
        download_gbif()
    elif args.process:
        run_process()
    else:
        download_obis()
        download_gbif()
        run_process()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_etl.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/aquatic_etl.py tests/test_aquatic_etl.py
git commit -m "feat(aquatic): add full ETL orchestrator with tile/species/index generation"
```

---

## Task 11: Aquatic Search Index

**Files:**
- Create: `scripts/build_aquatic_search_index.py`
- Test: `tests/test_aquatic_search_index.py`

Expand search index from 36 fish groups to ~50 aquatic groups.

- [ ] **Step 1: Write failing test**

```python
# tests/test_aquatic_search_index.py
import json
import pandas as pd
from scripts.build_aquatic_search_index import build_search_index

def test_search_index_has_all_groups():
    df = pd.DataFrame({
        "id": ["1", "2", "3"],
        "group": ["shark", "whale", "jellyfish"],
        "scientific_name": ["Carcharodon carcharias", "Megaptera novaeangliae", "Aurelia aurita"],
    })
    index = build_search_index(df)
    assert "shark" in index["groups"]
    assert "whale" in index["groups"]
    assert "jellyfish" in index["groups"]
    assert "1" in index["groups"]["shark"]["specIds"]

def test_search_index_by_spec_id():
    df = pd.DataFrame({
        "id": ["1"],
        "group": ["shark"],
        "scientific_name": ["Carcharodon carcharias"],
    })
    index = build_search_index(df)
    assert index["bySpecId"]["1"] == "shark"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_search_index.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_search_index.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/build_aquatic_search_index.py tests/test_aquatic_search_index.py
git commit -m "feat(aquatic): add search index builder for ~50 aquatic groups"
```

---

## Task 12: Update Validation Script

**Files:**
- Modify: `scripts/validate.py`
- Test: run existing + new validations

Add sprite field checks, groupDistribution validation, and sprites directory integrity.

- [ ] **Step 1: Write failing test**

```python
# tests/test_validate.py
from scripts.validate import validate_point_tile, validate_cluster_tile

def test_point_tile_requires_sprite(tmp_path):
    import json
    tile = {
        "zoom": 4, "x": 0, "y": 0,
        "points": [{"id": "1", "lat": 10.0, "lng": 20.0, "name": "Test"}]
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(tile))
    errors = validate_point_tile(p, require_sprite=True)
    assert any("sprite" in str(e) for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_validate.py::test_point_tile_requires_sprite -v`
Expected: FAIL

- [ ] **Step 3: Add sprite validation to validate.py**

Add a `require_sprite` parameter to `validate_point_tile` and `validate_cluster_tile`. When `True` (used for aquatic globe), check that `sprite` is present and non-null on every point and topItem. Add `validate_sprites_dir()` to check that all referenced SVGs exist and are valid.

Key additions to `validate.py`:

```python
def validate_point_tile(path, require_sprite=False):
    # ... existing checks ...
    if require_sprite:
        for pt in data.get("points", []):
            if not pt.get("sprite"):
                errors.append(ValidationError(path, f"Point {pt.get('id')} missing sprite"))

def validate_cluster_tile(path, require_sprite=False):
    # ... existing checks ...
    if require_sprite:
        for cluster in data.get("clusters", []):
            for item in cluster.get("topItems", []):
                if not item.get("sprite"):
                    errors.append(ValidationError(path, f"topItem {item.get('id')} missing sprite"))
            if "groupDistribution" not in cluster:
                errors.append(ValidationError(path, "Cluster missing groupDistribution"))

def validate_sprites_dir(globe_dir):
    """Validate sprites directory: manifest exists, all referenced files exist, SVGs valid."""
    errors = []
    sprites_dir = globe_dir / "sprites"
    manifest_path = sprites_dir / "manifest.json"
    if not manifest_path.exists():
        errors.append(ValidationError(manifest_path, "Missing manifest.json"))
        return errors

    manifest = json.loads(manifest_path.read_text())
    # Check all sprite files exist
    for sid, data in manifest.get("sprites", {}).items():
        svg_path = sprites_dir / data["file"]
        if not svg_path.exists():
            errors.append(ValidationError(svg_path, f"Missing sprite file for {sid}"))
        elif svg_path.stat().st_size > 3072:
            errors.append(ValidationError(svg_path, f"SVG too large: {svg_path.stat().st_size}B > 3KB"))

    for gid, filename in manifest.get("groupFallbacks", {}).items():
        if not (sprites_dir / filename).exists():
            errors.append(ValidationError(sprites_dir / filename, f"Missing group fallback for {gid}"))

    for bt, filename in manifest.get("bodyTypeFallbacks", {}).items():
        if not (sprites_dir / filename).exists():
            errors.append(ValidationError(sprites_dir / filename, f"Missing body type fallback for {bt}"))

    return errors
```

- [ ] **Step 4: Run tests**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_validate.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/validate.py tests/test_validate.py
git commit -m "feat(validate): add sprite field and manifest validation for aquatic globe"
```

---

## Task 13: Update DATA_CONTRACTS.md and CLAUDE.md

**Files:**
- Modify: `docs/DATA_CONTRACTS.md`
- Modify: `CLAUDE.md`

Document the new aquatic globe schemas, data sources, and sprite format.

- [ ] **Step 1: Update DATA_CONTRACTS.md**

Add the following sections:
- Aquatic globe directory structure (includes sprites/)
- Updated cluster tile schema with `groupDistribution` and `topItems[].sprite`
- Updated point tile schema with `sprite` and `group` fields
- Updated detail file schema with `sprite`, `group`, `bodyType`, `bodyGroup`
- Sprite manifest schema
- SVG format spec (viewBox, stroke, size limit)

- [ ] **Step 2: Update CLAUDE.md data sources table**

Add OBIS and GBIF entries:
```
| Aquatic | OBIS | S3 Parquet export from `s3://obis-products/` | None — public bucket |
| Aquatic | GBIF | Async Download API: 1 POST → wait → download ZIP | 1 request |
| Aquatic | FishBase | Same parquet reads as Fish globe | None |
```

- [ ] **Step 3: Commit**

```bash
git add docs/DATA_CONTRACTS.md CLAUDE.md
git commit -m "docs: add aquatic globe schemas and OBIS/GBIF data sources"
```

---

## Task 14: End-to-End Integration Test

**Files:**
- Create: `tests/test_aquatic_e2e.py`

Small-scale integration test using mock data to verify the full pipeline produces valid output.

- [ ] **Step 1: Write integration test**

```python
# tests/test_aquatic_e2e.py
"""End-to-end test: small mock dataset through full aquatic pipeline."""
import json
import pandas as pd
from pathlib import Path

from scripts.aquatic_etl import (
    merge_occurrences, enrich_with_fishbase, apply_classifications,
    resolve_sprites_on_df, generate_species_details, generate_index,
)
from scripts.tile_splitter import split_tiles
from scripts.build_sprite_manifest import build_manifest, resolve_sprite
from scripts.build_aquatic_search_index import build_search_index


def test_e2e_pipeline(tmp_path):
    """Full pipeline with 10 mock species produces valid output."""
    # Mock OBIS data
    obis = pd.DataFrame({
        "aphia_id": [137094, 137094, 105838, 105838, 123456,
                     234567, 345678, 456789, 567890, 678901],
        "lat": [47.6, 48.0, 10.0, 11.0, 35.0,
                -33.0, 60.0, 25.0, -10.0, 55.0],
        "lng": [-122.3, -122.5, 20.0, 21.0, 139.0,
                151.0, -5.0, -80.0, 45.0, 10.0],
        "scientific_name": [
            "Orcinus orca", "Orcinus orca",
            "Chelonia mydas", "Chelonia mydas",
            "Thunnus thynnus", "Carcharodon carcharias",
            "Gadus morhua", "Octopus vulgaris",
            "Aurelia aurita", "Hippocampus hippocampus",
        ],
        "class": ["Mammalia", "Mammalia", "Reptilia", "Reptilia",
                  "Actinopterygii", "Elasmobranchii", "Actinopterygii",
                  "Cephalopoda", "Scyphozoa", "Actinopterygii"],
        "order": ["Cetacea", "Cetacea", "Testudines", "Testudines",
                  "Scombriformes", "Lamniformes", "Gadiformes",
                  "Octopoda", "Semaeostomeae", "Syngnathiformes"],
        "family": ["Delphinidae", "Delphinidae", "Cheloniidae", "Cheloniidae",
                   "Scombridae", "Lamnidae", "Gadidae",
                   "Octopodidae", "Ulmaridae", "Syngnathidae"],
        "phylum": ["Chordata"] * 10,
    })
    gbif = pd.DataFrame(columns=obis.columns)  # empty for simplicity

    # 1. Merge
    merged = merge_occurrences(obis, gbif)
    assert len(merged) >= 8  # deduped

    # 2. Enrich (no FishBase match for simplicity)
    fishbase = pd.DataFrame(columns=["Genus", "Species", "SpecCode", "FBname",
                                      "PicPreferredName", "Vulnerability",
                                      "DepthRangeDeep", "Fresh", "Brack", "Saltwater"])
    enriched = enrich_with_fishbase(merged, fishbase)

    # 3. Classify
    enriched = apply_classifications(enriched)
    assert "dolphin" in enriched["group"].values
    assert "sea_turtle" in enriched["group"].values
    assert "jellyfish" in enriched["group"].values

    # 4. Build mock manifest
    manifest = build_manifest(
        species_data={},
        group_fallbacks={"dolphin": "grp-dolphin.svg", "shark": "grp-shark.svg"},
        body_type_fallbacks={"fusiform": "fb-fusiform.svg", "cetacean": "fb-cetacean.svg",
                             "flat": "fb-flat.svg", "cephalopod": "fb-cephalopod.svg",
                             "jellyfish": "fb-jellyfish.svg", "seahorse": "fb-seahorse.svg"},
    )

    # 5. Resolve sprites
    enriched["id"] = enriched["aphia_id"].astype(str)
    enriched["name"] = enriched["common_name"] if "common_name" in enriched.columns else enriched["scientific_name"]
    enriched["rarity"] = 1
    enriched = resolve_sprites_on_df(enriched, manifest)
    assert enriched["sprite"].notna().all()  # no nulls!

    # 6. Tile
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    enriched["water_type"] = enriched.get("water_type", "Saltwater")
    enriched["name_zh"] = None
    enriched["thumb"] = None
    enriched["precision"] = "exact"

    split_tiles(
        enriched, output_dir,
        filter_agg_keys=["water_type"],
        top_items_fields=["id", "name", "sprite", "group"],
        point_fields=["id", "lat", "lng", "name", "sprite", "group", "rarity", "water_type"],
    )

    # 7. Species details
    generate_species_details(enriched, output_dir)

    # 8. Index
    generate_index(enriched, output_dir)

    # 9. Search index
    search_idx = build_search_index(enriched)
    assert len(search_idx["groups"]) >= 5

    # Verify output structure
    assert (output_dir / "index.json").exists()
    assert (output_dir / "species").is_dir()
    assert (output_dir / "tiles" / "z0").is_dir()

    # Verify a species detail
    index = json.loads((output_dir / "index.json").read_text())
    assert index["globeId"] == "aquatic"
    assert index["totalItems"] > 0

    # Verify a tile has sprite field
    tile_files = list((output_dir / "tiles").rglob("*.json"))
    assert len(tile_files) > 0
```

- [ ] **Step 2: Run test**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python -m pytest tests/test_aquatic_e2e.py -v`
Expected: PASS (may need adjustments to function signatures discovered during integration)

- [ ] **Step 3: Fix any integration issues discovered**

This step handles any mismatches between individually-tested functions when they're wired together.

- [ ] **Step 4: Commit**

```bash
git add tests/test_aquatic_e2e.py
git commit -m "test(aquatic): add end-to-end integration test with mock data"
```

---

## Task 15: Run Full Pipeline on Real Data

**Prerequisite:** OBIS and GBIF bulk downloads completed.

- [ ] **Step 1: Download OBIS data**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python scripts/aquatic_etl.py --download`
Expected: Files saved to `data/raw/aquatic/`

- [ ] **Step 2: Run processing pipeline**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python scripts/aquatic_etl.py --process`
Expected: Output files generated in `output/aquatic/`

- [ ] **Step 3: Fetch sprites**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python scripts/fetch_aquatic_sprites.py --limit 500`
Expected: Raw sprites saved to `data/raw/aquatic/sprites/`

- [ ] **Step 4: Normalize sprites and build manifest**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python scripts/normalize_sprites.py && python scripts/build_sprite_manifest.py`
Expected: Normalized SVGs and manifest.json in `output/aquatic/sprites/`

- [ ] **Step 5: Re-run processing to attach sprites**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python scripts/aquatic_etl.py --process`
Expected: All tiles and species files now have resolved `sprite` fields

- [ ] **Step 6: Validate**

Run: `cd /Volumes/workplace/openglobes/openglobes-etl && python scripts/validate.py aquatic`
Expected: 0 errors

- [ ] **Step 7: Commit output**

```bash
git add data/raw/aquatic/ output/aquatic/
git commit -m "feat(aquatic): initial pipeline run with OBIS+GBIF data and 500 sprites"
```
