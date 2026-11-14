import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Dataset(SQLModel, table=True):
    __tablename__ = "datasets"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(index=True)
    file_path: str
    file_hash: str = Field(index=True)
    row_count: int = 0
    col_count: int = 0

    # Auto-detected or mapped column schema
    date_col: str = ""
    target_col: str = ""
    group_cols: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    regressor_cols: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    frequency: str = "D"

    # Data profiling report & audit logs
    quality_report: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    audit_log: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
