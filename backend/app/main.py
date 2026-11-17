import os
import time
import logging

# Free-hosting & concurrency safety: cap OpenMP/BLAS threads to prevent memory explosion & segfaults
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from contextlib import asynccontextmanager

from backend.app.api.router import api_router
from backend.app.config import settings
from backend.app.db import init_db, ping_db
from backend.app.services.sample_data import ensure_sample_data_file
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("forecastly")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and sample files on startup
    init_db()
    ensure_sample_data_file()
    logger.info("Forecastly engine initialized. Ready to accept forecasting jobs.")
    yield
    logger.info("Forecastly engine shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Automated sales forecasting web service with model backtesting and leaderboard comparison.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security Headers & Structured Request Logging Middleware
@app.middleware("http")
async def security_and_logging_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "accelerometer=(), camera=(), microphone=(), geolocation=()"

    # Skip logging high-frequency static asset polls
    if not request.url.path.startswith("/assets/"):
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)"
        )

    return response


# Friendly Cold-Start 404 Recovery Handler
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == status.HTTP_404_NOT_FOUND and request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={
                "detail": exc.detail,
                "cold_start_notice": (
                    "If the application instance recently restarted on ephemeral hosting, "
                    "in-memory runs or temporary uploads may have reset. Click 'Try sample data' "
                    "or re-upload your dataset to continue seamlessly."
                ),
            },
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Root health & readiness check endpoints
@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check():
    """Liveness probe: verifies web server process is responsive."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "prophet_enabled": settings.ENABLE_PROPHET,
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        "max_upload_rows": settings.MAX_UPLOAD_ROWS,
        "version": "1.0.0",
    }


@app.get("/ready", tags=["Health"])
@app.get("/api/ready", tags=["Health"])
def readiness_check():
    """Readiness probe: verifies database connectivity and disk readiness."""
    db_ok = ping_db()
    if not db_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection probe failed",
        )
    return {
        "status": "ready",
        "database": "connected",
        "sample_data": "available",
    }


# Include API router
app.include_router(api_router)

# Mount frontend production build if present (e.g. Docker container or local production build)
frontend_dist_dir = settings.BASE_DIR / "frontend" / "dist"
if frontend_dist_dir.exists() and (frontend_dist_dir / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str, request: Request):
        # Don't intercept API or docs routes
        if full_path.startswith("api") or full_path in ["docs", "redoc", "openapi.json", "health", "ready"]:
            return None
        file_path = frontend_dist_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist_dir / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
    )
