import io
from typing import Any
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def generate_multisheet_excel_report(
    run_dict: dict[str, Any],
    inventory_dict: dict[str, Any] = None,
) -> io.BytesIO:
    """
    Generates a professional multi-sheet Excel workbook with styled headers and borders:
    - Sheet 1: Forecast & Intervals (Date, Predicted, Lower 80, Upper 80, Lower 95, Upper 95)
    - Sheet 2: Leaderboard (Model, WAPE, MAE, RMSE, sMAPE, MASE, Coverage 80, Coverage 95)
    - Sheet 3: Inventory Support (Parameter, Value, Description)
    - Sheet 4: Summary & Metadata (Run ID, Dataset, Champion Model, Timestamp)
    """
    wb = openpyxl.Workbook()
    # Default active sheet
    ws_forecast = wb.active
    ws_forecast.title = "Forecast & Intervals"

    # Header styling
    header_fill = PatternFill(start_color="3B4252", end_color="3B4252", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    border_thin = Border(
        left=Side(style="thin", color="E5E7EB"),
        right=Side(style="thin", color="E5E7EB"),
        top=Side(style="thin", color="E5E7EB"),
        bottom=Side(style="thin", color="E5E7EB"),
    )

    # 1. Forecast & Intervals Sheet
    headers_f = ["Date", "Predicted Demand", "Lower 80% Band", "Upper 80% Band", "Lower 95% Band", "Upper 95% Band"]
    ws_forecast.append(headers_f)
    for col_num in range(1, len(headers_f) + 1):
        cell = ws_forecast.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    forecast_series = run_dict.get("forecast_series", [])
    for pt in forecast_series:
        if pt.get("predicted") is not None:
            row_data = [
                pt.get("date"),
                pt.get("predicted"),
                pt.get("lower_80", pt.get("lower_bound")),
                pt.get("upper_80", pt.get("upper_bound")),
                pt.get("lower_95"),
                pt.get("upper_95"),
            ]
            ws_forecast.append(row_data)

    # 2. Leaderboard Sheet
    ws_lead = wb.create_sheet(title="Model Leaderboard")
    headers_l = ["Model", "WAPE (%)", "MAE", "RMSE", "sMAPE (%)", "MASE", "80% Coverage", "95% Coverage", "Fit Time (s)"]
    ws_lead.append(headers_l)
    for col_num in range(1, len(headers_l) + 1):
        cell = ws_lead.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for item in run_dict.get("leaderboard", []):
        star = " (Best)" if item.get("is_best") else ""
        ws_lead.append([
            f"{item.get('model_name')}{star}",
            item.get("wape"),
            item.get("mae"),
            item.get("rmse"),
            item.get("smape"),
            item.get("mase"),
            f"{item.get('coverage_80', 80.0)}%",
            f"{item.get('coverage_95', 95.0)}%",
            item.get("fit_time_sec"),
        ])

    # 3. Inventory Decision Support Sheet
    ws_inv = wb.create_sheet(title="Inventory Support")
    headers_i = ["Parameter", "Value", "Description"]
    ws_inv.append(headers_i)
    for col_num in range(1, len(headers_i) + 1):
        cell = ws_inv.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font

    if inventory_dict and "inventory_summary" in inventory_dict:
        for row in inventory_dict["inventory_summary"]:
            ws_inv.append([row.get("parameter"), row.get("value"), row.get("description")])

    # 4. Summary & Metadata Sheet
    ws_meta = wb.create_sheet(title="Run Metadata")
    ws_meta.append(["Attribute", "Value"])
    for col_num in range(1, 3):
        cell = ws_meta.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font

    meta_items = [
        ("Run ID", run_dict.get("id")),
        ("Dataset ID", run_dict.get("dataset_id")),
        ("Dataset Name", run_dict.get("dataset_name")),
        ("Champion Model", run_dict.get("best_model")),
        ("Optimization Metric", run_dict.get("metric", "wape").upper()),
        ("Best WAPE", f"{run_dict.get('best_wape', 0.0)}%"),
        ("Forecast Horizon", f"{run_dict.get('horizon', 30)} days"),
        ("Created At", str(run_dict.get("created_at"))),
        ("Disclaimer", "Forecastly prediction intervals and inventory decision support are statistical estimations, not financial advice."),
    ]
    for k, v in meta_items:
        ws_meta.append([k, str(v)])

    # Auto-adjust column widths
    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                cell.font = data_font
                cell.border = border_thin
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            sheet.column_dimensions[col_letter].width = min(40, max(12, max_len + 3))

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream
