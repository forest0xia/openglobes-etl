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
