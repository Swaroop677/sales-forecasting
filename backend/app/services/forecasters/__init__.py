from typing import Type

from backend.app.config import settings
from backend.app.services.forecasters.base import Forecaster
from backend.app.services.forecasters.holt_winters import HoltWintersForecaster
from backend.app.services.forecasters.lgbm_forecaster import LightGBMForecaster
from backend.app.services.forecasters.seasonal_naive import SeasonalNaiveForecaster
from backend.app.services.forecasters.xgboost_forecaster import XGBoostForecaster

FORECASTER_REGISTRY: dict[str, Type[Forecaster]] = {
    "seasonal_naive": SeasonalNaiveForecaster,
    "holt_winters": HoltWintersForecaster,
    "lightgbm": LightGBMForecaster,
    "xgboost": XGBoostForecaster,
}


def get_forecaster(model_key: str) -> Forecaster:
    """Returns an instantiated forecaster matching the model key."""
    clean_key = model_key.lower().strip()
    if clean_key == "prophet":
        from backend.app.services.forecasters.prophet_forecaster import ProphetForecaster
        return ProphetForecaster()

    if clean_key in FORECASTER_REGISTRY:
        return FORECASTER_REGISTRY[clean_key]()

    raise ValueError(f"Unknown forecasting model: '{model_key}'. Available: {list(FORECASTER_REGISTRY.keys())}")


def list_available_models() -> list[dict]:
    """Returns metadata for models available in this deployment."""
    models = [
        {
            "id": "seasonal_naive",
            "name": "Seasonal Naive",
            "category": "Baseline",
            "description": "Standard retail baseline repeating last observed weekly cycles.",
            "is_default": True,
        },
        {
            "id": "holt_winters",
            "name": "Holt-Winters",
            "category": "Statistical",
            "description": "Triple exponential smoothing capturing level, trend, and weekly cycles.",
            "is_default": True,
        },
        {
            "id": "lightgbm",
            "name": "LightGBM",
            "category": "Machine Learning",
            "description": "Fast tree boosting with recursive lags, rolling statistics, and regressors.",
            "is_default": True,
        },
        {
            "id": "xgboost",
            "name": "XGBoost",
            "category": "Machine Learning",
            "description": "Regularized gradient boosting trees with calendar, lag, and promotional features.",
            "is_default": True,
        },
    ]

    if settings.ENABLE_PROPHET:
        models.append({
            "id": "prophet",
            "name": "Prophet",
            "category": "Additive",
            "description": "Decomposable time-series model handling holidays and changepoints.",
            "is_default": False,
        })

    return models
