"""Geometry utilities shared across pipeline modules."""

import numpy as np
import rasterio
from rasterio.mask import mask as rio_mask
from shapely.geometry import box, mapping


def bbox_to_wkt(bbox: tuple[float, float, float, float]) -> str:
    """Return a WKT POLYGON string for a (min_lon, min_lat, max_lon, max_lat) bbox."""
    min_lon, min_lat, max_lon, max_lat = bbox
    return (
        f"POLYGON(({min_lon} {min_lat},{max_lon} {min_lat},"
        f"{max_lon} {max_lat},{min_lon} {max_lat},{min_lon} {min_lat}))"
    )


def clip_array_to_bbox(
    array: np.ndarray,
    meta: dict,
    bbox: tuple[float, float, float, float],
) -> tuple[np.ndarray, dict]:
    """
    Clip a (bands, H, W) array/meta to a bounding box using rasterio.

    Returns the clipped array and updated meta.
    """
    import rasterio
    from rasterio.memory import MemoryFile

    geom = [mapping(box(*bbox))]
    with rasterio.MemoryFile() as memfile:
        with memfile.open(**meta) as src:
            src.write(array)
            clipped, transform = rio_mask(src, geom, crop=True)
            new_meta = src.meta.copy()
            new_meta.update(
                transform=transform,
                height=clipped.shape[1],
                width=clipped.shape[2],
            )
    return clipped, new_meta


def tile_id_from_bbox(bbox: tuple[float, float, float, float]) -> str:
    """
    Generate a compact tile identifier from bbox coordinates.
    e.g. (-65, -38, -57, -30) → 'w65s38e57n30'
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    lon0 = f"{'w' if min_lon < 0 else 'e'}{abs(int(min_lon))}"
    lat0 = f"{'s' if min_lat < 0 else 'n'}{abs(int(min_lat))}"
    lon1 = f"{'w' if max_lon < 0 else 'e'}{abs(int(max_lon))}"
    lat1 = f"{'s' if max_lat < 0 else 'n'}{abs(int(max_lat))}"
    return f"{lon0}{lat0}{lon1}{lat1}"
