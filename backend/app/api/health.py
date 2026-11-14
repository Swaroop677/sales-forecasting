from backend.app.config import settings
from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "prophet_enabled": settings.ENABLE_PROPHET,
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024),
        "max_upload_rows": settings.MAX_UPLOAD_ROWS,
        "version": "1.0.0",
    }
