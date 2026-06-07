from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import db

router = APIRouter()


@router.get("/marks/{mark_id}/compare", response_class=HTMLResponse)
async def compare_view(
    request: Request,
    mark_id: str,
    left: int | None = Query(None),
    right: int | None = Query(None),
):
    mark = db.get_mark(mark_id)
    if mark is None:
        return RedirectResponse(url="/", status_code=303)

    captures = db.list_captures(mark_id)
    left_capture = db.get_capture(left) if left else None
    right_capture = db.get_capture(right) if right else None

    if left_capture and left_capture.mark_id != mark_id:
        left_capture = None
    if right_capture and right_capture.mark_id != mark_id:
        right_capture = None

    return request.app.state.templates.TemplateResponse(
        request,
        "compare.html",
        {
            "mark": mark,
            "captures": captures,
            "left_capture": left_capture,
            "right_capture": right_capture,
        },
    )
