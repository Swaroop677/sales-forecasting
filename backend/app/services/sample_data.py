from pathlib import Path

import numpy as np
import pandas as pd
from backend.app.config import settings


def generate_retail_sales_data(
    start_date: str = "2021-01-01",
    end_date: str = "2023-12-31",
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generates realistic daily synthetic retail sales data for 3 stores x 5 products across 3 years.
    Includes:
    - Linear + slight quadratic trend
    - Weekly seasonality (weekend lifts)
    - Annual seasonality (holiday surges in Q4, summer bump)
    - Dynamic promotional campaigns and price elasticity
    - Known holiday spikes (Black Friday, Christmas Eve, etc.)
    - Realistic foot traffic regressor
    - Controlled anomalies (stockouts and viral promo surges)
    """
    np.random.seed(seed)
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")
    n_days = len(date_range)

    stores = ["Store_Downtown", "Store_Suburban", "Store_Metro"]
    products = [
        {"name": "Espresso_Beans", "base_price": 24.0, "base_volume": 85},
        {"name": "PourOver_Kettle", "base_price": 65.0, "base_volume": 35},
        {"name": "Organic_Tea_Box", "base_price": 18.0, "base_volume": 60},
        {"name": "Ceramic_Mug_Set", "base_price": 32.0, "base_volume": 45},
        {"name": "ColdBrew_Maker", "base_price": 48.0, "base_volume": 28},
    ]

    records = []

    # Precalculate calendar factors
    day_of_week = date_range.dayofweek.values  # 0=Monday, 6=Sunday
    day_of_year = date_range.dayofyear.values
    t = np.linspace(0, 3, n_days)  # 3 years progress

    # Base weekly multiplier: Mon (0.85) to Sat (1.45), Sun (1.35)
    weekly_curve = np.array([0.85, 0.90, 0.95, 1.05, 1.25, 1.45, 1.30])
    weekly_mult = weekly_curve[day_of_week]

    # Annual curve: Q4 peak (days 300 to 365) and summer peak (days 150 to 220)
    annual_mult = (
        1.0
        + 0.18 * np.sin(2 * np.pi * (day_of_year - 80) / 365.25)
        + 0.35 * np.exp(-((day_of_year - 350) ** 2) / (2 * (25**2)))  # Holiday peak
    )

    # General trend (+12% growth per year)
    trend_mult = 1.0 + 0.12 * t

    # Precompute holiday multiplier once
    holiday_mult = np.ones(n_days, dtype=float)
    for idx, d in enumerate(date_range):
        if d.month == 11 and 24 <= d.day <= 29 and d.weekday() == 4:  # Black Friday
            holiday_mult[idx] = 2.4
        elif d.month == 12 and d.day in [21, 22, 23, 24]:  # Christmas rush
            holiday_mult[idx] = 1.8
        elif d.month == 1 and d.day == 1:  # New Year slow
            holiday_mult[idx] = 0.45

    date_strings = [d.strftime("%Y-%m-%d") for d in date_range]

    for store_idx, store in enumerate(stores):
        store_factor = [1.15, 0.95, 1.05][store_idx]

        for prod_idx, prod in enumerate(products):
            base_vol = prod["base_volume"] * store_factor
            base_price = prod["base_price"]

            # Store & product specific seasonal tilt
            prod_phase = prod_idx * 0.4
            prod_seasonal = 1.0 + 0.10 * np.sin(2 * np.pi * (day_of_year + prod_phase * 30) / 365.25)

            # Promotions: random ~10-day campaigns roughly every 2 months
            promo_active = np.zeros(n_days, dtype=int)
            promo_discount = np.zeros(n_days, dtype=float)

            promo_starts = np.arange(25 + (store_idx * 13 + prod_idx * 17) % 35, n_days - 10, 60)
            for ps in promo_starts:
                dur = int(np.random.randint(4, 9))
                promo_active[ps : ps + dur] = 1
                promo_discount[ps : ps + dur] = float(np.random.uniform(0.15, 0.30))

            price = base_price * (1.0 - promo_discount) + np.random.normal(0, 0.25, n_days)
            price = np.round(np.clip(price, base_price * 0.65, base_price * 1.15), 2)

            traffic_base = 500 * store_factor
            foot_traffic = traffic_base * weekly_mult * (1.0 + 0.15 * promo_active) + np.random.normal(0, 35, n_days)
            foot_traffic = np.round(np.clip(foot_traffic, 150, 1800)).astype(int)

            promo_lift = 1.0 + promo_active * float(np.random.uniform(0.35, 0.65))
            price_elasticity = (base_price / price) ** 0.8

            expected_units = (
                base_vol
                * trend_mult
                * weekly_mult
                * annual_mult
                * prod_seasonal
                * promo_lift
                * price_elasticity
                * holiday_mult
            )

            noise = np.random.normal(1.0, 0.10, n_days)
            units = expected_units * noise

            outage_start = 450 + (store_idx * 20 + prod_idx * 15) % 100
            units[outage_start : outage_start + 3] *= 0.05

            spike_day = 850 + (store_idx * 30 + prod_idx * 25) % 80
            units[spike_day : spike_day + 2] *= 3.1

            units = np.round(np.clip(units, 0, None)).astype(int)
            revenue = np.round(units * price, 2)

            for i in range(n_days):
                records.append({
                    "date": date_strings[i],
                    "store": store,
                    "product": prod["name"],
                    "sales": int(units[i]),
                    "revenue": float(revenue[i]),
                    "price": float(price[i]),
                    "promo": int(promo_active[i]),
                    "foot_traffic": int(foot_traffic[i]),
                })

    df = pd.DataFrame(records)
    return df


def ensure_sample_data_file() -> Path:
    """Creates /data/sample/sales.csv if not already present."""
    sample_path = settings.DATA_DIR / "sample" / "sales.csv"
    if not sample_path.exists():
        df = generate_retail_sales_data()
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(sample_path, index=False)
    return sample_path
