"""
Soil moisture retrieval using the Water Cloud Model (WCM).

The WCM relates SAR backscatter σ⁰ and a vegetation descriptor (NDVI) to
volumetric soil moisture (VSM, m³/m³).

Model:
    σ⁰_total  = σ⁰_veg  + T² · σ⁰_soil
    σ⁰_veg    = A · V · cos(θ) · (1 - T²)
    T²        = exp(-2 · B · V / cos(θ))
    σ⁰_soil   = (σ⁰_total - σ⁰_veg) / T²

where V is a vegetation descriptor (here: NDVI), θ is incidence angle, and
A, B, C, D are calibration parameters.

Without in-situ calibration data this module exports:
  - Calibrated σ⁰ (dB) as a first-order moisture proxy
  - A simple empirical linear rescaling to [0, 0.5] m³/m³

For production use, calibrate A, B, C, D against SMAP L4 or in-situ data.
"""

from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

from pipeline.processing.export import save_cog


# WCM default parameters (uncalibrated — valid for C/L-band dry agricultural areas)
# Calibrate these against SMAP L4 for your AOI
WCM_A = 0.1
WCM_B = 0.1
DEFAULT_INCIDENCE_ANGLE_DEG = 35.0


def _load_sigma0(sar_path: Path) -> tuple[np.ndarray, dict]:
    """Load a single-band sigma0 (dB) GeoTIFF and return array + meta."""
    with rasterio.open(sar_path) as src:
        arr = src.read(1).astype(np.float32)
        arr[arr == src.nodata] = np.nan
        meta = src.meta.copy()
    return arr, meta


def _resample_to_match(source: np.ndarray, src_meta: dict, target_meta: dict) -> np.ndarray:
    """Reproject/resample source array to match target_meta grid."""
    destination = np.full(
        (target_meta["height"], target_meta["width"]), np.nan, dtype=np.float32
    )
    reproject(
        source=source,
        destination=destination,
        src_transform=src_meta["transform"],
        src_crs=src_meta["crs"],
        dst_transform=target_meta["transform"],
        dst_crs=target_meta["crs"],
        resampling=Resampling.bilinear,
        src_nodata=np.nan,
        dst_nodata=np.nan,
    )
    return destination


def _wcm_remove_vegetation(
    sigma0_db: np.ndarray,
    ndvi: np.ndarray,
    theta_deg: float = DEFAULT_INCIDENCE_ANGLE_DEG,
) -> np.ndarray:
    """
    Remove vegetation contribution using Water Cloud Model.
    Returns sigma0_soil_linear (not in dB).
    """
    theta = np.deg2rad(theta_deg)
    cos_theta = np.cos(theta)

    # Convert dB to linear
    sigma0_lin = 10.0 ** (sigma0_db / 10.0)

    # Vegetation descriptor (clip NDVI to [0,1])
    V = np.clip(ndvi, 0.0, 1.0)
    V = np.where(np.isfinite(V), V, 0.0)

    T2 = np.exp(-2.0 * WCM_B * V / cos_theta)
    sigma_veg = WCM_A * V * cos_theta * (1.0 - T2)

    sigma_soil = np.where(T2 > 1e-6, (sigma0_lin - sigma_veg) / T2, np.nan)
    sigma_soil = np.where(sigma_soil > 0, sigma_soil, np.nan)
    return sigma_soil


def _empirical_vsm(sigma0_soil_linear: np.ndarray) -> np.ndarray:
    """
    Empirically map sigma0_soil (linear) to VSM [0, 0.5] m³/m³.
    Replace with calibrated WCM coefficients for production.
    """
    sigma_db = np.where(sigma0_soil_linear > 0, 10 * np.log10(sigma0_soil_linear), np.nan)
    # Linear stretch: -25 dB (dry) → 0.05 m³/m³ ; -5 dB (wet) → 0.45 m³/m³
    vsm = 0.02 * sigma_db + 0.55
    return np.clip(vsm, 0.0, 0.5)


def build_moisture(
    sar_path: Path,
    ndvi_path: Path,
    acquisition_date: str,
    tile_id: str = "aoi",
    output_dir: Path | None = None,
    incidence_angle_deg: float = DEFAULT_INCIDENCE_ANGLE_DEG,
) -> dict[str, Path]:
    """
    Derive soil moisture maps from preprocessed SAR sigma0 and Sentinel-2 NDVI.

    Outputs (saved as COGs to data/processed/):
        backscatter_hh_<date>_<tile>.tif   — σ⁰ HH in dB
        soil_moisture_<date>_<tile>.tif    — VSM in m³/m³ (WCM estimate)

    Args:
        sar_path: path to the terrain-corrected, sigma0-in-dB GeoTIFF
        ndvi_path: path to the NDVI COG from pipeline/processing/indices.py
        acquisition_date: ISO date string for output filename
        tile_id: tile identifier for filename
        output_dir: output directory (default: data/processed)

    Returns:
        Dict with keys "backscatter_hh" and "soil_moisture" mapping to output paths.
    """
    from config import DATA_PROCESSED
    output_dir = output_dir or DATA_PROCESSED
    output_dir.mkdir(parents=True, exist_ok=True)

    date_tag = acquisition_date.replace("-", "")
    print(f"Building moisture maps from {sar_path.name} ...")

    sigma0, sar_meta = _load_sigma0(sar_path)

    # Load and co-register NDVI to SAR grid
    with rasterio.open(ndvi_path) as ndvi_src:
        ndvi_raw = ndvi_src.read(1).astype(np.float32)
        ndvi_meta = ndvi_src.meta.copy()

    ndvi = _resample_to_match(ndvi_raw, ndvi_meta, sar_meta)

    sigma_soil = _wcm_remove_vegetation(sigma0, ndvi, incidence_angle_deg)
    vsm = _empirical_vsm(sigma_soil)

    base_meta = sar_meta.copy()
    base_meta.update(count=1, dtype="float32", nodata=np.nan)

    outputs = {}

    # σ⁰ HH backscatter (dB)
    bsc_path = output_dir / f"backscatter_hh_{date_tag}_{tile_id}.tif"
    save_cog(sigma0[np.newaxis, :, :], bsc_path, base_meta)
    print(f"  Backscatter → {bsc_path.name}")
    outputs["backscatter_hh"] = bsc_path

    # Volumetric soil moisture (m³/m³)
    sm_path = output_dir / f"soil_moisture_{date_tag}_{tile_id}.tif"
    save_cog(vsm[np.newaxis, :, :], sm_path, base_meta)
    valid = vsm[np.isfinite(vsm)]
    print(f"  Soil moisture → {sm_path.name}  [mean={valid.mean():.3f} m³/m³]")
    outputs["soil_moisture"] = sm_path

    return outputs
