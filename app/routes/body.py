import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import db
from app.map_regions import (
    MAP_REGIONS,
    OVERVIEW_BACK_REGIONS,
    OVERVIEW_FRONT_REGIONS,
    REGION_LABELS,
    detail_svg_filename,
    is_mirrored,
    is_valid_region,
    region_label,
)
from app.overview_hotspots import FIGURE_BBOX, hotspots_for_side

router = APIRouter()


def _hotspot_payload(side: str, regions: tuple[str, ...], region_counts: dict[str, int]):
    hotspots = hotspots_for_side(side)
    return [
        {
            "region": region,
            "label": REGION_LABELS[region],
            "count": region_counts.get(region, 0),
            "left": hotspots[region][0],
            "top": hotspots[region][1],
            "width": hotspots[region][2],
            "height": hotspots[region][3],
        }
        for region in regions
    ]


def _hotspots_json(side: str) -> str:
    hotspots = hotspots_for_side(side)
    payload = {
        region: {
            "left": rect[0],
            "top": rect[1],
            "width": rect[2],
            "height": rect[3],
        }
        for region, rect in hotspots.items()
    }
    return json.dumps(payload)


def overview_context(request: Request) -> dict:
    region_counts = db.count_marks_by_region()
    debug = request.query_params.get("debug") == "1"
    return {
        "front_hotspots": _hotspot_payload(
            "front", OVERVIEW_FRONT_REGIONS, region_counts
        ),
        "back_hotspots": _hotspot_payload(
            "back", OVERVIEW_BACK_REGIONS, region_counts
        ),
        "region_counts": region_counts,
        "all_regions": [
            {
                "id": region,
                "label": REGION_LABELS[region],
                "count": region_counts.get(region, 0),
            }
            for region in MAP_REGIONS
        ],
        "debug": debug,
    }


@router.get("/body", response_class=HTMLResponse)
async def body_overview(request: Request):
    query = request.url.query
    target = f"/?{query}" if query else "/"
    return RedirectResponse(url=target, status_code=307)


@router.get("/body/calibrate", response_class=HTMLResponse)
async def body_calibrate(request: Request):
    return request.app.state.templates.TemplateResponse(
        request,
        "body_calibrate.html",
        {
            "front_hotspots_json": _hotspots_json("front"),
            "back_hotspots_json": _hotspots_json("back"),
            "figure_bbox_json": json.dumps(FIGURE_BBOX),
        },
    )


@router.get("/body/{region}", response_class=HTMLResponse)
async def body_region(request: Request, region: str):
    if not is_valid_region(region):
        return RedirectResponse(url="/", status_code=303)

    marks = db.list_marks_by_region(region)
    placed_marks = [
        {
            "id": m.id,
            "label": m.label,
            "map_x": m.map_x,
            "map_y": m.map_y,
            "url": f"/marks/{m.id}",
        }
        for m in marks
        if m.map_x is not None and m.map_y is not None
    ]
    unplaced_marks = db.list_marks(unplaced_only=True)

    svg_file = detail_svg_filename(region)
    return request.app.state.templates.TemplateResponse(
        request,
        "body_region.html",
        {
            "region": region,
            "region_label": region_label(region),
            "svg_file": svg_file,
            "mirrored": is_mirrored(region),
            "placed_marks": placed_marks,
            "unplaced_marks": unplaced_marks,
        },
    )
