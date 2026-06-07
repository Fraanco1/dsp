# Satellite Soil Analysis Platform

DeepTech hackathon project using Argentine satellite data (SAOCOM) to analyze
soil composition and moisture. Deliverable: a general-purpose web platform with
an interactive map dashboard.

**3 collaborators, each running Claude Code independently.**

---

## Collaboration Rules (read first)

This repo has 3 collaborators each using Claude Code simultaneously. To avoid
conflicts, each person owns a distinct layer of the stack. Claude Code agents
must not modify files outside their owner's layer without coordinating first.

### Layer ownership

| Layer | Directory | Owner | Claude Code branch |
|-------|-----------|-------|--------------------|
| Data pipeline (download + preprocess) | `pipeline/` | Nico | `feat/pipeline` |
| Backend API + tile server | `Arturo/backend/` | Arturo | `feat/backend` |
| Frontend map dashboard | `frontend/` | Franco | `feat/frontend` |

> Note: Arturo scaffolded his backend under `Arturo/backend/` (not `backend/`).
> Do not move or rename this without coordinating with him.

Shared files (`CLAUDE.md`, `.gitignore`, `pyproject.toml`, `docker-compose.yml`,
`README.md`) require a PR — no direct commits to `main` from Claude agents.

### Git workflow

- Branch from `main` — `git checkout -b feat/<layer>-<short-description>`
- Commit often with conventional commits: `feat:`, `fix:`, `chore:`, `docs:`
- Open a PR to merge into `main`; at least one other collaborator reviews
- Pull `main` before starting a new task: `git pull origin main`
- **Never force-push to `main`**

### What Claude Code should NOT do autonomously

- Commit or push to `main` directly
- Modify files in another layer's directory
- Install system packages (`apt`, `brew`) without documenting in `CLAUDE.md`
- Commit `.env` files, credentials, or raw satellite data files

### Interface contracts (how layers communicate)

**Pipeline → Backend:**
- Pipeline writes Cloud-Optimized GeoTIFFs to `data/processed/`
- Naming scheme: `<product>_<YYYYMMDD>_<tile>.tif`
  (e.g. `soil_moisture_20240315_pampa_r01c01.tif`)
