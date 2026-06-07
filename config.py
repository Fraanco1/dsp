import os
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"  # Pipeline → Backend contract

# AOI: Argentine Pampas (Buenos Aires, Córdoba, Santa Fe, La Pampa)
# West: -65°, East: -57°, South: -38°, North: -30°
DEFAULT_BBOX = (-65.0, -38.0, -57.0, -30.0)  # (min_lon, min_lat, max_lon, max_lat)

# Default date range: last 30 days
DEFAULT_DATE_END = date.today()
DEFAULT_DATE_START = DEFAULT_DATE_END - timedelta(days=30)

# NASA Earthdata — for ASF (SAOCOM) download and Copernicus DEM
EARTHDATA_USERNAME = os.getenv("EARTHDATA_USERNAME")
EARTHDATA_PASSWORD = os.getenv("EARTHDATA_PASSWORD")

# Copernicus Data Space / SentinelHub — for Sentinel-2 access
# OAuth credentials from https://shapps.dataspace.copernicus.eu/dashboard/
SH_CLIENT_ID = os.getenv("SH_CLIENT_ID")
SH_CLIENT_SECRET = os.getenv("SH_CLIENT_SECRET")

# CONAE direct catalog (optional, ASF is preferred programmatically)
CONAE_USER = os.getenv("CONAE_USER")
CONAE_PASSWORD = os.getenv("CONAE_PASSWORD")
