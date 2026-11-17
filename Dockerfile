# ==============================================================================
# Stage 1: Build Frontend (Vite + React + TypeScript)
# ==============================================================================
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Runtime Backend (Python 3.11 + FastAPI + ML Packages)
# ==============================================================================
FROM python:3.11-slim AS runtime

# Install system dependencies including OpenMP runtime for LightGBM / XGBoost
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy source code and sample data
COPY backend/ ./backend/
COPY data/ ./data/

# Copy built frontend static assets into production location
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Ensure runtime directories exist
RUN mkdir -p storage/artifacts storage/datasets

# Environment defaults (listening on $PORT, default 8080)
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV MKL_NUM_THREADS=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Execute FastAPI backend via Uvicorn with variable port substitution
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
