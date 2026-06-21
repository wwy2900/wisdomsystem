"""聊天/会话路由"""
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse
from api.schemas import (
    CreateSessionRequest, CreateSessionResponse,
    SessionListResponse, SessionInfo,
    SessionDetailResponse,
    ChatRequest, ChatResponse,
)
from api.dependencies import verify_api_key, get_chat_service
from services.chat_service import ChatService

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(req: CreateSessionRequest, service: ChatService = Depends(get_chat_service)):
    """创建会话"""
    session_id = service.create_session(req.user_id)
    return CreateSessionResponse(session_id=session_id)


@router.get("/users/{user_id}/sessions", response_model=SessionListResponse)
def list_user_sessions(user_id: str, service: ChatService = Depends(get_chat_service)):
    """查询用户历史会话"""
    sessions = service.list_user_sessions(user_id)
    return SessionListResponse(
        sessions=[SessionInfo(**s) for s in sessions]
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str, service: ChatService = Depends(get_chat_service)):
    """查询单个会话详情"""
    data = service.get_session(session_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionDetailResponse(
        session_id=data["session_id"],
        user_id=data["user_id"],
        messages=data["messages"],
    )


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, service: ChatService = Depends(get_chat_service)):
    """非流式聊天"""
    answer = service.chat(req.user_id, req.session_id, req.message)
    return ChatResponse(session_id=req.session_id, answer=answer)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, service: ChatService = Depends(get_chat_service)):
    """SSE 流式聊天"""

    async def event_generator():
        try:
            for event_type, content in service.chat_stream(req.user_id, req.session_id, req.message):
                yield {"event": event_type, "data": json.dumps({"content": content}, ensure_ascii=False)}
            yield {"event": "done", "data": json.dumps({"session_id": req.session_id}, ensure_ascii=False)}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"content": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(event_generator())
