"""
DSP — Satellite Soil Analysis Pipeline (Collaborator A: pipeline layer)

Usage:
    python main.py                             # full run, default Pampas AOI
    python main.py --steps download preprocess # download + SNAP only
    python main.py --steps indices moisture clustering
    python main.py --bbox "-64,-33,-63,-32" --start 2024-01-01 --end 2024-03-01

Output:
    Cloud-Optimized GeoTIFFs in data/processed/ following the contract:
        <product>_<date>_<tile>.tif
    The backend reads these via titiler at GET /tiles/{layer}/{z}/{x}/{y}.png
"""

import argparse
import sys
from pathlib import Path
from datetime import date

from config import DEFAULT_BBOX, DEFAULT_DATE_START, DEFAULT_DATE_END, DATA_PROCESSED
from pipeline.utils.geo import tile_id_from_bbox

ALL_STEPS = ["download", "preprocess", "indices", "moisture", "clustering"]


def parse_bbox(s: str) -> tuple[float, float, float, float]:
    parts = [float(x.strip()) for x in s.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "bbox must be 4 comma-separated floats: min_lon,min_lat,max_lon,max_lat"
        )
    return tuple(parts)


def run_pipeline(bbox, date_start: str, date_end: str, steps: list[str]):
    from pipeline.download.asf import download_saocom
    from pipeline.download.sentinel import download_sentinel2
    from pipeline.download.dem import download_dem
    from pipeline.preprocessing.sar import preprocess_all
    from pipeline.processing.indices import compute_indices
    from pipeline.processing.moisture import build_moisture
    from pipeline.processing.clustering import build_clusters
    from config import DATA_RAW

    tile_id = tile_id_from_bbox(bbox)
    outputs: dict[str, Path] = {}

    # ── 1. Download ────────────────────────────────────────────────
    if "download" in steps:
        print("\n[download] Fetching SAOCOM scenes from ASF ...")
        saocom_files = download_saocom(bbox, date_start, date_end)
        if not saocom_files:
            print("  WARNING: No SAOCOM scenes found. Moisture/clustering steps need SAR data.")

        print("\n[download] Fetching Sentinel-2 L2A mosaic ...")
        s2_path = download_sentinel2(bbox, date_start, date_end)
        outputs["s2"] = s2_path

        print("\n[download] Fetching Copernicus DEM tiles ...")
        download_dem(bbox)

    # ── 2. SAR Preprocessing (SNAP) ────────────────────────────────
    preprocessed_sar: list[Path] = []
    if "preprocess" in steps:
        print("\n[preprocess] Running SNAP calibration + terrain correction ...")
        preprocessed_sar = preprocess_all(
            saocom_dir=DATA_RAW / "saocom",
            output_dir=DATA_RAW / "saocom_preprocessed",
        )
        if preprocessed_sar:
            print(f"  Preprocessed {len(preprocessed_sar)} scene(s).")

    # ── 3. Spectral Indices (Sentinel-2) ───────────────────────────
    index_paths: dict[str, Path] = {}
    if "indices" in steps:
        s2_glob = sorted((DATA_RAW / "sentinel2").glob("*.tif"))
        if not s2_glob:
            print("\n[indices] No Sentinel-2 GeoTIFF found — skipping.")
        else:
            s2_path = s2_glob[-1]  # most recent
            print(f"\n[indices] Computing spectral indices from {s2_path.name} ...")
            index_paths = compute_indices(
                s2_path=s2_path,
                bbox=bbox,
                acquisition_date=date_start,
                tile_id=tile_id,
            )

    # ── 4. Soil Moisture (WCM) ─────────────────────────────────────
    moisture_paths: dict[str, Path] = {}
    if "moisture" in steps:
        sar_glob = sorted((DATA_RAW / "saocom_preprocessed").glob("*.tif"))
        ndvi_path = index_paths.get("ndvi") or next(DATA_PROCESSED.glob(f"ndvi_*_{tile_id}.tif"), None)
        if not sar_glob:
            print("\n[moisture] No preprocessed SAR found — skipping moisture step.")
        elif not ndvi_path:
            print("\n[moisture] No NDVI COG found — run 'indices' step first.")
        else:
            sar_path = sar_glob[-1]
            print(f"\n[moisture] Deriving soil moisture from {sar_path.name} + {ndvi_path.name} ...")
            moisture_paths = build_moisture(
                sar_path=sar_path,
                ndvi_path=ndvi_path,
                acquisition_date=date_start,
                tile_id=tile_id,
            )

    # ── 5. Clustering ──────────────────────────────────────────────
    if "clustering" in steps:
        feature_paths = {
            **{k: v for k, v in index_paths.items() if k in ("ndvi", "bsi", "ndmi")},
            **{k: v for k, v in moisture_paths.items() if k == "backscatter_hh"},
        }
        # Also look for already-produced COGs from previous runs
        for product in ("ndvi", "bsi", "ndmi", "backscatter_hh"):
            if product not in feature_paths:
                matches = sorted(DATA_PROCESSED.glob(f"{product}_*_{tile_id}.tif"))
                if matches:
                    feature_paths[product] = matches[-1]

        if len(feature_paths) < 2:
            print("\n[clustering] Need at least 2 feature layers — skipping.")
        else:
            print(f"\n[clustering] Clustering with features: {list(feature_paths.keys())} ...")
            cluster_path = build_clusters(
                feature_paths=feature_paths,
                acquisition_date=date_start,
                tile_id=tile_id,
            )
            outputs["soil_cluster"] = cluster_path

    outputs.update(index_paths)
    outputs.update(moisture_paths)
    return outputs


def main():
    parser = argparse.ArgumentParser(
        description="DSP satellite soil analysis pipeline — Collaborator A layer"
    )
    parser.add_argument(
        "--steps",
        nargs="+",
        choices=ALL_STEPS,
        default=ALL_STEPS,
        help=f"Pipeline steps to run (default: all). Choices: {ALL_STEPS}",
    )
    parser.add_argument(
        "--bbox",
        type=parse_bbox,
        default=DEFAULT_BBOX,
        metavar="min_lon,min_lat,max_lon,max_lat",
        help=f"AOI bounding box (default: Argentine Pampas {DEFAULT_BBOX})",
    )
    parser.add_argument("--start", default=str(DEFAULT_DATE_START), help="Start date (ISO)")
    parser.add_argument("--end", default=str(DEFAULT_DATE_END), help="End date (ISO)")
    args = parser.parse_args()

    print(f"\n{'='*64}")
    print("  DSP — Satellite Soil Analysis Pipeline")
    print(f"  AOI      : {args.bbox}")
    print(f"  Period   : {args.start} → {args.end}")
    print(f"  Steps    : {', '.join(args.steps)}")
    print(f"  Output   : {DATA_PROCESSED}/")
    print(f"{'='*64}")

    outputs = run_pipeline(args.bbox, args.start, args.end, args.steps)

    if outputs:
        print(f"\n{'='*64}")
        print("  COGs written to data/processed/:")
        for name, path in outputs.items():
            print(f"    {name:20s} → {path.name}")
        print(f"{'='*64}\n")


if __name__ == "__main__":
    main()
