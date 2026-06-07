import json
from pathlib import Path

from app import config

SETTINGS_PATH = config.DATA_DIR / "settings.json"


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_settings(settings: dict) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def get_import_folder() -> str:
    return str(load_settings().get("import_folder", "") or "")


def set_import_folder(path: str) -> None:
    settings = load_settings()
    settings["import_folder"] = path.strip()
    save_settings(settings)
