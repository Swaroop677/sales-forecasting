"""
Apache Airflow DAG: Forecastly Scheduled Retraining Pipeline (LOCAL ONLY).
Demonstrates an enterprise orchestrator mapping to Forecastly service layers:
Ingest -> Validate -> Clean -> Backtest -> Evaluate -> Register.
"""

from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:
    # Airflow not installed in lightweight free runtime
    DAG = None
    PythonOperator = None


def task_ingest(**kwargs):
    from backend.app.services.sample_data import generate_sample_sales_data
    df = generate_sample_sales_data()
    print(f"Ingested {len(df)} rows.")
    return len(df)


def task_validate(**kwargs):
    from backend.app.services.sample_data import generate_sample_sales_data
    from backend.app.services.data_profiler import profile_dataset
    df = generate_sample_sales_data()
    rep = profile_dataset(df, date_col="date", target_col="sales", group_cols=["store", "product"])
    print(f"Validation health score: {rep['health_score']}/100")
    return rep["health_score"]


def task_retrain(**kwargs):
    from backend.app.jobs.retrain import run_retrain_job
    result = run_retrain_job("airflow_retrain_report.md")
    print(f"Retrain completed: Champion model {result['best_model']} (WAPE: {result['best_wape']}%)")
    return result


if DAG is not None:
    default_args = {
        "owner": "forecastly",
        "depends_on_past": False,
        "start_date": datetime(2024, 1, 1),
        "email_on_failure": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    }

    dag = DAG(
        "forecastly_retrain_pipeline",
        default_args=default_args,
        description="Forecastly automated sales retraining pipeline",
        schedule_interval="@weekly",
        catchup=False,
    )

    t1 = PythonOperator(task_id="ingest_data", python_callable=task_ingest, dag=dag)
    t2 = PythonOperator(task_id="validate_dataset", python_callable=task_validate, dag=dag)
    t3 = PythonOperator(task_id="retrain_and_register", python_callable=task_retrain, dag=dag)

    t1 >> t2 >> t3
