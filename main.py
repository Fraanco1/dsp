"""
DSP — Satellite Data Pipeline
Usage:
    python main.py --maps terrain slope moisture vegetation
    python main.py --maps terrain slope --bbox "-65.5,-32.5,-63.0,-29.5"
    python main.py --maps vegetation --start 2024-01-01 --end 2024-03-01
"""

import argparse
import sys
from datetime import date

from config import DEFAULT_BBOX, DEFAULT_DATE_START, DEFAULT_DATE_END
from src.download.dem import download_dem
from src.download.conae import download_saocom
from src.download.sentinel import download_sentinel1, download_sentinel2
from src.processing.terrain import build_terrain
from src.processing.slope import build_slope
from src.processing.moisture import build_moisture
from src.processing.vegetation import build_vegetation


ALL_MAPS = ["terrain", "slope", "moisture", "vegetation"]


def parse_bbox(s: str) -> tuple[float, float, float, float]:
    parts = [float(x.strip()) for x in s.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox must be 4 comma-separated floats: min_lon,min_lat,max_lon,max_lat")
    return tuple(parts)


def main():
    parser = argparse.ArgumentParser(description="Download satellite data and generate map products.")
    parser.add_argument(
        "--maps", nargs="+", choices=ALL_MAPS, default=ALL_MAPS,
        help="Which maps to generate (default: all)",
    )
    parser.add_argument(
        "--bbox", type=parse_bbox, default=DEFAULT_BBOX,
        metavar="min_lon,min_lat,max_lon,max_lat",
        help=f"Bounding box (default: Córdoba, Argentina {DEFAULT_BBOX})",
    )
    parser.add_argument("--start", default=str(DEFAULT_DATE_START), help="Start date (ISO, default: 30 days ago)")
    parser.add_argument("--end", default=str(DEFAULT_DATE_END), help="End date (ISO, default: today)")
    parser.add_argument(
        "--skip-download", action="store_true",
        help="Skip download step and use already-downloaded data",
    )
    args = parser.parse_args()

    bbox = args.bbox
    date_start = args.start
    date_end = args.end
    maps = args.maps

    print(f"\n{'='*60}")
    print(f"  DSP — Satellite Data Pipeline")
    print(f"  AOI bbox : {bbox}")
    print(f"  Period   : {date_start} → {date_end}")
    print(f"  Maps     : {', '.join(maps)}")
    print(f"{'='*60}\n")

    # ── Downloads ──────────────────────────────────────────────────
    if not args.skip_download:
        needs_dem = "terrain" in maps or "slope" in maps
        needs_sar = "moisture" in maps
        needs_s2 = "vegetation" in maps

        if needs_dem:
            print("[1/3] Downloading DEM tiles ...")
            download_dem(bbox)

        if needs_sar:
            print("[2/3] Downloading SAOCOM (SAR) data ...")
            saocom_files = download_saocom(bbox, date_start, date_end)
            if not saocom_files:
                print("  SAOCOM unavailable — falling back to Sentinel-1 ...")
                download_sentinel1(bbox, date_start, date_end)

        if needs_s2:
            print("[3/3] Downloading Sentinel-2 L2A data ...")
            download_sentinel2(bbox, date_start, date_end)

    # ── Processing ─────────────────────────────────────────────────
    outputs = {}

    if "terrain" in maps:
        print("\n[terrain] Building terrain map ...")
        outputs["terrain"] = build_terrain(bbox)

    if "slope" in maps:
        print("\n[slope] Building slope map ...")
        terrain_path = outputs.get("terrain")
        outputs["slope"] = build_slope(terrain_path)

    if "moisture" in maps:
        print("\n[moisture] Building moisture proxy map ...")
        outputs["moisture"] = build_moisture(bbox)

    if "vegetation" in maps:
        print("\n[vegetation] Building NDVI vegetation map ...")
        outputs["vegetation"] = build_vegetation(bbox)

    # ── Summary ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  Output files:")
    for name, path in outputs.items():
        print(f"    {name:12s} → {path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
