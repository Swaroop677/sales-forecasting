import asyncio
import json
import time
from pathlib import Path
from sqlmodel import Session, select
from backend.app.db import engine, init_db
from backend.app.models.dataset import Dataset
from backend.app.models.run import ForecastRun
from backend.app.services.agent_runner import run_agent_stream
from backend.app.services.agent_tools.handlers import handle_run_forecast
from backend.app.services.llm.base import LLMProvider
from backend.app.services.llm.factory import get_llm_provider
from backend.app.services.sample_data import ensure_sample_data_file


def setup_eval_fixtures() -> tuple[str, str]:
    """Ensures a baseline sample dataset and forecast run exist for deterministic evaluation."""
    init_db()
    with Session(engine) as session:
        # Check dataset
        statement = select(Dataset).limit(1)
        dataset = session.exec(statement).first()
        if not dataset:
            from backend.app.api.datasets import create_sample_dataset
            dataset = create_sample_dataset(session=session)

        # Check run
        run_stmt = select(ForecastRun).where(ForecastRun.dataset_id == dataset.id).limit(1)
        run = session.exec(run_stmt).first()
        if not run or run.status != "completed":
            res = handle_run_forecast(
                session=session,
                dataset_id=dataset.id,
                horizon=30,
                series_id="all",
                models=["seasonal_naive", "lightgbm"],
            )
            run_id = res.get("result", {}).get("run_id", "")
        else:
            run_id = run.id

        return dataset.id, run_id


async def run_evaluation(provider: LLMProvider | None = None) -> dict:
    """Executes the 15-question benchmark suite and calculates metrics."""
    dataset_id, run_id = setup_eval_fixtures()
    provider = provider or get_llm_provider("fallback")

    evals_path = Path(__file__).parent / "benchmark_questions.json"
    with open(evals_path, "r") as f:
        questions = json.load(f)

    results = []
    correct_tools = 0
    grounded_turns = 0
    total_latency = 0.0

    print(f"\n=======================================================")
    print(f"  Forecastly Agent Benchmark: {provider.name}")
    print(f"  Model: {provider.model}")
    print(f"  Total Questions: {len(questions)}")
    print(f"=======================================================\n")

    for q in questions:
        q_id = q["id"]
        prompt = q["prompt"]
        exp_tool = q["expected_tool"]

        start_time = time.perf_counter()

        actual_tool = None
        grounding_verified = False
        response_text = ""

        # Consume SSE stream
        async for sse_chunk in run_agent_stream(
            user_query=prompt,
            provider=provider,
            dataset_id=dataset_id,
            run_id=run_id,
        ):
            # Parse SSE lines
            lines = sse_chunk.strip().split("\n")
            event_type = ""
            data_str = ""
            for line in lines:
                if line.startswith("event:"):
                    event_type = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_str = line[len("data:"):].strip()

            if event_type == "tool_start" and data_str:
                tool_data = json.loads(data_str)
                if not actual_tool:
                    actual_tool = tool_data.get("name")

            elif event_type == "token" and data_str:
                token_data = json.loads(data_str)
                response_text += token_data.get("content", "")

            elif event_type == "grounding" and data_str:
                g_data = json.loads(data_str)
                grounding_verified = g_data.get("verified", False)

        duration = time.perf_counter() - start_time
        total_latency += duration

        tool_match = (actual_tool == exp_tool)
        if tool_match:
            correct_tools += 1
        if grounding_verified:
            grounded_turns += 1

        results.append({
            "id": q_id,
            "category": q["category"],
            "prompt": prompt,
            "expected_tool": exp_tool,
            "selected_tool": actual_tool,
            "tool_match": tool_match,
            "grounded_verified": grounding_verified,
            "latency_seconds": round(duration, 3),
        })

        status_icon = "✓" if tool_match else "✗"
        ground_icon = "✓" if grounding_verified else "⚠"
        print(f"[{status_icon}] {q_id}: Tool: {actual_tool} (exp: {exp_tool}) | Grounding: {ground_icon} | {duration:.2f}s")

    n = len(questions)
    tool_accuracy = round((correct_tools / n) * 100.0, 1)
    grounded_rate = round((grounded_turns / n) * 100.0, 1)
    avg_latency = round(total_latency / n, 3)

    summary = {
        "provider": provider.name,
        "model": provider.model,
        "total_evals": n,
        "tool_selection_accuracy_pct": tool_accuracy,
        "grounded_number_rate_pct": grounded_rate,
        "average_latency_sec": avg_latency,
        "details": results,
    }

    print("\n-------------------------------------------------------")
    print(f"Summary Results:")
    print(f"- Tool Selection Accuracy : {tool_accuracy}% ({correct_tools}/{n})")
    print(f"- Grounded Number Rate    : {grounded_rate}% ({grounded_turns}/{n})")
    print(f"- Average Latency         : {avg_latency}s")
    print("-------------------------------------------------------\n")

    return summary


if __name__ == "__main__":
    asyncio.run(run_evaluation())
