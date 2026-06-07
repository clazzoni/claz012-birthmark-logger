# Detail region zoom crops — design spec

**Date:** 2026-06-07  
**Status:** Draft — awaiting user approval

## Problem

The body map overview uses detailed Wikimedia silhouettes (`overview_front.svg`, `overview_back.svg`). Detail region pages (e.g. `/body/left_hand`) still show simplistic schematic SVGs (`detail_hand.svg`, etc.) that do not match the overview style or anatomy.

## Decision summary

| Choice | Decision |
|--------|----------|
| Detail image strategy | **Option A:** Zoom crop from the same overview SVGs |
| Existing pin placements | **Option A:** Users reposition manually after upgrade |

## Goals

- Detail pages show a zoomed crop of the same silhouette used on the overview.
- Visual consistency between overview hotspots and detail placement views.
- Minimal change to pin coordinate model (still 0–1 normalized within the displayed image).
- Reuse calibrated `FIGURE_REGIONS` from `app/overview_hotspots.py` as crop boundaries.

## Non-goals

- Auto-migrating old schematic pin coordinates.
- Live viewport / pan-zoom (Option B).
- Third-party per-region illustration assets (Option C).
- Changing SQLite schema.

## Architecture

### Source of truth

- **Overview SVGs:** `web/static/body/overview_front.svg`, `overview_back.svg`
- **Region bounds:** `FIGURE_REGIONS` in `app/overview_hotspots.py` (figure-relative fractions)
- **Region → side mapping:** front regions use front SVG; back regions use back SVG

### Crop generation

New script: `scripts/generate_detail_crops.py`

1. Load overview SVG for the region's side (front/back).
2. Read overview `viewBox` and `FIGURE_BBOX` for that side.
3. Convert `FIGURE_REGIONS[side][region]` to SVG user-space crop rect.
4. Apply optional padding (default 8–12% of crop size) so limbs are not clipped at edges.
5. Emit one cropped SVG per **canonical** region file:
   - `detail_face.svg`, `detail_front_torso.svg`, `detail_back.svg`
   - `detail_arm.svg` (left arm crop; right arm mirrors via existing CSS)
   - `detail_leg.svg`, `detail_hand.svg`
6. Preserve fill/stroke palette (`#d9d2c7`, `#8a8078`, `#f8f5f0` background).

Right-side regions (`right_arm`, `right_leg`, `right_hand`) continue to reference the same file as their left counterpart; `MIRRORED_REGIONS` + `.mirrored` CSS unchanged.

### Region → source mapping

| Region | Source SVG | Output file |
|--------|------------|-------------|
| face | front | detail_face.svg |
| front_torso | front | detail_front_torso.svg |
| back | back | detail_back.svg |
| left_arm / right_arm | front or back | detail_arm.svg |
| left_leg / right_leg | front or back | detail_leg.svg |
| left_hand / right_hand | front | detail_hand.svg |

Arms/legs on the back overview use the back SVG crop. Hands are front-only.

### Runtime changes

- `DETAIL_SVG_FILES` in `app/map_regions.py`: add helper or dict entry for which **side** each region crops from (if not inferrable from `OVERVIEW_*_REGIONS`).
- No changes to `body-map.js` pin logic.
- No changes to `body_region.html` / `mark_place.html` structure.

### Existing placements

After deploy, marks with `map_x` / `map_y` may point to wrong locations on the new crops. Per user choice:

- Show a one-time note on region pages when marks exist: *"Detail images were updated — you may need to reposition pins."*
- Users clear and re-place via existing **Place on map** / **Clear map placement** flows.
- No DB migration.

## UI

- Detail images use same max-width / centering as overview (`region-svg-img` already full width of card).
- Cropped SVGs are taller/wider per region aspect ratio; container stays centered.

## Testing

- Script runs without error; 6 detail SVG files regenerated.
- pytest: region pages return 200 and reference correct `detail_*.svg`.
- Manual: open `/body/left_hand`, confirm Wikimedia-style hand (not schematic).
- Manual: place pin, save, reload — pin stays in same relative position.

## Regeneration workflow

When `FIGURE_REGIONS` is recalibrated on the overview:

```bash
python scripts/generate_detail_crops.py
```

Detail crops stay aligned with overview hotspots.

## Risks

| Risk | Mitigation |
|------|------------|
| Tight crops clip fingers/toes | Padding parameter in generator |
| Back `FIGURE_REGIONS` values > 1.0 | Clamp to figure bounds when computing crop |
| Old pins misleading | Short notice on region page |

## Open questions

None — user confirmed manual reposition.
