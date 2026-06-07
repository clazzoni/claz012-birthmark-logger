"""Generate zoomed detail SVGs cropped from overview silhouettes."""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.overview_hotspots import FIGURE_BBOX, FIGURE_REGIONS  # noqa: E402

BODY_DIR = ROOT / "web" / "static" / "body"
OVERVIEW_FILES = {
    "front": BODY_DIR / "overview_front.svg",
    "back": BODY_DIR / "overview_back.svg",
}

SVG_NS = "http://www.w3.org/2000/svg"
PADDING_RATIO = 0.10

# (output filename, overview side, region key in FIGURE_REGIONS, aria-label)
DETAIL_CROPS: tuple[tuple[str, str, str, str], ...] = (
    ("detail_face.svg", "front", "face", "Face detail"),
    ("detail_front_torso.svg", "front", "front_torso", "Front torso detail"),
    ("detail_back.svg", "back", "back", "Back detail"),
    ("detail_arm.svg", "front", "left_arm", "Arm detail"),
    ("detail_leg.svg", "front", "left_leg", "Leg detail"),
    ("detail_hand.svg", "front", "left_hand", "Hand detail"),
)


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def parse_viewbox(svg_path: Path) -> tuple[float, float, float, float]:
    root = ET.parse(svg_path).getroot()
    parts = [float(v) for v in root.get("viewBox", "0 0 1 1").split()]
    return parts[0], parts[1], parts[2], parts[3]


def clamp_rect(rect: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = rect
    return (
        max(0.0, min(1.0, x0)),
        max(0.0, min(1.0, y0)),
        max(0.0, min(1.0, x1)),
        max(0.0, min(1.0, y1)),
    )


def figure_rect_to_crop(
    side: str,
    rect: tuple[float, float, float, float],
    overview_vb: tuple[float, float, float, float],
    padding_ratio: float = PADDING_RATIO,
) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = clamp_rect(rect)
    vx, vy, vw, vh = overview_vb
    fb = FIGURE_BBOX[side]

    fig_x = vx + (fb["left"] / 100.0) * vw
    fig_y = vy + (fb["top"] / 100.0) * vh
    fig_w = (fb["width"] / 100.0) * vw
    fig_h = (fb["height"] / 100.0) * vh

    crop_x = fig_x + x0 * fig_w
    crop_y = fig_y + y0 * fig_h
    crop_w = (x1 - x0) * fig_w
    crop_h = (y1 - y0) * fig_h

    pad = max(crop_w, crop_h) * padding_ratio
    return crop_x - pad, crop_y - pad, crop_w + 2 * pad, crop_h + 2 * pad


def write_cropped_svg(
    source: Path,
    output: Path,
    crop: tuple[float, float, float, float],
    label: str,
) -> None:
    cx, cy, cw, ch = crop
    tree = ET.parse(source)
    root = tree.getroot()

    root.set("viewBox", f"{cx} {cy} {cw} {ch}")
    root.set("role", "img")
    root.set("aria-label", label)

    for el in root.iter():
        if _strip_ns(el.tag) != "rect":
            continue
        x = el.get("x")
        y = el.get("y")
        if x is None or y is None:
            continue
        try:
            float(x)
            float(y)
        except ValueError:
            continue
        el.set("x", str(cx))
        el.set("y", str(cy))
        el.set("width", str(cw))
        el.set("height", str(ch))
        el.set("fill", "#f8f5f0")
        break

    xml = ET.tostring(root, encoding="unicode")
    output.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n' + xml,
        encoding="utf-8",
    )


def main() -> None:
    viewboxes = {side: parse_viewbox(path) for side, path in OVERVIEW_FILES.items()}

    for filename, side, region, label in DETAIL_CROPS:
        rect = FIGURE_REGIONS[side][region]
        crop = figure_rect_to_crop(side, rect, viewboxes[side])
        out = BODY_DIR / filename
        write_cropped_svg(OVERVIEW_FILES[side], out, crop, label)
        print(f"Wrote {filename} from {side}/{region} viewBox={crop}")

    print("Done.")


if __name__ == "__main__":
    main()
