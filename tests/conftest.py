import pytest

from app import config, db


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    images_dir = data_dir / "images"
    thumbs_dir = data_dir / "thumbs"
    temp_dir = data_dir / "temp"
    db_path = data_dir / "bodymap.db"

    for directory in (images_dir, thumbs_dir, temp_dir):
        directory.mkdir(parents=True)

    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "IMAGES_DIR", images_dir)
    monkeypatch.setattr(config, "THUMBS_DIR", thumbs_dir)
    monkeypatch.setattr(config, "TEMP_DIR", temp_dir)

    db.init_db()
    yield data_dir
