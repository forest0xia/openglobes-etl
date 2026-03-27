"""Crop text labels from sprite images and pack into sprite sheet(s).

1. Detects species-name text at the bottom of each sprite by finding
   a gap of empty rows between the animal body and text below.
2. Crops each sprite to remove text, keeping only the animal.
3. Normalizes all sprites to a uniform height (preserving aspect ratio).
4. Packs sprites into 1-2 sprite sheet atlas images.
5. Generates a spritesheet.json manifest with coordinates.

Usage:
    python scripts/crop_and_pack_sprites.py
"""
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image

SPRITE_DIR = Path(__file__).resolve().parent.parent / "output" / "aquatic" / "sprites"
OUT_DIR = SPRITE_DIR  # output alongside originals
MIN_GAP_ROWS = 3  # minimum empty rows to count as a gap between animal and text
ALPHA_THRESHOLD = 20  # pixels with alpha > this are considered opaque
TARGET_HEIGHT = 64  # normalize all sprites to this height
SHEET_MAX_WIDTH = 2048  # max width of a sprite sheet
SHEET_PADDING = 2  # pixels between sprites in sheet


def find_text_crop_row(alpha: np.ndarray) -> int:
    """Find the row where we should crop to remove text below the animal.

    Identifies contiguous "bands" of content rows, finds the main animal body
    (the band with the most total opaque pixels), and crops everything below it.

    Returns the crop row (exclusive bottom bound for the animal).
    If no text is detected, returns the image height.
    """
    h, w = alpha.shape
    row_counts = np.array([np.sum(alpha[r, :] > ALPHA_THRESHOLD) for r in range(h)])

    # Find contiguous bands of rows that have content
    bands = []  # list of (start_row, end_row, total_pixels)
    in_band = False
    band_start = 0
    band_pixels = 0

    for r in range(h):
        if row_counts[r] > 0:
            if not in_band:
                band_start = r
                band_pixels = 0
                in_band = True
            band_pixels += row_counts[r]
        else:
            if in_band:
                bands.append((band_start, r, band_pixels))
                in_band = False

    if in_band:
        bands.append((band_start, h, band_pixels))

    if len(bands) <= 1:
        return h  # single band or empty — no text to remove

    # The main body is the band with the most total opaque pixels
    main_band_idx = max(range(len(bands)), key=lambda i: bands[i][2])
    main_band_end = bands[main_band_idx][1]

    # Check if there are bands below the main body (i.e., text)
    bands_below = [b for b in bands if b[0] >= main_band_end]
    if not bands_below:
        return h  # no content below main body

    # Verify the gap between main body and first text band is real
    first_text_band = min(bands_below, key=lambda b: b[0])
    gap_size = first_text_band[0] - main_band_end

    if gap_size < MIN_GAP_ROWS:
        return h  # gap too small, probably part of the animal

    # Verify text is in the lower portion of the image
    if main_band_end < h * 0.35:
        return h  # main body ends too high, something is off

    return main_band_end


def crop_to_content(img: Image.Image) -> Image.Image:
    """Crop image to its opaque content bounding box, removing text first."""
    arr = np.array(img.convert("RGBA"))
    alpha = arr[:, :, 3]
    h, w = alpha.shape

    # First detect and remove text
    crop_row = find_text_crop_row(alpha)

    # Zero out everything below crop_row (text area)
    if crop_row < h:
        arr[crop_row:, :, 3] = 0
        alpha = arr[:, :, 3]

    # Now find bounding box of remaining content
    opaque = alpha > ALPHA_THRESHOLD
    rows = np.any(opaque, axis=1)
    cols = np.any(opaque, axis=0)

    if not np.any(rows):
        return img  # fully transparent, return as-is

    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    # Add 1px padding
    rmin = max(0, rmin - 1)
    cmin = max(0, cmin - 1)
    rmax = min(h - 1, rmax + 1)
    cmax = min(w - 1, cmax + 1)

    return Image.fromarray(arr[rmin:rmax + 1, cmin:cmax + 1])


def normalize_height(img: Image.Image, target_h: int) -> Image.Image:
    """Resize image to target height, preserving aspect ratio."""
    w, h = img.size
    if h == 0:
        return img
    scale = target_h / h
    new_w = max(1, round(w * scale))
    return img.resize((new_w, target_h), Image.LANCZOS)


