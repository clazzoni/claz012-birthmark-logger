# Birth Mark Tracker

Local-first web app for tracking dermatoscope photos of birth marks over time. Register marks, import JPEG/HEIC photos with EXIF dates, and compare any two captures side by side.

## Requirements

- Python 3.11+
- Windows, macOS, or Linux

## Setup

Install dependencies once into your standard Python environment:

```bash
cd "c:\JCCODE\#clazzoni\claz012-birthmark-logger"
python -m pip install -r requirements.txt
```

## Run

From the project folder, using your normal `python`:

```bash
python -m app.main
```

This starts uvicorn on **127.0.0.1:8000** with auto-reload enabled (code changes restart the server).

Or, without auto-reload:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Stop

If the server is running in a terminal you can find, press **Ctrl+C** once or twice.

If you do not know which terminal started it, stop whatever is listening on port 8000.

**Windows (PowerShell):**

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

With auto-reload enabled, a worker process may keep the port open after the parent exits. If the port is still in use, run the command again or stop any remaining `python` processes tied to this app.

**macOS / Linux:**

```bash
lsof -ti:8000 | xargs kill
```

## Workflow

1. **Add a mark** — give it a label (e.g. "left upper back") and optional body region and notes.
2. **Import photos** — select the mark, upload dermatoscope images. EXIF capture dates are read automatically; edit them if needed, then save.
3. **Compare** — pick any two capture dates for the same mark and view them side by side.

## Body map

The **home page** shows the front and back body maps on the left and the mark list on the right.

1. Click a region on the front or back overview (face, torso, arms, legs, hands, back).
2. On a region page, click **Place on map** for an unplaced mark, or open an existing pin.
3. Click the diagram to set the pin position, then **Save placement**.

To **move an existing pin**, open the mark and click **Move pin** (also available from the home list and region pages). Click the new position on the diagram, then **Save new position**. Use **Change region** if the mark should move to a different body region.

Marks without map placement still appear in the list (shown as **Unplaced**). Use the **Unplaced on map only** filter to find them.

Map data is stored per mark in SQLite (`map_region`, `map_x`, `map_y`). SVG diagrams live in `web/static/body/`.

The body map overview uses detailed gender-neutral silhouettes from [Wikimedia Commons (CC0)](https://commons.wikimedia.org/wiki/File:Silhouette_humain_asexue_anterieur_posterieur.svg). See `web/static/body/ATTRIBUTION.md`.

### Calibrating clickable regions

If a region box does not line up with the body image:

1. Open **http://127.0.0.1:8000/?debug=1** to show region outlines on the home page.
2. Open **http://127.0.0.1:8000/body/calibrate** to drag and resize each region.
3. Click **Copy coordinates** and paste into `FIGURE_REGIONS` in `app/overview_hotspots.py` (or share the output in chat).

Hotspots are stored as fractions within the figure silhouette, so they stay aligned if the SVG padding changes.

Detail region pages use zoomed crops from the same overview silhouettes. Regenerate after recalibrating:

```bash
python scripts/generate_detail_crops.py
```

## Data storage

Everything lives under `data/`:

- `data/bodymap.db` — SQLite index of marks and captures
- `data/images/{mark_id}/` — full-size JPEG images
- `data/thumbs/{mark_id}/` — thumbnails for timelines

Back up by copying the entire `data/` folder.

## Google Photos workflow

1. Take dermatoscope photos on your phone (uploaded to Google Photos as usual).
2. Download selected images to your computer.
3. In Birth Mark Tracker: pick the mark → Import photos → upload the downloaded files.

## Tests

```bash
python -m pytest
```
