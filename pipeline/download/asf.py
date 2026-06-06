"""Download SAOCOM GRD scenes from Alaska Satellite Facility (ASF).

ASF distributes SAOCOM products under a CONAE–NASA data-sharing agreement.
Authentication uses a NASA Earthdata account (free).
"""

from pathlib import Path
import asf_search as asf
from config import DATA_RAW, EARTHDATA_USERNAME, EARTHDATA_PASSWORD


def search_saocom(
    bbox: tuple[float, float, float, float],
    date_start: str,
    date_end: str,
    processing_level: str = "GRD_HD",
) -> asf.ASFSearchResults:
    """
    Search SAOCOM scenes on ASF covering the given bbox and time window.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        date_start / date_end: ISO date strings e.g. "2024-01-01"
        processing_level: ASF product type — GRD_HD (default) or SLC

    Returns:
        ASFSearchResults iterable.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    wkt = (
        f"POLYGON(({min_lon} {min_lat},{max_lon} {min_lat},"
        f"{max_lon} {max_lat},{min_lon} {max_lat},{min_lon} {min_lat}))"
    )

    level = asf.PRODUCT_TYPE.GRD_HD if processing_level == "GRD_HD" else asf.PRODUCT_TYPE.SLC

    results = asf.search(
        platform=[asf.PLATFORM.SAOCOM1A, asf.PLATFORM.SAOCOM1B],
        processingLevel=level,
        intersectsWith=wkt,
        start=date_start,
        end=date_end,
    )
    return results


def download_saocom(
    bbox: tuple[float, float, float, float],
    date_start: str,
    date_end: str,
    processing_level: str = "GRD_HD",
    dest: Path | None = None,
) -> list[Path]:
    """
    Search and download SAOCOM scenes from ASF.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        date_start / date_end: ISO date strings
        processing_level: "GRD_HD" or "SLC"
        dest: destination directory (default: data/raw/saocom)

    Returns:
        List of downloaded file paths (.zip).
    """
    dest = dest or DATA_RAW / "saocom"
    dest.mkdir(parents=True, exist_ok=True)

    print(f"Searching ASF for SAOCOM {processing_level} scenes ...")
    results = search_saocom(bbox, date_start, date_end, processing_level)

    if not results:
        print("No SAOCOM scenes found for the given bbox and date range.")
        return []

    print(f"Found {len(results)} scene(s). Downloading to {dest} ...")

    if not EARTHDATA_USERNAME or not EARTHDATA_PASSWORD:
        raise EnvironmentError(
            "EARTHDATA_USERNAME and EARTHDATA_PASSWORD must be set in .env "
            "to download from ASF. Register at https://urs.earthdata.nasa.gov/"
        )

    session = asf.ASFSession().auth_with_creds(EARTHDATA_USERNAME, EARTHDATA_PASSWORD)
    results.download(path=str(dest), session=session)

    paths = sorted(dest.glob("*.zip"))
    print(f"Downloaded {len(paths)} file(s).")
    return paths
