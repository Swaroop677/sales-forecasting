import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ForecastRun(SQLModel, table=True):
    __tablename__ = "forecast_runs"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    dataset_id: str = Field(index=True)
    dataset_hash: str = Field(default="")
    dataset_name: str = Field(default="")
    series_id: str = Field(default="all", index=True)
    horizon: int = Field(default=30)
    models_requested: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    n_folds: int = Field(default=3)
    metric: str = Field(default="wape")

    status: str = Field(default="pending", index=True)  # pending, running, completed, failed
    progress: int = Field(default=0)  # 0 to 100
    current_step: str = Field(default="Queued")
    error_message: Optional[str] = None

    best_model: Optional[str] = None
    leaderboard: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    fold_metrics: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    forecast_series: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    backtest_overlay: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))

    artifact_path: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = None
