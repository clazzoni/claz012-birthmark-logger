import io
import zipfile
from pathlib import Path

from PIL import Image

from app.import_sources import (
    extract_zip_images,
    is_allowed_import_path,
    iter_supported_files,
    previews_from_sources,
    resolve_import_folder,
)
from app.settings_store import set_import_folder


def _jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buffer, format="JPEG")
    return buffer.getvalue()


def test_iter_supported_files(tmp_path):
    (tmp_path / "photo.jpg").write_bytes(_jpeg_bytes())
    (tmp_path / "notes.txt").write_text("skip", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "other.heic").write_bytes(_jpeg_bytes())

    names = [name for _, name in iter_supported_files(tmp_path)]
    assert names == ["nested/other.heic", "photo.jpg"]


def test_extract_zip_images(tmp_path):
    zip_path = tmp_path / "photos.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("a.jpg", _jpeg_bytes())
        archive.writestr("ignore.txt", "nope")

    sources, temp_dir = extract_zip_images(zip_path)
    assert temp_dir is not None
    assert len(sources) == 1
    assert sources[0][1] == "a.jpg"

    previews, errors = previews_from_sources(sources)
    assert not errors
    assert len(previews) == 1
    assert previews[0]["original_filename"] == "a.jpg"


def test_set_import_folder_allows_custom_path(tmp_path):
    folder = tmp_path / "imports"
    folder.mkdir()
    set_import_folder(str(folder))
    assert resolve_import_folder("") == folder.resolve()
    assert is_allowed_import_path(folder)
