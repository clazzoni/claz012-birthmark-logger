import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app import db
from app.import_sources import (
    extract_zip_images,
    is_zip_filename,
    iter_supported_files,
    previews_from_sources,
    resolve_import_folder,
)
from app.settings_store import get_import_folder, set_import_folder
from app.storage import (
    clear_temp_files,
    compute_file_hash,
    delete_capture_files,
    ensure_dirs,
    get_temp_path,
    is_supported,
    store_capture_file,
)

router = APIRouter()


def _parse_form_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _import_template_context(mark, **extra) -> dict:
    return {
        "mark": mark,
        "previews": None,
        "import_folder": get_import_folder(),
        **extra,
    }


async def _sources_from_upload(
    upload: UploadFile,
) -> tuple[list[tuple[Path, str]], list[str], list[Path]]:
    if not upload.filename:
        return [], ["Skipped file with no name"], []

    filename = upload.filename.replace("\\", "/").split("/")[-1]

    if is_zip_filename(filename):
        suffix = ".zip"
    elif is_supported(filename):
        suffix = Path(filename).suffix.lower()
    else:
        return [], [f"Skipped unsupported file: {filename}"], []

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await upload.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    sources: list[tuple[Path, str]] = []
    errors: list[str] = []
    cleanup_paths: list[Path] = [tmp_path]

    try:
        if is_zip_filename(filename):
            try:
                sources, zip_temp_dir = extract_zip_images(tmp_path)
                if zip_temp_dir is not None:
                    cleanup_paths.append(zip_temp_dir)
                if not sources:
                    errors.append(f"No supported images found in ZIP: {filename}")
            except Exception as exc:
                errors.append(f"{filename}: {exc}")
        else:
            sources.append((tmp_path, filename))
    except Exception:
        for path in cleanup_paths:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink(missing_ok=True)
        raise

    return sources, errors, cleanup_paths


async def _previews_from_uploads(
    uploads: list[UploadFile],
) -> tuple[list[dict], list[str]]:
    all_sources: list[tuple[Path, str]] = []
    errors: list[str] = []
    cleanup_paths: list[Path] = []

    for upload in uploads:
        sources, upload_errors, paths_to_cleanup = await _sources_from_upload(upload)
        all_sources.extend(sources)
        errors.extend(upload_errors)
        cleanup_paths.extend(paths_to_cleanup)

    try:
        previews, preview_errors = previews_from_sources(all_sources)
        errors.extend(preview_errors)
        return previews, errors
    finally:
        for path in cleanup_paths:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink(missing_ok=True)


@router.get("/marks/{mark_id}/import", response_class=HTMLResponse)
async def import_form(request: Request, mark_id: str):
    mark = db.get_mark(mark_id)
    if mark is None:
        return RedirectResponse(url="/", status_code=303)
    return request.app.state.templates.TemplateResponse(
        request,
        "import.html",
        _import_template_context(mark),
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
    previews, errors = await _previews_from_uploads(files)

    return request.app.state.templates.TemplateResponse(
        request,
        "import.html",
        _import_template_context(mark, previews=previews or None, errors=errors),
    )


@router.post("/marks/{mark_id}/import/from-folder", response_class=HTMLResponse)
async def import_from_folder(
    request: Request,
    mark_id: str,
    folder_path: str = Form(""),
):
    mark = db.get_mark(mark_id)
    if mark is None:
        return RedirectResponse(url="/", status_code=303)

    ensure_dirs()
    folder = resolve_import_folder(folder_path)
    errors: list[str] = []

    if folder is None:
        errors.append(
            "Folder not found or not allowed. Use a path under your home folder, "
            "Downloads, data/, or save a default folder in Settings."
        )
        return request.app.state.templates.TemplateResponse(
            request,
            "import.html",
            _import_template_context(
                mark,
                errors=errors,
                import_folder=folder_path.strip() or get_import_folder(),
            ),
        )

    if folder_path.strip():
        set_import_folder(folder_path.strip())

    sources = iter_supported_files(folder)
    if not sources:
        errors.append(f"No supported images found in {folder}")

    previews, preview_errors = previews_from_sources(sources)
    errors.extend(preview_errors)

    return request.app.state.templates.TemplateResponse(
        request,
        "import.html",
        _import_template_context(
            mark,
            previews=previews or None,
            errors=errors,
            import_folder=str(folder),
        ),
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
        _import_template_context(
            mark,
            errors=errors or ["No photos were imported."],
            skipped_duplicates=skipped_duplicates,
        ),
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
