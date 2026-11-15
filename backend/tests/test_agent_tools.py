import pytest
from sqlmodel import Session, select
from backend.app.api.datasets import create_sample_dataset
from backend.app.db import engine, init_db
from backend.app.models.dataset import Dataset
from backend.app.services.agent_tools.handlers import (
    execute_tool,
    handle_clean_data,
    handle_compare_periods,
    handle_executive_summary,
    handle_find_anomalies,
    handle_get_forecast,
    handle_get_leaderboard,
    handle_profile_dataset,
    handle_run_forecast,
    handle_top_movers,
    handle_validate_data,
    handle_what_if,
)


@pytest.fixture(scope="module", autouse=True)
def setup_test_data():
    init_db()
    with Session(engine) as session:
        # Create sample dataset if not present
        stmt = select(Dataset).limit(1)
        dataset = session.exec(stmt).first()
        if not dataset:
            create_sample_dataset(session=session)


def get_sample_dataset_id() -> str:
    with Session(engine) as session:
        return session.exec(select(Dataset).limit(1)).first().id


def test_tool_profile_and_validate_dataset():
    with Session(engine) as session:
        ds_id = get_sample_dataset_id()

        # Profile
        res_prof = handle_profile_dataset(session, ds_id)
        assert "result" in res_prof
        assert res_prof["result"]["row_count"] > 1000
        assert res_prof["result"]["health_score"] >= 80

        # Validate
        res_val = handle_validate_data(session, ds_id)
        assert res_val["result"]["is_valid_for_forecasting"] is True
        assert "recommendation" in res_val["result"]


def test_tool_clean_data():
    with Session(engine) as session:
        ds_id = get_sample_dataset_id()
        res_clean = handle_clean_data(session, ds_id)
        assert "result" in res_clean
        assert "actions_taken" in res_clean["result"]
        assert res_clean["result"]["rows_after_clean"] > 0


def test_tool_run_forecast_and_retrieval():
    with Session(engine) as session:
        ds_id = get_sample_dataset_id()

        # Run fast 7-day forecast
        res_run = handle_run_forecast(
            session=session,
            dataset_id=ds_id,
            horizon=7,
            series_id="all",
            models=["seasonal_naive", "lightgbm"],
        )
        assert "result" in res_run
        run_id = res_run["result"]["run_id"]
        assert run_id is not None
        assert res_run["result"]["best_model"] is not None
        assert res_run["chart_spec"]["type"] == "bar"

        # Leaderboard
        res_lb = handle_get_leaderboard(session, run_id)
        assert len(res_lb["result"]["models"]) >= 2
        assert res_lb["result"]["winning_model"] is not None

        # Forecast
        res_fc = handle_get_forecast(session, run_id)
        assert res_fc["result"]["forecast_total"] > 0
        assert res_fc["result"]["horizon_days"] == 7
        assert res_fc["chart_spec"]["type"] == "forecast"


def test_tool_compare_periods():
    with Session(engine) as session:
        ds_id = get_sample_dataset_id()
        res = handle_compare_periods(session, ds_id, period_a="last 4 weeks", period_b="prior 4 weeks")
        assert "result" in res
        assert "period_a" in res["result"]
        assert "period_b" in res["result"]
        assert "difference" in res["result"]
        assert res["chart_spec"]["type"] == "comparison_bars"


def test_tool_find_anomalies():
    with Session(engine) as session:
        ds_id = get_sample_dataset_id()
        res = handle_find_anomalies(session, ds_id)
        assert "result" in res
        assert "anomalies" in res["result"]
        assert res["chart_spec"]["type"] == "anomalies"


def test_tool_top_movers_and_what_if_and_executive_summary():
    with Session(engine) as session:
        ds_id = get_sample_dataset_id()
        # Ensure a run exists
        fc = handle_run_forecast(session, ds_id, horizon=7, series_id="all", models=["seasonal_naive"])
        run_id = fc["result"]["run_id"]

        # Top Movers
        res_movers = handle_top_movers(session, run_id)
        assert "result" in res_movers

        # What-If Simulation
        res_sim = handle_what_if(session, run_id, promo_change_pct=25.0, price_change_pct=-10.0)
        assert "result" in res_sim
        assert "simulation_disclaimer" in res_sim["result"]
        assert res_sim["result"]["volume_impact_pct"] > 0  # +25% promo and -10% price yields volume lift
        assert res_sim["chart_spec"]["type"] == "scenario_comparison"

        # Executive Summary
        res_summary = handle_executive_summary(session, run_id)
        assert "result" in res_summary
        facts = res_summary["result"]["facts"]
        assert "outlook" in facts
        assert "drivers" in facts
        assert "risks" in facts
        assert "recommended_actions" in facts
        assert "confidence" in facts


def test_execute_tool_dispatcher():
    with Session(engine) as session:
        ds_id = get_sample_dataset_id()
        res = execute_tool(session, "validate_data", {"dataset_id": ds_id})
        assert "result" in res
        assert res["result"]["is_valid_for_forecasting"] is True

        # Invalid tool returns clean error
        err_res = execute_tool(session, "non_existent_tool", {})
        assert "error" in err_res
