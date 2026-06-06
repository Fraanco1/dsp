import os
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_OUTPUT = BASE_DIR / "data" / "output"

# Default AOI: Córdoba province, Argentina (min_lon, min_lat, max_lon, max_lat)
DEFAULT_BBOX = (-65.5, -32.5, -63.0, -29.5)

# Default date range: last 30 days
DEFAULT_DATE_END = date.today()
DEFAULT_DATE_START = DEFAULT_DATE_END - timedelta(days=30)

# Credentials
EARTHDATA_USERNAME = os.getenv("EARTHDATA_USERNAME")
EARTHDATA_PASSWORD = os.getenv("EARTHDATA_PASSWORD")

CDSE_USER = os.getenv("CDSE_USER")
CDSE_PASSWORD = os.getenv("CDSE_PASSWORD")

CONAE_USER = os.getenv("CONAE_USER")
CONAE_PASSWORD = os.getenv("CONAE_PASSWORD")

# CONAE STAC catalog endpoint
CONAE_STAC_URL = "https://catalogos.conae.gov.ar/stac"
