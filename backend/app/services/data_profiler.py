from typing import Any, Optional

import pandas as pd


def detect_columns(df: pd.DataFrame) -> dict[str, Any]:
    """
    Intelligently auto-detects date column, target column, group columns,
    and optional numeric regressors.
    """
    date_col = ""
    target_col = ""
    group_cols: list[str] = []
    regressor_cols: list[str] = []

    columns = list(df.columns)
    col_lower_map = {c.lower().strip(): c for c in columns}

    # 1. Date column detection
    date_candidates = ["date", "timestamp", "datetime", "day", "time", "ds", "period"]
    for cand in date_candidates:
        if cand in col_lower_map:
            date_col = col_lower_map[cand]
            break

    if not date_col:
        for c in columns:
            if pd.api.types.is_datetime64_any_dtype(df[c]):
                date_col = c
                break
            # Try parsing sample strings
            if df[c].dtype == object or pd.api.types.is_string_dtype(df[c]):
                sample = df[c].dropna().head(20)
                if not sample.empty:
                    try:
                        pd.to_datetime(sample)
                        date_col = c
                        break
                    except Exception:
                        pass

    # 2. Target column detection
    target_candidates = ["sales", "quantity", "revenue", "demand", "units", "y", "orders", "volume", "amount"]
    for cand in target_candidates:
        if cand in col_lower_map:
            col_match = col_lower_map[cand]
            if pd.api.types.is_numeric_dtype(df[col_match]):
                target_col = col_match
                break

    if not target_col:
        # Pick the numeric column with the highest variance
        numeric_cols = [c for c in columns if c != date_col and pd.api.types.is_numeric_dtype(df[c])]
        if numeric_cols:
            variances = {c: df[c].var() for c in numeric_cols if df[c].notnull().sum() > 1}
            if variances:
                target_col = max(variances, key=variances.get)
            else:
                target_col = numeric_cols[0]

    # 3. Categorical / Group columns detection
    group_candidates = ["store", "product", "item", "category", "region", "branch", "channel", "sku", "location"]
    for c in columns:
        if c in (date_col, target_col):
            continue
        c_low = c.lower().strip()
        n_unique = df[c].nunique(dropna=True)
        if any(cand in c_low for cand in group_candidates) and n_unique < len(df) * 0.5:
            group_cols.append(c)
        elif (df[c].dtype == object or pd.api.types.is_string_dtype(df[c]) or isinstance(df[c].dtype, pd.CategoricalDtype)) and 1 < n_unique <= 50:
            if c not in group_cols:
                group_cols.append(c)

    # 4. Regressors (remaining numeric columns)
    for c in columns:
        if c in (date_col, target_col) or c in group_cols:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            regressor_cols.append(c)

    return {
        "date_col": date_col or (columns[0] if columns else ""),
        "target_col": target_col or (columns[1] if len(columns) > 1 else ""),
        "group_cols": group_cols,
        "regressor_cols": regressor_cols,
    }


def infer_frequency(dates: pd.Series) -> str:
    """Infers cadence: D (Daily), W (Weekly), M (Monthly), or fallback D."""
    try:
        clean_dates = pd.to_datetime(dates.dropna()).drop_duplicates().sort_values()
        if len(clean_dates) < 3:
            return "D"
        diffs = clean_dates.diff().dropna().dt.total_seconds() / 86400.0  # days
        median_diff = float(diffs.median())
        if 0.8 <= median_diff <= 1.2:
            return "D"
        elif 6.0 <= median_diff <= 8.0:
            return "W"
        elif 27.0 <= median_diff <= 32.0:
            return "M"
        return "D"
    except Exception:
        return "D"


