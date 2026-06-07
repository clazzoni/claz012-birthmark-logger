from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

EXIF_DATETIME_ORIGINAL = 36867
EXIF_DATETIME = 306


def _parse_exif_datetime(value: str) -> datetime | None:
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def read_capture_date(path: Path) -> tuple[datetime, bool, str | None]:
    """Return (captured_at, exif_found, warning)."""
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            if exif:
                for tag in (EXIF_DATETIME_ORIGINAL, EXIF_DATETIME):
                    raw = exif.get(tag)
                    if raw:
                        parsed = _parse_exif_datetime(str(raw))
                        if parsed:
                            return parsed, True, None
    except Exception:
        pass

    mtime = path.stat().st_mtime
    fallback = datetime.fromtimestamp(mtime, tz=timezone.utc)
    return (
        fallback,
        False,
        "No EXIF date found; using file modification time.",
    )
