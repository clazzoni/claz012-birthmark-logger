from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import db
from app.config import DATA_DIR, HOST, IMAGES_DIR, PORT, THUMBS_DIR, WEB_DIR
from app.map_regions import REGION_LABELS
from app.routes import body, captures, compare, marks
from app.routes.body import overview_context
from app.settings_store import get_import_folder, set_import_folder
from app.storage import ensure_dirs, register_heif

register_heif()
ensure_dirs()
db.init_db()

app = FastAPI(title="Birth Mark Tracker")
templates = Jinja2Templates(directory=WEB_DIR / "templates")
templates.env.globals["region_labels"] = REGION_LABELS
app.state.templates = templates

app.include_router(marks.router)
app.include_router(captures.router)
app.include_router(compare.router)
app.include_router(body.router)

app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
app.mount("/thumbs", StaticFiles(directory=THUMBS_DIR), name="thumbs")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, q: str = "", unplaced: str = ""):
    search = q.strip() or None
    unplaced_only = unplaced.lower() in ("1", "true", "yes")
    mark_list = db.list_marks(search=search, unplaced_only=unplaced_only)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "marks": mark_list,
            "search": q,
            "unplaced_only": unplaced_only,
            **overview_context(request),
        },
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, saved: str = ""):
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "data_dir": DATA_DIR.resolve(),
            "import_folder": get_import_folder(),
            "saved": saved.lower() in ("1", "true", "yes"),
        },
    )


@app.post("/settings", response_class=HTMLResponse)
async def save_settings(request: Request, import_folder: str = Form("")):
    set_import_folder(import_folder)
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "data_dir": DATA_DIR.resolve(),
            "import_folder": get_import_folder(),
            "saved": True,
        },
    )


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)


if __name__ == "__main__":
    run()