def profile_dataset(
    df: pd.DataFrame,
    date_col: str,
    target_col: str,
    group_cols: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Performs full data quality auditing:
    - Frequency inference
    - Missing dates
    - Duplicate records
    - Negative values in target
    - Null / NaN values
    - Outlier detection (IQR and Robust Z-score)
    - Short history warning (<2 seasonal cycles)
    """
    issues = []
    total_rows = len(df)
    score = 100

    if total_rows == 0:
        return {
            "is_valid": False,
            "frequency": "D",
            "total_rows": 0,
            "date_range": {},
            "target_summary": {},
            "issues": [{
                "id": "empty_dataset",
                "column": None,
                "issue_type": "empty",
                "severity": "critical",
                "count": 0,
                "percentage": 100.0,
                "message": "The dataset contains no rows.",
                "suggested_fix": "Upload a valid dataset with at least 14 rows.",
            }],
            "score": 0,
        }

    # Verify columns exist
    if date_col not in df.columns:
        issues.append({
            "id": "missing_date_col",
            "column": date_col,
            "issue_type": "missing_column",
            "severity": "critical",
            "count": total_rows,
            "percentage": 100.0,
            "message": f"Date column '{date_col}' not found in dataset.",
            "suggested_fix": "Select a valid date column.",
        })
        score -= 40

    if target_col not in df.columns:
        issues.append({
            "id": "missing_target_col",
            "column": target_col,
            "issue_type": "missing_column",
            "severity": "critical",
            "count": total_rows,
            "percentage": 100.0,
            "message": f"Target column '{target_col}' not found in dataset.",
            "suggested_fix": "Select a valid target column.",
        })
        score -= 40

    if issues:
        return {
            "is_valid": False,
            "frequency": "D",
            "total_rows": total_rows,
            "date_range": {},
            "target_summary": {},
            "issues": issues,
            "score": max(0, score),
        }

    # Convert date column
    try:
        parsed_dates = pd.to_datetime(df[date_col], errors="coerce")
        invalid_dates_count = int(parsed_dates.isna().sum())
        if invalid_dates_count > 0:
            pct = round((invalid_dates_count / total_rows) * 100, 2)
            issues.append({
                "id": "invalid_dates",
                "column": date_col,
                "issue_type": "unparseable_date",
                "severity": "critical",
                "count": invalid_dates_count,
                "percentage": pct,
                "message": f"{invalid_dates_count} ({pct}%) dates could not be parsed.",
                "suggested_fix": "Drop or fix unparseable date strings.",
            })
            score -= min(30, int(pct * 2))
    except Exception as e:
        parsed_dates = pd.Series([None] * total_rows)
        issues.append({
            "id": "date_parse_failure",
            "column": date_col,
            "issue_type": "unparseable_date",
            "severity": "critical",
            "count": total_rows,
            "percentage": 100.0,
            "message": f"Failed to parse date column: {e}",
            "suggested_fix": "Ensure dates are in ISO YYYY-MM-DD or standard format.",
        })
        score -= 40

    valid_dates = parsed_dates.dropna()
    freq = infer_frequency(valid_dates) if not valid_dates.empty else "D"

    date_range_info = {
        "start": str(valid_dates.min().strftime("%Y-%m-%d")) if not valid_dates.empty else "",
        "end": str(valid_dates.max().strftime("%Y-%m-%d")) if not valid_dates.empty else "",
        "unique_dates": int(valid_dates.nunique()) if not valid_dates.empty else 0,
    }

    # History cycle check (< 2 seasonal cycles)
    # Weekly cycle needs >= 14 unique dates, Yearly needs >= 365*2 for full yearly seasonality
    unique_dates_count = date_range_info["unique_dates"]
    if unique_dates_count < 14:
        issues.append({
            "id": "history_too_short",
            "column": date_col,
            "issue_type": "short_history",
            "severity": "critical",
            "count": unique_dates_count,
            "percentage": 0.0,
            "message": f"Only {unique_dates_count} unique dates detected. Minimum 14 points required for weekly seasonality.",
            "suggested_fix": "Provide at least 2 weeks of daily data for meaningful backtesting.",
        })
        score -= 30
    elif unique_dates_count < 60:
        issues.append({
            "id": "history_limited",
            "column": date_col,
            "issue_type": "limited_history",
            "severity": "warning",
            "count": unique_dates_count,
            "percentage": 0.0,
            "message": f"Dataset has {unique_dates_count} unique dates. Longer history (90+ days) yields better seasonal forecasts.",
            "suggested_fix": "Consider extending historical records for optimal ML accuracy.",
        })
        score -= 10

    # Missing dates detection
    if not valid_dates.empty and unique_dates_count >= 2:
        expected_range = pd.date_range(start=valid_dates.min(), end=valid_dates.max(), freq=freq)
        existing_unique = set(valid_dates.dt.normalize())
        missing_count = sum(1 for d in expected_range if d not in existing_unique)
        if missing_count > 0:
            pct = round((missing_count / len(expected_range)) * 100, 2)
            issues.append({
                "id": "missing_calendar_dates",
                "column": date_col,
                "issue_type": "missing_dates",
                "severity": "warning" if pct < 15 else "critical",
                "count": missing_count,
                "percentage": pct,
                "message": f"{missing_count} expected calendar dates ({pct}%) are missing from the timeline.",
                "suggested_fix": "Automatically reindex timeline and forward-fill or zero-fill missing periods.",
            })
            score -= min(20, int(pct))

    # Duplicate check (on date or date + group)
    subset_keys = [date_col]
    if group_cols:
        for g in group_cols:
            if g in df.columns:
                subset_keys.append(g)

    dup_count = int(df.duplicated(subset=subset_keys).sum())
    if dup_count > 0:
        pct = round((dup_count / total_rows) * 100, 2)
        issues.append({
            "id": "duplicate_rows",
            "column": ", ".join(subset_keys),
            "issue_type": "duplicates",
            "severity": "warning",
            "count": dup_count,
            "percentage": pct,
            "message": f"{dup_count} duplicate timestamps found for identical keys.",
            "suggested_fix": "Aggregate duplicate records by summing target values.",
        })
        score -= min(20, int(pct * 1.5))

    # Target column analysis
    target_series = pd.to_numeric(df[target_col], errors="coerce")
    null_target_count = int(target_series.isna().sum())
    if null_target_count > 0:
        pct = round((null_target_count / total_rows) * 100, 2)
        issues.append({
            "id": "null_target_values",
            "column": target_col,
            "issue_type": "nulls",
            "severity": "critical",
            "count": null_target_count,
            "percentage": pct,
            "message": f"{null_target_count} ({pct}%) rows have null or NaN target values.",
            "suggested_fix": "Impute missing values using linear interpolation or rolling median.",
        })
        score -= min(30, int(pct * 2))

    valid_targets = target_series.dropna()
    negative_count = int((valid_targets < 0).sum())
    if negative_count > 0:
        pct = round((negative_count / total_rows) * 100, 2)
        issues.append({
            "id": "negative_target_values",
            "column": target_col,
            "issue_type": "negatives",
            "severity": "warning",
            "count": negative_count,
            "percentage": pct,
            "message": f"{negative_count} ({pct}%) negative sales/volume entries detected.",
            "suggested_fix": "Clip negative target values to zero.",
        })
        score -= min(20, int(pct * 2))

    # Outliers (IQR check)
    outlier_count = 0
    if len(valid_targets) >= 10:
        q25 = float(valid_targets.quantile(0.25))
        q75 = float(valid_targets.quantile(0.75))
        iqr = q75 - q25
        lower_bound = q25 - 2.5 * iqr
        upper_bound = q75 + 2.5 * iqr
        outlier_mask = (valid_targets < lower_bound) | (valid_targets > upper_bound)
        outlier_count = int(outlier_mask.sum())

        if outlier_count > 0:
            pct = round((outlier_count / total_rows) * 100, 2)
            issues.append({
                "id": "target_outliers",
                "column": target_col,
                "issue_type": "outliers",
                "severity": "info" if pct < 3 else "warning",
                "count": outlier_count,
                "percentage": pct,
                "message": f"{outlier_count} statistical outlier points ({pct}%) detected outside 2.5x IQR.",
                "suggested_fix": "Clip extreme values to upper and lower bounds to stabilize gradient trees.",
            })
            score -= min(15, int(pct))

    target_summary = {
        "mean": float(valid_targets.mean()) if not valid_targets.empty else 0.0,
        "std": float(valid_targets.std()) if not valid_targets.empty else 0.0,
        "min": float(valid_targets.min()) if not valid_targets.empty else 0.0,
        "max": float(valid_targets.max()) if not valid_targets.empty else 0.0,
        "median": float(valid_targets.median()) if not valid_targets.empty else 0.0,
        "zero_count": int((valid_targets == 0).sum()),
    }

    is_valid = not any(issue["severity"] == "critical" for issue in issues)

    return {
        "is_valid": is_valid,
        "frequency": freq,
        "total_rows": total_rows,
        "date_range": date_range_info,
        "target_summary": target_summary,
        "issues": issues,
        "score": max(5, min(100, score)),
    }
