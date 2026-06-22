"""Authenticated self-scoped routes for the Vue frontend."""
import json

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sse_starlette.sse import EventSourceResponse

from api.dependencies import get_chat_service, get_current_user, get_knowledge_service
from api.schemas import (
    CreateSessionResponse,
    KnowledgeDeleteResponse,
    KnowledgeUploadResponse,
    MeChatRequest,
    MeSessionListResponse,
    SessionDetailResponse,
    SessionInfo,
    UserChunkListResponse,
)


router = APIRouter(prefix="/api/v1/me", tags=["me"])


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(
    current_user: dict = Depends(get_current_user),
    service=Depends(get_chat_service),
):
    session_id = service.create_session(current_user["id"])
    return CreateSessionResponse(session_id=session_id)


@router.get("/sessions", response_model=MeSessionListResponse)
def list_sessions(
    current_user: dict = Depends(get_current_user),
    service=Depends(get_chat_service),
):
    sessions = service.list_user_sessions(current_user["id"])
    return MeSessionListResponse(sessions=[SessionInfo(**item) for item in sessions])


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    service=Depends(get_chat_service),
):
    session = service.get_user_session(session_id, current_user["id"])
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionDetailResponse(
        session_id=session["session_id"],
        user_id=session["user_id"],
        messages=session["messages"],
    )


@router.post("/chat/stream")
async def chat_stream(
    req: MeChatRequest,
    current_user: dict = Depends(get_current_user),
    service=Depends(get_chat_service),
):
    session_id = req.session_id
    if session_id:
        session = service.get_user_session(session_id, current_user["id"])
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    else:
        session_id = service.create_session(current_user["id"])

    async def event_generator():
        yield {"event": "session", "data": json.dumps({"session_id": session_id}, ensure_ascii=False)}
        try:
            for event_type, content in service.chat_stream(current_user["id"], session_id, req.message):
                yield {"event": event_type, "data": json.dumps({"content": content}, ensure_ascii=False)}
            yield {"event": "done", "data": json.dumps({"session_id": session_id}, ensure_ascii=False)}
        except Exception as exc:
            yield {"event": "error", "data": json.dumps({"content": str(exc)}, ensure_ascii=False)}

    return EventSourceResponse(event_generator())


@router.get("/knowledge/chunks", response_model=UserChunkListResponse)
def list_private_chunks(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    service=Depends(get_knowledge_service),
):
    result = service.list_user_chunks(current_user["id"], limit=limit, offset=offset)
    return UserChunkListResponse(user_id=current_user["id"], **result)


@router.post("/knowledge/documents/upload", response_model=KnowledgeUploadResponse)
async def upload_private_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    service=Depends(get_knowledge_service),
):
    try:
        content = await file.read()
        result = service.add_uploaded_document(file.filename or "knowledge", content, user_id=current_user["id"])
        return KnowledgeUploadResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/knowledge/chunks/{doc_id}", response_model=KnowledgeDeleteResponse)
def delete_private_chunk(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
    service=Depends(get_knowledge_service),
):
    result = service.delete_chunk(doc_id, user_id=current_user["id"])
    return KnowledgeDeleteResponse(**result)
