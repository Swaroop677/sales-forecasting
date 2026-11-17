from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class RunCreateRequest(BaseModel):
    dataset_id: str
    series_id: str = "all"
    horizon: int = Field(default=30, ge=1, le=365)
    models: list[str] = Field(default_factory=lambda: ["seasonal_naive", "holt_winters", "lightgbm", "xgboost"])
    n_folds: int = Field(default=3, ge=2, le=10)
    metric: str = Field(default="wape")  # wape, mae, rmse, smape, mase


class LeaderboardItem(BaseModel):
    model_name: str
    mae: float
    rmse: float
    wape: float
    smape: float
    mase: float
    coverage_80: Optional[float] = None
    coverage_95: Optional[float] = None
    q_80: Optional[float] = None
    q_95: Optional[float] = None
    coverage_summary: Optional[str] = None
    fit_time_sec: float
    is_best: bool = False


class ForecastPoint(BaseModel):
    date: str
    actual: Optional[float] = None
    predicted: Optional[float] = None
    models: dict[str, float] = Field(default_factory=dict)
    lower_80: Optional[float] = None
    upper_80: Optional[float] = None
    lower_95: Optional[float] = None
    upper_95: Optional[float] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None


class BacktestPoint(BaseModel):
    date: str
    actual: float
    predictions: dict[str, float] = Field(default_factory=dict)


class RunStatusResponse(BaseModel):
    id: str
    dataset_id: str
    dataset_name: str
    series_id: str
    status: str  # pending, running, completed, failed
    progress: int
    current_step: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class RunResultResponse(BaseModel):
    id: str
    dataset_id: str
    dataset_name: str
    series_id: str
    horizon: int
    metric: str
    status: str
    best_model: Optional[str] = None
    leaderboard: list[LeaderboardItem] = Field(default_factory=list)
    fold_metrics: list[dict[str, Any]] = Field(default_factory=list)
    forecast_series: list[ForecastPoint] = Field(default_factory=list)
    backtest_overlay: list[BacktestPoint] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    completed_at: Optional[datetime] = None


class RunSummaryResponse(BaseModel):
    id: str
    dataset_id: str
    dataset_name: str
    series_id: str
    horizon: int
    status: str
    best_model: Optional[str] = None
    best_wape: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