def pack_sprites(sprites: list[tuple[str, Image.Image]]) -> list[dict]:
    """Pack sprites into sprite sheet(s) using a simple row-packing algorithm.

    Returns list of sheet info dicts with sprite coordinates.
    """
    # Sort by height descending for better packing (all same height after normalize)
    # Then by width descending
    sprites.sort(key=lambda s: (-s[1].size[1], -s[1].size[0]))

    sheets = []
    current_sheet_sprites = []
    current_x = 0
    current_row_height = 0
    current_y = 0
    sheet_width = 0

    for name, img in sprites:
        w, h = img.size

        # Check if sprite fits in current row
        if current_x + w > SHEET_MAX_WIDTH and current_x > 0:
            # Start new row
            current_y += current_row_height + SHEET_PADDING
            current_x = 0
            current_row_height = 0

        current_sheet_sprites.append({
            "name": name,
            "img": img,
            "x": current_x,
            "y": current_y,
            "w": w,
            "h": h,
        })

        current_x += w + SHEET_PADDING
        current_row_height = max(current_row_height, h)
        sheet_width = max(sheet_width, current_x - SHEET_PADDING)

    # Finalize sheet dimensions
    sheet_height = current_y + current_row_height

    # Check if we need to split into 2 sheets
    total_area = sheet_width * sheet_height
    if total_area > 4096 * 4096 and len(current_sheet_sprites) > 10:
        # Split roughly in half
        mid = len(current_sheet_sprites) // 2
        first_half = [(s["name"], s["img"]) for s in current_sheet_sprites[:mid]]
        second_half = [(s["name"], s["img"]) for s in current_sheet_sprites[mid:]]
        return pack_sprites(first_half) + _pack_single_sheet(second_half, sheet_index=1)

    return _build_sheet(current_sheet_sprites, sheet_width, sheet_height, 0)


def _build_sheet(sprite_entries: list[dict], width: int, height: int, sheet_index: int) -> list[dict]:
    """Render a single sprite sheet and return manifest entries."""
    sheet = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    manifest = []
    for entry in sprite_entries:
        sheet.paste(entry["img"], (entry["x"], entry["y"]))
        manifest.append({
            "name": entry["name"],
            "sheet": sheet_index,
            "x": entry["x"],
            "y": entry["y"],
            "w": entry["w"],
            "h": entry["h"],
        })

    # Save PNG
    png_name = f"spritesheet-{sheet_index}.png"
    png_path = OUT_DIR / png_name
    sheet.save(png_path, "PNG", optimize=True)
    png_size = os.path.getsize(png_path)

    # Save WebP (lossy with alpha, quality 90 — good balance of size and quality)
    webp_name = f"spritesheet-{sheet_index}.webp"
    webp_path = OUT_DIR / webp_name
    sheet.save(webp_path, "WEBP", quality=90)
    webp_size = os.path.getsize(webp_path)

    print(f"  Sheet {sheet_index}: {width}x{height}, {len(sprite_entries)} sprites")
    print(f"    PNG: {png_size/1024:.0f} KB | WebP: {webp_size/1024:.0f} KB")

    return manifest


def _pack_single_sheet(sprites: list[tuple[str, Image.Image]], sheet_index: int) -> list[dict]:
    """Pack sprites into a single sheet with given index."""
    entries = []
    current_x = 0
    current_y = 0
    current_row_height = 0
    sheet_width = 0

    for name, img in sprites:
        w, h = img.size
        if current_x + w > SHEET_MAX_WIDTH and current_x > 0:
            current_y += current_row_height + SHEET_PADDING
            current_x = 0
            current_row_height = 0

        entries.append({
            "name": name, "img": img,
            "x": current_x, "y": current_y, "w": w, "h": h,
        })
        current_x += w + SHEET_PADDING
        current_row_height = max(current_row_height, h)
        sheet_width = max(sheet_width, current_x - SHEET_PADDING)

    sheet_height = current_y + current_row_height
    return _build_sheet(entries, sheet_width, sheet_height, sheet_index)


