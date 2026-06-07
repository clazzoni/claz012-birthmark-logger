"""Split Wikimedia CC0 silhouette into front/back overview SVGs."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "web" / "static" / "body" / "wikimedia_full.svg"
OUT_FRONT = ROOT / "web" / "static" / "body" / "overview_front.svg"
OUT_BACK = ROOT / "web" / "static" / "body" / "overview_back.svg"

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _path_bbox(path_d: str) -> tuple[float, float, float, float] | None:
    nums = [float(n) for n in re.findall(r"-?\d*\.?\d+", path_d)]
    if len(nums) < 4:
        return None
    xs = nums[0::2]
    ys = nums[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def main() -> None:
    tree = ET.parse(SOURCE)
    root = tree.getroot()

    layer = root.find(f".//{{{SVG_NS}}}g[@id='layer1']")
    if layer is None:
        raise SystemExit("layer1 not found")

    groups = [child for child in layer if _strip_ns(child.tag) == "g"]
    if len(groups) != 2:
        raise SystemExit(f"expected 2 body groups, found {len(groups)}")

    bboxes = []
    for group in groups:
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        for path in group.iter():
            if _strip_ns(path.tag) != "path":
                continue
            d = path.get("d")
            if not d:
                continue
            bbox = _path_bbox(d)
            if bbox is None:
                continue
            x0, y0, x1, y1 = bbox
            min_x, min_y = min(min_x, x0), min(min_y, y0)
            max_x, max_y = max(max_x, x1), max(max_y, y1)
        bboxes.append((min_x, min_y, max_x, max_y))

    # In the combined Wikimedia file, posterior (back) is on the left and
    # anterior (front) is on the right.
    left_idx = 0 if bboxes[0][0] < bboxes[1][0] else 1
    right_idx = 1 - left_idx
    back_idx = left_idx
    front_idx = right_idx

    def build_single(group: ET.Element, bbox: tuple[float, float, float, float], label: str, out: Path) -> None:
        min_x, min_y, max_x, max_y = bbox
        width = max_x - min_x
        height = max_y - min_y
        pad = max(width, height) * 0.04
        view_x = min_x - pad
        view_y = min_y - pad
        view_w = width + 2 * pad
        view_h = height + 2 * pad

        svg = ET.Element(
            "svg",
            {
                "xmlns": SVG_NS,
                "viewBox": f"{view_x} {view_y} {view_w} {view_h}",
                "role": "img",
                "aria-label": label,
            },
        )
        bg = ET.SubElement(
            svg,
            "rect",
            {
                "x": str(view_x),
                "y": str(view_y),
                "width": str(view_w),
                "height": str(view_h),
                "fill": "#f8f5f0",
            },
        )
        _ = bg  # background rect

        g = ET.SubElement(svg, "g")
        for path in group.iter():
            if _strip_ns(path.tag) != "path":
                continue
            attrs = dict(path.attrib)
            attrs.pop("style", None)
            attrs["fill"] = "#d9d2c7"
            attrs["stroke"] = "#8a8078"
            attrs["stroke-width"] = attrs.get("stroke-width", "1.2")
            ET.SubElement(g, "path", attrs)

        out.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            + ET.tostring(svg, encoding="unicode"),
            encoding="utf-8",
        )

    build_single(groups[front_idx], bboxes[front_idx], "Front body overview", OUT_FRONT)
    build_single(groups[back_idx], bboxes[back_idx], "Back body overview", OUT_BACK)
    print("Wrote", OUT_FRONT.name, OUT_BACK.name)


if __name__ == "__main__":
    main()
