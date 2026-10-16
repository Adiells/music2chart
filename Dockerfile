# ==============================================================================
# Stage 1: Build Frontend Assets (Vite + React 19 + TypeScript + Three.js)
# ==============================================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Runtime Container (Python 3.11 + PyTorch + FFmpeg + FastAPI)
# ==============================================================================
FROM python:3.11-slim AS runtime

# Prevent Python from writing bytecode and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser \
    XDG_CACHE_HOME=/home/appuser/.cache \
    TORCH_HOME=/home/appuser/.cache/torch \
    DEBIAN_FRONTEND=noninteractive

# Install essential system dependencies: ffmpeg, libsndfile1, git, and compiler tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project metadata and source packages required to install this project.
COPY pyproject.toml /app/
COPY README.md /app/
COPY config /app/config
COPY dataset /app/dataset
COPY src /app/src
COPY tests /app/tests

# Install Python dependencies without cache
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir ".[dev]"

# Copy compiled frontend SPA assets from builder stage
COPY --from=frontend-builder /build/dist /app/frontend/dist

# Create runtime directories for uploads, stems, and output containers
RUN groupadd --gid 10001 appgroup && \
    useradd --uid 10001 --gid appgroup --shell /bin/bash --create-home appuser && \
    mkdir -p /app/tmp/uploads /app/tmp/output /app/tmp/stems /home/appuser/.cache/torch /home/appuser/.cache/demucs && \
    chown -R appuser:appgroup /app /home/appuser/.cache

EXPOSE 8000

# Start asynchronous FastAPI REST service with uvicorn
USER appuser
ENTRYPOINT ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
