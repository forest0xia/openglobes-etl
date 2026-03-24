"""Cut individual animals from ChatGPT composite images.

Expects images with transparent backgrounds and animal names listed
in the bottom text. Animals are detected via alpha channel and sorted
in reading order (top-to-bottom, left-to-right) to match the name list.

Usage:
    python scripts/cut_composite_sprites.py /path/to/composite.png "Name1, Name2, Name3, Name4"
    python scripts/cut_composite_sprites.py /path/to/folder/  # process all PNGs, parse names from image
"""
import sys
import re
import numpy as np
from PIL import Image
from scipy import ndimage
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "aquatic" / "sprites" / "chatgpt_cut"


def cut_animals(src_path: Path, names: list[str], out_dir: Path = OUT_DIR, min_area: int = 500, padding: int = 5):
    """Cut individual animals from a composite image using alpha channel."""
    img = Image.open(src_path).convert("RGBA")
    arr = np.array(img)
    h, w = arr.shape[:2]

    opaque = arr[:, :, 3] > 128

    # Cut off bottom 12% (text area)
    text_cutoff = int(h * 0.88)
    opaque[text_cutoff:, :] = False

    labeled, num = ndimage.label(opaque)

    regions = []
    for lbl in range(1, num + 1):
        ys, xs = np.where(labeled == lbl)
        area = len(ys)
        if area < min_area:
            continue
        bbox = (ys.min(), xs.min(), ys.max(), xs.max())
        regions.append({
            "label": lbl, "bbox": bbox, "area": area,
            "center_y": (bbox[0] + bbox[2]) // 2,
            "center_x": (bbox[1] + bbox[3]) // 2,
        })

    # Sort reading order: top to bottom, left to right
    regions.sort(key=lambda r: (r["center_y"], r["center_x"]))

    if len(regions) != len(names):
        print(f"  WARNING: Found {len(regions)} animals but {len(names)} names")

    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for i, r in enumerate(regions):
        if i >= len(names):
            break
        name = names[i].strip()
        t, l, b, ri = r["bbox"]
        t = max(0, t - padding)
        l = max(0, l - padding)
        b = min(h, b + padding)
        ri = min(w, ri + padding)

        crop = arr[t:b, l:ri].copy()
        crop_mask = labeled[t:b, l:ri] == r["label"]
        crop[~crop_mask, 3] = 0

        result = Image.fromarray(crop)
        filename = re.sub(r'[^a-z0-9_]', '_', name.lower().strip()).strip('_') + ".png"
        out_path = out_dir / filename
        result.save(out_path, "PNG")
        results.append((name, filename, ri - l, b - t))
        print(f"  [{i}] {name} -> {filename} ({ri-l}x{b-t})")

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python cut_composite_sprites.py <image_or_folder> [\"Name1, Name2, ...\"]")
        return

    path = Path(sys.argv[1])
    names_arg = sys.argv[2] if len(sys.argv) > 2 else None

    if path.is_dir():
        for f in sorted(path.glob("*.png")):
            print(f"\nProcessing {f.name}...")
            if names_arg:
                names = [n.strip() for n in names_arg.split(",")]
            else:
                print("  ERROR: Provide names as second argument for folder mode")
                continue
            cut_animals(f, names)
    else:
        if names_arg:
            names = [n.strip() for n in names_arg.split(",")]
        else:
            print("ERROR: Provide names as second argument")
            print('  Example: python cut_composite_sprites.py image.png "Orca, Clownfish, Shark, Jellyfish"')
            return
        cut_animals(path, names)


if __name__ == "__main__":
    main()
