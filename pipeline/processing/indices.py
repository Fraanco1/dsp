"""
Compute spectral indices from Sentinel-2 L2A multi-band GeoTIFF.

Band order (as saved by pipeline/download/sentinel.py):
    1: B02 (Blue,  490 nm)
    2: B03 (Green, 560 nm)
    3: B04 (Red,   665 nm)
    4: B08 (NIR,   842 nm)
    5: B11 (SWIR1, 1610 nm)
    6: B12 (SWIR2, 2190 nm)
    7: SCL (Scene Classification Layer — cloud mask)

Indices computed:
    NDVI  = (NIR - Red)   / (NIR + Red)           vegetation density
    NDMI  = (NIR - SWIR1) / (NIR + SWIR1)         vegetation/canopy moisture
    NDWI  = (Green - NIR) / (Green + NIR)          open water
    BSI   = ((SWIR1 + Red) - (NIR + Blue))
            / ((SWIR1 + Red) + (NIR + Blue))       bare soil
"""

from pathlib import Path
from datetime import date
import numpy as np
import rasterio
from rasterio.transform import from_bounds

from pipeline.utils.geo import clip_array_to_bbox
from pipeline.processing.export import save_cog


SCL_CLOUD_VALUES = {3, 8, 9, 10, 11}  # cloud shadow, medium/high cloud, cirrus, snow


def _load_bands(s2_path: Path) -> tuple[dict[str, np.ndarray], dict]:
    """Load all bands and return dict of float32 arrays + rasterio meta."""
    band_keys = ["B02", "B03", "B04", "B08", "B11", "B12", "SCL"]
    with rasterio.open(s2_path) as src:
        meta = src.meta.copy()
        arrays = {}
        for i, key in enumerate(band_keys, start=1):
            arr = src.read(i).astype(np.float32)
            if key != "SCL":
                arr = arr / 10_000.0  # DN → reflectance
                arr[arr <= 0] = np.nan
            arrays[key] = arr
    return arrays, meta


def _cloud_mask(scl: np.ndarray) -> np.ndarray:
    """Return boolean mask: True where pixel is cloud/shadow/snow."""
    mask = np.zeros(scl.shape, dtype=bool)
    for v in SCL_CLOUD_VALUES:
        mask |= scl == v
    return mask


def _safe_ratio(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        result = (a - b) / (a + b)
        result[~np.isfinite(result)] = np.nan
    return np.clip(result, -1.0, 1.0)


def compute_indices(
    s2_path: Path,
    bbox: tuple[float, float, float, float],
    acquisition_date: str,
    tile_id: str = "aoi",
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """
    Compute NDVI, NDMI, NDWI, BSI from a Sentinel-2 GeoTIFF and export as COGs.

    Args:
        s2_path: path to the multi-band Sentinel-2 GeoTIFF
        bbox: (min_lon, min_lat, max_lon, max_lat) used only for logging
        acquisition_date: ISO date string for output filename
        tile_id: tile identifier for filename (e.g. "pampa_r01c01")
        output_dir: directory for output COGs (default: data/processed)

    Returns:
        Dict mapping index name to output COG path.
    """
    from config import DATA_PROCESSED
    output_dir = output_dir or DATA_PROCESSED
    output_dir.mkdir(parents=True, exist_ok=True)

    date_tag = acquisition_date.replace("-", "")
    print(f"Computing spectral indices from {s2_path.name} ...")

    bands, meta = _load_bands(s2_path)
    cloud = _cloud_mask(bands["SCL"])

    def masked(arr: np.ndarray) -> np.ndarray:
        a = arr.copy()
        a[cloud] = np.nan
        return a

    b02 = masked(bands["B02"])
    b03 = masked(bands["B03"])
    b04 = masked(bands["B04"])
    b08 = masked(bands["B08"])
    b11 = masked(bands["B11"])

    ndvi = _safe_ratio(b08, b04)
    ndmi = _safe_ratio(b08, b11)
    ndwi = _safe_ratio(b03, b08)
    with np.errstate(divide="ignore", invalid="ignore"):
        bsi_num = (b11 + b04) - (b08 + b02)
        bsi_den = (b11 + b04) + (b08 + b02)
        bsi = np.where(bsi_den != 0, bsi_num / bsi_den, np.nan)
        bsi = np.clip(bsi, -1.0, 1.0)

    out_meta = meta.copy()
    out_meta.update(count=1, dtype="float32", nodata=np.nan)

    outputs = {}
    for name, arr in [("ndvi", ndvi), ("ndmi", ndmi), ("ndwi", ndwi), ("bsi", bsi)]:
        path = output_dir / f"{name}_{date_tag}_{tile_id}.tif"
        save_cog(arr[np.newaxis, :, :], path, out_meta)
        valid = arr[np.isfinite(arr)]
        print(
            f"  {name.upper():5s} → {path.name}  "
            f"[mean={valid.mean():.3f}, min={valid.min():.3f}, max={valid.max():.3f}]"
        )
        outputs[name] = path

    return outputs
