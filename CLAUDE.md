# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeepTech hackathon platform ingesting Argentine satellite data (SAOCOM L-band SAR + Sentinel-2 optical) to derive soil moisture, vegetation indices, and soil composition. Full stack: Python data pipeline → FastAPI tile server → React + Leaflet map dashboard.

---

## Collaboration Rules (read first)

**3 collaborators each run Claude Code independently. Never modify files outside your layer.**

| Layer | Directory | Owner | Branch |
|-------|-----------|-------|--------|
| Data pipeline | `pipeline/` | Nico | `feat/pipeline` |
| Backend API | `Arturo/backend/` | Arturo | `feat/backend` |
| Frontend dashboard | `frontend/` | Franco | `feat/frontend` |

Shared files (`CLAUDE.md`, `.gitignore`, `docker-compose.yml`, `README.md`) require a PR — no direct commits to `main`.

### Git workflow
- Branch from `main`: `git checkout -b feat/<layer>-<description>`
- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`
- PR required to merge into `main`; at least one collaborator reviews
- **Never force-push to `main`**

### What Claude Code must not do autonomously
- Commit or push to `main` directly
- Modify files in another layer's directory
- Install system packages without documenting in `CLAUDE.md`
- Commit `.env` files, credentials, or raw satellite data files

---

## Running the Stack

```bash
# Backend (Terminal 1)
cd Arturo/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (Terminal 2) — Node must be on PATH
# If node not found: export PATH="$HOME/.local/bin:$PATH"
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

```bash
# Pipeline — full run (default Pampas AOI, last 30 days)
python main.py

# Pipeline — specific steps only
python main.py --steps download preprocess
python main.py --steps indices moisture clustering

# Pipeline — custom AOI and date range
python main.py --bbox "-64,-33,-63,-32" --start 2024-01-01 --end 2024-03-01
```

**Frontend scripts** (`frontend/package.json`):
- `npm run dev` — Vite dev server on port 5173
- `npm run build` — production build
- `npm run preview` — preview production build

There are no automated tests in this repo yet.

---

## Architecture

### Data flow

```
data/raw/          → pipeline processes → data/processed/*.tif
data/processed/    → backend reads     → GET /tiles/{stem}/{z}/{x}/{y}.png
backend :8000      → Vite proxy        → frontend :5173
```

`data/processed/` is the sole handoff point between pipeline and backend. Backend never writes here; pipeline never calls the backend.

### COG naming contract

Files must match: `<product>_<YYYYMMDD>_<tile>.tif`
e.g. `soil_moisture_20240315_pampa_r01c01.tif`

Valid products: `ndvi`, `ndmi`, `ndwi`, `bsi`, `soil_moisture`, `backscatter_hh`, `soil_cluster`

