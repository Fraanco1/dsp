# DSP — Satellite Soil Analysis Platform

An interactive web platform for soil composition and moisture analysis over the **Argentine Pampas**, powered by SAOCOM L-band SAR and Sentinel-2 multispectral imagery.

Built at the **DeepTech Hackathon** by a 3-person team, each operating an independent Claude Code agent on a separate layer of the stack.

---

## What it does

Ingests satellite data from Argentine and ESA missions, runs geophysical retrieval algorithms, and serves the results as an interactive map with toggleable analytical layers.

| Layer | Source | Algorithm |
|-------|--------|-----------|
| Soil Moisture | SAOCOM 1A/1B (L-band SAR) | Water Cloud Model (σ⁰ HH/HV + NDVI) |
| Bare Soil Index | Sentinel-2 SWIR/NIR/Red/Blue | BSI spectral index |
| Vegetation Water | Sentinel-2 NIR/SWIR1 | NDMI |
| Vegetation Density | Sentinel-2 NIR/Red | NDVI |
| Open Water | Sentinel-2 Green/NIR | NDWI |
| SAR Backscatter | SAOCOM L-band HH | Terrain-corrected σ⁰ (dB) |
| Soil Composition | SAOCOM + Sentinel-2 fusion | K-means / HDBSCAN clustering |

**Area of interest:** Argentine Pampas — Buenos Aires, Córdoba, Santa Fe, La Pampa provinces  
`-65°W to -57°W · -38°S to -30°S`

---

## Architecture

```
SAOCOM GRD (ASF / CONAE)          Sentinel-2 L2A (Copernicus)
         │                                    │
         └──────────────┬─────────────────────┘
                        │
              ┌─────────▼─────────┐
              │   pipeline/       │  Collaborator A
              │                   │
              │  • Download       │  asf-search, sentinelhub
              │  • SAR preproc    │  SNAP, pyroSAR
              │  • Indices        │  rasterio, numpy
              │  • Soil moisture  │  Water Cloud Model
              │  • Clustering     │  scikit-learn
              └─────────┬─────────┘
                        │
               data/processed/
               <product>_<date>_<tile>.tif   ← Cloud-Optimized GeoTIFFs
                        │
              ┌─────────▼─────────┐
              │   Arturo/backend/ │  Collaborator B  (Arturo)
              │                   │
              │  FastAPI          │  GET /layers
              │  + rio-tiler      │  GET /tiles/{layer}/{z}/{x}/{y}.png
              │  + rasterio       │  GET /tiles/{layer}/tilejson.json
              └─────────┬─────────┘
                        │
              ┌─────────▼─────────┐
              │   frontend/       │  Collaborator C
              │                   │
              │  React + Leaflet  │  Interactive map dashboard
              │  Layer panel      │  Toggle layers, view legend
              │  Live /layers API │  Auto-discovers available products
              └───────────────────┘
```

---

## Quick Start

### 1. Clone and set up credentials

```bash
git clone https://github.com/Fraanco1/dsp.git
cd dsp
cp .env.example .env   # fill in NASA Earthdata and Copernicus credentials
```

### 2. Generate synthetic test data (no credentials needed)

```bash
cd dsp
python3 -m venv .venv && .venv/bin/pip install rasterio
.venv/bin/python Arturo/scripts/generate_test_data.py
# → writes 7 COGs to data/processed/
```

### 3. Start the backend

```bash
cd Arturo/backend
python3 -m venv .venv && pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs
```

### 4. Start the frontend

```bash
cd frontend
npm install && npm run dev
# → http://localhost:5173
```

### 5. Or run everything with Docker Compose

```bash
docker compose up
```

---

## API Reference

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Liveness check |
| `GET /layers` | GeoJSON FeatureCollection of all available products |
| `GET /tiles/{layer}/{z}/{x}/{y}.png` | Map tile for a product at zoom/x/y |
| `GET /tiles/{layer}/tilejson.json` | TileJSON 2.2 metadata (bounds, zoom range, tile URL) |

**Query parameters for tile endpoint:**

| Param | Example | Description |
|-------|---------|-------------|
| `rescale` | `0,0.5` | Linear stretch min,max |
| `colormap_name` | `blues` | Matplotlib colormap name |

---

## Analytical Layers

| Product ID | Colormap | Range | Description |
|------------|----------|-------|-------------|
| `soil_moisture` | Blues | 0 – 0.5 m³/m³ | Volumetric water content |
| `ndvi` | RdYlGn | -1 – 1 | Vegetation density |
| `ndmi` | RdYlGn | -1 – 1 | Canopy moisture |
| `ndwi` | Blues | -1 – 1 | Open water detection |
| `bsi` | YlOrRd | -1 – 1 | Bare soil exposure |
| `backscatter_hh` | Greys | -25 – -5 dB | SAR L-band HH |
| `soil_cluster` | Tab10 | 0 – 5 | Unsupervised soil type |

---

## Data Sources

| Source | What for | Access |
|--------|----------|--------|
| [CONAE / ASF Vertex](https://search.asf.alaska.edu/) | SAOCOM GRD scenes | NASA Earthdata account |
| [Copernicus Data Space](https://dataspace.copernicus.eu/) | Sentinel-2 L2A | Copernicus OAuth |
| [CONAE Catalog](https://catalogos.conae.gov.ar/) | Direct SAOCOM access | CONAE account |
| [NASA SMAP L4](https://nsidc.org/data/SPL4SMGP) | Soil moisture calibration | NASA Earthdata |

---

## Pipeline

Run the full pipeline or individual steps:

```bash
# Full run (download → preprocess → indices → moisture → clustering)
python main.py

# Individual steps
python main.py --steps download indices
python main.py --steps moisture clustering

# Custom AOI and date range
python main.py --bbox "-64,-33,-63,-32" --start 2024-03-01 --end 2024-03-31
```

Output COGs follow the contract: `data/processed/<product>_<date>_<tile>.tif`  
The backend picks them up automatically — no restart required.

---

## Tech Stack

**Pipeline:** `asf-search` · `sentinelhub` · `pyroSAR` · `snapista` · `rasterio` · `xarray` · `scikit-learn` · `rio-cogeo`

**Backend:** `FastAPI` · `rio-tiler` · `rasterio` · `pydantic-settings` · `uvicorn`

**Frontend:** `React 18` · `Leaflet` · `react-leaflet` · `Vite`

---

## Team

| Layer | Owner | Branch |
|-------|-------|--------|
| Data pipeline | Collaborator A (Nico) | `Pipeline` |
| Backend API + tile server | Arturo | `feat/backend-*` |
| Frontend map dashboard | Collaborator C (Franco) | `feat/frontend` |
