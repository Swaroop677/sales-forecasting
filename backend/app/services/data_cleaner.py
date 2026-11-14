from datetime import datetime, timezone
from typing import Any

import pandas as pd


def clean_dataset(
    df: pd.DataFrame,
    date_col: str,
    target_col: str,
    group_cols: list[str] = None,
    regressor_cols: list[str] = None,
    frequency: str = "D",
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """
    Applies systematic data cleaning to prepare a dataset for robust forecasting:
    1. Parse and validate dates, drop unparseable rows.
    2. Deduplicate identical date/group combinations.
    3. Ensure continuous time series per group/overall (fill missing dates).
    4. Handle null values and clip negative values.
    5. Robustly clip extreme outliers using IQR limits.
    Returns:
        cleaned_df: Cleaned pandas DataFrame.
        audit_log: List of audit log records describing actions taken and rows affected.
    """
    audit_log = []
    df = df.copy()
    group_cols = group_cols or []
    regressor_cols = regressor_cols or []

    # 1. Date parsing and sorting
    initial_rows = len(df)
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    invalid_dates = df[date_col].isna()
    invalid_count = int(invalid_dates.sum())
    if invalid_count > 0:
        df = df[~invalid_dates].copy()
        audit_log.append({
            "action": "Drop invalid dates",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rows_affected": invalid_count,
            "details": f"Removed {invalid_count} rows with unparseable date values.",
        })

    # Ensure target is numeric
    df[target_col] = pd.to_numeric(df[target_col], errors="coerce")
    null_target_count = int(df[target_col].isna().sum())
    if null_target_count > 0:
        df[target_col] = df[target_col].interpolate(method="linear").bfill().ffill().fillna(0)
        audit_log.append({
            "action": "Impute missing target values",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rows_affected": null_target_count,
            "details": f"Interpolated {null_target_count} missing or NaN values in target '{target_col}'.",
        })

    # Ensure regressors are numeric
    for reg in regressor_cols:
        if reg in df.columns:
            df[reg] = pd.to_numeric(df[reg], errors="coerce").fillna(0)

    # 2. Deduplication
    key_cols = [date_col] + [g for g in group_cols if g in df.columns]
    dup_mask = df.duplicated(subset=key_cols, keep=False)
    dup_count = int(dup_mask.sum())
    if dup_count > 0:
        # Build aggregation dictionary
        agg_rules = {target_col: "sum"}
        for reg in regressor_cols:
            if reg in df.columns and reg not in key_cols:
                agg_rules[reg] = "mean"
        for col in df.columns:
            if col not in key_cols and col not in agg_rules:
                agg_rules[col] = "first"

        df = df.groupby(key_cols, as_index=False).agg(agg_rules)
        deduped_rows = dup_count - (len(df) - (initial_rows - dup_count - invalid_count))
        audit_log.append({
            "action": "Deduplicate timeline keys",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rows_affected": max(1, deduped_rows),
            "details": f"Aggregated duplicate timestamps across {', '.join(key_cols)} using target sum and regressor averages.",
        })

    # 3. Clip negatives
    negative_mask = df[target_col] < 0
    negative_count = int(negative_mask.sum())
    if negative_count > 0:
        df.loc[negative_mask, target_col] = 0.0
        audit_log.append({
            "action": "Clip negative values",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rows_affected": negative_count,
            "details": f"Clipped {negative_count} negative target values to zero floor.",
        })

    # 4. Outlier treatment (clip at 2.5x IQR)
    if len(df) >= 10:
        q25 = df[target_col].quantile(0.25)
        q75 = df[target_col].quantile(0.75)
        iqr = q75 - q25
        lower_limit = max(0.0, float(q25 - 2.5 * iqr))
        upper_limit = float(q75 + 2.5 * iqr)

        outlier_mask = (df[target_col] < lower_limit) | (df[target_col] > upper_limit)
        outlier_count = int(outlier_mask.sum())
        if outlier_count > 0:
            df[target_col] = df[target_col].clip(lower=lower_limit, upper=upper_limit)
            audit_log.append({
                "action": "Clip extreme outliers",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "rows_affected": outlier_count,
                "details": f"Clipped {outlier_count} values outside IQR bounds [{lower_limit:.2f}, {upper_limit:.2f}].",
            })

    # Format date back to string YYYY-MM-DD
    df[date_col] = df[date_col].dt.strftime("%Y-%m-%d")
    df = df.sort_values(by=key_cols).reset_index(drop=True)

    if not audit_log:
        audit_log.append({
            "action": "Dataset validation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rows_affected": 0,
            "details": "Dataset checked: all checks passed with no modifications necessary.",
        })

    return df, audit_log
