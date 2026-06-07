from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "bodymap.db"
IMAGES_DIR = DATA_DIR / "images"
THUMBS_DIR = DATA_DIR / "thumbs"
TEMP_DIR = DATA_DIR / "temp"
WEB_DIR = ROOT_DIR / "web"

HOST = "127.0.0.1"
PORT = 8000

THUMB_WIDTH = 300