def main():
    print("=== Sprite Crop & Pack Pipeline ===\n")

    # Load existing manifest for metadata
    manifest_path = SPRITE_DIR / "manifest.json"
    existing_manifest = {}
    if manifest_path.exists():
        with open(manifest_path) as f:
            data = json.load(f)
            # manifest.json has "sprites" dict keyed by species name
            sprites_dict = data.get("sprites", data)
            if isinstance(sprites_dict, dict):
                existing_manifest = sprites_dict
            else:
                for entry in sprites_dict:
                    key = entry["file"].replace("sp-", "").replace(".png", "")
                    existing_manifest[key] = entry

    # Find all individual sprites
    sprite_files = sorted(SPRITE_DIR.glob("sp-*.png"))
    print(f"Found {len(sprite_files)} individual sprites")

    # Step 1: Crop text from all sprites
    print("\n[1/3] Cropping text labels...")
    cropped = []
    text_removed_count = 0

    for sp_file in sprite_files:
        img = Image.open(sp_file).convert("RGBA")
        original_h = img.size[1]

        cropped_img = crop_to_content(img)
        new_h = cropped_img.size[1]

        name = sp_file.stem  # e.g. "sp-amphiprion_ocellaris"
        had_text = new_h < original_h * 0.85  # significant height reduction = had text

        if had_text:
            text_removed_count += 1

        cropped.append((name, cropped_img))

    print(f"  Text removed from {text_removed_count}/{len(sprite_files)} sprites")

    # Step 2: Normalize heights
    print(f"\n[2/3] Normalizing to {TARGET_HEIGHT}px height...")
    normalized = []
    for name, img in cropped:
        norm = normalize_height(img, TARGET_HEIGHT)
        normalized.append((name, norm))

    widths = [img.size[0] for _, img in normalized]
    print(f"  Width range: {min(widths)}-{max(widths)}px")
    print(f"  Total sprites: {len(normalized)}")

    # Also save cropped individual sprites (overwrite originals)
    for name, img in normalized:
        img.save(SPRITE_DIR / f"{name}.png", "PNG")

    # Step 3: Pack into sprite sheets
    print("\n[3/3] Packing sprite sheets...")
    manifest_entries = pack_sprites(normalized)

    # Build manifest with metadata
    sheet_manifest = {
        "sheets": [],
        "sprites": {},
    }

    # Collect sheet info
    sheet_files = sorted(SPRITE_DIR.glob("spritesheet-*.png"))
    for sf in sheet_files:
        img = Image.open(sf)
        webp_name = sf.stem + ".webp"
        sheet_manifest["sheets"].append({
            "png": sf.name,
            "webp": webp_name,
            "width": img.size[0],
            "height": img.size[1],
        })

    # Build sprite lookup
    for entry in manifest_entries:
        name = entry["name"]
        key = name.replace("sp-", "")  # e.g. "amphiprion_ocellaris"
        meta = existing_manifest.get(key, {})
        if not meta:
            # Try without leading underscore or other variations
            for k, v in existing_manifest.items():
                if k.replace("-", "_") == key or v.get("file", "") == f"{name}.png":
                    meta = v
                    break

        sheet_manifest["sprites"][name] = {
            "sheet": entry["sheet"],
            "x": entry["x"],
            "y": entry["y"],
            "w": entry["w"],
            "h": entry["h"],
            "group": meta.get("group", ""),
            "bodyType": meta.get("bodyType", ""),
        }

    # Write spritesheet manifest
    manifest_out = OUT_DIR / "spritesheet.json"
    with open(manifest_out, "w") as f:
        json.dump(sheet_manifest, f, indent=2)

    total_png_size = sum(os.path.getsize(sf) for sf in sheet_files)
    webp_files = sorted(SPRITE_DIR.glob("spritesheet-*.webp"))
    total_webp_size = sum(os.path.getsize(sf) for sf in webp_files)
    total_individual_size = sum(
        os.path.getsize(SPRITE_DIR / f"{name}.png") for name, _ in normalized
    )

    print(f"\n=== Summary ===")
    print(f"  Sprites processed: {len(normalized)}")
    print(f"  Text labels removed: {text_removed_count}")
    print(f"  Sheet(s): {len(sheet_files)}")
    print(f"  Sheet PNG total: {total_png_size/1024:.0f} KB")
    print(f"  Sheet WebP total: {total_webp_size/1024:.0f} KB")
    print(f"  Individual sprites: {total_individual_size/1024:.0f} KB")
    print(f"  Manifest: {manifest_out.name}")


if __name__ == "__main__":
    main()
