"""Extract front / side / back turnaround views from the MainGirlfriend design sheet.

Usage (from any directory):
    python3 prepare_reference_images.py

Outputs (next to this script):
    References/Front.png
    References/Side.png
    References/Back.png
    References/reference_layout.json   # read by setup_blender_references.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: python3 -m pip install pillow")


# ---------------------------------------------------------------------------
# Adjustable settings
# ---------------------------------------------------------------------------

SOURCE_IMAGE_NAME = "MainGirlfriend_Reference.png"
OUTPUT_DIR_NAME = "References"
LAYOUT_FILE_NAME = "reference_layout.json"

# The crop boxes below were measured on a 1536x1024 design sheet.
# If the sheet is replaced with a different size, re-measure CROP_BOXES.
EXPECTED_SOURCE_SIZE = (1536, 1024)

# Search regions inside the top-centre turnaround panel, in source pixels:
# (left, top, right, bottom), right/bottom exclusive.
# Each box must contain exactly one character and nothing else
# (no header label, neighbouring view, big pose illustration or info panel).
#
#   Turnaround order on the sheet:
#   Front | 3/4 front | Side (profile, facing left) | 3/4 back | Back
#
# Measured character bounds (head top .. sole) for reference:
#   Front x 400-551, y 52-370
#   Side  x 739-859, y 48-369
#   Back  x 1026-1179, y 48-369
CROP_BOXES = {
    "Front": (392, 44, 562, 382),
    "Side": (725, 44, 870, 382),
    "Back": (1017, 44, 1186, 382),
}

# True: trim each crop box down to the character automatically
#       (top = head top, bottom = sole).
# False: use CROP_BOXES as-is. In that case each box must already be tight,
#        with its top edge on the head top and its bottom edge on the soles.
AUTO_TRIM = True

# A pixel counts as "character" when the sum of absolute RGB differences
# from the background colour exceeds this value. Faint floor shadows stay below it.
BACKGROUND_THRESHOLD = 60
MIN_ROW_PIXELS = 6
MIN_COLUMN_PIXELS = 2

# Empty margin (output pixels) added around each character.
PADDING_PX = 16


# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_PATH = SCRIPT_DIR / SOURCE_IMAGE_NAME
OUTPUT_DIR = SCRIPT_DIR / OUTPUT_DIR_NAME

Box = tuple[int, int, int, int]
Color = tuple[int, int, int]


def estimate_background(image: Image.Image, box: Box) -> Color:
    left, top, right, bottom = box
    px = image.load()
    border = []
    for x in range(left, right):
        border.append(px[x, top])
        border.append(px[x, bottom - 1])
    for y in range(top, bottom):
        border.append(px[left, y])
        border.append(px[right - 1, y])
    return tuple(int(statistics.median(c[i] for c in border)) for i in range(3))


def detect_character_box(image: Image.Image, box: Box, background: Color) -> Box | None:
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    px = image.load()
    row_counts = [0] * height
    col_counts = [0] * width
    br, bg, bb = background

    for y in range(height):
        for x in range(width):
            r, g, b = px[left + x, top + y]
            if abs(r - br) + abs(g - bg) + abs(b - bb) > BACKGROUND_THRESHOLD:
                row_counts[y] += 1
                col_counts[x] += 1

    rows = [y for y, count in enumerate(row_counts) if count >= MIN_ROW_PIXELS]
    cols = [x for x, count in enumerate(col_counts) if count >= MIN_COLUMN_PIXELS]
    if not rows or not cols:
        return None

    return (left + cols[0], top + rows[0], left + cols[-1] + 1, top + rows[-1] + 1)


def validate_box(name: str, box: Box, size: tuple[int, int]) -> None:
    left, top, right, bottom = box
    if not (0 <= left < right <= size[0] and 0 <= top < bottom <= size[1]):
        sys.exit(f"[{name}] crop box {box} is outside the source image {size}.")


def resolve_character_box(name: str, image: Image.Image, crop_box: Box, background: Color) -> Box:
    if not AUTO_TRIM:
        return crop_box

    detected = detect_character_box(image, crop_box, background)
    if detected is None:
        sys.exit(
            f"[{name}] no character found inside crop box {crop_box}. "
            "Adjust CROP_BOXES or set AUTO_TRIM = False."
        )

    crop_height = crop_box[3] - crop_box[1]
    detected_height = detected[3] - detected[1]
    if detected_height < crop_height * 0.5:
        sys.exit(
            f"[{name}] detected character {detected} is much smaller than crop box {crop_box}. "
            "Check CROP_BOXES or BACKGROUND_THRESHOLD."
        )

    touching = [
        side
        for side, hit in (
            ("left", detected[0] == crop_box[0]),
            ("top", detected[1] == crop_box[1]),
            ("right", detected[2] == crop_box[2]),
            ("bottom", detected[3] == crop_box[3]),
        )
        if hit
    ]
    if touching:
        print(
            f"  WARNING [{name}] character touches the crop box edge ({', '.join(touching)}); "
            "it may be cut off. Consider enlarging CROP_BOXES."
        )

    return detected


def main() -> None:
    if not SOURCE_PATH.is_file():
        sys.exit(f"Source image not found: {SOURCE_PATH}")

    source = Image.open(SOURCE_PATH).convert("RGB")
    if source.size != EXPECTED_SOURCE_SIZE:
        sys.exit(
            f"Source image is {source.size[0]}x{source.size[1]}, "
            f"but CROP_BOXES were measured on {EXPECTED_SOURCE_SIZE[0]}x{EXPECTED_SOURCE_SIZE[1]}. "
            "Re-measure CROP_BOXES and update EXPECTED_SOURCE_SIZE."
        )

    print(f"Source: {SOURCE_PATH.name} ({source.size[0]}x{source.size[1]})")

    characters: dict[str, tuple[Box, Color]] = {}
    for name, crop_box in CROP_BOXES.items():
        validate_box(name, crop_box, source.size)
        background = estimate_background(source, crop_box)
        char_box = resolve_character_box(name, source, crop_box, background)
        characters[name] = (char_box, background)
        print(
            f"  {name:5s} crop {crop_box} -> character {char_box} "
            f"({char_box[2] - char_box[0]}x{char_box[3] - char_box[1]} px)"
        )

    # Every view is scaled uniformly so head top and soles land on the same rows.
    target_height = max(box[3] - box[1] for box, _ in characters.values())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    layout = {
        "source_image": SOURCE_IMAGE_NAME,
        "character_height_px": target_height,
        "views": {},
    }

    for name, (char_box, background) in characters.items():
        crop = source.crop(char_box)
        scale = target_height / crop.height
        if crop.height != target_height:
            crop = crop.resize(
                (max(1, round(crop.width * scale)), target_height),
                Image.Resampling.LANCZOS,
            )

        canvas = Image.new(
            "RGB",
            (crop.width + PADDING_PX * 2, target_height + PADDING_PX * 2),
            background,
        )
        canvas.paste(crop, (PADDING_PX, PADDING_PX))

        file_name = f"{name}.png"
        canvas.save(OUTPUT_DIR / file_name)

        layout["views"][name] = {
            "file": file_name,
            "width": canvas.width,
            "height": canvas.height,
            "head_top_px": PADDING_PX,
            "sole_px": PADDING_PX + target_height,
            "center_x_px": canvas.width / 2,
            "source_box": list(char_box),
            "scale": round(scale, 6),
        }
        print(f"  saved {OUTPUT_DIR_NAME}/{file_name} ({canvas.width}x{canvas.height}, scale {scale:.4f})")

    layout_path = OUTPUT_DIR / LAYOUT_FILE_NAME
    layout_path.write_text(json.dumps(layout, indent=2), encoding="utf-8")
    print(f"  saved {OUTPUT_DIR_NAME}/{LAYOUT_FILE_NAME}")


if __name__ == "__main__":
    main()
