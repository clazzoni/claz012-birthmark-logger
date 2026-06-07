from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from app.exif_dates import read_capture_date


def _make_jpeg_with_exif(path: Path, dt: datetime) -> None:
    image = Image.new("RGB", (40, 40), color="red")
    exif = image.getexif()
    exif[36867] = dt.strftime("%Y:%m:%d %H:%M:%S")
    image.save(path, exif=exif)


def test_read_capture_date_from_exif(tmp_path):
    image_path = tmp_path / "photo.jpg"
    expected = datetime(2023, 8, 15, 9, 30, 0, tzinfo=timezone.utc)
    _make_jpeg_with_exif(image_path, expected)

    captured_at, exif_found, warning = read_capture_date(image_path)

    assert exif_found is True
    assert warning is None
    assert captured_at.year == 2023
    assert captured_at.month == 8
    assert captured_at.day == 15
    assert captured_at.hour == 9
    assert captured_at.minute == 30


def test_read_capture_date_fallback_to_mtime(tmp_path):
    image_path = tmp_path / "plain.jpg"
    Image.new("RGB", (20, 20), color="blue").save(image_path)

    captured_at, exif_found, warning = read_capture_date(image_path)

    assert exif_found is False
    assert warning is not None
    assert captured_at.tzinfo is not None
