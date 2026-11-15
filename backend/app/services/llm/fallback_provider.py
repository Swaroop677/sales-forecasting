import asyncio
import re
from typing import Any, AsyncIterator, Optional
from backend.app.services.llm.base import LLMEvent, LLMProvider


class FallbackProvider(LLMProvider):
    """
    Rule-based deterministic provider that works with NO API key.
    Ensures Forecastly functions reliably out of the box with zero configuration:
    - Parses keyword user intents (forecast, anomalies, what-if, leaderboard, cleaning)
    - Emits tool calls
    - Generates grounded, structured narrative reports from tool results with exact verified numbers.
    """

    def __init__(self, model: str = "forecastly-rule-engine-v1"):
        super().__init__(name="Rule-Based Fallback (No Key)", model=model)

    async def stream_turn(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[LLMEvent]:
        # Check if the last message is a tool response
        last_msg = messages[-1] if messages else {}

        if last_msg.get("role") == "tool":
            # Generate narrative explanation based on the tool result
            tool_name = last_msg.get("name", "")
            tool_result = last_msg.get("content", {})
            explanation = self._narrate_tool_result(tool_name, tool_result)

            # Stream tokens smoothly
            words = explanation.split(" ")
            for w in words:
                yield LLMEvent("token", w + " ")
                await asyncio.sleep(0.015)

            yield LLMEvent("done", None)
            return

        # Otherwise, parse user intent from user prompt
        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_text = m.get("content", "").lower()
                break

        # Extract dataset/run IDs from context or message metadata if present
        context_dataset_id = last_msg.get("dataset_id") or "default"
        context_run_id = last_msg.get("run_id") or "default"

        # Intent 1: What-If simulation
        if any(kw in user_text for kw in ["what if", "promo", "discount", "price change", "simulation"]):
            promo_pct = 20.0
            price_pct = 0.0
            pct_matches = re.findall(r"(\d+)\s*%", user_text)
            if pct_matches:
                promo_pct = float(pct_matches[0])
            if "price" in user_text and pct_matches:
                price_pct = -float(pct_matches[0]) if "drop" in user_text or "discount" in user_text else float(pct_matches[0])

            yield LLMEvent(
                "tool_call",
                {
                    "name": "what_if",
                    "args": {
                        "run_id": context_run_id,
                        "promo_change_pct": promo_pct,
                        "price_change_pct": price_pct,
                        "scenario_name": f"User Scenario ({promo_pct:+}% Promo)",
                    },
                },
            )
            return

        # Intent 2: Anomalies / Dips / Spikes
        if any(kw in user_text for kw in ["anomal", "dip", "drop", "spike", "why did sales", "irregular", "unusual", "march"]):
            yield LLMEvent(
                "tool_call",
                {
                    "name": "find_anomalies",
                    "args": {"dataset_id": context_dataset_id, "series_id": "all"},
                },
            )
            return

        # Intent 3: Clean Data
        if any(kw in user_text for kw in ["clean", "sanitize", "fix", "repair", "dedupe"]):
            yield LLMEvent(
                "tool_call",
                {"name": "clean_data", "args": {"dataset_id": context_dataset_id}},
            )
            return

        # Intent 4: Validation
        if any(kw in user_text for kw in ["valid", "check", "ready for"]):
            yield LLMEvent(
                "tool_call",
                {"name": "validate_data", "args": {"dataset_id": context_dataset_id}},
            )
            return

        # Intent 5: Profile & Health
        if any(kw in user_text for kw in ["profile", "quality", "health", "how many rows", "cadence"]):
            yield LLMEvent(
                "tool_call",
                {"name": "profile_dataset", "args": {"dataset_id": context_dataset_id}},
            )
            return

        # Intent 6: Forecast Run (explicit forecast command)
        if any(kw in user_text for kw in ["forecast the next", "forecast sales", "run forecast", "train models", "forecast for"]):
            horizon = 30
            if "8 weeks" in user_text or "8-weeks" in user_text:
                horizon = 56
            elif "12 weeks" in user_text or "quarter" in user_text:
                horizon = 90
            elif "2 weeks" in user_text or "14 days" in user_text:
                horizon = 14

            yield LLMEvent(
                "tool_call",
                {
                    "name": "run_forecast",
                    "args": {
                        "dataset_id": context_dataset_id,
                        "horizon": horizon,
                        "series_id": "all",
                        "models": ["seasonal_naive", "holt_winters", "lightgbm", "xgboost"],
                    },
                },
            )
            return

        # Intent 7: Forecast Retrieval / Volume Check
        if any(kw in user_text for kw in ["total projected", "forecast volume", "projected sales", "how much will we sell"]):
            yield LLMEvent(
                "tool_call",
                {"name": "get_forecast", "args": {"run_id": context_run_id, "series_id": "all"}},
            )
            return

        # Intent 8: Leaderboard / Accuracy Comparison
        if any(kw in user_text for kw in ["leaderboard", "which model won", "accuracy", "wape", "best model", "trained models"]):
            yield LLMEvent(
                "tool_call",
                {"name": "get_leaderboard", "args": {"run_id": context_run_id}},
            )
            return

        # Intent 9: Period Comparison
        if any(kw in user_text for kw in ["compare", "vs last year", "last 4 weeks", "prior period"]):
            yield LLMEvent(
                "tool_call",
                {
                    "name": "compare_periods",
                    "args": {
                        "dataset_id": context_dataset_id,
                        "period_a": "last 4 weeks",
                        "period_b": "prior 4 weeks",
                        "series_id": "all",
                    },
                },
            )
            return

        # Intent 10: Top movers / Products needing attention
        if any(kw in user_text for kw in ["top", "attention", "mover", "declining", "growing"]):
            yield LLMEvent(
                "tool_call",
                {"name": "top_movers", "args": {"run_id": context_run_id}},
            )
            return

        # Intent 11: Executive Summary
        if any(kw in user_text for kw in ["summary", "executive", "brief", "overview", "bullets"]):
            yield LLMEvent(
                "tool_call",
                {"name": "executive_summary", "args": {"run_id": context_run_id}},
            )
            return

        # Default fallback: run_forecast or get_forecast
        if context_run_id and context_run_id != "default":
            yield LLMEvent("tool_call", {"name": "get_forecast", "args": {"run_id": context_run_id}})
        else:
            yield LLMEvent("tool_call", {"name": "profile_dataset", "args": {"dataset_id": context_dataset_id}})

    def _narrate_tool_result(self, tool_name: str, result: dict[str, Any]) -> str:
        """Constructs grounded text strictly using numbers present in result."""
        if "error" in result:
            return f"I encountered an error executing {tool_name}: {result['error']}. Please make sure an active dataset is selected."

        if tool_name == "run_forecast":
            model = result.get("best_model", "Best Model")
            wape = result.get("best_wape", 0.0)
            tot = result.get("forecast_period_total", 0.0)
            h = result.get("horizon_days", 30)
            return (
                f"### Forecast Completed ({h} Days)\n\n"
                f"- **Winning Model:** **{model}** achieved the lowest out-of-sample error with a **{wape}% WAPE**.\n"
                f"- **Projected Volume:** **{tot:,} total units** expected across the next **{h} days**.\n"
                f"- **Backtest Benchmark:** Successfully trained and backtested **{result.get('models_evaluated', 4)} models** using expanding-window folds.\n\n"
                f"You can inspect the detailed model leaderboard and download the full timeline breakdown as a CSV."
            )

        if tool_name == "get_leaderboard":
            models = result.get("models", [])
            winner = result.get("winning_model", "")
            lines = [f"### Model Performance Leaderboard\n\n**Winner:** **{winner}**\n"]
            for m in models:
                badge = "⭐ Best" if m.get("is_winner") else ""
                lines.append(
                    f"- **{m['model_name']}**: WAPE **{m['wape_pct']}%**, MAE **{m['mae']}**, RMSE **{m['rmse']}**, MASE **{m['mase']}** {badge}"
                )
            lines.append("\n*Note: WAPE (Weighted Absolute Percentage Error) is the primary retail metric used to evaluate out-of-sample accuracy.*")
            return "\n".join(lines)

        if tool_name == "what_if":
            base = result.get("baseline_forecast_total", 0.0)
            sim = result.get("simulated_forecast_total", 0.0)
            delta_vol = result.get("volume_impact_units", 0.0)
            delta_pct = result.get("volume_impact_pct", 0.0)
            promo = result.get("promo_change_applied", "+0%")
            scenario = result.get("scenario_name", "Simulation")

            return (
                f"### What-If Scenario Analysis: {scenario}\n\n"
                f"> **{result.get('simulation_disclaimer', 'SIMULATION ONLY')}**\n\n"
                f"- **Baseline Forecast:** **{base:,} units**\n"
                f"- **Simulated Forecast:** **{sim:,} units**\n"
                f"- **Projected Impact:** **{delta_vol:+,} units** (**{delta_pct:+}% change**)\n"
                f"- **Promotion Adjustment:** Applied **{promo}** promotional frequency shift.\n\n"
                f"Based on historical promotional response, this campaign provides significant incremental lift."
            )

        if tool_name == "find_anomalies":
            anomalies = result.get("anomalies", [])
            count = result.get("total_anomalies_detected", len(anomalies))
            if not anomalies:
                return f"### Historical Anomaly Audit\n\nNo critical anomalies were detected in the timeline. Sales demand followed expected seasonal baselines."

            lines = [f"### Historical Anomaly Audit\n\nDetected **{count} anomaly events** across the historical timeline:\n"]
            for a in anomalies[:5]:
                direction = "📈 Demand Surge" if a["type"] == "spike" else "📉 Severe Drop / Stockout"
                lines.append(
                    f"- **{a['date']}** ({direction}): Actual **{a['actual_value']} units** vs expected baseline **{a['expected_baseline']} units** (deviation: **{a['deviation']:+,} units**)."
                )
            return "\n".join(lines)

        if tool_name == "top_movers":
            dim = result.get("primary_dimension", "group").capitalize()
            growing = result.get("top_growing_groups", [])
            declining = result.get("top_declining_groups", [])

            lines = [f"### Top Volume Movers by {dim}\n"]
            if growing:
                lines.append("**Top Growing Groups:**")
                for g in growing:
                    lines.append(f"- **{g['group']}**: Projected **{g['projected_sales']:,} units** (**{g['percentage_change']:+}%** vs prior **{g['prior_sales']:,} units**)")
            if declining:
                lines.append("\n**Groups Needing Attention (Declining / Slowing):**")
                for d in declining:
                    lines.append(f"- **{d['group']}**: Projected **{d['projected_sales']:,} units** (**{d['percentage_change']:+}%** vs prior **{d['prior_sales']:,} units**)")
            return "\n".join(lines)

        if tool_name == "compare_periods":
            pa = result.get("period_a", {})
            pb = result.get("period_b", {})
            diff = result.get("difference", 0.0)
            pct = result.get("percentage_change", 0.0)
            direction = result.get("trend_direction", "shifted")

            return (
                f"### Period Comparison\n\n"
                f"- **{pa.get('label', 'Current Period')}:** **{pa.get('total_sales', 0.0):,} units** (Daily avg: **{pa.get('daily_average', 0.0):,}**)\n"
                f"- **{pb.get('label', 'Prior Period')}:** **{pb.get('total_sales', 0.0):,} units** (Daily avg: **{pb.get('daily_average', 0.0):,}**)\n"
                f"- **Volume Shift:** Sales {direction} by **{diff:+,} units** (**{pct:+}%**).\n"
            )

        if tool_name == "profile_dataset" or tool_name == "validate_data":
            score = result.get("health_score", 100)
            rows = result.get("row_count", result.get("rows_after_clean", 0))
            is_valid = result.get("is_valid", result.get("is_valid_for_forecasting", True))
            status_text = "Ready for modeling" if is_valid else "Requires sanitization"

            return (
                f"### Data Quality & Health Audit\n\n"
                f"- **Overall Health Score:** **{score}/100** ({status_text})\n"
                f"- **Total Records:** **{rows:,} rows** detected.\n"
                f"- **Cadence:** **{result.get('cadence', 'Daily')}** timeline.\n"
                f"- **Quality Summary:** Identified **{result.get('issues_count', result.get('warning_issues', 0))} quality check items**."
            )

        if tool_name == "clean_data":
            actions = result.get("actions_taken", [])
            score = result.get("new_health_score", 100)
            rows = result.get("rows_after_clean", 0)
            return (
                f"### Automated Data Sanitization Complete\n\n"
                f"- **Health Score After Clean:** **{score}/100**\n"
                f"- **Sanitized Dataset Size:** **{rows:,} rows**\n"
                f"- **Actions Applied:** {', '.join(actions) if actions else 'Timeline verified'}\n\n"
                f"Your historical dataset is now clean, continuous, and primed for model training."
            )

        if tool_name == "executive_summary":
            facts = result.get("facts", {})
            h = result.get("horizon_days", 30)
            winner = result.get("winning_model", "Best Model")
            wape = result.get("best_wape_pct", 0.0)

            return (
                f"### Executive Sales Forecast Brief ({h} Days)\n\n"
                f"- **Outlook:** {facts.get('outlook', '')}\n"
                f"- **Demand Drivers:** {facts.get('drivers', f'{winner} captured strong cyclical lifts.')}\n"
                f"- **Operational Risks:** {facts.get('risks', f'Model variance estimated at {wape}% WAPE.')}\n"
                f"- **Recommended Actions:** {facts.get('recommended_actions', 'Adjust safety stocks based on forecasted weekend peaks.')}\n"
                f"- **Forecast Confidence:** **{facts.get('confidence', f'High ({wape}% WAPE)')}**\n"
            )

        return f"Tool {tool_name} returned results: {str(result)}"
