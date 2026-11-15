from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from backend.app.db import get_session
from backend.app.models.chat import ChatMessage, ChatSession
from backend.app.models.dataset import Dataset
from backend.app.models.run import ForecastRun
from backend.app.schemas.agent import (
    AutopilotRequest,
    ChatMessageResponse,
    ChatRequest,
    ChatSessionResponse,
    TestConnectionRequest,
    TestConnectionResponse,
)
from backend.app.services.agent_runner import run_agent_stream
from backend.app.services.agent_tools.handlers import (
    handle_clean_data,
    handle_executive_summary,
    handle_run_forecast,
    handle_validate_data,
)
from backend.app.services.llm.base import LLMEvent
from backend.app.services.llm.factory import check_rate_limit, get_llm_provider

router = APIRouter(prefix="/agent", tags=["AI Agent"])


@router.post("/chat")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    x_llm_provider: str | None = Header(default=None),
    x_llm_api_key: str | None = Header(default=None),
    x_llm_base_url: str | None = Header(default=None),
    x_llm_model: str | None = Header(default=None),
):
    """
    Streaming conversation endpoint powered by Server-Sent Events (SSE).
    Emits token, tool_start, tool_result, chart, grounding, and done events.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit reached. Please wait a moment before sending more messages.",
        )

    # Priority: Header -> Body -> Default
    provider_name = x_llm_provider or body.provider
    api_key = x_llm_api_key or body.api_key
    base_url = x_llm_base_url or body.base_url
    model = x_llm_model or body.model

    provider = get_llm_provider(
        provider_name=provider_name,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    generator = run_agent_stream(
        user_query=body.message,
        provider=provider,
        session_id=body.session_id,
        dataset_id=body.dataset_id,
        run_id=body.run_id,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/autopilot")
def run_autopilot(request: AutopilotRequest, session: Session = Depends(get_session)):
    """
    One-click autonomous pipeline:
    1. Validates dataset
    2. Cleans anomalies/gaps
    3. Trains and backtests 4 candidate models
    4. Generates an executive briefing (5 bullets: outlook, drivers, risks, recommended actions, confidence)
    """
    dataset = session.get(Dataset, request.dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    # Step 1: Validate
    val_res = handle_validate_data(session, dataset.id)

    # Step 2: Clean
    clean_res = handle_clean_data(session, dataset.id)

    # Step 3: Train & Forecast
    models = request.models or ["seasonal_naive", "holt_winters", "lightgbm", "xgboost"]
    forecast_res = handle_run_forecast(
        session=session,
        dataset_id=dataset.id,
        horizon=request.horizon,
        series_id="all",
        models=models,
    )

    run_id = forecast_res.get("result", {}).get("run_id")
    if not run_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Autopilot forecast run failed.")

    # Step 4: Executive Summary
    summary_res = handle_executive_summary(session, run_id)

    return {
        "status": "completed",
        "dataset_name": dataset.name,
        "run_id": run_id,
        "validation": val_res.get("result"),
        "cleaning": clean_res.get("result"),
        "forecast": forecast_res.get("result"),
        "executive_summary": summary_res.get("result", {}).get("facts", {}),
        "chart_spec": forecast_res.get("chart_spec"),
    }


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_llm_connection(body: TestConnectionRequest):
    """Verifies that the provided API credentials connect successfully with the target model."""
    provider = get_llm_provider(
        provider_name=body.provider,
        api_key=body.api_key,
        base_url=body.base_url,
        model=body.model,
    )

    # Attempt a quick 1-turn response
    test_messages = [{"role": "user", "content": "Hello. Answer with one word: 'Forecastly'."}]

    collected_tokens = []
    error_msg = None

    try:
        async for event in provider.stream_turn(
            messages=test_messages,
            tools=[],
            system_prompt="Answer briefly.",
        ):
            if event.event_type == "token":
                collected_tokens.append(event.data)
            elif event.event_type == "error":
                error_msg = event.data
                break
    except Exception as e:
        error_msg = str(e)

    if error_msg:
        return TestConnectionResponse(
            success=False,
            message=f"Connection failed: {error_msg}",
            model=provider.model,
            provider=provider.name,
        )

    return TestConnectionResponse(
        success=True,
        message=f"Successfully connected to {provider.name} ({provider.model})!",
        model=provider.model,
        provider=provider.name,
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
def list_chat_sessions(session: Session = Depends(get_session)):
    statement = select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(20)
    sessions = session.exec(statement).all()

    result = []
    for s in sessions:
        # Load messages
        msgs = session.exec(
            select(ChatMessage).where(ChatMessage.session_id == s.id).order_by(ChatMessage.created_at.asc())
        ).all()
        msg_responses = [
            ChatMessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                tool_calls=m.tool_calls or [],
                chart_spec=m.chart_spec,
                grounding_info=m.grounding_info,
                created_at=m.created_at,
            )
            for m in msgs
        ]
        result.append(
            ChatSessionResponse(
                id=s.id,
                title=s.title,
                dataset_id=s.dataset_id,
                run_id=s.run_id,
                created_at=s.created_at,
                updated_at=s.updated_at,
                messages=msg_responses,
            )
        )
    return result


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(session_id: str, session: Session = Depends(get_session)):
    chat_session = session.get(ChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")

    msgs = session.exec(
        select(ChatMessage).where(ChatMessage.session_id == chat_session.id).order_by(ChatMessage.created_at.asc())
    ).all()

    return ChatSessionResponse(
        id=chat_session.id,
        title=chat_session.title,
        dataset_id=chat_session.dataset_id,
        run_id=chat_session.run_id,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
        messages=[
            ChatMessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                tool_calls=m.tool_calls or [],
                chart_spec=m.chart_spec,
                grounding_info=m.grounding_info,
                created_at=m.created_at,
            )
            for m in msgs
        ],
    )


@router.delete("/sessions/{session_id}")
def delete_chat_session(session_id: str, session: Session = Depends(get_session)):
    chat_session = session.get(ChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")

    msgs = session.exec(select(ChatMessage).where(ChatMessage.session_id == session_id)).all()
    for m in msgs:
        session.delete(m)
    session.delete(chat_session)
    session.commit()
    return {"status": "deleted", "id": session_id}
