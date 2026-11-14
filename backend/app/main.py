from contextlib import asynccontextmanager

from backend.app.api.router import api_router
from backend.app.config import settings
from backend.app.db import init_db
from backend.app.services.sample_data import ensure_sample_data_file
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and sample files on startup
    init_db()
    ensure_sample_data_file()
    yield


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

# Root health check endpoint
@app.get("/health", tags=["Health"])
def root_health():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "prophet_enabled": settings.ENABLE_PROPHET,
        "version": "1.0.0",
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
        if full_path.startswith("api") or full_path in ["docs", "redoc", "openapi.json", "health"]:
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
        reload=settings.DEBUG,
    )
