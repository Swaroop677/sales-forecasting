from typing import Any
import numpy as np
import pandas as pd


def compute_segment_and_season_performance(
    df: pd.DataFrame,
    date_col: str,
    target_col: str,
    group_cols: list[str],
    regressor_cols: list[str],
    backtest_overlay: list[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Computes cross-sectional performance metrics sliced by:
    1. Group segments (Store / Product)
    2. Seasonal intervals (Month / Meteorological Seasons)
    3. Promo vs Non-promo activity
    Identifies high-risk/underperforming segments and generates plain-English insights.
    """
    df_clean = df.copy()
    df_clean[date_col] = pd.to_datetime(df_clean[date_col], errors="coerce")
    df_clean = df_clean.dropna(subset=[date_col]).sort_values(by=date_col)

    df_clean["month_num"] = df_clean[date_col].dt.month
    df_clean["month_name"] = df_clean[date_col].dt.strftime("%b")

    # Map meteorological seasons
    def get_season(m: int) -> str:
        if m in [12, 1, 2]:
            return "Winter"
        elif m in [3, 4, 5]:
            return "Spring"
        elif m in [6, 7, 8]:
            return "Summer"
        return "Fall"

    df_clean["season"] = df_clean["month_num"].apply(get_season)

    # 1. Season Performance
    season_metrics = []
    season_order = ["Spring", "Summer", "Fall", "Winter"]
    for s_name in season_order:
        s_df = df_clean[df_clean["season"] == s_name]
        if not s_df.empty:
            total_sales = float(s_df[target_col].sum())
            mean_sales = float(s_df[target_col].mean())
            std_sales = float(s_df[target_col].std()) if len(s_df) > 1 else 0.0
            cv = round((std_sales / max(1.0, mean_sales)) * 100, 1)  # coefficient of variation
            season_metrics.append({
                "season": s_name,
                "total_sales": round(total_sales, 1),
                "avg_daily_sales": round(mean_sales, 1),
                "volatility_pct": cv,
                "row_count": len(s_df),
            })

    # 2. Monthly Performance
    month_metrics = []
    for m_num in range(1, 13):
        m_df = df_clean[df_clean["month_num"] == m_num]
        if not m_df.empty:
            m_name = m_df["month_name"].iloc[0]
            month_metrics.append({
                "month_num": m_num,
                "month": m_name,
                "total_sales": round(float(m_df[target_col].sum()), 1),
                "avg_sales": round(float(m_df[target_col].mean()), 1),
                "share_pct": round(float(m_df[target_col].sum() / max(1.0, df_clean[target_col].sum())) * 100, 1),
            })

    # 3. Promo vs Non-Promo Performance
    promo_col = next((c for c in regressor_cols if "promo" in c.lower() or "discount" in c.lower()), None)
    promo_metrics = []
    promo_lift_pct = 0.0
    if promo_col and promo_col in df_clean.columns:
        promo_active = df_clean[df_clean[promo_col] > 0]
        promo_inactive = df_clean[df_clean[promo_col] <= 0]

        mean_promo = float(promo_active[target_col].mean()) if not promo_active.empty else 0.0
        mean_non_promo = float(promo_inactive[target_col].mean()) if not promo_inactive.empty else 0.0

        if mean_non_promo > 0:
            promo_lift_pct = round(((mean_promo - mean_non_promo) / mean_non_promo) * 100, 1)

        promo_metrics = [
            {
                "condition": "Promotional Days",
                "days": len(promo_active),
                "avg_daily_sales": round(mean_promo, 1),
                "total_sales": round(float(promo_active[target_col].sum()), 1) if not promo_active.empty else 0.0,
            },
            {
                "condition": "Non-Promotional Days",
                "days": len(promo_inactive),
                "avg_daily_sales": round(mean_non_promo, 1),
                "total_sales": round(float(promo_inactive[target_col].sum()), 1) if not promo_inactive.empty else 0.0,
            },
        ]

    # 4. Group Segments & Worst Performing Segments
    group_results = []
    worst_segments = []
    primary_group_col = group_cols[0] if group_cols else None

    if primary_group_col and primary_group_col in df_clean.columns:
        for grp_val, grp_df in df_clean.groupby(primary_group_col):
            tot = float(grp_df[target_col].sum())
            avg = float(grp_df[target_col].mean())
            std = float(grp_df[target_col].std()) if len(grp_df) > 1 else 0.0
            cv = round((std / max(1.0, avg)) * 100, 1)
            # Heuristic WAPE proxy based on volatility and missingness
            risk_score = round(min(99.0, max(5.0, cv * 0.45 + (100 - min(100, len(grp_df) / 10)))), 1)

            entry = {
                "segment": str(grp_val),
                "total_sales": round(tot, 1),
                "avg_daily_sales": round(avg, 1),
                "volatility_pct": cv,
                "forecast_error_proxy_wape": risk_score,
                "status": "High Risk" if risk_score > 35 else ("Moderate Risk" if risk_score > 20 else "Healthy"),
            }
            group_results.append(entry)

        group_results.sort(key=lambda x: x["forecast_error_proxy_wape"], reverse=True)
        worst_segments = group_results[:5]

    # 5. Segment Heatmap Matrix (Primary Group vs Season)
    heatmap_matrix: list[dict[str, Any]] = []
    if primary_group_col and primary_group_col in df_clean.columns:
        piv = df_clean.pivot_table(
            index=primary_group_col,
            columns="season",
            values=target_col,
            aggfunc="mean",
            fill_value=0.0,
        )
        for grp_name, row in piv.iterrows():
            row_dict = {"segment": str(grp_name)}
            for s in season_order:
                row_dict[s] = round(float(row.get(s, 0.0)), 1)
            heatmap_matrix.append(row_dict)

    # 6. Plain-English Takeaway
    takeaway_parts = []
    if season_metrics:
        peak_season = max(season_metrics, key=lambda x: x["total_sales"])
        low_season = min(season_metrics, key=lambda x: x["total_sales"])
        takeaway_parts.append(
            f"Demand peaks strongly in {peak_season['season']} ({peak_season['total_sales']:,.0f} units) "
            f"and experiences a trough during {low_season['season']}."
        )

    if promo_metrics and promo_lift_pct != 0.0:
        takeaway_parts.append(
            f"Promotions generate a {promo_lift_pct:+.1f}% average daily demand lift."
        )

    if worst_segments:
        top_risk = worst_segments[0]
        takeaway_parts.append(
            f"Segment '{top_risk['segment']}' exhibits highest forecast error risk "
            f"({top_risk['forecast_error_proxy_wape']}% WAPE proxy) driven by {top_risk['volatility_pct']}% sales volatility."
        )

    takeaway = " ".join(takeaway_parts) or "Segment and seasonality patterns remain consistent across groups."

    return {
        "season_performance": season_metrics,
        "month_performance": month_metrics,
        "promo_performance": promo_metrics,
        "promo_lift_pct": promo_lift_pct,
        "group_segments": group_results,
        "worst_segments": worst_segments,
        "heatmap_matrix": heatmap_matrix,
        "takeaway": takeaway,
    }
