import numpy as np
import pytest
from backend.app.services.metrics import (
    calculate_all_metrics,
    mean_absolute_error,
    mean_absolute_scaled_error,
    root_mean_squared_error,
    symmetric_mean_absolute_percentage_error,
    weighted_absolute_percentage_error,
)


def test_mae_and_rmse():
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred = np.array([12.0, 18.0, 33.0])

    # Absolute errors: [2, 2, 3] -> MAE = 7/3
    assert pytest.approx(mean_absolute_error(y_true, y_pred), 0.01) == 7.0 / 3.0

    # Squared errors: [4, 4, 9] -> MSE = 17/3 -> RMSE = sqrt(17/3)
    assert pytest.approx(root_mean_squared_error(y_true, y_pred), 0.01) == np.sqrt(17.0 / 3.0)


def test_wape():
    y_true = np.array([100.0, 200.0, 300.0])
    y_pred = np.array([90.0, 210.0, 330.0])

    # Total error: |10| + |10| + |30| = 50. Total actual: 600.
    # WAPE = 50 / 600 * 100 = 8.333%
    assert pytest.approx(weighted_absolute_percentage_error(y_true, y_pred), 0.01) == (50.0 / 600.0) * 100.0


def test_wape_zero_handling():
    y_true = np.array([0.0, 0.0])
    y_pred = np.array([0.0, 0.0])
    assert weighted_absolute_percentage_error(y_true, y_pred) == 0.0

    y_pred_nonzero = np.array([5.0, 10.0])
    assert weighted_absolute_percentage_error(y_true, y_pred_nonzero) == 100.0


def test_smape():
    y_true = np.array([100.0, 100.0])
    y_pred = np.array([100.0, 100.0])
    assert symmetric_mean_absolute_percentage_error(y_true, y_pred) == 0.0

    # Test bound [0, 200]
    y_pred_diff = np.array([0.0, 0.0])
    y_true_pos = np.array([100.0, 100.0])
    assert symmetric_mean_absolute_percentage_error(y_true_pos, y_pred_diff) == 200.0


def test_mase():
    # In-sample seasonal pattern (period=2): [10, 20, 10, 20]
    y_train = np.array([10.0, 20.0, 10.0, 20.0, 10.0, 20.0])
    y_true = np.array([10.0, 20.0])
    y_pred = np.array([10.0, 20.0])

    # Perfect forecast should give MASE = 0
    assert mean_absolute_scaled_error(y_true, y_pred, y_train, seasonality=2) == 0.0


def test_calculate_all_metrics_dict():
    y_true = np.array([50.0, 60.0, 70.0])
    y_pred = np.array([52.0, 58.0, 73.0])
    res = calculate_all_metrics(y_true, y_pred)
    assert "mae" in res
    assert "rmse" in res
    assert "wape" in res
    assert "smape" in res
    assert "mase" in res
