import asyncio
from backend.app.services.llm.fallback_provider import FallbackProvider


def test_fallback_provider_intent_tool_calls():
    async def _run():
        provider = FallbackProvider()

        # 1. Forecast intent
        events = [
            e async for e in provider.stream_turn(
                messages=[{"role": "user", "content": "Forecast the next 8 weeks of demand"}],
                tools=[],
                system_prompt="",
            )
        ]
        tool_events = [e for e in events if e.event_type == "tool_call"]
        assert len(tool_events) == 1
        assert tool_events[0].data["name"] == "run_forecast"
        assert tool_events[0].data["args"]["horizon"] == 56

        # 2. What-If intent
        events_whatif = [
            e async for e in provider.stream_turn(
                messages=[{"role": "user", "content": "What if I run a 25% promo next month?"}],
                tools=[],
                system_prompt="",
            )
        ]
        tc_whatif = [e for e in events_whatif if e.event_type == "tool_call"]
        assert len(tc_whatif) == 1
        assert tc_whatif[0].data["name"] == "what_if"
        assert tc_whatif[0].data["args"]["promo_change_pct"] == 25.0

        # 3. Anomaly intent
        events_anom = [
            e async for e in provider.stream_turn(
                messages=[{"role": "user", "content": "Why did sales dip in March?"}],
                tools=[],
                system_prompt="",
            )
        ]
        tc_anom = [e for e in events_anom if e.event_type == "tool_call"]
        assert len(tc_anom) == 1
        assert tc_anom[0].data["name"] == "find_anomalies"

        # 4. Top movers intent
        events_movers = [
            e async for e in provider.stream_turn(
                messages=[{"role": "user", "content": "Which products need attention or are declining?"}],
                tools=[],
                system_prompt="",
            )
        ]
        tc_movers = [e for e in events_movers if e.event_type == "tool_call"]
        assert len(tc_movers) == 1
        assert tc_movers[0].data["name"] == "top_movers"

    asyncio.run(_run())


def test_fallback_provider_narration():
    async def _run():
        provider = FallbackProvider()

        tool_result = {
            "best_model": "LightGBM",
            "best_wape": 8.45,
            "forecast_period_total": 12450.0,
            "horizon_days": 30,
            "models_evaluated": 4,
        }

        messages = [
            {"role": "user", "content": "Run forecast"},
            {"role": "tool", "name": "run_forecast", "content": tool_result},
        ]

        tokens = []
        async for event in provider.stream_turn(messages, tools=[], system_prompt=""):
            if event.event_type == "token":
                tokens.append(event.data)

        narrative = "".join(tokens)
        assert "LightGBM" in narrative
        assert "8.45" in narrative
        assert "12,450" in narrative
        assert "30 days" in narrative.lower()

    asyncio.run(_run())
