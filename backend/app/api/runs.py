import io
import os

import pandas as pd
from backend.app.db import get_session
from backend.app.models.dataset import Dataset
from backend.app.models.run import ForecastRun
from backend.app.schemas.run import (
    RunCreateRequest,
    RunResultResponse,
    RunStatusResponse,
    RunSummaryResponse,
)
from backend.app.services.forecasters import list_available_models
from backend.app.services.run_manager import execute_forecast_run
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlmodel import Session, select

router = APIRouter(prefix="/runs", tags=["Forecast Runs"])


@router.get("/models")
def get_available_models():
    """Returns available forecasting models and metadata."""
    return list_available_models()


@router.post("", response_model=RunStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def create_run(
    request: RunCreateRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Enqueues a rolling-origin backtest and multi-step forecast job."""
    dataset = session.get(Dataset, request.dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found. Please upload a dataset or use sample data.",
        )

    # Validate models requested
    valid_model_ids = {m["id"] for m in list_available_models()}
    selected_models = [m for m in request.models if m in valid_model_ids]
    if not selected_models:
        selected_models = ["seasonal_naive", "holt_winters", "lightgbm", "xgboost"]

    run = ForecastRun(
        dataset_id=dataset.id,
        dataset_hash=dataset.file_hash,
        dataset_name=dataset.name,
        series_id=request.series_id,
        horizon=request.horizon,
        models_requested=selected_models,
        n_folds=request.n_folds,
        metric=request.metric,
        status="pending",
        progress=0,
        current_step="Validating parameters",
    )

    session.add(run)
    session.commit()
    session.refresh(run)

    # Launch background job in-process
    background_tasks.add_task(execute_forecast_run, run.id)

    return run


@router.get("/{run_id}", response_model=RunStatusResponse)
def get_run_status(run_id: str, session: Session = Depends(get_session)):
    """Pollable endpoint for tracking training/backtesting progress."""
    run = session.get(ForecastRun, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Forecast run not found or was deleted.",
        )
    return run


@router.get("/{run_id}/result", response_model=RunResultResponse)
def get_run_result(run_id: str, session: Session = Depends(get_session)):
    """Fetches full forecast output, leaderboard, and backtest comparison points."""
    run = session.get(ForecastRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forecast run not found.")

    if run.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=run.error_message or "Forecast run failed.",
        )

    if run.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail=f"Forecast is currently {run.status} ({run.progress}% - {run.current_step}).",
        )

    # Reconstruct summary dict if not explicitly saved
    best_item = next((item for item in (run.leaderboard or []) if item.get("is_best")), None)
    best_wape = best_item.get("wape", 0.0) if best_item else 0.0

    forecast_pts = [p for p in (run.forecast_series or []) if p.get("predicted") is not None]
    forecast_total = sum(p.get("predicted", 0.0) for p in forecast_pts)

    actual_pts = [p for p in (run.forecast_series or []) if p.get("actual") is not None]
    last_actual_total = sum(p.get("actual", 0.0) for p in actual_pts[-run.horizon :]) if actual_pts else 0.0
    pct_change = (
        round(((forecast_total - last_actual_total) / max(1.0, last_actual_total)) * 100.0, 1)
        if last_actual_total > 0
        else 0.0
    )

    summary = {
        "last_period_total": round(last_actual_total, 2),
        "forecast_total": round(forecast_total, 2),
        "pct_change": pct_change,
        "best_model": run.best_model or "Best Model",
        "best_wape": best_wape,
        "horizon": run.horizon,
        "n_folds": run.n_folds,
    }

    return RunResultResponse(
        id=run.id,
        dataset_id=run.dataset_id,
        dataset_name=run.dataset_name,
        series_id=run.series_id,
        horizon=run.horizon,
        metric=run.metric,
        status=run.status,
        best_model=run.best_model,
        leaderboard=run.leaderboard or [],
        fold_metrics=run.fold_metrics or [],
        forecast_series=run.forecast_series or [],
        backtest_overlay=run.backtest_overlay or [],
        summary=summary,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


@router.get("", response_model=list[RunSummaryResponse])
def list_runs(session: Session = Depends(get_session)):
    """Lists historical forecast runs for comparison and auditing."""
    statement = select(ForecastRun).order_by(ForecastRun.created_at.desc()).limit(50)
    runs = session.exec(statement).all()

    summary_list = []
    for r in runs:
        best_wape = None
        if r.leaderboard:
            best_entry = next((item for item in r.leaderboard if item.get("is_best")), None)
            if best_entry:
                best_wape = best_entry.get("wape")

        summary_list.append(
            RunSummaryResponse(
                id=r.id,
                dataset_id=r.dataset_id,
                dataset_name=r.dataset_name,
                series_id=r.series_id,
                horizon=r.horizon,
                status=r.status,
                best_model=r.best_model,
                best_wape=best_wape,
                created_at=r.created_at,
                completed_at=r.completed_at,
            )
        )

    return summary_list


@router.get("/{run_id}/download")
def download_forecast_csv(run_id: str, session: Session = Depends(get_session)):
    """Exports future forecast predictions and model breakdowns as a downloadable CSV."""
    run = session.get(ForecastRun, run_id)
    if not run or not run.forecast_series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forecast run data not found.")

    rows = []
    for pt in run.forecast_series:
        if pt.get("predicted") is not None:
            row_dict = {
                "date": pt["date"],
                "predicted_sales": pt.get("predicted"),
                "lower_bound_80": pt.get("lower_bound"),
                "upper_bound_80": pt.get("upper_bound"),
            }
            # Add individual models
            if pt.get("models"):
                for m_name, m_val in pt["models"].items():
                    row_dict[f"model_{m_name.lower().replace(' ', '_')}"] = m_val
            rows.append(row_dict)

    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No forecast points available.")

    df_export = pd.DataFrame(rows)
    stream = io.StringIO()
    df_export.to_csv(stream, index=False)

    return Response(
        content=stream.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=forecast_{run.id[:8]}.csv"},
    )


# ==========================================
# Phase 3: Advanced Analytics & MLOps Routes
# ==========================================

@router.get("/{run_id}/explain")
def get_run_explainability(
    run_id: str,
    date: str = None,
    session: Session = Depends(get_session),
):
    """
    Computes global and local feature importance via native TreeSHAP (for LightGBM/XGBoost)
    or seasonal decomposition (for Holt-Winters/Naive).
    """
    from backend.app.services.ml.explainability import explain_decomposition, explain_tree_forecast

    run = session.get(ForecastRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    dataset = session.get(Dataset, run.dataset_id)
    if not dataset or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file missing.")

    df = pd.read_csv(dataset.file_path)
    future_dates = [pt["date"] for pt in run.forecast_series if pt.get("predicted") is not None]

    # Check if champion model artifact exists on disk
    if run.artifact_path and os.path.exists(run.artifact_path):
        try:
            import joblib
            model_artifact = joblib.load(run.artifact_path)
            # Try to explain tree model
            from backend.app.services.feature_builder import build_tabular_features
            df_clean = df.dropna(subset=[dataset.date_column, dataset.target_column]).sort_values(by=dataset.date_column)
            feat_df, target_series, feat_names = build_tabular_features(
                df=df_clean,
                date_col=dataset.date_column,
                target_col=dataset.target_column,
                regressor_cols=dataset.regressor_columns or [],
            )
            # Get underlying regressor inside the Forecaster wrapper if present
            raw_model = getattr(model_artifact, "model", model_artifact)
            explanation = explain_tree_forecast(
                model=raw_model,
                feature_names=feat_names,
                X_sample=feat_df.tail(60).values,
                target_date=date,
                future_dates=future_dates,
            )
            return explanation
        except Exception:
            pass

    # Fallback to seasonal decomposition
    return explain_decomposition(df, dataset.date_column, dataset.target_column)


@router.get("/{run_id}/segments")
def get_run_segment_performance(
    run_id: str,
    session: Session = Depends(get_session),
):
    """Returns cross-sectional metrics sliced by store/product, season, and promotions."""
    from backend.app.services.ml.segments import compute_segment_and_season_performance

    run = session.get(ForecastRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    dataset = session.get(Dataset, run.dataset_id)
    if not dataset or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file missing.")

    df = pd.read_csv(dataset.file_path)
    return compute_segment_and_season_performance(
        df=df,
        date_col=dataset.date_column,
        target_col=dataset.target_column,
        group_cols=dataset.group_columns or [],
        regressor_cols=dataset.regressor_columns or [],
        backtest_overlay=run.backtest_overlay or [],
    )


@router.get("/{run_id}/inventory")
def get_run_inventory_support(
    run_id: str,
    lead_time_days: int = 7,
    service_level: str = "95%",
    current_stock: float = 300.0,
    session: Session = Depends(get_session),
):
    """
    Computes statistical safety stock, reorder point, and replenishment recommendations.
    Clearly labelled: Extension: decision support, not advice.
    """
    from backend.app.services.ml.inventory import calculate_inventory_recommendations

    run = session.get(ForecastRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")

    residuals = []
    if run.backtest_overlay:
        best_name = run.best_model
        for pt in run.backtest_overlay:
            act = pt.get("actual", 0.0)
            pred = pt.get("predictions", {}).get(best_name, act)
            residuals.append(abs(float(act) - float(pred)))

    return calculate_inventory_recommendations(
        forecast_points=run.forecast_series or [],
        backtest_residuals=residuals,
        lead_time_days=lead_time_days,
        service_level=service_level,
        current_stock=current_stock,
    )


@router.get("/{run_id}/inventory/export")
def export_inventory_csv(
    run_id: str,
    lead_time_days: int = 7,
    service_level: str = "95%",
    current_stock: float = 300.0,
    session: Session = Depends(get_session),
):
    """Downloads inventory decision support table as CSV."""
    from backend.app.services.ml.inventory import (
        calculate_inventory_recommendations,
        generate_inventory_csv,
    )

    run = session.get(ForecastRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")

    residuals = [abs(pt.get("actual", 0) - pt.get("predictions", {}).get(run.best_model, 0)) for pt in (run.backtest_overlay or [])]
    inv_data = calculate_inventory_recommendations(
        forecast_points=run.forecast_series or [],
        backtest_residuals=residuals,
        lead_time_days=lead_time_days,
        service_level=service_level,
        current_stock=current_stock,
    )
    csv_text = generate_inventory_csv(inv_data)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=inventory_support_{run.id[:8]}.csv"},
    )


@router.get("/{run_id}/export/excel")
def export_run_excel(run_id: str, session: Session = Depends(get_session)):
    """Exports multi-sheet Excel workbook: Forecast, Leaderboard, Inventory, Metadata."""
    from backend.app.services.ml.excel_export import generate_multisheet_excel_report
    from backend.app.services.ml.inventory import calculate_inventory_recommendations

    run = session.get(ForecastRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")

    residuals = [abs(pt.get("actual", 0) - pt.get("predictions", {}).get(run.best_model, 0)) for pt in (run.backtest_overlay or [])]
    inv_data = calculate_inventory_recommendations(
        forecast_points=run.forecast_series or [],
        backtest_residuals=residuals,
        lead_time_days=7,
        service_level="95%",
        current_stock=300.0,
    )

    excel_bytes = generate_multisheet_excel_report(run_dict=run.dict(), inventory_dict=inv_data)
    return Response(
        content=excel_bytes.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=forecastly_report_{run.id[:8]}.xlsx"},
    )
