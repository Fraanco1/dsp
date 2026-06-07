"""
Export raster arrays as Cloud-Optimized GeoTIFFs (COG).

Output naming convention (Pipeline → Backend contract):
    <product>_<date>_<tile>.tif
    e.g. soil_moisture_20240315_pampa_r01c01.tif

The backend (titiler) consumes these COGs directly via the tile endpoint.
"""

from pathlib import Path
import numpy as np
import rasterio
from rasterio.shutil import copy as rio_copy

try:
    from rio_cogeo.cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles
    RIO_COGEO = True
except ImportError:
    RIO_COGEO = False


def save_cog(
    array: np.ndarray,
    output_path: Path,
    meta: dict,
    overview_levels: list[int] | None = None,
) -> Path:
    """
    Write a numpy array to a Cloud-Optimized GeoTIFF.

    Falls back to a plain GeoTIFF with internal overviews if rio-cogeo is not
    installed (still readable by titiler, just not strictly COG-spec).

    Args:
        array: shape (bands, height, width)
        output_path: destination .tif path
        meta: rasterio metadata dict (must include crs, transform, dtype, etc.)
        overview_levels: overview decimation factors (default [2, 4, 8, 16])

    Returns:
        Path to the written file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    overview_levels = overview_levels or [2, 4, 8, 16]

    write_meta = meta.copy()
    write_meta.update(
        driver="GTiff",
        count=array.shape[0],
        dtype=str(array.dtype),
    )

    if RIO_COGEO:
        tmp_path = output_path.with_suffix(".tmp.tif")
        with rasterio.open(tmp_path, "w", **write_meta) as dst:
            dst.write(array)
        profile = cog_profiles.get("deflate")
        cog_translate(str(tmp_path), str(output_path), profile, in_memory=True, quiet=True)
        tmp_path.unlink()
    else:
        # Fallback: plain GeoTIFF with internal overviews
        write_meta.update(compress="deflate", tiled=True, blockxsize=512, blockysize=512)
        with rasterio.open(output_path, "w", **write_meta) as dst:
            dst.write(array)
            dst.build_overviews(overview_levels, rasterio.enums.Resampling.average)
            dst.update_tags(ns="rio_overview", resampling="average")

    return output_path
