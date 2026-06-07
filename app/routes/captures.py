import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app import db
from app.storage import (
    clear_temp_files,
    compute_file_hash,
    delete_capture_files,
    ensure_dirs,
    get_temp_path,
    is_supported,
    preview_upload,
    save_temp_upload,
    store_capture_file,
)

router = APIRouter()


def _parse_form_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/marks/{mark_id}/import", response_class=HTMLResponse)
async def import_form(request: Request, mark_id: str):
    mark = db.get_mark(mark_id)
    if mark is None:
        return RedirectResponse(url="/", status_code=303)
    return request.app.state.templates.TemplateResponse(
        request, "import.html", {"mark": mark, "previews": None}
    )


@router.post("/marks/{mark_id}/import", response_class=HTMLResponse)
async def import_preview(
    request: Request,
    mark_id: str,
    files: list[UploadFile] = File(...),
):
    mark = db.get_mark(mark_id)
    if mark is None:
        return RedirectResponse(url="/", status_code=303)

    ensure_dirs()
    previews: list[dict] = []
    errors: list[str] = []

    for upload in files:
        if not upload.filename or not is_supported(upload.filename):
            errors.append(f"Skipped unsupported file: {upload.filename or 'unknown'}")
            continue

        suffix = upload.filename.rsplit(".", 1)[-1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
            content = await upload.read()
            tmp.write(content)
            tmp_path = tmp.name

        path = Path(tmp_path)
        try:
            temp_id, stored = save_temp_upload(path, upload.filename)
            info = preview_upload(stored, upload.filename)
            previews.append(
                {
                    "temp_id": temp_id,
                    "original_filename": info["original_filename"],
                    "captured_at": info["captured_at"],
                    "exif_found": info["exif_found"],
                    "warning": info["warning"],
                }
            )
        finally:
            path.unlink(missing_ok=True)

    return request.app.state.templates.TemplateResponse(
        request,
        "import.html",
        {"mark": mark, "previews": previews, "errors": errors},
    )


@router.post("/marks/{mark_id}/import/confirm")
async def import_confirm(
    request: Request,
    mark_id: str,
):
    mark = db.get_mark(mark_id)
    if mark is None:
        return RedirectResponse(url="/", status_code=303)

    form = await request.form()
    temp_ids = form.getlist("temp_id")
    dates = form.getlist("captured_at")
    filenames = form.getlist("original_filename")

    imported = 0
    skipped_duplicates: list[str] = []
    errors: list[str] = []
    processed_temp_ids: list[str] = []

    for temp_id, date_str, original_filename in zip(temp_ids, dates, filenames):
        processed_temp_ids.append(temp_id)
        temp_path = get_temp_path(temp_id)
        if temp_path is None:
            errors.append(f"Missing temp file for {original_filename}")
            continue

        try:
            captured_at = _parse_form_datetime(date_str)
            file_hash = compute_file_hash(temp_path)

            if db.capture_hash_exists(mark_id, file_hash):
                skipped_duplicates.append(original_filename)
                continue

            relative_path = store_capture_file(
                temp_path, mark_id, captured_at, file_hash
            )
            db.insert_capture(
                mark_id=mark_id,
                captured_at=captured_at,
                file_path=relative_path,
                file_hash=file_hash,
                original_filename=original_filename,
            )
            imported += 1
        except Exception as exc:
            errors.append(f"{original_filename}: {exc}")

    clear_temp_files(processed_temp_ids)

    detail_url = f"/marks/{mark_id}"
    if imported:
        return RedirectResponse(url=detail_url, status_code=303)

    mark = db.get_mark(mark_id)
    return request.app.state.templates.TemplateResponse(
        request,
        "import.html",
        {
            "mark": mark,
            "previews": None,
            "errors": errors or ["No photos were imported."],
            "skipped_duplicates": skipped_duplicates,
        },
    )


@router.get(
    "/marks/{mark_id}/captures/{capture_id}/delete",
    response_class=HTMLResponse,
)
async def delete_capture_form(
    request: Request, mark_id: str, capture_id: int
):
    mark = db.get_mark(mark_id)
    capture = db.get_capture(capture_id)
    if mark is None or capture is None or capture.mark_id != mark_id:
        return RedirectResponse(url="/", status_code=303)
    return request.app.state.templates.TemplateResponse(
        request,
        "capture_delete.html",
        {"mark": mark, "capture": capture},
    )


@router.post("/marks/{mark_id}/captures/{capture_id}/delete")
async def confirm_delete_capture(mark_id: str, capture_id: int):
    capture = db.get_capture(capture_id)
    if capture is None or capture.mark_id != mark_id:
        return RedirectResponse(url="/", status_code=303)
    db.delete_capture(capture_id)
    delete_capture_files(capture.file_path)
    return RedirectResponse(url=f"/marks/{mark_id}", status_code=303)