COGs must have internal overviews and be ≥2048×2048 px for zoom level 7+ support (smaller rasters top out at zoom 5–6 and won't render at the default map zoom).

### Backend (`Arturo/backend/`)

```
app/
  main.py          — FastAPI app, CORS middleware, router registration
  config.py        — pydantic-settings: data_dir (default ../../data/processed), port 8000
  routers/
    tiles.py       — GET /tiles/{layer}/{z}/{x}/{y}.png + TileJSON endpoint
                     Uses COGReader (rio-tiler) to render PNG tiles with colormap
    layers.py      — GET /layers → GeoJSON FeatureCollection from catalog service
  services/
    catalog.py     — Scans data_dir/*.tif, parses filenames with regex, returns features
    colormaps.py   — Maps product name → rio-tiler colormap name (blues, rdylgn, etc.)
```

`tiles.py:_product_from_layer()` extracts the product name from the layer stem to select the right colormap. `catalog.py` uses `_FILENAME_RE` to reject any file not matching the naming contract.

Backend config is via `.env` at `Arturo/backend/.env` (not the root `.env`). Override `data_dir` there if needed.

### Frontend (`frontend/src/`)

```
config/layers.js   — Static metadata for all 7 products (label, unit, color, min/max, colormap)
                     LAYER_ORDER controls display order in the panel
hooks/useLayers.js — Fetches GET /layers, merges with LAYER_META, groups by product (most recent date wins)
                     Falls back to all layers "pending" if backend is offline
App.jsx            — Root: manages activeId state, passes activeLayer down to MapView + Legend
components/
  MapView.jsx      — Leaflet map centered on Argentine Pampas (-34, -61), zoom 7
                     OverlayLayer swaps the tile URL when activeLayer changes (no map remount)
                     Tile URL: /tiles/{layer.layerId}/{z}/{x}/{y}.png — layerId is the full stem
  LayerPanel.jsx   — Sidebar list; shows date (YYYYMMDD formatted) or "pending" badge
  Legend.jsx       — Color ramp legend using layer min/max/unit from LAYER_META
  Header.jsx       — Shows backend online/offline status
```

Key design decision: `useLayers` merges static `LAYER_META` (display config) with live `/layers` data (availability + dates). A layer exists in the UI even when no COG is present — it shows as "pending". `layer.available` gates whether the tile overlay is rendered.

Vite proxy (`vite.config.js`) forwards `/tiles` and `/layers` to `http://localhost:8000` — no CORS issues in dev.

### Pipeline (`pipeline/`)

```
download/
  asf.py           — SAOCOM (authenticated) and Sentinel-1 (unauthenticated) via asf-search
  sentinel.py      — Sentinel-2 L2A via sentinelhub
  dem.py           — Copernicus DEM tiles
preprocessing/
  sar.py           — ESA SNAP calibration + terrain correction via snapista/pyroSAR
processing/
  indices.py       — NDVI, NDMI, NDWI, BSI from Sentinel-2 (band order documented at top of file)
  moisture.py      — Water Cloud Model soil moisture retrieval from SAR σ⁰ + NDVI
  clustering.py    — K-means/HDBSCAN on fused SAR + optical feature stack
  export.py        — save_cog(): writes numpy arrays as COGs; falls back to plain GeoTIFF if rio-cogeo missing
utils/geo.py       — clip_array_to_bbox(), tile_id_from_bbox()
```

Root `config.py` sets `DATA_RAW` and `DATA_PROCESSED` paths, loads credentials from `.env`.
Root `main.py` is the pipeline CLI entry point — orchestrates all steps in order.

---

## Interface Contracts

### Backend → Frontend (`GET /layers` response shape)

```json
{
  "properties": {
    "id": "soil_moisture_20240315_pampa_r01c01",  // full file stem → tile URL
    "product": "soil_moisture",                    // short name → matches LAYER_META key
    "date": "20240315",                            // YYYYMMDD
    "tile": "pampa_r01c01",
    "bounds": [-65.0, -38.0, -57.0, -30.0]        // [west, south, east, north]
  }
}
```

### Adding a new product
1. **Pipeline**: export COG as `<product>_<date>_<tile>.tif` to `data/processed/`
2. **Backend**: add colormap entry in `Arturo/backend/app/services/colormaps.py`
3. **Frontend**: add entry to `LAYER_META` and `LAYER_ORDER` in `frontend/src/config/layers.js`

---

## Environment Variables

Copy `.env.example` to `.env` at the repo root before running the pipeline:

| Variable | Used for |
|----------|----------|
| `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD` | ASF SAOCOM download + Copernicus DEM |
| `SH_CLIENT_ID` / `SH_CLIENT_SECRET` | Sentinel-2 via sentinelhub |
| `CONAE_USER` / `CONAE_PASSWORD` | Direct CONAE catalog (optional; ASF is preferred) |

The backend reads its own `Arturo/backend/.env` for `data_dir` override.

---

## AOI

Argentine Pampas: West −65°, East −57°, South −38°, North −30° (Buenos Aires, Córdoba, Santa Fe, La Pampa). This bbox is hardcoded as `DEFAULT_BBOX` in `config.py` and as `BOUNDS` in `MapView.jsx`.
