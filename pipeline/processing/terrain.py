"""Mosaic DEM tiles and compute terrain/slope COGs."""

import subprocess
from pathlib import Path
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from shapely.geometry import box, mapping

from pipeline.processing.export import save_cog


def build_terrain(
    bbox: tuple[float, float, float, float],
    dem_dir: Path | None = None,
    acquisition_date: str = "00000000",
    tile_id: str = "aoi",
    output_dir: Path | None = None,
) -> Path:
    """
    Mosaic DEM tiles (GeoTIFF or SRTM .hgt), clip to bbox, export terrain COG.

    Returns path to terrain COG.
    """
    from config import DATA_RAW, DATA_PROCESSED
    dem_dir = dem_dir or DATA_RAW / "dem"
    output_dir = output_dir or DATA_PROCESSED
    output_dir.mkdir(parents=True, exist_ok=True)

    date_tag = acquisition_date.replace("-", "")
    out_path = output_dir / f"terrain_{date_tag}_{tile_id}.tif"

    tile_paths = (
        sorted(dem_dir.glob("*.tif")) +
        sorted(dem_dir.glob("*.TIF")) +
        sorted(dem_dir.glob("*.hgt"))
    )
    if not tile_paths:
        raise FileNotFoundError(f"No DEM tiles found in {dem_dir}")

    print(f"Mosaicking {len(tile_paths)} DEM tile(s) ...")
    datasets = [rasterio.open(p) for p in tile_paths]
    mosaic, mosaic_transform = merge(datasets)
    src_crs = datasets[0].crs
    for ds in datasets:
        ds.close()

    aoi_geom = [mapping(box(*bbox))]
    with rasterio.MemoryFile() as mf:
        meta = dict(driver="GTiff", height=mosaic.shape[1], width=mosaic.shape[2],
                    count=1, dtype=mosaic.dtype, crs=src_crs, transform=mosaic_transform)
        with mf.open(**meta) as tmp:
            tmp.write(mosaic)
            clipped, clip_transform = mask(tmp, aoi_geom, crop=True)
            clip_meta = tmp.meta.copy()

    clip_meta.update(height=clipped.shape[1], width=clipped.shape[2],
                     transform=clip_transform, count=1, dtype="float32", nodata=np.nan)
    arr = clipped[0].astype(np.float32)
    arr[arr == clip_meta.get("nodata", -32768)] = np.nan

    save_cog(arr[np.newaxis], out_path, clip_meta)
    print(f"Terrain COG saved to {out_path}")
    return out_path


def build_slope(
    terrain_path: Path,
    acquisition_date: str = "00000000",
    tile_id: str = "aoi",
    output_dir: Path | None = None,
) -> Path:
    """Run gdaldem slope on a terrain COG. Returns path to slope COG."""
    from config import DATA_PROCESSED
    output_dir = output_dir or DATA_PROCESSED
    out_path = output_dir / f"slope_{acquisition_date.replace('-','')}_{tile_id}.tif"

    cmd = ["gdaldem", "slope", str(terrain_path), str(out_path),
           "-of", "GTiff", "-b", "1", "-s", "111120"]
    print(f"Computing slope ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gdaldem slope failed:\n{result.stderr}")
    print(f"Slope COG saved to {out_path}")
    return out_path
