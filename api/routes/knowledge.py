"""Legacy API-key protected knowledge management routes."""
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from api.dependencies import get_knowledge_service, verify_api_key
from api.schemas import (
    KnowledgeChunkListResponse,
    KnowledgeDeleteResponse,
    KnowledgeRebuildResponse,
    KnowledgeSearchResponse,
    KnowledgeUploadResponse,
    UserChunkListResponse,
)


router = APIRouter(prefix="/api/v1/knowledge", dependencies=[Depends(verify_api_key)], tags=["legacy"])


@router.post("/documents/upload", response_model=KnowledgeUploadResponse, deprecated=True)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Query("__shared__"),
    service=Depends(get_knowledge_service),
):
    try:
        content = await file.read()
        result = service.add_uploaded_document(file.filename or "knowledge", content, user_id=user_id)
        return KnowledgeUploadResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/chunks", response_model=KnowledgeChunkListResponse, deprecated=True)
def list_chunks(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str | None = Query(None),
    service=Depends(get_knowledge_service),
):
    return KnowledgeChunkListResponse(**service.list_chunks(limit=limit, offset=offset, user_id=user_id))


@router.get("/search", response_model=KnowledgeSearchResponse, deprecated=True)
def search_chunks(
    query: str = Query(..., min_length=1),
    k: int = Query(5, ge=1, le=20),
    user_id: str | None = Query(None),
    service=Depends(get_knowledge_service),
):
    return KnowledgeSearchResponse(query=query, results=service.search_chunks(query=query, k=k, user_id=user_id))


@router.delete("/chunks/{doc_id}", response_model=KnowledgeDeleteResponse, deprecated=True)
def delete_chunk(
    doc_id: str,
    user_id: str | None = Query(None),
    service=Depends(get_knowledge_service),
):
    result = service.delete_chunk(doc_id, user_id=user_id)
    return KnowledgeDeleteResponse(**result)


@router.post("/rebuild", response_model=KnowledgeRebuildResponse, deprecated=True)
def rebuild_knowledge(service=Depends(get_knowledge_service)):
    return KnowledgeRebuildResponse(**service.rebuild())


@router.get("/users/{user_id}/chunks", response_model=UserChunkListResponse, deprecated=True)
def list_user_chunks(
    user_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service=Depends(get_knowledge_service),
):
    result = service.list_user_chunks(user_id, limit=limit, offset=offset)
    return UserChunkListResponse(user_id=user_id, **result)
