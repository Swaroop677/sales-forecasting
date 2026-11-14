from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from backend.app.config import settings
from backend.app.db import engine
from backend.app.models.dataset import Dataset
from backend.app.models.run import ForecastRun
from backend.app.services.backtest import run_rolling_origin_backtest
from sqlmodel import Session


def execute_forecast_run(run_id: str) -> None:
    """
    Executes forecast run asynchronously via FastAPI BackgroundTasks:
    1. Loads dataset and parameters from database.
    2. Slices series (overall aggregate or single series group).
    3. Runs expanding-window backtesting and evaluation.
    4. Serializes the winning model artifact (joblib) into storage/artifacts.
    5. Saves full metrics, leaderboard, and forecast points to SQLite.
    """
    with Session(engine) as session:
        run = session.get(ForecastRun, run_id)
        if not run:
            return

        run.status = "running"
        run.progress = 5
        run.current_step = "Loading dataset"
        session.add(run)
        session.commit()

        dataset = session.get(Dataset, run.dataset_id)
        if not dataset:
            run.status = "failed"
            run.error_message = "Dataset not found in database."
            session.add(run)
            session.commit()
            return

        # Friendly 404/failure if ephemeral disk restarted
        dataset_path = Path(dataset.file_path)
        if not dataset_path.exists():
            run.status = "failed"
            run.error_message = (
                "Dataset file not found on disk (ephemeral disk may have restarted). "
                "Please re-upload your file or click 'Use sample data'."
            )
            session.add(run)
            session.commit()
            return

        try:
            # Read dataset file
            if dataset_path.suffix.lower() in [".xlsx", ".xls"]:
                df = pd.read_excel(dataset_path)
            else:
                df = pd.read_csv(dataset_path)

            date_col = dataset.date_col
            target_col = dataset.target_col
            group_cols = dataset.group_cols or []
            regressor_cols = dataset.regressor_cols or []

            # 2. Slice series
            run.progress = 8
            run.current_step = "Filtering series"
            session.add(run)
            session.commit()

            if run.series_id != "all" and group_cols:
                # Format: "val1__val2" or "Store_A__Product_1"
                parts = run.series_id.split("__")
                query_mask = pd.Series([True] * len(df))
                for g_idx, g_col in enumerate(group_cols):
                    if g_idx < len(parts) and g_col in df.columns:
                        query_mask = query_mask & (df[g_col].astype(str) == parts[g_idx])
                df_series = df[query_mask].copy()
            else:
                # Combined total series: group by date and sum target, mean regressors
                agg_dict = {target_col: "sum"}
                for r in regressor_cols:
                    if r in df.columns:
                        agg_dict[r] = "mean"
                # Check if group columns exist and multiple rows per date
                if df[date_col].duplicated().any():
                    df_series = df.groupby(date_col, as_index=False).agg(agg_dict)
                else:
                    df_series = df.copy()

            # Ensure numeric target
            df_series[target_col] = pd.to_numeric(df_series[target_col], errors="coerce").fillna(0)
            df_series = df_series.sort_values(by=date_col).reset_index(drop=True)

            def progress_callback(pct: int, step_desc: str):
                run.progress = pct
                run.current_step = step_desc
                session.add(run)
                session.commit()

            # 3. Execute backtest
            result = run_rolling_origin_backtest(
                df=df_series,
                date_col=date_col,
                target_col=target_col,
                regressor_cols=regressor_cols,
                horizon=run.horizon,
                models=run.models_requested,
                n_folds=run.n_folds,
                metric_to_optimize=run.metric,
                progress_callback=progress_callback,
            )

            # 4. Save model artifact
            artifact_filename = f"model_{run.id}_{result['best_model_key']}.joblib"
            artifact_file = settings.STORAGE_DIR / "artifacts" / artifact_filename
            joblib.dump(result["best_model_instance"], artifact_file)

            # 5. Update run record
            run.status = "completed"
            run.progress = 100
            run.current_step = "Completed"
            run.best_model = result["best_model_name"]
            run.leaderboard = result["leaderboard"]
            run.fold_metrics = result["fold_metrics"]
            run.forecast_series = result["forecast_series"]
            run.backtest_overlay = result["backtest_overlay"]
            run.artifact_path = str(artifact_file)
            run.completed_at = datetime.now(timezone.utc)

            session.add(run)
            session.commit()

        except Exception as e:
            run.status = "failed"
            run.progress = 0
            run.current_step = "Failed"
            run.error_message = f"Error during model training/backtesting: {str(e)}"
            session.add(run)
            session.commit()
