"""Overview hotspot coordinates aligned to Wikimedia silhouette figure bounds.

Regions are defined as fractions (x0, y0, x1, y1) within the figure bounding box,
then converted to CSS percentages relative to the full SVG viewBox (including padding).
"""

from __future__ import annotations

# Measured from overview_front.svg / overview_back.svg path bounds vs viewBox.
FIGURE_BBOX: dict[str, dict[str, float]] = {
    "front": {"left": 4.127, "top": 3.704, "width": 91.746, "height": 92.593},
    "back": {"left": 3.704, "top": 3.781, "width": 92.593, "height": 92.439},
}

# Fractions within the figure silhouette (0 = left/top of body, 1 = right/bottom).
FIGURE_REGIONS = {
    "front": {
        "face": (0.313, 0.116, 0.451, 0.293),
        "front_torso": (0.308, 0.290, 0.459, 0.576),
        "left_arm": (0.475, 0.225, 0.736, 0.525),
        "left_hand": (0.505, 0.526, 0.704, 0.667),
        "left_leg": (0.390, 0.585, 0.497, 1.024),
        "right_arm": (0.051, 0.239, 0.311, 0.539),
        "right_hand": (0.075, 0.532, 0.274, 0.673),
        "right_leg": (0.272, 0.572, 0.368, 1.025),
    },
    "back": {
        "back": (0.759, 0.266, 0.915, 0.630),
        "left_arm": (0.540, 0.275, 0.760, 0.634),
        "left_leg": (0.738, 0.625, 0.825, 1.029),
        "right_arm": (0.924, 0.135, 1.025, 0.663),
        "right_leg": (0.846, 0.622, 0.930, 1.029),
    },
}


def figure_rect_to_percent(
    side: str, rect: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    """Convert a figure-relative rect to CSS left/top/width/height percentages."""
    x0, y0, x1, y1 = rect
    box = FIGURE_BBOX[side]
    left = box["left"] + x0 * box["width"]
    top = box["top"] + y0 * box["height"]
    width = (x1 - x0) * box["width"]
    height = (y1 - y0) * box["height"]
    return (round(left, 1), round(top, 1), round(width, 1), round(height, 1))


def percent_rect_to_figure(
    side: str, rect: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    """Convert CSS percentages back to figure-relative fractions."""
    left, top, width, height = rect
    box = FIGURE_BBOX[side]
    x0 = (left - box["left"]) / box["width"]
    y0 = (top - box["top"]) / box["height"]
    x1 = x0 + width / box["width"]
    y1 = y0 + height / box["height"]
    return (
        round(max(0.0, min(1.0, x0)), 3),
        round(max(0.0, min(1.0, y0)), 3),
        round(max(0.0, min(1.0, x1)), 3),
        round(max(0.0, min(1.0, y1)), 3),
    )


def hotspots_for_side(side: str) -> dict[str, tuple[float, float, float, float]]:
    return {
        region: figure_rect_to_percent(side, rect)
        for region, rect in FIGURE_REGIONS[side].items()
    }
