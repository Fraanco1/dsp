"""Compute NDVI vegetation index from Sentinel-2 L2A bands."""

from pathlib import Path
import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import box, mapping

from config import DATA_RAW, DATA_OUTPUT


def _find_band(scene_dir: Path, band_id: str) -> Path:
    """Find a specific Sentinel-2 band file (e.g. B04, B08) inside a .SAFE dir."""
    pattern = f"**/*_{band_id}_10m.jp2"
    matches = list(scene_dir.glob(pattern))
    if not matches:
        # Fall back to any resolution
        matches = list(scene_dir.glob(f"**/*_{band_id}*.jp2"))
    if not matches:
        raise FileNotFoundError(f"Band {band_id} not found under {scene_dir}")
    return matches[0]


def _load_clipped_band(band_path: Path, aoi_geom: list) -> tuple[np.ndarray, dict]:
    with rasterio.open(band_path) as src:
        clipped, transform = mask(src, aoi_geom, crop=True)
        meta = src.meta.copy()
        meta.update(transform=transform, height=clipped.shape[1], width=clipped.shape[2])
    return clipped[0].astype(np.float32), meta


def build_vegetation(
    bbox: tuple[float, float, float, float],
    s2_dir: Path | None = None,
    output: Path | None = None,
) -> Path:
    """
    Compute NDVI from the most-recent Sentinel-2 L2A scene covering bbox.

    NDVI = (NIR - Red) / (NIR + Red)  using bands B08 (NIR) and B04 (Red).
    Output values are clipped to [-1, 1]; no-data pixels become NaN.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        s2_dir: directory containing downloaded .SAFE Sentinel-2 scenes
        output: output GeoTIFF path

    Returns:
        Path to the NDVI GeoTIFF.
    """
    s2_dir = s2_dir or DATA_RAW / "sentinel2"
    output = output or DATA_OUTPUT / "vegetation_ndvi.tif"
    output.parent.mkdir(parents=True, exist_ok=True)

    safe_dirs = sorted(s2_dir.glob("*.SAFE")) + sorted(s2_dir.glob("*.safe"))
    if not safe_dirs:
        raise FileNotFoundError(
            f"No Sentinel-2 .SAFE scenes found in {s2_dir}. "
            "Run the download step first."
        )

    # Use the most recent scene (sorted alphabetically, date is in the name)
    scene = safe_dirs[-1]
    print(f"Computing NDVI from {scene.name} ...")

    aoi_geom = [mapping(box(*bbox))]

    red, meta = _load_clipped_band(_find_band(scene, "B04"), aoi_geom)
    nir, _ = _load_clipped_band(_find_band(scene, "B08"), aoi_geom)

    # Sentinel-2 L2A reflectance is scaled by 10000
    red = red / 10000.0
    nir = nir / 10000.0

    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir - red) / (nir + red)
        ndvi = np.clip(ndvi, -1.0, 1.0)
        # Mark no-data (zero reflectance pixels) as NaN
        ndvi[red == 0] = np.nan

    meta.update(dtype="float32", count=1, nodata=np.nan, driver="GTiff")
    with rasterio.open(output, "w", **meta) as dst:
        dst.write(ndvi, 1)

    valid = ndvi[np.isfinite(ndvi)]
    print(
        f"NDVI map saved to {output}  "
        f"[min={valid.min():.3f}, mean={valid.mean():.3f}, max={valid.max():.3f}]"
    )
    return output
