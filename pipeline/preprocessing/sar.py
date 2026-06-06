"""
SAR preprocessing chain via ESA SNAP (through snapista).

Steps applied to each SAOCOM GRD scene:
  1. Apply orbit file
  2. Radiometric calibration → sigma0 (linear)
  3. Speckle filtering (Lee)
  4. Range-Doppler terrain correction (Copernicus DEM 30 m)
  5. Convert to dB (linear sigma0 → σ⁰ dB)
  6. Export as GeoTIFF

Requires SNAP to be installed:
    https://step.esa.int/main/download/snap-download/

snapista wraps SNAP graph execution from Python.
"""

from pathlib import Path
import subprocess
import shutil

try:
    from snapista import Graph, Operator
    SNAP_AVAILABLE = True
except ImportError:
    SNAP_AVAILABLE = False

from config import DATA_RAW


def _check_snap():
    if not SNAP_AVAILABLE:
        raise RuntimeError(
            "snapista is not installed. Run: pip install snapista\n"
            "Also ensure ESA SNAP is installed: https://step.esa.int/main/download/snap-download/"
        )
    if not shutil.which("gpt"):
        raise RuntimeError(
            "ESA SNAP 'gpt' command not found in PATH. "
            "Install SNAP and ensure its bin/ directory is in PATH."
        )


def preprocess_scene(
    input_path: Path,
    output_path: Path,
    dem_name: str = "Copernicus 30m Global DEM",
    speckle_filter: str = "Lee",
    polarisations: str = "HH,HV",
) -> Path:
    """
    Run the full SNAP preprocessing chain on one SAOCOM GRD scene.

    Args:
        input_path: path to the downloaded .zip or .dim SAOCOM scene
        output_path: output GeoTIFF path (sigma0 dB, terrain-corrected)
        dem_name: SNAP DEM name for terrain correction
        speckle_filter: SNAP speckle filter name ("Lee", "Refined Lee", etc.)
        polarisations: comma-separated list e.g. "HH,HV"

    Returns:
        Path to the output GeoTIFF.
    """
    _check_snap()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    g = Graph()

    g.add_node(
        Operator("Read", file=str(input_path)),
        node_id="read",
    )
    g.add_node(
        Operator("Apply-Orbit-File", orbitType="Sentinel Precise (Auto Download)"),
        node_id="orbit",
        source="read",
    )
    g.add_node(
        Operator(
            "Calibration",
            selectedPolarisations=polarisations,
            outputSigmaBand=True,
            outputBetaBand=False,
            outputGammaBand=False,
            outputImageInComplex=False,
        ),
        node_id="cal",
        source="orbit",
    )
    g.add_node(
        Operator("Speckle-Filter", filter=speckle_filter, filterSizeX=5, filterSizeY=5),
        node_id="speckle",
        source="cal",
    )
    g.add_node(
        Operator(
            "Terrain-Correction",
            demName=dem_name,
            pixelSpacingInMeter=20.0,
            mapProjection="AUTO:42001",  # UTM auto-zone
            nodataValueAtSea=False,
            saveDEM=False,
            saveLatLon=False,
        ),
        node_id="tc",
        source="speckle",
    )
    g.add_node(
        Operator("LinearToFromdB"),
        node_id="db",
        source="tc",
    )
    g.add_node(
        Operator("Write", file=str(output_path), formatName="GeoTIFF"),
        node_id="write",
        source="db",
    )

    print(f"Running SNAP preprocessing chain on {input_path.name} ...")
    g.run()
    print(f"Preprocessed scene saved to {output_path}")
    return output_path


def preprocess_all(
    saocom_dir: Path | None = None,
    output_dir: Path | None = None,
    **kwargs,
) -> list[Path]:
    """
    Preprocess all SAOCOM .zip scenes in saocom_dir.

    Returns list of output GeoTIFF paths.
    """
    saocom_dir = saocom_dir or DATA_RAW / "saocom"
    output_dir = output_dir or DATA_RAW / "saocom_preprocessed"
    output_dir.mkdir(parents=True, exist_ok=True)

    scenes = sorted(saocom_dir.glob("*.zip")) + sorted(saocom_dir.glob("*.dim"))
    if not scenes:
        raise FileNotFoundError(f"No SAOCOM scenes found in {saocom_dir}")

    results = []
    for scene in scenes:
        out = output_dir / f"{scene.stem}_sigma0_db.tif"
        if out.exists():
            print(f"Already preprocessed: {out.name}")
            results.append(out)
            continue
        results.append(preprocess_scene(scene, out, **kwargs))

    return results
