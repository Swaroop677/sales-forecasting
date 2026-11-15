from typing import Any, Optional
from pydantic import BaseModel, Field


class ProfileDatasetArgs(BaseModel):
    dataset_id: str = Field(description="ID of the dataset to profile")


class ValidateDataArgs(BaseModel):
    dataset_id: str = Field(description="ID of the dataset to validate")


class CleanDataArgs(BaseModel):
    dataset_id: str = Field(description="ID of the dataset to sanitize and clean")


class RunForecastArgs(BaseModel):
    dataset_id: str = Field(description="ID of the dataset to forecast")
    horizon: int = Field(default=30, ge=1, le=365, description="Forecast horizon in days")
    series_id: str = Field(default="all", description="Series identifier ('all' for total or group key)")
    models: list[str] = Field(
        default_factory=lambda: ["seasonal_naive", "holt_winters", "lightgbm", "xgboost"],
        description="Candidate models to backtest and compare",
    )


class GetLeaderboardArgs(BaseModel):
    run_id: str = Field(description="ID of the completed forecast run")


class GetForecastArgs(BaseModel):
    run_id: str = Field(description="ID of the completed forecast run")
    series_id: Optional[str] = Field(default="all", description="Series identifier to retrieve")


class ComparePeriodsArgs(BaseModel):
    dataset_id: str = Field(description="ID of the dataset to analyze")
    period_a: str = Field(
        description="First period description or date range (e.g. 'last 4 weeks', '2023-11-01 to 2023-11-28')"
    )
    period_b: str = Field(
        description="Second period description or date range (e.g. 'prior 4 weeks', 'same period last year')"
    )
    series_id: Optional[str] = Field(default="all", description="Specific series group or 'all'")


class FindAnomaliesArgs(BaseModel):
    dataset_id: str = Field(description="ID of the dataset to audit for anomalies")
    series_id: Optional[str] = Field(default="all", description="Specific series to audit or 'all'")


class TopMoversArgs(BaseModel):
    run_id: str = Field(description="ID of the forecast run to calculate top movers across groups")


class WhatIfArgs(BaseModel):
    run_id: str = Field(description="ID of the baseline forecast run")
    promo_change_pct: Optional[float] = Field(
        default=0.0, description="Percentage change in promotion frequency/discount (e.g. 20.0 for +20%)"
    )
    price_change_pct: Optional[float] = Field(
        default=0.0, description="Percentage change in price (e.g. -10.0 for a 10% discount)"
    )
    scenario_name: Optional[str] = Field(default="Custom Scenario", description="Label for the simulation")


class ExecutiveSummaryArgs(BaseModel):
    run_id: str = Field(description="ID of the forecast run to generate executive summary facts for")


# Tool Registry Definitions for LLM Function Calling (OpenAI & Gemini format)
AGENT_TOOL_DEFINITIONS = [
    {
        "name": "profile_dataset",
        "description": "Inspects dataset quality, cadence (daily/weekly), row count, column roles, and data health score.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "ID of the dataset to profile"},
            },
            "required": ["dataset_id"],
        },
    },
    {
        "name": "validate_data",
        "description": "Validates whether the dataset meets forecasting prerequisites (minimum 2 seasonal cycles, parseable dates, valid target column).",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "ID of the dataset to validate"},
            },
            "required": ["dataset_id"],
        },
    },
    {
        "name": "clean_data",
        "description": "Executes automated sanitization on dataset (deduplicates timeline keys, fills date gaps, clips negative sales, and bounds outliers).",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "ID of the dataset to clean"},
            },
            "required": ["dataset_id"],
        },
    },
    {
        "name": "run_forecast",
        "description": "Triggers a full backtesting and forecasting job across candidate models, returns the winning model and error metrics.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "ID of the dataset"},
                "horizon": {"type": "integer", "description": "Forecast horizon in days (default: 30)"},
                "series_id": {"type": "string", "description": "Series to forecast ('all' for total aggregate, or specific store/product)"},
                "models": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Models to backtest: seasonal_naive, holt_winters, lightgbm, xgboost",
                },
            },
            "required": ["dataset_id"],
        },
    },
    {
        "name": "get_leaderboard",
        "description": "Fetches out-of-sample backtest leaderboard metrics (WAPE, MAE, RMSE, sMAPE, MASE) for all models in a forecast run.",
        "parameters": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "ID of the forecast run"},
            },
            "required": ["run_id"],
        },
    },
    {
        "name": "get_forecast",
        "description": "Fetches historical actuals and future forecasted numbers, summary totals, and trajectory percentage change.",
        "parameters": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "ID of the forecast run"},
                "series_id": {"type": "string", "description": "Series identifier ('all' by default)"},
            },
            "required": ["run_id"],
        },
    },
    {
        "name": "compare_periods",
        "description": "Compares historical sales between two distinct periods (e.g. 'last 4 weeks' vs 'prior 4 weeks' or 'same period last year').",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "ID of the dataset"},
                "period_a": {"type": "string", "description": "First period (e.g. 'last 4 weeks' or '2023-11-01 to 2023-11-28')"},
                "period_b": {"type": "string", "description": "Second period (e.g. 'prior 4 weeks' or 'same period last year')"},
                "series_id": {"type": "string", "description": "Series identifier ('all' by default)"},
            },
            "required": ["dataset_id", "period_a", "period_b"],
        },
    },
    {
        "name": "find_anomalies",
        "description": "Identifies historical anomalies and outliers (stockout dips, holiday spikes, abnormal promotional surges) using residual/IQR analysis.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "ID of the dataset"},
                "series_id": {"type": "string", "description": "Series identifier ('all' by default)"},
            },
            "required": ["dataset_id"],
        },
    },
    {
        "name": "top_movers",
        "description": "Calculates which store or product groups exhibit the largest projected volume change (highest positive and negative movers).",
        "parameters": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "ID of the forecast run"},
            },
            "required": ["run_id"],
        },
    },
    {
        "name": "what_if",
        "description": "Simulates a hypothetical pricing or promotional scenario (+/- X% price or promo lift) and calculates projected demand delta vs baseline.",
        "parameters": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "ID of the baseline forecast run"},
                "promo_change_pct": {"type": "number", "description": "Promotion discount change in percent (e.g. +20.0 for 20% more promotion)"},
                "price_change_pct": {"type": "number", "description": "Price change in percent (e.g. -10.0 for a 10% discount)"},
                "scenario_name": {"type": "string", "description": "Label for the what-if simulation"},
            },
            "required": ["run_id"],
        },
    },
    {
        "name": "executive_summary",
        "description": "Generates structured factual bullets for an executive brief: volume outlook, key drivers, operational risks, and recommendations.",
        "parameters": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "ID of the forecast run"},
            },
            "required": ["run_id"],
        },
    },
]
