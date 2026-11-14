from backend.app.api.datasets import router as datasets_router
from backend.app.api.health import router as health_router
from backend.app.api.runs import router as runs_router
from fastapi import APIRouter

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(datasets_router)
api_router.include_router(runs_router)
