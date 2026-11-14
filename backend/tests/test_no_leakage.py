import numpy as np
import pandas as pd
from backend.app.services.feature_builder import build_feature_matrix


def test_target_features_do_not_leak_future_or_current_data():
    """
    Rigorously proves that features generated at time t only use historical observations strictly before t.
    Specifically:
    1. Given two dataframes that are identical up to t - 1, but where y_t and all future values
       are altered dramatically.
    2. The feature row computed for time t MUST be completely identical between both runs for
       all lag and rolling statistics.
    """
    n = 30
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    base_sales = np.arange(1, n + 1) * 10.0

    df_a = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "sales": base_sales,
    })

    # Pick test index t*
    t_star = 15

    # df_b is identical to df_a up to t_star - 1, but completely modified from t_star onwards
    df_b = df_a.copy()
    df_b.loc[t_star:, "sales"] = df_b.loc[t_star:, "sales"] * 1000.0 + 9999.0

    # Build feature matrices
    X_a = build_feature_matrix(
        df=df_a,
        date_col="date",
        target_col="sales",
        lags=(1, 2, 7),
        windows=(3, 7),
    )

    X_b = build_feature_matrix(
        df=df_b,
        date_col="date",
        target_col="sales",
        lags=(1, 2, 7),
        windows=(3, 7),
    )

    target_derived_cols = [
        col for col in X_a.columns
        if col.startswith("lag_") or col.startswith("rolling_")
    ]

    # Verify that for row t_star, all target features are IDENTICAL despite sales[t_star] being altered!
    for col in target_derived_cols:
        val_a = X_a.loc[t_star, col]
        val_b = X_b.loc[t_star, col]
        assert val_a == val_b, (
            f"LEAKAGE DETECTED in '{col}' at index {t_star}: "
            f"changing y[{t_star}] changed the feature value from {val_a} to {val_b}!"
        )

    # Verify for all rows strictly before t_star as well
    for row_idx in range(t_star):
        for col in target_derived_cols:
            val_a = X_a.loc[row_idx, col]
            val_b = X_b.loc[row_idx, col]
            assert val_a == val_b, (
                f"LEAKAGE DETECTED in '{col}' at historical row {row_idx}!"
            )


def test_fold_split_train_features_only_use_train_slice():
    """
    Proves that training fold features never access test fold rows during backtesting.
    """
    dates = pd.date_range("2023-01-01", periods=50, freq="D")
    sales = np.random.uniform(50, 150, 50)
    df = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "sales": sales})

    split_idx = 35
    train_df = df.iloc[:split_idx].copy()

    # Features calculated on train_df alone
    X_train_isolated = build_feature_matrix(
        df=train_df,
        date_col="date",
        target_col="sales",
        lags=(1, 7),
        windows=(7,),
    )

    # Features calculated on full df
    X_full = build_feature_matrix(
        df=df,
        date_col="date",
        target_col="sales",
        lags=(1, 7),
        windows=(7,),
    )
    X_train_from_full = X_full.iloc[:split_idx]

    # Target-derived features in train slice must match exactly
    for col in ["lag_1", "lag_7", "rolling_mean_7"]:
        np.testing.assert_allclose(
            X_train_isolated[col].values,
            X_train_from_full[col].values,
            err_msg=f"Discrepancy in train features for {col}",
        )
