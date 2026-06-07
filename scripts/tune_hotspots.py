"""Estimate overview hotspot percentages from path bounding boxes."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG_NS = "http://www.w3.org/2000/svg"


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def parse_viewbox(svg_path: Path) -> tuple[float, float, float, float]:
    root = ET.parse(svg_path).getroot()
    vb = root.get("viewBox", "0 0 1 1").split()
    return tuple(float(v) for v in vb)  # type: ignore


def path_bboxes(svg_path: Path) -> list[tuple[float, float, float, float]]:
    root = ET.parse(svg_path).getroot()
    boxes = []
    for path in root.iter():
        if _strip_ns(path.tag) != "path":
            continue
        d = path.get("d", "")
        nums = [float(n) for n in re.findall(r"-?\d*\.?\d+", d)]
        if len(nums) < 4:
            continue
        xs = nums[0::2]
        ys = nums[1::2]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return boxes


def cluster_region(boxes, viewbox, x_range, y_range):
    vx, vy, vw, vh = viewbox
    selected = []
    for x0, y0, x1, y1 in boxes:
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        nx = (cx - vx) / vw
        ny = (cy - vy) / vh
        if x_range[0] <= nx <= x_range[1] and y_range[0] <= ny <= y_range[1]:
            selected.append((x0, y0, x1, y1))
    if not selected:
        return None
    x0 = min(b[0] for b in selected)
    y0 = min(b[1] for b in selected)
    x1 = max(b[2] for b in selected)
    y1 = max(b[3] for b in selected)
    return (
        (x0 - vx) / vw * 100,
        (y0 - vy) / vh * 100,
        (x1 - x0) / vw * 100,
        (y1 - y0) / vh * 100,
    )


def main() -> None:
    front = ROOT / "web/static/body/overview_front.svg"
    back = ROOT / "web/static/body/overview_back.svg"
    fvb = parse_viewbox(front)
    fboxes = path_bboxes(front)
    regions = {
        "face": ((0.35, 0.65), (0.0, 0.18)),
        "front_torso": ((0.25, 0.75), (0.14, 0.48)),
        "left_arm": ((0.0, 0.28), (0.12, 0.42)),
        "right_arm": ((0.72, 1.0), (0.12, 0.42)),
        "left_hand": ((0.0, 0.22), (0.38, 0.52)),
        "right_hand": ((0.78, 1.0), (0.38, 0.52)),
        "left_leg": ((0.2, 0.48), (0.46, 1.0)),
        "right_leg": ((0.52, 0.8), (0.46, 1.0)),
    }
    print("FRONT", fvb)
    for name, ranges in regions.items():
        hs = cluster_region(fboxes, fvb, *ranges)
        print(name, hs)

    bvb = parse_viewbox(back)
    bboxes = path_bboxes(back)
    back_regions = {
        "back": ((0.25, 0.75), (0.12, 0.5)),
        "left_arm": ((0.0, 0.28), (0.12, 0.42)),
        "right_arm": ((0.72, 1.0), (0.12, 0.42)),
        "left_leg": ((0.2, 0.48), (0.46, 1.0)),
        "right_leg": ((0.52, 0.8), (0.46, 1.0)),
    }
    print("BACK", bvb)
    for name, ranges in back_regions.items():
        hs = cluster_region(bboxes, bvb, *ranges)
        print(name, hs)


if __name__ == "__main__":
    main()
