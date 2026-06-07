from datetime import datetime, timezone

from app import db
from app.map_regions import MAP_REGIONS, is_valid_region
from app.models import MarkCreate, MarkPlacement


def test_map_region_constants():
    assert len(MAP_REGIONS) == 9
    assert is_valid_region("left_arm")
    assert not is_valid_region("torso")


def test_detail_svg_by_view():
    from app.map_regions import detail_svg_filename, is_mirrored

    assert detail_svg_filename("left_arm") == "detail_arm.svg"
    assert detail_svg_filename("left_arm", "back") == "detail_arm_back.svg"
    assert detail_svg_filename("left_leg", "back") == "detail_leg_back.svg"
    assert detail_svg_filename("face", "back") == "detail_face.svg"
    assert is_mirrored("left_arm") is True
    assert is_mirrored("right_arm") is False


def test_update_mark_placement():
    mark = db.create_mark(MarkCreate(label="arm mark"))
    placement = MarkPlacement(map_region="left_arm", map_x=0.4, map_y=0.6)
    updated = db.update_mark_placement(mark.id, placement)

    assert updated is not None
    assert updated.map_region == "left_arm"
    assert updated.map_x == 0.4
    assert updated.map_y == 0.6
    assert updated.is_placed is True


def test_list_marks_by_region():
    first = db.create_mark(MarkCreate(label="first"))
    second = db.create_mark(MarkCreate(label="second"))
    db.update_mark_placement(
        first.id,
        MarkPlacement(map_region="face", map_x=0.5, map_y=0.5),
    )
    db.update_mark_placement(
        second.id,
        MarkPlacement(map_region="back", map_x=0.2, map_y=0.3),
    )

    face_marks = db.list_marks_by_region("face")
    assert len(face_marks) == 1
    assert face_marks[0].id == first.id


def test_count_marks_by_region():
    mark = db.create_mark(MarkCreate(label="leg"))
    db.update_mark_placement(
        mark.id,
        MarkPlacement(map_region="left_leg", map_x=0.1, map_y=0.9),
    )

    counts = db.count_marks_by_region()
    assert counts["left_leg"] == 1
    assert counts["face"] == 0


def test_list_unplaced_marks():
    placed = db.create_mark(MarkCreate(label="placed"))
    unplaced = db.create_mark(MarkCreate(label="unplaced"))
    db.update_mark_placement(
        placed.id,
        MarkPlacement(map_region="face", map_x=0.5, map_y=0.5),
    )
    db.insert_capture(
        mark_id=unplaced.id,
        captured_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        file_path=f"{unplaced.id}/file.jpg",
        file_hash="x",
        original_filename="a.jpg",
    )

    results = db.list_marks(unplaced_only=True)
    assert len(results) == 1
    assert results[0].id == unplaced.id


def test_clear_mark_placement():
    mark = db.create_mark(MarkCreate(label="clear me"))
    db.update_mark_placement(
        mark.id,
        MarkPlacement(map_region="right_hand", map_x=0.3, map_y=0.7),
    )

    cleared = db.clear_mark_placement(mark.id)
    assert cleared is not None
    assert cleared.is_placed is False
    assert cleared.map_region is None
