"""Download Sentinel-2 L2A imagery via SentinelHub (Copernicus Data Space)."""

from pathlib import Path
from datetime import datetime
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from sentinelhub import (
    SentinelHubRequest,
    DataCollection,
    MimeType,
    CRS,
    BBox,
    SHConfig,
    bbox_to_dimensions,
)
from config import DATA_RAW, SH_CLIENT_ID, SH_CLIENT_SECRET


def _get_config() -> SHConfig:
    if not SH_CLIENT_ID or not SH_CLIENT_SECRET:
        raise EnvironmentError(
            "SH_CLIENT_ID and SH_CLIENT_SECRET must be set in .env. "
            "Create an OAuth client at https://shapps.dataspace.copernicus.eu/dashboard/"
        )
    config = SHConfig()
    config.sh_client_id = SH_CLIENT_ID
    config.sh_client_secret = SH_CLIENT_SECRET
    config.sh_base_url = "https://sh.dataspace.copernicus.eu"
    config.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    return config


# Evalscript: returns B2 (Blue), B3 (Green), B4 (Red), B8 (NIR),
#             B11 (SWIR1), B12 (SWIR2), SCL (cloud mask) — all at 20m
_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{bands: ["B02","B03","B04","B08","B11","B12","SCL"], units: "DN"}],
    output: {bands: 7, sampleType: "UINT16"}
  };
}
function evaluatePixel(s) {
  return [s.B02, s.B03, s.B04, s.B08, s.B11, s.B12, s.SCL];
}
"""

BAND_NAMES = ["B02", "B03", "B04", "B08", "B11", "B12", "SCL"]
RESOLUTION_M = 20  # metres


def download_sentinel2(
    bbox: tuple[float, float, float, float],
    date_start: str,
    date_end: str,
    max_cloud_cover: int = 20,
    dest: Path | None = None,
) -> Path:
    """
    Download a cloud-filtered Sentinel-2 L2A mosaic covering bbox as a multi-band GeoTIFF.

    Bands (in order): B02, B03, B04, B08, B11, B12, SCL
    DN values are raw Sentinel-2 L2A integers (divide by 10 000 for reflectance).

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        date_start / date_end: ISO date strings
        max_cloud_cover: maximum scene cloud cover % (0–100)
        dest: destination directory (default: data/raw/sentinel2)

    Returns:
        Path to the saved GeoTIFF.
    """
    dest = dest or DATA_RAW / "sentinel2"
    dest.mkdir(parents=True, exist_ok=True)

    config = _get_config()
    sh_bbox = BBox(bbox=bbox, crs=CRS.WGS84)
    size = bbox_to_dimensions(sh_bbox, resolution=RESOLUTION_M)

    date_tag = date_start.replace("-", "")
    output_path = dest / f"s2_l2a_{date_tag}_{date_end.replace('-','')}.tif"

    if output_path.exists():
        print(f"Sentinel-2 file already exists: {output_path.name}")
        return output_path

    print(f"Requesting Sentinel-2 L2A mosaic ({size[0]}×{size[1]} px, ≤{max_cloud_cover}% cloud) ...")

    request = SentinelHubRequest(
        evalscript=_EVALSCRIPT,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A.define_from(
                    "s2", service_url=config.sh_base_url
                ),
                time_interval=(date_start, date_end),
                other_args={
                    "dataFilter": {
                        "maxCloudCoverage": max_cloud_cover,
                        "mosaickingOrder": "leastCC",
                    }
                },
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=sh_bbox,
        size=size,
        config=config,
    )

    data = request.get_data()[0]  # shape: (H, W, 7)

    transform = from_bounds(*bbox, width=size[0], height=size[1])
    meta = {
        "driver": "GTiff",
        "count": len(BAND_NAMES),
        "dtype": "uint16",
        "width": size[0],
        "height": size[1],
        "crs": "EPSG:4326",
        "transform": transform,
    }

    with rasterio.open(output_path, "w", **meta) as dst:
        for i, name in enumerate(BAND_NAMES):
            dst.write(data[:, :, i], i + 1)
            dst.update_tags(i + 1, name=name)

    print(f"Sentinel-2 mosaic saved to {output_path}")
    return output_path
