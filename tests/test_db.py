from datetime import datetime, timezone

from app import db
from app.models import MarkCreate, MarkUpdate


def test_create_mark_assigns_sequential_ids():
    first = db.create_mark(MarkCreate(label="left shoulder"))
    second = db.create_mark(MarkCreate(label="right arm"))

    assert first.id == "BM-001"
    assert second.id == "BM-002"


def test_list_marks_includes_capture_stats():
    mark = db.create_mark(MarkCreate(label="back mark", body_region="back"))
    captured_at = datetime(2024, 5, 1, 12, 0, tzinfo=timezone.utc)
    db.insert_capture(
        mark_id=mark.id,
        captured_at=captured_at,
        file_path=f"{mark.id}/2024-05-01_abc.jpg",
        file_hash="abc123",
        original_filename="photo.jpg",
    )

    marks = db.list_marks()
    assert len(marks) == 1
    assert marks[0].capture_count == 1
    assert marks[0].last_capture_at == captured_at


def test_search_marks():
    db.create_mark(MarkCreate(label="left shoulder", body_region="arm"))
    db.create_mark(MarkCreate(label="right calf", body_region="leg"))

    results = db.list_marks(search="shoulder")
    assert len(results) == 1
    assert results[0].label == "left shoulder"


def test_update_mark():
    mark = db.create_mark(MarkCreate(label="old label"))
    updated = db.update_mark(
        mark.id,
        MarkUpdate(label="new label", body_region="back", notes="watch closely"),
    )

    assert updated is not None
    assert updated.label == "new label"
    assert updated.body_region == "back"
    assert updated.notes == "watch closely"


def test_delete_mark_removes_mark_and_captures():
    mark = db.create_mark(MarkCreate(label="to delete"))
    db.insert_capture(
        mark_id=mark.id,
        captured_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        file_path=f"{mark.id}/file.jpg",
        file_hash="delete-hash",
        original_filename="a.jpg",
    )

    assert db.delete_mark(mark.id) is True
    assert db.get_mark(mark.id) is None
    assert db.list_captures(mark.id) == []


def test_delete_mark_returns_false_for_missing():
    assert db.delete_mark("BM-999") is False


def test_delete_capture_removes_single_capture():
    mark = db.create_mark(MarkCreate(label="test"))
    db.insert_capture(
        mark_id=mark.id,
        captured_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        file_path=f"{mark.id}/2024-01-01_a.jpg",
        file_hash="hash-a",
        original_filename="a.jpg",
    )
    second = db.insert_capture(
        mark_id=mark.id,
        captured_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        file_path=f"{mark.id}/2024-06-01_b.jpg",
        file_hash="hash-b",
        original_filename="b.jpg",
    )

    deleted = db.delete_capture(second.id)
    assert deleted is not None
    assert deleted.id == second.id
    assert db.get_capture(second.id) is None
    assert len(db.list_captures(mark.id)) == 1


def test_delete_capture_returns_none_for_missing():
    assert db.delete_capture(9999) is None


def test_duplicate_hash_detection():
    mark = db.create_mark(MarkCreate(label="test"))
    db.insert_capture(
        mark_id=mark.id,
        captured_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        file_path=f"{mark.id}/file.jpg",
        file_hash="same-hash",
        original_filename="a.jpg",
    )

    assert db.capture_hash_exists(mark.id, "same-hash") is True
    assert db.capture_hash_exists(mark.id, "other-hash") is False
