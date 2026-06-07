# Project Task Board

Status key: `[ ]` todo · `[x]` done · `[~]` in progress

---

## Backend — Arturo ✅

- [x] Scaffold FastAPI app with CORS and health endpoint
- [x] `GET /layers` — scans `data/processed/`, returns GeoJSON FeatureCollection
- [x] `GET /tiles/{layer}/{z}/{x}/{y}.png` — serves COG tiles via rio-tiler
- [x] `GET /tiles/{layer}/tilejson.json` — TileJSON 2.2 metadata
- [x] Per-product colormaps (blues, rdylgn, ylorrd, tab10, greys)
- [x] Per-product default rescale ranges so tiles render without query params
- [x] `?rescale=` and `?colormap_name=` query param support
- [x] RGBA transparency for NoData pixels
- [x] Timeline support — `dates` array in `/layers`, `?date=YYYYMMDD` on tile endpoints
- [x] Synthetic test data generator (`Arturo/scripts/generate_test_data.py`)
- [x] Dockerfile + docker-compose

---

## Frontend — Franco

- [x] React + Vite + Leaflet scaffold
- [x] OSM basemap centered on Argentine Pampas
- [x] Layer panel sidebar with product toggle
- [x] `useLayers` hook — fetches `/layers`, merges with static metadata
- [x] Graceful fallback when backend is offline ("pending" state)
- [x] Legend component
- [x] Vite proxy for `/tiles` and `/layers` → backend port 8000
- [ ] **Fix `window.L` bug** — `MapView.jsx` uses `window.L` which is never set in Vite.
      Change to `import L from 'leaflet'` at the top of the file.
      Without this fix, **overlay tiles will never appear on the map**.
- [ ] **Wire timeline slider** — the backend now returns `dates: ["20240315", ...]`
      per layer in `/layers`. Steps:
      1. Collect the union of all `dates` arrays across all features
      2. Sort them ascending, map to a range slider
      3. On slider change, pass `?date=YYYYMMDD` to the tile URL
      4. Show the selected date as a human-readable label above the slider
- [ ] Merge `feat/frontend` into `main`

---

## Pipeline — Nico

- [x] SAOCOM download via `asf-search` (ASF / NASA Earthdata)
- [x] Sentinel-2 download via `sentinelhub` (Copernicus)
- [x] DEM download (Copernicus GLO-30)
- [x] SAR preprocessing via SNAP (calibration, terrain correction, speckle filter)
- [x] Spectral indices — NDVI, NDMI, NDWI, BSI from Sentinel-2
- [x] Soil moisture retrieval — Water Cloud Model
- [x] Soil clustering — K-means on fused SAR + optical features
- [x] COG export to `data/processed/<product>_<date>_<tile>.tif`
- [ ] **Install ESA SNAP** — required for SAR preprocessing step.
      Download: https://step.esa.int/main/download/snap-download/
- [ ] **Run the pipeline** with credentials from `.env`:
      ```bash
      python main.py --steps download indices
      python main.py --steps moisture clustering
      ```
      This replaces synthetic test data with real Pampas imagery.
- [ ] Verify at least one full date of all 7 products lands in `data/processed/`

---

## Integration — everyone

- [ ] End-to-end smoke test: backend running + frontend open in browser + real COGs
      → all 7 layers render on the map with correct colors
- [ ] Timeline slider moves through at least 2 real acquisition dates
- [ ] Demo recording or live walkthrough for submission
