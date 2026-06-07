from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import db
from app.map_regions import (
    MAP_REGIONS,
    REGION_LABELS,
    detail_svg_filename,
    is_mirrored,
    is_valid_region,
    normalize_view,
    region_label,
)
from app.models import MarkCreate, MarkPlacement, MarkUpdate
from app.routes.body import overview_context
from app.storage import delete_mark_files

router = APIRouter()


def _normalize_body_region(value: str) -> str | None:
    region = value.strip()
    if not region:
        return None
    return region if is_valid_region(region) else None


def _mark_form_context(request: Request, mark, action: str) -> dict:
    legacy_body_region = None
    if mark and mark.body_region and not is_valid_region(mark.body_region):
        legacy_body_region = mark.body_region
    return {
        "mark": mark,
        "action": action,
        "regions": MAP_REGIONS,
        "region_labels": REGION_LABELS,
        "legacy_body_region": legacy_body_region,
        **overview_context(request),
    }


@router.get("/marks/new", response_class=HTMLResponse)
async def new_mark_form(request: Request):
    return request.app.state.templates.TemplateResponse(
        request,
        "mark_form.html",
        _mark_form_context(request, mark=None, action="Create"),
    )


@router.post("/marks/new")
async def create_mark(
    request: Request,
    label: str = Form(...),
    body_region: str = Form(""),
    notes: str = Form(""),
):
    data = MarkCreate(
        label=label.strip(),
        body_region=_normalize_body_region(body_region),
        notes=notes.strip() or None,
    )
    mark = db.create_mark(data)
    return RedirectResponse(url=f"/marks/{mark.id}", status_code=303)


@router.get("/marks/{mark_id}/edit", response_class=HTMLResponse)
async def edit_mark_form(request: Request, mark_id: str):
    mark = db.get_mark(mark_id)
    if mark is None:
        return RedirectResponse(url="/", status_code=303)
    return request.app.state.templates.TemplateResponse(
        request,
        "mark_form.html",
        _mark_form_context(request, mark=mark, action="Save"),
    )


@router.post("/marks/{mark_id}/edit")
async def update_mark(
    request: Request,
    mark_id: str,
    label: str = Form(...),
    body_region: str = Form(""),
    notes: str = Form(""),
):
    data = MarkUpdate(
        label=label.strip(),
        body_region=_normalize_body_region(body_region),
        notes=notes.strip() or None,
    )
    mark = db.update_mark(mark_id, data)
    if mark is None:
        return RedirectResponse(url="/", status_code=303)
    return RedirectResponse(url=f"/marks/{mark_id}", status_code=303)


@router.get("/marks/{mark_id}/delete", response_class=HTMLResponse)
async def delete_mark_form(request: Request, mark_id: str):
    mark = db.get_mark(mark_id)
    if mark is None:
        return RedirectResponse(url="/", status_code=303)
    return request.app.state.templates.TemplateResponse(
        request, "mark_delete.html", {"mark": mark}
    )


@router.post("/marks/{mark_id}/delete")
async def confirm_delete_mark(mark_id: str):
    if not db.get_mark(mark_id):
        return RedirectResponse(url="/", status_code=303)
    db.delete_mark(mark_id)
    delete_mark_files(mark_id)
    return RedirectResponse(url="/", status_code=303)


@router.get("/marks/{mark_id}/place", response_class=HTMLResponse)
async def place_mark_form(
    request: Request,
    mark_id: str,
    region: str | None = Query(None),
    view: str | None = Query(None),
):
    mark = db.get_mark(mark_id)
    if mark is None:
        return RedirectResponse(url="/", status_code=303)

    selected_region = region or mark.map_region
    if selected_region and not is_valid_region(selected_region):
        selected_region = None

    svg_file = detail_svg_filename(selected_region, view) if selected_region else None
    same_region = bool(
        selected_region and mark.map_region and selected_region == mark.map_region
    )
    placement_preview: list[dict] = []
    if same_region and mark.map_x is not None and mark.map_y is not None:
        placement_preview = [
            {
                "id": mark.id,
                "label": mark.label,
                "map_x": mark.map_x,
                "map_y": mark.map_y,
            }
        ]
    return request.app.state.templates.TemplateResponse(
        request,
        "mark_place.html",
        {
            "mark": mark,
            "regions": MAP_REGIONS,
            "region_labels": REGION_LABELS,
            "selected_region": selected_region,
            "selected_region_label": (
                region_label(selected_region) if selected_region else None
            ),
            "svg_file": svg_file,
            "mirrored": is_mirrored(selected_region) if selected_region else False,
            "placement_preview": placement_preview,
            "same_region": same_region,
        },
    )


@router.post("/marks/{mark_id}/place")
async def save_mark_placement(
    mark_id: str,
    map_region: str = Form(...),
    map_x: float = Form(...),
    map_y: float = Form(...),
):
    mark = db.get_mark(mark_id)
    if mark is None:
        return RedirectResponse(url="/", status_code=303)

    if not is_valid_region(map_region):
        return RedirectResponse(url=f"/marks/{mark_id}/place", status_code=303)

    try:
        placement = MarkPlacement(
            map_region=map_region, map_x=map_x, map_y=map_y
        )
    except Exception:
        return RedirectResponse(url=f"/marks/{mark_id}/place", status_code=303)

    updated = db.update_mark_placement(mark_id, placement)
    if updated is None:
        return RedirectResponse(url=f"/marks/{mark_id}/place", status_code=303)
    return RedirectResponse(url=f"/marks/{mark_id}", status_code=303)


@router.post("/marks/{mark_id}/place/clear")
async def clear_mark_placement(mark_id: str):
    if db.clear_mark_placement(mark_id) is None:
        return RedirectResponse(url="/", status_code=303)
    return RedirectResponse(url=f"/marks/{mark_id}", status_code=303)


@router.get("/marks/{mark_id}", response_class=HTMLResponse)
async def mark_detail(request: Request, mark_id: str):
    mark = db.get_mark(mark_id)
    if mark is None:
        return RedirectResponse(url="/", status_code=303)
    captures = db.list_captures(mark_id)
    return request.app.state.templates.TemplateResponse(
        request,
        "mark_detail.html",
        {
            "mark": mark,
            "captures": captures,
            "map_region_label": (
                region_label(mark.map_region) if mark.map_region else None
            ),
            "body_region_label": (
                region_label(mark.body_region)
                if mark.body_region and is_valid_region(mark.body_region)
                else mark.body_region
            ),
        },
    )
