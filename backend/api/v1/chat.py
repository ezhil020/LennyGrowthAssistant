"""api/v1/chat.py — Chat endpoint with SSE streaming."""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from backend.models.schemas import ChatRequest
from backend.services.chat_service import ChatService
from backend.services.dependencies import get_chat_service

router = APIRouter(tags=["chat"])


@router.post("/sessions/{session_id}/chat")
async def chat(
    session_id: str,
    body: ChatRequest,
    request: Request,
    chat_svc: ChatService = Depends(get_chat_service),
):
    """Send a message and get a streaming SSE response.

    SSE event types:
      - routing: {skill_chosen, intent, confidence, pass_used, context_signals}
      - token: {text} — streamed response tokens
      - sources: SourceAttribution JSON
      - artifact: {id, type, content, version, title}
      - session_title: {title}
      - done: {message_id}
      - error: {message}
    """
    request_id = getattr(request.state, "request_id", "")

    async def event_stream():
        try:
            async for event in chat_svc.handle_stream(
                session_id=session_id,
                user_message_text=body.message,
                request_id=request_id,
            ):
                event_type = event.get("event", "message")
                data = json.dumps(event.get("data", {}), default=str)
                yield f"event: {event_type}\ndata: {data}\n\n"
        except Exception as e:
            error_data = json.dumps({"message": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
