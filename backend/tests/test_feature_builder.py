import pandas as pd
from backend.app.services.feature_builder import (
    build_feature_matrix,
    build_lag_features,
    build_rolling_features,
    create_calendar_features,
)


def test_calendar_features():
    dates = pd.Series(["2023-01-01", "2023-01-02", "2023-01-03"])
    cal = create_calendar_features(dates)

    assert "day_of_week" in cal.columns
    assert "is_weekend" in cal.columns
    assert "month" in cal.columns
    assert "dow_sin" in cal.columns
    assert "dow_cos" in cal.columns

    # 2023-01-01 was Sunday (day_of_week = 6, is_weekend = 1)
    assert cal.loc[0, "day_of_week"] == 6
    assert cal.loc[0, "is_weekend"] == 1


def test_lag_features_shift():
    y = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    lags = build_lag_features(y, lags=(1, 2))

    assert "lag_1" in lags.columns
    assert "lag_2" in lags.columns

    # lag_1 at index 1 is y[0] = 10.0
    assert lags.loc[1, "lag_1"] == 10.0
    # lag_2 at index 2 is y[0] = 10.0
    assert lags.loc[2, "lag_2"] == 10.0


def test_rolling_features_shift():
    y = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    rolling = build_rolling_features(y, windows=(2,))

    # At index 2 (value 30.0), rolling window of size 2 must only use [y[0], y[1]] = [10, 20]
    # mean([10, 20]) = 15.0
    assert rolling.loc[2, "rolling_mean_2"] == 15.0


def test_build_feature_matrix():
    df = pd.DataFrame({
        "date": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"],
        "sales": [100.0, 150.0, 120.0, 180.0],
        "promo": [0, 1, 0, 1],
    })

    X = build_feature_matrix(
        df=df,
        date_col="date",
        target_col="sales",
        regressor_cols=["promo"],
        lags=(1, 2),
        windows=(2,),
    )

    assert not X.empty
    assert len(X) == 4
    assert "promo" in X.columns
    assert "lag_1" in X.columns
    assert "rolling_mean_2" in X.columns
    assert not X.isna().any().any()
