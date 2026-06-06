"""Mosaic and clip DEM tiles into a single terrain GeoTIFF."""

from pathlib import Path
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import box, mapping

from config import DATA_RAW, DATA_OUTPUT


def build_terrain(
    bbox: tuple[float, float, float, float],
    dem_dir: Path | None = None,
    output: Path | None = None,
    target_crs: str = "EPSG:4326",
) -> Path:
    """
    Mosaic all DEM tiles in dem_dir, clip to bbox, and export terrain.tif.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        dem_dir: directory containing downloaded DEM tiles
        output: output GeoTIFF path
        target_crs: output CRS (default WGS84)

    Returns:
        Path to the output terrain GeoTIFF.
    """
    dem_dir = dem_dir or DATA_RAW / "dem"
    output = output or DATA_OUTPUT / "terrain.tif"
    output.parent.mkdir(parents=True, exist_ok=True)

    tile_paths = sorted(dem_dir.glob("*.tif")) + sorted(dem_dir.glob("*.TIF"))
    if not tile_paths:
        raise FileNotFoundError(f"No DEM tiles found in {dem_dir}")

    print(f"Mosaicking {len(tile_paths)} DEM tile(s) ...")
    datasets = [rasterio.open(p) for p in tile_paths]
    mosaic, mosaic_transform = merge(datasets)

    # Use the CRS from the first tile
    src_crs = datasets[0].crs
    for ds in datasets:
        ds.close()

    # Clip to AOI bbox
    aoi_geom = [mapping(box(*bbox))]
    with rasterio.MemoryFile() as memfile:
        meta = {
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "count": mosaic.shape[0],
            "dtype": mosaic.dtype,
            "crs": src_crs,
            "transform": mosaic_transform,
        }
        with memfile.open(**meta) as tmp:
            tmp.write(mosaic)
            clipped, clipped_transform = mask(tmp, aoi_geom, crop=True)
            clipped_meta = tmp.meta.copy()

    clipped_meta.update(
        height=clipped.shape[1],
        width=clipped.shape[2],
        transform=clipped_transform,
    )

    # Reproject to target CRS if needed
    if str(src_crs) != target_crs:
        print(f"Reprojecting to {target_crs} ...")
        dst_transform, dst_width, dst_height = calculate_default_transform(
            src_crs, target_crs, clipped.shape[2], clipped.shape[1], *_bbox_from_transform(clipped_transform, clipped.shape)
        )
        reprojected = np.empty((clipped.shape[0], dst_height, dst_width), dtype=clipped.dtype)
        reproject(
            source=clipped,
            destination=reprojected,
            src_transform=clipped_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=target_crs,
            resampling=Resampling.bilinear,
        )
        clipped_meta.update(crs=target_crs, transform=dst_transform, width=dst_width, height=dst_height)
        final = reprojected
    else:
        final = clipped

    with rasterio.open(output, "w", **clipped_meta) as dst:
        dst.write(final)

    print(f"Terrain map saved to {output}")
    return output


def _bbox_from_transform(transform, shape) -> tuple:
    """Return (left, bottom, right, top) from a rasterio transform and array shape."""
    _, height, width = shape
    left = transform.c
    top = transform.f
    right = left + width * transform.a
    bottom = top + height * transform.e
    return left, bottom, right, top
