import importlib
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import db

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(isolated_data):
    import app.db as db_module
    import app.main as main_module
    import app.routes.body as body_module
    import app.routes.captures as captures_module
    import app.routes.marks as marks_module

    importlib.reload(db_module)
    importlib.reload(body_module)
    importlib.reload(captures_module)
    importlib.reload(marks_module)
    importlib.reload(main_module)
    return TestClient(main_module.app)


def _jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (30, 30), color="purple").save(buffer, format="JPEG")
    return buffer.getvalue()


def test_home_and_create_mark_flow(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Birth marks" in response.text

    new_form = client.get("/marks/new")
    assert new_form.status_code == 200
    assert 'name="body_region"' in new_form.text
    assert "overview_front.svg" in new_form.text
    assert "Front torso" in new_form.text
    assert "mark-form.js" in new_form.text

    response = client.post(
        "/marks/new",
        data={"label": "left upper back", "body_region": "back", "notes": "monthly check"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/marks/BM-001"

    response = client.get("/marks/BM-001")
    assert response.status_code == 200
    assert "left upper back" in response.text


def test_compare_page_with_two_captures(client):
    client.post(
        "/marks/new",
        data={"label": "test mark", "body_region": "", "notes": ""},
        follow_redirects=True,
    )

    db.insert_capture(
        mark_id="BM-001",
        captured_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        file_path="BM-001/2024-01-01_aaaa.jpg",
        file_hash="hash-a",
        original_filename="jan.jpg",
    )
    db.insert_capture(
        mark_id="BM-001",
        captured_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        file_path="BM-001/2024-06-01_bbbb.jpg",
        file_hash="hash-b",
        original_filename="jun.jpg",
    )

    captures = db.list_captures("BM-001")
    compare = client.get(
        f"/marks/BM-001/compare?left={captures[0].id}&right={captures[1].id}"
    )
    assert compare.status_code == 200
    assert "Compare captures" in compare.text


def test_delete_mark_flow(client):
    client.post(
        "/marks/new",
        data={"label": "delete me", "body_region": "", "notes": ""},
        follow_redirects=True,
    )

    confirm_page = client.get("/marks/BM-001/delete")
    assert confirm_page.status_code == 200
    assert "Delete mark" in confirm_page.text
    assert "delete me" in confirm_page.text

    response = client.post("/marks/BM-001/delete", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    assert db.get_mark("BM-001") is None
    assert client.get("/marks/BM-001", follow_redirects=False).status_code == 303


def test_delete_capture_flow(client):
    client.post(
        "/marks/new",
        data={"label": "photo mark", "body_region": "", "notes": ""},
        follow_redirects=True,
    )
    capture = db.insert_capture(
        mark_id="BM-001",
        captured_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        file_path="BM-001/2024-01-01_aaaa.jpg",
        file_hash="hash-a",
        original_filename="jan.jpg",
    )

    confirm_page = client.get(f"/marks/BM-001/captures/{capture.id}/delete")
    assert confirm_page.status_code == 200
    assert "Delete photo" in confirm_page.text

    response = client.post(
        f"/marks/BM-001/captures/{capture.id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/marks/BM-001"
    assert db.get_capture(capture.id) is None


def test_body_map_pages(client):
    home = client.get("/")
    assert home.status_code == 200
    assert "Birth marks" in home.text
    assert "overview_front.svg" in home.text
    assert "overview_back.svg" in home.text
    assert "Wikimedia Commons" in home.text
    assert "/body/calibrate" in home.text

    legacy = client.get("/body", follow_redirects=False)
    assert legacy.status_code == 307
    assert legacy.headers["location"] == "/"

    calibrate = client.get("/body/calibrate")
    assert calibrate.status_code == 200
    assert "Calibrate body regions" in calibrate.text
    assert "body-calibrate.js" in calibrate.text

    client.post(
        "/marks/new",
        data={"label": "mapped", "body_region": "", "notes": ""},
        follow_redirects=True,
    )
    response = client.post(
        "/marks/BM-001/place",
        data={"map_region": "face", "map_x": 0.5, "map_y": 0.4},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/marks/BM-001"

    move_form = client.get("/marks/BM-001/place")
    assert move_form.status_code == 200
    assert "Move pin" in move_form.text
    assert "detail_face.svg" in move_form.text
    assert "Save new position" in move_form.text

    response = client.post(
        "/marks/BM-001/place",
        data={"map_region": "face", "map_x": 0.25, "map_y": 0.75},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/marks/BM-001"
    moved = db.get_mark("BM-001")
    assert moved.map_x == 0.25
    assert moved.map_y == 0.75

    region_page = client.get("/body/face")
    assert region_page.status_code == 200
    assert "mapped" in region_page.text
    assert "reposition pins" in region_page.text

    hand_page = client.get("/body/left_hand")
    assert hand_page.status_code == 200
    hand_svg = (ROOT / "web/static/body/detail_hand.svg").read_text(encoding="utf-8")
    assert "viewBox=" in hand_svg
    assert 'viewBox="0 0 160 200"' not in hand_svg


def test_import_preview(client):
    client.post(
        "/marks/new",
        data={"label": "import test", "body_region": "", "notes": ""},
        follow_redirects=True,
    )

    files = [
        ("files", ("jan.jpg", _jpeg_bytes(), "image/jpeg")),
    ]
    preview = client.post("/marks/BM-001/import", files=files)
    assert preview.status_code == 200
    assert "Review capture dates" in preview.text
    assert "jan.jpg" in preview.text
