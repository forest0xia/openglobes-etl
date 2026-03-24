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

SPRITE_OVERRIDES_PATH = ROOT / "data" / "raw" / "aquatic" / "sprite_overrides.json"


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


if __name__ == "__main__":
    main()
