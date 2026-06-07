import hashlib
import secrets
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image

from app import config
from app.exif_dates import read_capture_date

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}


def ensure_dirs() -> None:
    for directory in (config.IMAGES_DIR, config.THUMBS_DIR, config.TEMP_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def register_heif() -> None:
    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
    except ImportError:
        pass


def is_supported(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def compute_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_image(path: Path) -> Image.Image:
    register_heif()
    image = Image.open(path)
    image.load()
    return image


def save_as_jpeg(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with _open_image(source) as image:
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(destination, format="JPEG", quality=92)


def build_capture_filename(captured_at: datetime, file_hash: str) -> str:
    date_part = captured_at.strftime("%Y-%m-%d")
    short_hash = file_hash[:8]
    return f"{date_part}_{short_hash}.jpg"


def store_capture_file(
    source: Path,
    mark_id: str,
    captured_at: datetime,
    file_hash: str,
) -> str:
    filename = build_capture_filename(captured_at, file_hash)
    relative = Path(mark_id) / filename
    destination = config.IMAGES_DIR / relative
    if destination.exists():
        suffix = secrets.token_hex(4)
        filename = f"{captured_at.strftime('%Y-%m-%d')}_{file_hash[:8]}_{suffix}.jpg"
        relative = Path(mark_id) / filename
        destination = config.IMAGES_DIR / relative
    save_as_jpeg(source, destination)
    generate_thumbnail(destination)
    return relative.as_posix()


def generate_thumbnail(image_path: Path) -> Path:
    relative = image_path.relative_to(config.IMAGES_DIR)
    thumb_path = config.THUMBS_DIR / relative
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    with _open_image(image_path) as image:
        if image.width > config.THUMB_WIDTH:
            ratio = config.THUMB_WIDTH / image.width
            size = (config.THUMB_WIDTH, max(1, int(image.height * ratio)))
            image = image.resize(size, Image.Resampling.LANCZOS)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(thumb_path, format="JPEG", quality=85)
    return thumb_path


def thumb_relative_path(file_path: str) -> str:
    return file_path


def save_temp_upload(source_path: Path, original_filename: str) -> tuple[str, Path]:
    ensure_dirs()
    temp_id = uuid.uuid4().hex
    destination = config.TEMP_DIR / f"{temp_id}{Path(original_filename).suffix.lower()}"
    shutil.copy2(source_path, destination)
    return temp_id, destination


def get_temp_path(temp_id: str) -> Path | None:
    matches = list(config.TEMP_DIR.glob(f"{temp_id}.*"))
    return matches[0] if matches else None


def remove_temp_file(temp_id: str) -> None:
    path = get_temp_path(temp_id)
    if path and path.exists():
        path.unlink()


def clear_temp_files(temp_ids: list[str]) -> None:
    for temp_id in temp_ids:
        remove_temp_file(temp_id)


def delete_mark_files(mark_id: str) -> None:
    for base_dir in (config.IMAGES_DIR, config.THUMBS_DIR):
        mark_dir = base_dir / mark_id
        if mark_dir.exists():
            shutil.rmtree(mark_dir)


def delete_capture_files(file_path: str) -> None:
    for base_dir in (config.IMAGES_DIR, config.THUMBS_DIR):
        path = base_dir / file_path
        if path.exists():
            path.unlink()


def preview_upload(path: Path, original_filename: str) -> dict:
    captured_at, exif_found, warning = read_capture_date(path)
    return {
        "original_filename": original_filename,
        "captured_at": captured_at,
        "exif_found": exif_found,
        "warning": warning,
    }
