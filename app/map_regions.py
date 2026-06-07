MAP_REGIONS: tuple[str, ...] = (
    "face",
    "front_torso",
    "back",
    "left_arm",
    "right_arm",
    "left_leg",
    "right_leg",
    "left_hand",
    "right_hand",
)

REGION_LABELS: dict[str, str] = {
    "face": "Face",
    "front_torso": "Front torso",
    "back": "Back",
    "left_arm": "Left arm",
    "right_arm": "Right arm",
    "left_leg": "Left leg",
    "right_leg": "Right leg",
    "left_hand": "Left hand",
    "right_hand": "Right hand",
}

OVERVIEW_FRONT_REGIONS: tuple[str, ...] = (
    "face",
    "front_torso",
    "left_arm",
    "right_arm",
    "left_leg",
    "right_leg",
    "left_hand",
    "right_hand",
)

OVERVIEW_BACK_REGIONS: tuple[str, ...] = (
    "back",
    "left_arm",
    "right_arm",
    "left_leg",
    "right_leg",
)

DETAIL_SVG_FILES: dict[str, str] = {
    "face": "detail_face.svg",
    "front_torso": "detail_front_torso.svg",
    "back": "detail_back.svg",
    "left_arm": "detail_arm.svg",
    "right_arm": "detail_arm.svg",
    "left_leg": "detail_leg.svg",
    "right_leg": "detail_leg.svg",
    "left_hand": "detail_hand.svg",
    "right_hand": "detail_hand.svg",
}

BACK_LIMB_SVG_FILES: dict[str, str] = {
    "left_arm": "detail_arm_back.svg",
    "right_arm": "detail_arm_back.svg",
    "left_leg": "detail_leg_back.svg",
    "right_leg": "detail_leg_back.svg",
}

LIMB_REGIONS: frozenset[str] = frozenset(
    {"left_arm", "right_arm", "left_leg", "right_leg"}
)

MIRRORED_REGIONS: frozenset[str] = frozenset(
    {"left_arm", "left_leg", "left_hand"}
)


def is_valid_region(region: str) -> bool:
    return region in MAP_REGIONS


def region_label(region: str) -> str:
    return REGION_LABELS.get(region, region)


def normalize_view(view: str | None) -> str:
    if view and view.lower() == "back":
        return "back"
    return "front"


def detail_svg_filename(region: str | None, view: str | None = None) -> str | None:
    if not region:
        return None
    side = normalize_view(view)
    if side == "back" and region in LIMB_REGIONS:
        return BACK_LIMB_SVG_FILES.get(region)
    return DETAIL_SVG_FILES.get(region)


def is_mirrored(region: str) -> bool:
    return region in MIRRORED_REGIONS