- Products: `ndvi`, `ndmi`, `ndwi`, `bsi`, `soil_moisture`, `backscatter_hh`, `soil_cluster`
- COGs must have internal overviews and be ≥2048×2048 px for zoom level 7+ support
  (smaller rasters top out at zoom 5–6 and won't render at the default map zoom)

**Backend → Frontend:**
- `GET /layers` — returns GeoJSON FeatureCollection where each feature has:
  ```json
  {
    "properties": {
      "id": "soil_moisture_20240315_pampa_r01c01",  ← full file stem (used in tile URL)
      "product": "soil_moisture",                    ← short product name
      "date": "20240315",                            ← YYYYMMDD
      "tile": "pampa_r01c01",
      "bounds": [-65.0, -38.0, -57.0, -30.0]
    }
  }
  ```
- `GET /tiles/{full_stem}/{z}/{x}/{y}.png` — PNG tile; colormap applied server-side
- `GET /health` — `{"status": "ok"}`
- Backend runs on port **8000**; frontend Vite proxy forwards `/tiles` and `/layers` to it

---

## Project Goal

Build a platform that ingests SAR and multispectral satellite data from
Argentine/partner missions and derives:
- **Soil moisture content** (volumetric water content, m³/m³)
- **Bare Soil Index (BSI)** and soil type proxies
- **Vegetation water content** (NDWI / NDMI)
- Fused SAR + optical layers for unsupervised soil composition clustering

Primary output: interactive map with toggleable analytical layers served from
a Python backend to a React + Leaflet/Deck.gl frontend.

---

## Satellite Data Sources

### SAOCOM (primary — Argentine national asset)
- **Operator:** CONAE (Comisión Nacional de Actividades Espaciales)
- **Satellites:** SAOCOM 1A (launched 2018) and SAOCOM 1B (launched 2020)
- **Sensor:** L-band SAR (1.27 GHz), HH+HV polarizations
- **Why L-band:** penetrates vegetation canopy; backscatter is highly sensitive
  to soil dielectric constant (directly related to soil moisture content)
- **Swath / resolution:** 320–350 km swath (ScanSAR), 10–30 m resolution (Stripmap)
- **Products:**
  - SLC (Single Look Complex) — raw phase + amplitude, for interferometry
  - GRD (Ground Range Detected) — detected amplitude, ready for soil retrieval
  - MLA (Multi-Look Amplitude)
- **Revisit:** ~16 days per satellite, ~8 days combined

### Sentinel-2 (complementary — optical multispectral)
- **Operator:** ESA / Copernicus (distributed by CONAE under agreement)
- **Bands used:** Blue (B2), Green (B3), Red (B4), NIR (B8), SWIR1 (B11), SWIR2 (B12)
- **Resolution:** 10 m (visible/NIR), 20 m (SWIR)
- **Use:** spectral indices (NDVI, NDMI, BSI), cloud masking, optical fusion with SAR

### SAC-D / Aquarius (historical reference)
- Argentine satellite (2011–2015), carried the Aquarius L-band radiometer
- Measured sea-surface salinity; useful as historical context, not for current analysis

---

## Data Access

### CONAE Catalog (SAOCOM official source)
- URL: https://catalogos.conae.gov.ar/
- Requires free registration with CONAE
- Provides SAOCOM GRD and SLC products for Argentina and surrounding regions
- Contact: datos@conae.gov.ar for bulk/API access questions

### Alaska Satellite Facility (ASF) — Vertex
- URL: https://search.asf.alaska.edu/
- API docs: https://docs.asf.alaska.edu/api/basics/
- Distributes SAOCOM products under CONAE–NASA data sharing agreement
- **Programmatic access:**
  ```
  pip install asf-search
  ```
  ```python
  import asf_search as asf

  # SAOCOM is NOT in asf.PLATFORM constants — pass as strings
  # SAOCOM search requires an authenticated session (unauthenticated returns empty)
  session = asf.ASFSession().auth_with_creds('user', 'pass')
  results = asf.search(
      platform=["SAOCOM-1A", "SAOCOM-1B"],
      processingLevel="GRD_HD",
      intersectsWith='POLYGON((-65 -38, -57 -38, -57 -30, -65 -30, -65 -38))',
      start='2024-01-01',
      end='2024-12-31',
      opts=asf.ASFSearchOptions(session=session),
  )
  results.download(path='./data/raw', session=session)
  ```
- **Sentinel-1 search works without auth** and is a good fallback for pipeline testing:
  ```python
  results = asf.search(
      platform=[asf.PLATFORM.SENTINEL1A, asf.PLATFORM.SENTINEL1B],
      processingLevel=asf.PRODUCT_TYPE.GRD_HD,
      intersectsWith='POLYGON((-65 -38, -57 -38, -57 -30, -65 -30, -65 -38))',
      start='2024-01-01', end='2024-12-31', maxResults=20,
  )
  ```
- Authentication: NASA Earthdata account (free) at https://urs.earthdata.nasa.gov/

### Copernicus Data Space Ecosystem (Sentinel-2)
- URL: https://dataspace.copernicus.eu/
- OData / STAC API available, free registration
- ```
  pip install sentinelhub
  ```

### Google Earth Engine (alternative / validation)
- SAOCOM availability on GEE is limited — prefer ASF for SAOCOM
- Sentinel-2 fully available on GEE: `ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")`
- Useful for quick validation and visualization during development

---

## Processing Pipeline (planned)

```
Raw SAOCOM GRD
    │
    ├── Radiometric calibration (sigma0)
    ├── Terrain correction (DEM: SRTM 30m or Argentina IGN DEM)
    ├── Speckle filtering (Lee, Refined Lee, or CNN-based)
    │
    ▼
Backscatter σ⁰ (dB)  ──────────────────────────────────┐
    │                                                    │
    ▼                                                    ▼
Soil Moisture Retrieval                        SAR Texture Features
(Water Cloud Model or ML regression)           (GLCM: contrast, entropy)
    │                                                    │
    └──────────────────┬─────────────────────────────────┘
                       │
              Sentinel-2 Spectral Indices
              (NDVI, NDMI, BSI, MNDWI)
                       │
                       ▼
              Fused Feature Stack → Clustering / Classification
                       │
                       ▼
              Cloud-Optimized GeoTIFF tiles
                       │
                       ▼
              FastAPI tile server → React + Leaflet frontend
```

### Key algorithms
- **Soil Moisture:** Water Cloud Model (WCM) — relates σ⁰(HH), σ⁰(HV), NDVI to
  volumetric soil moisture. Requires calibration data (in-situ or SMAP product).
- **Bare Soil Index:**
  `BSI = ((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))`
- **NDMI (moisture):**
  `NDMI = (NIR - SWIR1) / (NIR + SWIR1)`
- **Soil clustering:** K-means or HDBSCAN on [σ⁰HH, σ⁰HV, NDVI, BSI, NDMI]

---

## Tech Stack

### Pipeline (Python) — Nico
| Library | Purpose |
|---------|---------|
| `asf-search` | SAOCOM/Sentinel-1 search and download from ASF |
| `sentinelhub` | Sentinel-2 data access |
| `pyroSAR` / `snapista` | SAR metadata + ESA SNAP preprocessing |
| `rasterio` | Raster I/O and reprojection |
| `xarray` + `rioxarray` | Multidimensional array operations |
| `numpy`, `scipy` | Numerical processing |
| `scikit-learn` | K-means clustering, regression |
| `rio-cogeo` | Export Cloud-Optimized GeoTIFFs |

### Backend (Python) — Arturo
| Library | Purpose |
|---------|---------|
| `FastAPI` | REST API framework |
| `uvicorn` | ASGI server |
| `rio-tiler` | COG tile rendering (replaces titiler for direct control) |
| `rasterio` | Raster bounds/metadata reading |
| `pydantic-settings` | Config via `.env` |

### Frontend (JavaScript) — Franco
| Library | Purpose |
|---------|---------|
| React 18 | UI framework |
| Vite | Build tool + dev server (port 5173) |
| Leaflet + react-leaflet | Base map + raster tile overlay |
| Node.js v22 LTS | Runtime (installed to `~/.local/` via direct binary download) |

### Infrastructure (hackathon-scale)
- Local processing; `data/processed/` is the shared data handoff directory
- Backend `data_dir` defaults to `../../data/processed` relative to `Arturo/backend/`
- Frontend Vite proxy: `/tiles` and `/layers` → `http://localhost:8000`
- No Docker required for local dev (docker-compose available for deployment)

### Running the stack locally
```bash
# Terminal 1 — backend
cd Arturo/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — frontend (Node must be on PATH)
# If node not found: export PATH="$HOME/.local/bin:$PATH"
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## AOI (Area of Interest)

Focus on the Argentine Pampas — highest agricultural value, densely monitored,
SAOCOM coverage is consistent. Example bounding box:
```
West: -65°, East: -57°, South: -38°, North: -30°
(covers Buenos Aires, Córdoba, Santa Fe, La Pampa provinces)
```

---

## Reference Products (for validation / calibration)
- **SMAP L4** (NASA): global 9 km soil moisture, daily — use to calibrate WCM
- **MODIS Terra/Aqua**: land surface temperature, vegetation indices (free via NASA Earthdata)
- **Argentina IGN DEM**: national 30 m digital elevation model for terrain correction

---

## Accounts to Register

| Service | URL | Required for |
|---------|-----|-------------|
| CONAE Catalog | https://catalogos.conae.gov.ar/ | Direct SAOCOM download |
| NASA Earthdata | https://urs.earthdata.nasa.gov/ | ASF download (SAOCOM via ASF) |
| Copernicus Data Space | https://dataspace.copernicus.eu/ | Sentinel-2 access |
| Google Earth Engine | https://earthengine.google.com/ | Optional validation |

---

## Current Status

### Done
- [x] NASA Earthdata account registered (Franco)
- [x] `asf-search` installed; Sentinel-1 scene search working over Pampas AOI
- [x] Pipeline layer scaffolded: download, preprocessing, indices, moisture, clustering modules
- [x] Backend scaffolded: FastAPI + rio-tiler serving COG tiles at `/tiles/{stem}/{z}/{x}/{y}.png`
- [x] Frontend scaffolded: React + Leaflet, layer panel (7 layers), legend, live `/layers` hook
- [x] Full stack running locally — frontend at :5173, backend at :8000, proxy connected
- [x] Synthetic soil moisture COG tested end-to-end through the full stack

### In progress
- [ ] SAOCOM download via CONAE catalog (requires CONAE account + manual portal access)
- [ ] SAOCOM search via ASF authenticated session (NASA Earthdata credentials needed in env)
- [ ] Sentinel-2 download via Copernicus Data Space (needs `SH_CLIENT_ID` / `SH_CLIENT_SECRET`)

### Pending
- [ ] Download real SAOCOM GRD scene over Pampas AOI
- [ ] Download matching Sentinel-2 scene (same date ±3 days, cloud < 20%)
- [ ] Run SAR preprocessing (calibration + terrain correction + speckle filter via SNAP)
- [ ] Compute NDVI, NDMI, NDWI, BSI from real Sentinel-2 data
- [ ] Run Water Cloud Model soil moisture retrieval
- [ ] Run K-means clustering on fused SAR + optical feature stack
- [ ] Replace synthetic COG with real pipeline outputs in `data/processed/`
