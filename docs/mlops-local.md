# Local MLOps Stack (MLflow, MinIO, & Airflow)

> **Important Note:** This profile is strictly **LOCAL ONLY** for advanced experimentation and MLOps reporting. It is not bundled into the lightweight Cloud Run / Render free-tier container.

---

## 1. Running MLflow & MinIO with Docker Compose
To start the local MLflow tracking server and MinIO S3-compatible artifact storage:
```bash
docker compose -f docker-compose.mlops.yml up -d
```
- **MLflow Tracking UI**: [http://localhost:5000](http://localhost:5000)
- **MinIO Console**: [http://localhost:9001](http://localhost:9001) (`minioadmin` / `miniopassword`)

---

## 2. Airflow Orchestration DAG
The DAG file is located at `dags/forecastly_retrain_dag.py`. It showcases enterprise DAG orchestration across Forecastly's deterministic service functions:
1. `ingest_data`: Reads or synchronizes sales timeline transactions.
2. `validate_dataset`: Runs the data profiler and evaluates health scores.
3. `retrain_and_register`: Runs expanding-window backtesting across candidate models, evaluates split-conformal coverage, and registers the winning model.
