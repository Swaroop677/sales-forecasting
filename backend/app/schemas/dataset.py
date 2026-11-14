from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ColumnMappingUpdate(BaseModel):
    date_col: str
    target_col: str
    group_cols: list[str] = Field(default_factory=list)
    regressor_cols: list[str] = Field(default_factory=list)


class QualityIssue(BaseModel):
    id: str
    column: Optional[str] = None
    issue_type: str  # missing_dates, duplicates, negatives, nulls, outliers, short_history, etc.
    severity: str  # critical, warning, info
    count: int = 0
    percentage: float = 0.0
    message: str
    suggested_fix: str


class QualityReport(BaseModel):
    is_valid: bool
    frequency: str
    total_rows: int
    date_range: dict[str, Any]
    target_summary: dict[str, Any]
    issues: list[QualityIssue]
    score: int  # 0 to 100 quality score


class AuditLogEntry(BaseModel):
    action: str
    timestamp: str
    rows_affected: int
    details: str


class DatasetResponse(BaseModel):
    id: str
    name: str
    file_hash: str
    row_count: int
    col_count: int
    date_col: str
    target_col: str
    group_cols: list[str]
    regressor_cols: list[str]
    frequency: str
    quality_report: Optional[dict[str, Any]] = None
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetPreviewResponse(BaseModel):
    columns: list[str]
    dtypes: dict[str, str]
    total_rows: int
    page: int
    page_size: int
    rows: list[dict[str, Any]]


class SeriesOption(BaseModel):
    id: str  # "all" or specific group key
    name: str
    row_count: int
    date_start: str
    date_end: str
