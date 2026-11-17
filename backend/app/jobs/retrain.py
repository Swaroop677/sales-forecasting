"""
Automated Scheduled Retraining Job.
Can be executed via GitHub Actions cron, cron daemon, or command line:
    python -m backend.app.jobs.retrain
Trains candidate forecasters, selects the champion model by WAPE, evaluates conformal intervals,
and outputs a markdown metrics report artifact.
"""

import os
import sys
from datetime import datetime
from sqlmodel import Session, select

from backend.app.db import engine, init_db
from backend.app.models.dataset import Dataset
from backend.app.models.run import Run
from backend.app.services.backtest import run_rolling_origin_backtest
from backend.app.services.sample_data import generate_sample_sales_data


def run_retrain_job(output_md_path: str = "retrain_report.md") -> dict:
    print(f"[{datetime.now().isoformat()}] Starting scheduled retraining job...")
    init_db()

    with Session(engine) as session:
        # 1. Fetch or create reference dataset
        dataset = session.exec(select(Dataset).limit(1)).first()
        if not dataset:
            print("No existing dataset found. Generating synthetic retail dataset...")
            sample_df = generate_sample_sales_data()
            dataset = Dataset(
                name="Scheduled Retrain Sample Data",
                original_filename="sales.csv",
                file_path="data/sample/sales.csv",
                row_count=len(sample_df),
                file_size_bytes=os.path.getsize("data/sample/sales.csv") if os.path.exists("data/sample/sales.csv") else 50000,
                date_column="date",
                target_column="sales",
                group_columns=["store", "product"],
                regressor_columns=["promo", "price"],
                status="ready",
            )
            session.add(dataset)
            session.commit()
            session.refresh(dataset)
            df = sample_df
        else:
            print(f"Retraining on dataset '{dataset.name}' (ID: {dataset.id})...")
            import pandas as pd
            if os.path.exists(dataset.file_path):
                df = pd.read_csv(dataset.file_path)
            else:
                df = generate_sample_sales_data()

        # 2. Run backtest with 3 folds across candidate models
        models = ["seasonal_naive", "holt_winters", "lightgbm", "xgboost"]
        backtest_result = run_rolling_origin_backtest(
            df=df,
            date_col=dataset.date_column,
            target_col=dataset.target_column,
            regressor_cols=dataset.regressor_columns or [],
            horizon=30,
            models=models,
            n_folds=3,
            metric_to_optimize="wape",
        )

        leaderboard = backtest_result["leaderboard"]
        summary = backtest_result["summary"]
        best_model = summary["best_model"]
        best_wape = summary["best_wape"]
        cov_80 = summary.get("coverage_80", 80.0)
        cov_95 = summary.get("coverage_95", 95.0)

        # 3. Record run in SQLite registry
        run_record = Run(
            dataset_id=dataset.id,
            series_id="all",
            horizon=30,
            models=models,
            n_folds=3,
            metric="wape",
            status="completed",
            progress=100,
            current_step="Scheduled retrain complete",
            best_model=best_model,
            best_wape=best_wape,
            leaderboard=leaderboard,
            fold_metrics=backtest_result["fold_metrics"],
            forecast_series=backtest_result["forecast_series"],
            backtest_overlay=backtest_result["backtest_overlay"],
            summary=summary,
            completed_at=datetime.utcnow(),
        )
        session.add(run_record)
        session.commit()
        session.refresh(run_record)

        print(f"Retraining successful! Champion model: {best_model} (WAPE: {best_wape}%). Run ID: {run_record.id}")

        # 4. Generate Markdown Report Artifact
        md_content = f"""# Forecastly Automated Retraining Report
Generated: **{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}**  
Dataset: **{dataset.name}** (`{dataset.row_count:,}` rows)  
Run ID: `{run_record.id}`

## Champion Model
- **Winning Model**: `{best_model}`
- **Out-of-Sample WAPE**: **{best_wape}%**
- **Forecast Horizon**: 30 days
- **Conformal Coverage (80% target)**: **{cov_80}%**
- **Conformal Coverage (95% target)**: **{cov_95}%**

## Model Leaderboard
| Model | WAPE (%) | MAE | RMSE | sMAPE (%) | MASE | 80% Coverage | Fit Time (s) |
|---|---|---|---|---|---|---|---|
"""
        for item in leaderboard:
            star = " 🏆" if item.get("is_best") else ""
            md_content += (
                f"| {item['model_name']}{star} | {item['wape']:.2f}% | {item['mae']:.2f} | "
                f"{item['rmse']:.2f} | {item['smape']:.2f}% | {item['mase']:.3f} | "
                f"{item.get('coverage_80', 80.0):.1f}% | {item['fit_time_sec']:.2f}s |\n"
            )

        md_content += f"""
## Forecast KPI Summary
- **Historical 30-Day Actual Total**: {summary.get('last_period_total', 0.0):,.0f} units
- **Forecasted 30-Day Total**: {summary.get('forecast_total', 0.0):,.0f} units
- **Projected Period-over-Period Delta**: {summary.get('pct_change', 0.0):+.1f}%

---
*Report automatically produced by Forecastly Scheduled Retrain Job.*
"""
        with open(output_md_path, "w") as f:
            f.write(md_content)

        print(f"Metrics report written to: {output_md_path}")
        return {
            "run_id": run_record.id,
            "best_model": best_model,
            "best_wape": best_wape,
            "report_path": output_md_path,
        }


if __name__ == "__main__":
    report_file = sys.argv[1] if len(sys.argv) > 1 else "retrain_report.md"
    run_retrain_job(report_file)
