import pytest
from backend.app.db import init_db
from backend.app.main import app
from backend.app.services.run_manager import execute_forecast_run
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


client = TestClient(app)


def test_health_endpoints():
    r1 = client.get("/health")
    assert r1.status_code == 200
    assert r1.json()["status"] == "healthy"

    r2 = client.get("/api/health")
    assert r2.status_code == 200
    assert r2.json()["status"] == "healthy"


def test_api_sample_clean_and_forecast_workflow():
    # 1. Create sample dataset
    resp = client.post("/api/datasets/sample")
    assert resp.status_code == 201
    dataset = resp.json()
    dataset_id = dataset["id"]

    assert dataset["date_col"] == "date"
    assert dataset["target_col"] in ["sales", "revenue"]
    assert dataset["row_count"] > 1000

    # 2. Preview dataset
    preview_resp = client.get(f"/api/datasets/{dataset_id}/preview?page=1&page_size=10")
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()
    assert len(preview_data["rows"]) == 10
    assert "date" in preview_data["columns"]

    # 3. Clean dataset
    clean_resp = client.post(f"/api/datasets/{dataset_id}/clean")
    assert clean_resp.status_code == 200
    clean_data = clean_resp.json()
    assert clean_data["id"] == dataset_id
    assert isinstance(clean_data["audit_log"], list)

    # 4. Enqueue a fast forecast run (horizon=7, 2 folds, 2 fast models)
    run_payload = {
        "dataset_id": dataset_id,
        "series_id": "all",
        "horizon": 7,
        "models": ["seasonal_naive", "lightgbm"],
        "n_folds": 2,
        "metric": "wape",
    }
    create_run_resp = client.post("/api/runs", json=run_payload)
    assert create_run_resp.status_code == 202
    run_info = create_run_resp.json()
    run_id = run_info["id"]

    # Execute synchronous step for test stability
    execute_forecast_run(run_id)

    # 5. Check run status
    status_resp = client.get(f"/api/runs/{run_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "completed"
    assert status_data["progress"] == 100

    # 6. Fetch full result
    result_resp = client.get(f"/api/runs/{run_id}/result")
    assert result_resp.status_code == 200
    result_data = result_resp.json()
    assert result_data["best_model"] is not None
    assert len(result_data["leaderboard"]) >= 2
    assert len(result_data["forecast_series"]) > 0

    # Best model badge flag
    best_entries = [m for m in result_data["leaderboard"] if m["is_best"]]
    assert len(best_entries) == 1

    # 7. Download forecast CSV
    download_resp = client.get(f"/api/runs/{run_id}/download")
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "text/csv; charset=utf-8"
    csv_text = download_resp.text
    assert "date,predicted_sales" in csv_text
