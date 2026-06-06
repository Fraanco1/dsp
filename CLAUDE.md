# Satellite Soil Analysis Platform

DeepTech hackathon project using Argentine satellite data (SAOCOM) to analyze
soil composition and moisture. Deliverable: a general-purpose web platform with
an interactive map dashboard.

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

  results = asf.search(
      platform=asf.PLATFORM.SAOCOM1A,
      processingLevel=asf.PRODUCT_TYPE.GRD_HD,
      intersectsWith='POLYGON((-64 -33, -63 -33, -63 -32, -64 -32, -64 -33))',
      start='2024-01-01',
      end='2024-12-31',
  )
  results.download(path='./data/raw', session=asf.ASFSession().auth_with_creds('user','pass'))
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

### Backend (Python)
| Library | Purpose |
|---------|---------|
| `asf-search` | SAOCOM scene search and download from ASF |
| `sentinelhub` | Sentinel-2 data access |
| `pyroSAR` | SAR metadata handling and SNAP workflow automation |
| `snapista` | Python bindings for ESA SNAP (SAR preprocessing) |
| `rasterio` | Raster I/O and reprojection |
| `xarray` + `rioxarray` | Multidimensional array operations on rasters |
| `numpy`, `scipy` | Numerical processing |
| `scikit-learn` | ML models (regression, clustering) |
| `rio-cogeo` | Export Cloud-Optimized GeoTIFFs |
| `FastAPI` | REST API + tile serving |
| `titiler` | Dynamic COG tile server (plugs into FastAPI) |

### Frontend
| Library | Purpose |
|---------|---------|
| React | UI framework |
| Leaflet / react-leaflet | Base map + raster tile overlay |
| Deck.gl (optional) | GPU-accelerated large dataset visualization |

### Infrastructure (hackathon-scale)
- Local processing or single cloud VM (GPU optional for ML inference)
- Static COG tiles served from local filesystem or S3-compatible storage
- No Kubernetes needed at this stage

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

- [ ] Register accounts (CONAE, NASA Earthdata, Copernicus)
- [ ] Test `asf-search` programmatic SAOCOM scene search
- [ ] Download one SAOCOM GRD scene over Pampas AOI
- [ ] Download matching Sentinel-2 scene (same date ±3 days, cloud < 20%)
- [ ] Set up ESA SNAP for SAR preprocessing (or `snapista` wrapper)
- [ ] Run calibration + terrain correction + speckle filter on test scene
- [ ] Compute BSI and NDMI from Sentinel-2
- [ ] Prototype soil moisture retrieval (start with empirical σ⁰ → SM regression)
- [ ] Scaffold FastAPI + titiler tile server
- [ ] Scaffold React + Leaflet frontend
