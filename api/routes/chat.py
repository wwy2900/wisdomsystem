"""Legacy API-key protected chat and session routes."""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from api.dependencies import get_chat_service, verify_api_key
from api.schemas import (
    ChatRequest,
    ChatResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    SessionDetailResponse,
    SessionInfo,
    SessionListResponse,
)


router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)], tags=["legacy"])


@router.post("/sessions", response_model=CreateSessionResponse, deprecated=True)
def create_session(req: CreateSessionRequest, service=Depends(get_chat_service)):
    return CreateSessionResponse(session_id=service.create_session(req.user_id))


@router.get("/users/{user_id}/sessions", response_model=SessionListResponse, deprecated=True)
def list_user_sessions(user_id: str, service=Depends(get_chat_service)):
    sessions = service.list_user_sessions(user_id)
    return SessionListResponse(sessions=[SessionInfo(**item) for item in sessions])


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse, deprecated=True)
def get_session(session_id: str, service=Depends(get_chat_service)):
    data = service.get_session(session_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionDetailResponse(
        session_id=data["session_id"],
        user_id=data["user_id"],
        messages=data["messages"],
    )


@router.post("/chat", response_model=ChatResponse, deprecated=True)
def chat(req: ChatRequest, service=Depends(get_chat_service)):
    answer = service.chat(req.user_id, req.session_id, req.message)
    return ChatResponse(session_id=req.session_id, answer=answer)


@router.post("/chat/stream", deprecated=True)
async def chat_stream(req: ChatRequest, service=Depends(get_chat_service)):
    async def event_generator():
        try:
            done_payload = {"session_id": req.session_id, "sources": []}
            for event_type, payload in service.chat_stream(req.user_id, req.session_id, req.message):
                if event_type == "_done":
                    done_payload["sources"] = payload.get("sources", [])
                    continue
                yield {"event": event_type, "data": json.dumps(payload, ensure_ascii=False)}
            yield {"event": "done", "data": json.dumps(done_payload, ensure_ascii=False)}
        except Exception as exc:
            yield {"event": "error", "data": json.dumps({"content": str(exc)}, ensure_ascii=False)}

    return EventSourceResponse(event_generator())
