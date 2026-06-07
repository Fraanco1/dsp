FROM python:3.11-slim

# GDAL system libraries required by rasterio / pyroSAR
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py main.py ./
COPY pipeline/ ./pipeline/

# data/ is mounted as a volume by docker-compose — not baked into the image
RUN mkdir -p data/raw data/processed

CMD ["python", "main.py"]
