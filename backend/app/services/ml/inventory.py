import io
import csv
from typing import Any
import numpy as np


SERVICE_LEVEL_Z_FACTORS = {
    "90%": 1.282,
    "95%": 1.645,
    "99%": 2.326,
    0.90: 1.282,
    0.95: 1.645,
    0.99: 2.326,
}


def calculate_inventory_recommendations(
    forecast_points: list[dict[str, Any]],
    backtest_residuals: list[float],
    lead_time_days: int = 7,
    service_level: str = "95%",
    current_stock: float = 300.0,
    unit_cost: float = 25.0,
) -> dict[str, Any]:
    """
    Computes statistical inventory decision support:
    - Safety Stock = z * sigma(forecast_error) * sqrt(L)
    - Reorder Point = (mean_daily_demand * L) + Safety Stock
    - Status: 'Reorder now', 'OK', or 'Overstock risk'
    Clearly labelled: Extension: decision support, not advice.
    """
    # 1. Parse service level z-factor
    z = SERVICE_LEVEL_Z_FACTORS.get(service_level, 1.645)

    # 2. Daily forecast statistics
    pred_vals = [pt["predicted"] for pt in forecast_points if pt.get("predicted") is not None]
    if not pred_vals:
        pred_vals = [50.0] * lead_time_days
    daily_demand_mean = float(np.mean(pred_vals))
    lead_time_demand = float(daily_demand_mean * lead_time_days)

    # 3. Forecast error dispersion (sigma)
    clean_res = [abs(r) for r in backtest_residuals if np.isfinite(r)]
    sigma_error = float(np.std(clean_res)) if len(clean_res) > 2 else float(daily_demand_mean * 0.20)
    sigma_error = max(1.0, sigma_error)

    # 4. Safety Stock & Reorder Point
    safety_stock = float(z * sigma_error * np.sqrt(max(1, lead_time_days)))
    reorder_point = float(lead_time_demand + safety_stock)

    # 5. Status determination
    if current_stock <= reorder_point:
        status = "Reorder now"
        status_color = "red"
        # Suggested replenishment order: bring stock up to ROP + 1 cycle of lead-time demand
        order_qty = max(0.0, round(reorder_point - current_stock + lead_time_demand, 0))
    elif current_stock > (reorder_point * 2.2):
        status = "Overstock risk"
        status_color = "amber"
        order_qty = 0.0
    else:
        status = "OK"
        status_color = "emerald"
        order_qty = 0.0

    days_of_supply = round(current_stock / max(1.0, daily_demand_mean), 1)

    items = [
        {
            "parameter": "Daily Demand (Forecast Avg)",
            "value": f"{round(daily_demand_mean, 1):,} units/day",
            "description": "Mean predicted demand over the forecast horizon",
        },
        {
            "parameter": "Lead Time",
            "value": f"{lead_time_days} days",
            "description": "Replenishment delivery window",
        },
        {
            "parameter": "Service Level",
            "value": f"{service_level} (z = {z})",
            "description": "Desired cycle service probability against stockouts",
        },
        {
            "parameter": "Lead Time Demand (μ_LT)",
            "value": f"{round(lead_time_demand, 1):,} units",
            "description": "Expected cumulative consumption during supplier lead time",
        },
        {
            "parameter": "Safety Stock (SS)",
            "value": f"{round(safety_stock, 1):,} units",
            "description": "z × σ(error) × √L buffer protecting against demand shocks",
        },
        {
            "parameter": "Reorder Point (ROP)",
            "value": f"{round(reorder_point, 1):,} units",
            "description": "Trigger threshold: when inventory drops to this level, place order",
        },
        {
            "parameter": "Current Inventory",
            "value": f"{round(current_stock, 1):,} units ({days_of_supply} days supply)",
            "description": "Reported on-hand stock",
        },
        {
            "parameter": "Suggested Replenishment",
            "value": f"{round(order_qty, 0):,} units" if order_qty > 0 else "0 units",
            "description": "Recommended order size to restore optimal inventory position",
        },
    ]

    return {
        "disclaimer": "Extension: decision support, not advice. Verify against supplier constraints and minimum order quantities.",
        "status": status,
        "status_color": status_color,
        "lead_time_days": lead_time_days,
        "service_level": service_level,
        "z_factor": z,
        "current_stock": round(current_stock, 1),
        "days_of_supply": days_of_supply,
        "daily_demand_mean": round(daily_demand_mean, 1),
        "lead_time_demand": round(lead_time_demand, 1),
        "safety_stock": round(safety_stock, 1),
        "reorder_point": round(reorder_point, 1),
        "suggested_order_qty": round(order_qty, 0),
        "estimated_order_cost": round(order_qty * unit_cost, 2),
        "inventory_summary": items,
    }


def generate_inventory_csv(inventory_data: dict[str, Any]) -> str:
    """Exports inventory decision support metrics into CSV text format."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Parameter", "Value", "Description"])
    for row in inventory_data.get("inventory_summary", []):
        writer.writerow([row.get("parameter"), row.get("value"), row.get("description")])
    return output.getvalue()
