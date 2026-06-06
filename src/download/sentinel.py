"""Download Sentinel-1 (SAR) and Sentinel-2 (optical) from Copernicus Data Space."""

from pathlib import Path
from cdsetool.query import query_features
from cdsetool.download import download_features
from cdsetool.credentials import Credentials
from config import DATA_RAW, CDSE_USER, CDSE_PASSWORD


def _get_credentials() -> Credentials | None:
    if CDSE_USER and CDSE_PASSWORD:
        return Credentials(CDSE_USER, CDSE_PASSWORD)
    return None


def download_sentinel1(
    bbox: tuple[float, float, float, float],
    date_start: str,
    date_end: str,
    dest: Path | None = None,
) -> list[Path]:
    """
    Download Sentinel-1 GRD IW scenes (VV+VH) covering bbox.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        date_start / date_end: ISO date strings
        dest: destination directory

    Returns:
        List of downloaded .SAFE or .zip paths.
    """
    dest = dest or DATA_RAW / "sentinel1"
    dest.mkdir(parents=True, exist_ok=True)

    min_lon, min_lat, max_lon, max_lat = bbox
    footprint = (
        f"POLYGON(({min_lon} {min_lat},{max_lon} {min_lat},"
        f"{max_lon} {max_lat},{min_lon} {max_lat},{min_lon} {min_lat}))"
    )

    print("Searching Copernicus Data Space for Sentinel-1 GRD ...")
    features = list(
        query_features(
            "Sentinel1",
            {
                "startDate": date_start,
                "completionDate": date_end,
                "processingLevel": "LEVEL1",
                "productType": "IW_GRDH_1S",
                "geometry": footprint,
            },
        )
    )

    if not features:
        print("No Sentinel-1 scenes found.")
        return []

    print(f"Found {len(features)} scene(s). Downloading to {dest} ...")
    creds = _get_credentials()
    paths = list(download_features(features, str(dest), credentials=creds))
    return [Path(p) for p in paths]


def download_sentinel2(
    bbox: tuple[float, float, float, float],
    date_start: str,
    date_end: str,
    max_cloud_cover: int = 20,
    dest: Path | None = None,
) -> list[Path]:
    """
    Download Sentinel-2 L2A scenes (surface reflectance) covering bbox.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        date_start / date_end: ISO date strings
        max_cloud_cover: maximum cloud cover percentage (0-100)
        dest: destination directory

    Returns:
        List of downloaded .SAFE or .zip paths.
    """
    dest = dest or DATA_RAW / "sentinel2"
    dest.mkdir(parents=True, exist_ok=True)

    min_lon, min_lat, max_lon, max_lat = bbox
    footprint = (
        f"POLYGON(({min_lon} {min_lat},{max_lon} {min_lat},"
        f"{max_lon} {max_lat},{min_lon} {max_lat},{min_lon} {min_lat}))"
    )

    print("Searching Copernicus Data Space for Sentinel-2 L2A ...")
    features = list(
        query_features(
            "Sentinel2",
            {
                "startDate": date_start,
                "completionDate": date_end,
                "processingLevel": "S2MSI2A",
                "cloudCover": f"[0,{max_cloud_cover}]",
                "geometry": footprint,
            },
        )
    )

    if not features:
        print("No Sentinel-2 scenes found.")
        return []

    print(f"Found {len(features)} scene(s). Downloading to {dest} ...")
    creds = _get_credentials()
    paths = list(download_features(features, str(dest), credentials=creds))
    return [Path(p) for p in paths]
