"""
Build a static search index mapping common group names to species IDs.

Uses FishBase families table (Family → Order → Class) and family common names
to assign every species to one or more searchable groups.

Output: output/fish/search_index.json

Usage:
    python scripts/build_search_index.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "fishbase"
OUTPUT = ROOT / "output" / "fish" / "search_index.json"

# ── Group definitions ──
# Each group: keyword matches against family CommonName, or explicit Order/Class/Family rules.
# Priority: first match wins (a species belongs to its most specific group).

GROUP_RULES = [
    # --- Elasmobranchii subgroups (by Order) ---
    {"id": "shark", "label": "Sharks", "class": "Elasmobranchii",
     "orders": ["Carcharhiniformes", "Lamniformes", "Orectolobiformes", "Squaliformes",
                "Hexanchiformes", "Echinorhiniformes", "Heterodontiformes",
                "Pristiophoriformes", "Squatiniformes"]},
    {"id": "ray", "label": "Rays & Skates", "class": "Elasmobranchii",
     "orders": ["Rajiformes", "Myliobatiformes", "Torpediniformes", "Rhinopristiformes"]},

    # --- By Order (distinctive groups) ---
    {"id": "eel", "label": "Eels", "orders": ["Anguilliformes"]},
    {"id": "catfish", "label": "Catfish", "orders": ["Siluriformes"]},
    {"id": "flatfish", "label": "Flatfish", "orders": ["Pleuronectiformes"]},
    {"id": "pufferfish", "label": "Pufferfish & Boxfish", "orders": ["Tetraodontiformes"]},
    {"id": "carp", "label": "Carp & Minnows", "orders": ["Cypriniformes"]},
    {"id": "salmon", "label": "Salmon & Trout", "families": ["Salmonidae"]},
    {"id": "piranha", "label": "Piranhas & Characins", "orders": ["Characiformes"]},
    {"id": "herring", "label": "Herring & Sardines", "orders": ["Clupeiformes"]},
    {"id": "cod", "label": "Cod & Haddock", "orders": ["Gadiformes"]},
    {"id": "anglerfish", "label": "Anglerfish", "orders": ["Lophiiformes"]},
    {"id": "scorpionfish", "label": "Scorpionfish & Lionfish", "orders": ["Scorpaeniformes"]},
    {"id": "goby", "label": "Gobies", "orders": ["Gobiiformes"]},
    {"id": "cichlid", "label": "Cichlids", "families": ["Cichlidae"]},

    # --- By Family (iconic groups) ---
    {"id": "tuna", "label": "Tuna & Mackerel", "families": ["Scombridae"]},
    {"id": "seahorse", "label": "Seahorses & Pipefish", "families": ["Syngnathidae"]},
    {"id": "clownfish", "label": "Clownfish & Damselfish", "families": ["Pomacentridae"]},
    {"id": "angelfish", "label": "Angelfish", "families": ["Pomacanthidae"]},
    {"id": "butterflyfish", "label": "Butterflyfish", "families": ["Chaetodontidae"]},
    {"id": "wrasse", "label": "Wrasses", "families": ["Labridae"]},
    {"id": "grouper", "label": "Groupers & Sea Bass", "families": ["Serranidae", "Epinephelidae"]},
    {"id": "snapper", "label": "Snappers", "families": ["Lutjanidae"]},
    {"id": "barracuda", "label": "Barracudas", "families": ["Sphyraenidae"]},
    {"id": "swordfish", "label": "Swordfish & Marlin", "families": ["Xiphiidae", "Istiophoridae"]},
    {"id": "parrotfish", "label": "Parrotfish", "families": ["Scaridae"]},
    {"id": "surgeonfish", "label": "Surgeonfish & Tangs", "families": ["Acanthuridae"]},
    {"id": "blenny", "label": "Blennies", "families": ["Blenniidae"]},
    {"id": "moray", "label": "Moray Eels", "families": ["Muraenidae"]},
    {"id": "sturgeon", "label": "Sturgeons", "families": ["Acipenseridae"]},
    {"id": "lungfish", "label": "Lungfish", "families": ["Ceratodontidae", "Lepidosirenidae", "Protopteridae"]},
    {"id": "tarpon", "label": "Tarpons & Bonefish", "families": ["Megalopidae", "Albulidae"]},

    # --- By Class (catch-alls) ---
    {"id": "chimaera", "label": "Chimaeras", "class_only": "Holocephali"},
    {"id": "hagfish", "label": "Hagfish", "class_only": "Myxini"},
    {"id": "lamprey", "label": "Lampreys", "class_only": "Petromyzonti"},
    {"id": "coelacanth", "label": "Coelacanths", "class_only": "Coelacanthi"},
]


def build_index():
    # Load families table: FamCode → (Family, Order, Class)
    fam = pd.read_parquet(RAW_DIR / "families.parquet")
    fam = fam.dropna(subset=["FamCode", "Family"])
    fam["FamCode"] = pd.to_numeric(fam["FamCode"], errors="coerce")
    fam = fam.dropna(subset=["FamCode"])
    fam["FamCode"] = fam["FamCode"].astype(int)
    fam = fam.drop_duplicates(subset=["FamCode"], keep="first")
    fam_lookup = {
        int(r["FamCode"]): {"family": r["Family"], "order": r.get("Order", ""), "class": r.get("Class", "")}
        for _, r in fam.iterrows()
    }

    # Load species
    sp = pd.read_parquet(RAW_DIR / "species.parquet")
    sp["SpecCode"] = pd.to_numeric(sp["SpecCode"], errors="coerce")
    sp["FamCode"] = pd.to_numeric(sp["FamCode"], errors="coerce")
    sp = sp.dropna(subset=["SpecCode", "FamCode"])
    sp["SpecCode"] = sp["SpecCode"].astype(int)
    sp["FamCode"] = sp["FamCode"].astype(int)

    # Assign each species to groups
    groups = {r["id"]: {"label": r["label"], "specCodes": [], "count": 0} for r in GROUP_RULES}
    groups["other"] = {"label": "Other Bony Fish", "specCodes": [], "count": 0}
    by_spec = {}

    for _, row in sp.iterrows():
        spec = int(row["SpecCode"])
        fc = int(row["FamCode"])
        tax = fam_lookup.get(fc, {"family": "", "order": "", "class": ""})

        matched = []
        for rule in GROUP_RULES:
            hit = False
            if "class_only" in rule:
                hit = tax["class"] == rule["class_only"]
            elif "families" in rule and tax["family"] in rule["families"]:
                hit = True
            elif "orders" in rule and tax["order"] in rule.get("orders", []):
                if "class" in rule:
                    hit = tax["class"] == rule["class"]
                else:
                    hit = True

            if hit:
                matched.append(rule["id"])

        if not matched:
            matched = ["other"]

        for g in matched:
            groups[g]["specCodes"].append(spec)
            groups[g]["count"] += 1
        by_spec[str(spec)] = matched

    # Remove empty groups
    groups = {k: v for k, v in groups.items() if v["count"] > 0}

    # Sort specCodes for deterministic output
    for g in groups.values():
        g["specCodes"].sort()

    index = {"groups": groups, "bySpecCode": by_spec}

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(index, ensure_ascii=False))

    # Stats
    print(f"Search index built: {len(groups)} groups, {len(by_spec)} species mapped")
    print()
    for gid, g in sorted(groups.items(), key=lambda x: -x[1]["count"]):
        print(f"  {gid:<20} {g['label']:<30} {g['count']:>6} species")

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"\nOutput: {OUTPUT} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    build_index()
