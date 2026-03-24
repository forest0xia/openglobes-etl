"""Generate aquatic species sprites using OpenAI DALL-E 3."""
import json
import os
import time
import base64
from pathlib import Path
from PIL import Image
from io import BytesIO
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
SPRITE_LIST_PATH = ROOT / "data" / "raw" / "aquatic" / "sprite_species_list.json"
RAW_DIR = ROOT / "data" / "raw" / "aquatic" / "sprites" / "dalle3"
OUTPUT_DIR = ROOT / "output" / "aquatic" / "sprites"

# Real-world body length by group → icon pixel size (32-128)
GROUP_SIZE_MAP = {
    # Large marine mammals
    "whale": 128,
    "dolphin": 112,
    "seal": 96,
    "sea_otter": 80,
    # Large fish
    "shark": 112,
    "ray": 96,
    "swordfish": 96,
    "tuna_mackerel": 96,
    "barracuda": 80,
    "sturgeon": 80,
    "sunfish": 96,
    "grouper": 80,
    # Medium fish
    "salmon_trout": 72,
    "cod": 72,
    "bass": 64,
    "snapper": 64,
    "catfish": 64,
    "carp_minnow": 64,
    "eel": 72,
    "moray": 72,
    "herring": 56,
    "piranha": 56,
    "flatfish": 56,
    "parrotfish": 64,
    "wrasse": 56,
    "cichlid": 56,
    # Small fish
    "clownfish": 48,
    "angelfish": 48,
    "butterflyfish": 48,
    "goby": 40,
    "blenny": 40,
    "seahorse": 48,
    "pufferfish": 56,
    "scorpionfish": 56,
    "surgeonfish": 56,
    "triggerfish": 56,
    "anchovy": 40,
    "flying_fish": 48,
    "anglerfish": 56,
    "lamprey": 48,
    "hagfish": 40,
    "lungfish": 64,
    # Reptiles
    "sea_turtle": 96,
    "sea_snake": 72,
    # Cephalopods
    "octopus_squid": 80,
    # Crustaceans
    "crab_lobster": 64,
    "shrimp": 40,
    # Cnidarians
    "jellyfish": 64,
    "coral": 48,
    # Echinoderms
    "starfish": 48,
    # Mollusks
    "clam_mussel": 40,
    "sea_snail": 40,
    # Other
    "sponge": 40,
    "other_fish": 56,
    "other": 48,
}


def get_icon_size(group: str) -> int:
    """Get target icon pixel size for a species group."""
    return GROUP_SIZE_MAP.get(group, 48)


def build_prompt(common_name: str) -> str:
    """Build the DALL-E 3 prompt."""
    return (
        f"Wide shot of a {common_name}. "
        f"Straight full body shot, zoomed out. "
        f"real look, nature photography style, vivid natural colors, "
        f"detailed, only show one single animal, "
        f"isolated on plain black background"
    )


def generate_sprite(common_name: str, species_id: str, client: OpenAI) -> bool:
    """Generate a single sprite with DALL-E 3. Returns True if successful."""
    raw_path = RAW_DIR / f"{species_id}.png"
    if raw_path.exists():
        return True

    prompt = build_prompt(common_name)

    try:
        resp = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard",
            style="natural",
            response_format="b64_json",
        )
        img_data = base64.b64decode(resp.data[0].b64_json)
        raw_path.write_bytes(img_data)
        return True
    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def resize_sprite(species_id: str, group: str):
    """Resize raw generated image to target icon size."""
    raw_path = RAW_DIR / f"{species_id}.png"
    out_path = OUTPUT_DIR / f"sp-{species_id}.png"
    if not raw_path.exists():
        return False

    target_size = get_icon_size(group)
    img = Image.open(raw_path)
    img = img.resize((target_size, target_size), Image.LANCZOS)
    img.save(out_path, "PNG", optimize=True)
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate aquatic sprites with DALL-E 3")
    parser.add_argument("--limit", type=int, default=0, help="Limit species count (0=all)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N species")
    parser.add_argument("--resize-only", action="store_true", help="Only resize existing raw images")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between API calls (seconds)")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key and not args.resize_only:
        print("ERROR: Set OPENAI_API_KEY environment variable")
        return

    client = OpenAI(api_key=api_key) if api_key else None

    if not SPRITE_LIST_PATH.exists():
        print(f"ERROR: Species list not found at {SPRITE_LIST_PATH}")
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    species_list = json.loads(SPRITE_LIST_PATH.read_text())
    if args.offset:
        species_list = species_list[args.offset:]
    if args.limit > 0:
        species_list = species_list[:args.limit]

    print(f"Processing {len(species_list)} species (offset={args.offset})")
    cost_estimate = len(species_list) * 0.04
    print(f"Estimated cost: ${cost_estimate:.2f} (DALL-E 3 1024x1024 @ $0.04/image)")

    generated = 0
    skipped = 0
    failed = 0

    for i, sp in enumerate(species_list):
        sid = str(sp["id"])
        sci_name = sp["scientificName"]
        group = sp.get("group", "other")
        # Use common name if available, otherwise use genus from scientific name
        common_name = sci_name
        target_size = get_icon_size(group)

        if args.resize_only:
            if resize_sprite(sid, group):
                generated += 1
            continue

        raw_path = RAW_DIR / f"{sid}.png"
        if raw_path.exists():
            resize_sprite(sid, group)
            skipped += 1
            continue

        print(f"  [{i+1}/{len(species_list)}] {sci_name} ({group}, {target_size}px)")
        success = generate_sprite(common_name, sid, client)
        if success:
            resize_sprite(sid, group)
            generated += 1
        else:
            failed += 1

        if args.delay > 0:
            time.sleep(args.delay)

        # Progress update every 50
        if (i + 1) % 50 == 0:
            print(f"  --- Progress: {i+1}/{len(species_list)} | Generated: {generated} | Failed: {failed} ---")

    print(f"\nDone: {generated} generated, {skipped} skipped, {failed} failed")
    print(f"Actual cost: ~${generated * 0.04:.2f}")


if __name__ == "__main__":
    main()
