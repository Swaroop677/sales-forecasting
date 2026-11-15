import asyncio
import json
from typing import Any, AsyncIterator
from sqlmodel import Session, select
from backend.app.config import settings
from backend.app.db import engine
from backend.app.models.chat import ChatMessage, ChatSession
from backend.app.models.dataset import Dataset
from backend.app.models.run import ForecastRun
from backend.app.services.agent_tools.definitions import AGENT_TOOL_DEFINITIONS
from backend.app.services.agent_tools.handlers import execute_tool
from backend.app.services.grounding import (
    SYSTEM_SAFETY_PROMPT,
    sanitize_untrusted_input,
    verify_numeric_grounding,
)
from backend.app.services.llm.base import LLMEvent, LLMProvider


async def run_agent_stream(
    user_query: str,
    provider: LLMProvider,
    session_id: str | None = None,
    dataset_id: str | None = None,
    run_id: str | None = None,
) -> AsyncIterator[str]:
    """
    Core agent loop orchestrating multi-turn tool calling and SSE streaming:
    Events streamed:
    - token: partial text chunks
    - tool_start: tool name and arguments
    - tool_result: compact output summary
    - chart: visualization specification (bar, line, etc.)
    - grounding: numeric verification report
    - done: stream completion signal
    - error: error message
    """
    with Session(engine) as db_session:
        # 1. Resolve or create ChatSession
        chat_session = None
        if session_id:
            chat_session = db_session.get(ChatSession, session_id)

        if not chat_session:
            # Look up dataset / run title
            ds_name = "Forecasting Session"
            if dataset_id:
                ds = db_session.get(Dataset, dataset_id)
                if ds:
                    ds_name = f"Session - {ds.name}"

            chat_session = ChatSession(
                title=ds_name,
                dataset_id=dataset_id,
                run_id=run_id,
            )
            db_session.add(chat_session)
            db_session.commit()
            db_session.refresh(chat_session)

        # Update dataset/run context if provided
        if dataset_id:
            chat_session.dataset_id = dataset_id
        if run_id:
            chat_session.run_id = run_id
        db_session.add(chat_session)
        db_session.commit()

        # 2. Save User Message
        user_msg = ChatMessage(
            session_id=chat_session.id,
            role="user",
            content=user_query,
        )
        db_session.add(user_msg)
        db_session.commit()

        # 3. Build Conversation History
        history_msgs = db_session.exec(
            select(ChatMessage)
            .where(ChatMessage.session_id == chat_session.id)
            .order_by(ChatMessage.created_at.asc())
        ).all()

        # Cap history to avoid token explosion
        recent_history = history_msgs[-12:]

        messages_for_llm: list[dict[str, Any]] = []

        # Add active context header as untrusted data
        context_notes = []
        if chat_session.dataset_id:
            context_notes.append(f"active_dataset_id: '{chat_session.dataset_id}'")
        if chat_session.run_id:
            context_notes.append(f"active_run_id: '{chat_session.run_id}'")

        if context_notes:
            messages_for_llm.append({
                "role": "system",
                "content": f"Context environment:\n" + "\n".join(context_notes),
            })

        for hm in recent_history:
            if hm.role == "user":
                messages_for_llm.append({
                    "role": "user",
                    "content": sanitize_untrusted_input(hm.content),
                    "dataset_id": chat_session.dataset_id,
                    "run_id": chat_session.run_id,
                })
            elif hm.role == "assistant":
                item: dict[str, Any] = {"role": "assistant", "content": hm.content}
                if hm.tool_calls:
                    item["tool_calls"] = hm.tool_calls
                messages_for_llm.append(item)

        # 4. Multi-Turn Tool Calling Execution Loop
        tool_iterations = 0
        max_tool_iterations = settings.MAX_AGENT_TOOL_STEPS
        accumulated_tokens: list[str] = []
        accumulated_tool_calls: list[dict[str, Any]] = []
        accumulated_tool_outputs: list[dict[str, Any]] = []
        captured_chart_spec: dict[str, Any] | None = None

        while tool_iterations < max_tool_iterations:
            tool_iterations += 1
            has_tool_call = False
            turn_tool_calls: list[dict[str, Any]] = []

            async for event in provider.stream_turn(
                messages=messages_for_llm,
                tools=AGENT_TOOL_DEFINITIONS,
                system_prompt=SYSTEM_SAFETY_PROMPT,
            ):
                if event.event_type == "token":
                    accumulated_tokens.append(event.data)
                    yield f"event: token\ndata: {json.dumps({'content': event.data})}\n\n"

                elif event.event_type == "tool_call":
                    has_tool_call = True
                    tool_data = event.data
                    tool_name = tool_data.get("name")
                    tool_args = tool_data.get("args", {})

                    # Inject active dataset_id or run_id if missing in tool arguments
                    if "dataset_id" in tool_args and (not tool_args["dataset_id"] or tool_args["dataset_id"] == "default"):
                        tool_args["dataset_id"] = chat_session.dataset_id or ""
                    elif "dataset_id" not in tool_args and chat_session.dataset_id and tool_name in ["profile_dataset", "validate_data", "clean_data", "run_forecast", "compare_periods", "find_anomalies"]:
                        tool_args["dataset_id"] = chat_session.dataset_id

                    if "run_id" in tool_args and (not tool_args["run_id"] or tool_args["run_id"] == "default"):
                        tool_args["run_id"] = chat_session.run_id or ""
                    elif "run_id" not in tool_args and chat_session.run_id and tool_name in ["get_leaderboard", "get_forecast", "top_movers", "what_if", "executive_summary"]:
                        tool_args["run_id"] = chat_session.run_id

                    turn_tool_calls.append({"name": tool_name, "args": tool_args})
                    accumulated_tool_calls.append({"name": tool_name, "args": tool_args})

                    # Emit tool_start SSE
                    yield f"event: tool_start\ndata: {json.dumps({'name': tool_name, 'args': tool_args})}\n\n"

                    # Execute tool in database session
                    tool_res = execute_tool(db_session, tool_name, tool_args)

                    # Update session run_id if tool created a forecast run
                    if tool_name == "run_forecast" and "run_id" in tool_res.get("result", {}):
                        chat_session.run_id = tool_res["result"]["run_id"]
                        db_session.add(chat_session)
                        db_session.commit()

                    chart = tool_res.get("chart_spec")
                    if chart:
                        captured_chart_spec = chart
                        yield f"event: chart\ndata: {json.dumps(chart)}\n\n"

                    compact_result = tool_res.get("result", {})
                    accumulated_tool_outputs.append(compact_result)

                    # Emit tool_result SSE
                    yield f"event: tool_result\ndata: {json.dumps({'name': tool_name, 'result': compact_result})}\n\n"

                    # Add tool response to messages for next turn
                    messages_for_llm.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": compact_result,
                    })

                elif event.event_type == "error":
                    yield f"event: error\ndata: {json.dumps({'message': event.data})}\n\n"
                    return

            # If no tool was called in this turn, the assistant finished speaking
            if not has_tool_call:
                break

        full_response_text = "".join(accumulated_tokens).strip()

        # 5. Numeric Grounding Verification Check
        grounding_result = verify_numeric_grounding(
            response_text=full_response_text,
            tool_outputs=accumulated_tool_outputs,
        )

        yield f"event: grounding\ndata: {json.dumps(grounding_result)}\n\n"

        # 6. Save Assistant Response in Database
        assistant_msg = ChatMessage(
            session_id=chat_session.id,
            role="assistant",
            content=full_response_text,
            tool_calls=accumulated_tool_calls,
            chart_spec=captured_chart_spec,
            grounding_info=grounding_result,
        )
        db_session.add(assistant_msg)
        db_session.commit()
        db_session.refresh(assistant_msg)

        # 7. Emit Done Event
        yield f"event: done\ndata: {json.dumps({'session_id': chat_session.id, 'message_id': assistant_msg.id})}\n\n"
