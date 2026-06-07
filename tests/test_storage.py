from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from app.storage import (
    build_capture_filename,
    compute_file_hash,
    delete_capture_files,
    delete_mark_files,
    is_supported,
    store_capture_file,
)


def test_is_supported_extensions():
    assert is_supported("photo.jpg") is True
    assert is_supported("photo.HEIC") is True
    assert is_supported("photo.gif") is False


def test_compute_file_hash_stable(tmp_path):
    path = tmp_path / "sample.jpg"
    Image.new("RGB", (10, 10), color="green").save(path)

    first = compute_file_hash(path)
    second = compute_file_hash(path)

    assert first == second
    assert len(first) == 64


def test_build_capture_filename():
    captured_at = datetime(2025, 6, 7, 14, 0, tzinfo=timezone.utc)
    filename = build_capture_filename(captured_at, "abcdef1234567890")

    assert filename == "2025-06-07_abcdef12.jpg"


def test_store_capture_file_creates_jpeg_and_thumb(isolated_data):
    source = isolated_data / "source.png"
    Image.new("RGB", (120, 80), color="orange").save(source)

    captured_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    file_hash = compute_file_hash(source)
    relative = store_capture_file(source, "BM-001", captured_at, file_hash)

    from app.config import IMAGES_DIR, THUMBS_DIR

    image_path = IMAGES_DIR / relative
    thumb_path = THUMBS_DIR / relative

    assert image_path.exists()
    assert thumb_path.exists()
    assert image_path.suffix == ".jpg"


def test_delete_mark_files_removes_image_and_thumb_dirs(isolated_data):
    source = isolated_data / "source.png"
    Image.new("RGB", (120, 80), color="orange").save(source)

    captured_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    file_hash = compute_file_hash(source)
    store_capture_file(source, "BM-001", captured_at, file_hash)

    from app.config import IMAGES_DIR, THUMBS_DIR

    assert (IMAGES_DIR / "BM-001").exists()
    assert (THUMBS_DIR / "BM-001").exists()

    delete_mark_files("BM-001")

    assert not (IMAGES_DIR / "BM-001").exists()
    assert not (THUMBS_DIR / "BM-001").exists()


def test_delete_capture_files_removes_single_files(isolated_data):
    source = isolated_data / "source.png"
    Image.new("RGB", (120, 80), color="orange").save(source)

    captured_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
    file_hash = compute_file_hash(source)
    relative = store_capture_file(source, "BM-001", captured_at, file_hash)

    from app.config import IMAGES_DIR, THUMBS_DIR

    assert (IMAGES_DIR / relative).exists()
    assert (THUMBS_DIR / relative).exists()

    delete_capture_files(relative)

    assert not (IMAGES_DIR / relative).exists()
    assert not (THUMBS_DIR / relative).exists()
    assert (IMAGES_DIR / "BM-001").exists()
