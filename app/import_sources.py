from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from app import config
from app.settings_store import get_import_folder, load_settings
from app.storage import is_supported, preview_upload, save_temp_upload

ZIP_EXTENSIONS = {".zip"}


def default_allowed_roots() -> list[Path]:
    roots: list[Path] = [Path.home().resolve(), config.DATA_DIR.resolve()]
    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        roots.append(downloads.resolve())
    return roots


def allowed_import_roots() -> list[Path]:
    roots = default_allowed_roots()
    settings = load_settings()
    for key in ("import_folder",):
        value = settings.get(key, "")
        if value:
            path = Path(value).expanduser()
            if path.is_dir():
                roots.append(path.resolve())
    for value in settings.get("import_roots", []):
        path = Path(str(value)).expanduser()
        if path.is_dir():
            roots.append(path.resolve())
    unique: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root not in seen:
            seen.add(root)
            unique.append(root)
    return unique


def is_allowed_import_path(folder: Path) -> bool:
    target = folder.expanduser().resolve()
    if not target.is_dir():
        return False
    for root in allowed_import_roots():
        if target == root or root in target.parents:
            return True
    return False


def resolve_import_folder(path_str: str | None) -> Path | None:
    candidate = (path_str or "").strip() or get_import_folder().strip()
    if not candidate:
        return None
    folder = Path(candidate).expanduser()
    if not is_allowed_import_path(folder):
        return None
    return folder.resolve()


def iter_supported_files(directory: Path) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        if not is_supported(path.name):
            continue
        display_name = path.relative_to(directory).as_posix()
        found.append((path, display_name))
    return found


def extract_zip_images(zip_path: Path) -> tuple[list[tuple[Path, str]], Path | None]:
    """Extract supported images from a ZIP into a temp directory."""
    config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="import_zip_", dir=config.TEMP_DIR))
    sources: list[tuple[Path, str]] = []
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                if not is_supported(name):
                    continue
                extracted = archive.extract(info, temp_dir)
                extracted_path = Path(extracted)
                rel = Path(info.filename).as_posix()
                sources.append((extracted_path, rel))
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    if not sources:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return [], None
    return sources, temp_dir


def preview_from_path(source_path: Path, original_filename: str) -> dict:
    temp_id, stored = save_temp_upload(source_path, original_filename)
    info = preview_upload(stored, original_filename)
    return {
        "temp_id": temp_id,
        "original_filename": info["original_filename"],
        "captured_at": info["captured_at"],
        "exif_found": info["exif_found"],
        "warning": info["warning"],
    }


def previews_from_sources(
    sources: list[tuple[Path, str]],
) -> tuple[list[dict], list[str]]:
    previews: list[dict] = []
    errors: list[str] = []
    for source_path, original_filename in sources:
        if not is_supported(original_filename):
            errors.append(f"Skipped unsupported file: {original_filename}")
            continue
        try:
            previews.append(preview_from_path(source_path, original_filename))
        except Exception as exc:
            errors.append(f"{original_filename}: {exc}")
    return previews, errors


def is_zip_filename(filename: str) -> bool:
    return Path(filename).suffix.lower() in ZIP_EXTENSIONS
