"""Knowledge base management routes."""
from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status

from api.dependencies import get_knowledge_service, verify_api_key
from api.schemas import (
    KnowledgeChunkListResponse,
    KnowledgeDeleteResponse,
    KnowledgeRebuildResponse,
    KnowledgeSearchResponse,
    KnowledgeUploadResponse,
    UserChunkListResponse,
)
from services.knowledge_service import KnowledgeService


router = APIRouter(prefix="/api/v1/knowledge", dependencies=[Depends(verify_api_key)])


@router.post("/documents/upload", response_model=KnowledgeUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Query("__shared__"),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """Upload a txt/pdf document and index it immediately."""
    try:
        content = await file.read()
        result = service.add_uploaded_document(file.filename or "knowledge", content, user_id=user_id)
        return KnowledgeUploadResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/chunks", response_model=KnowledgeChunkListResponse)
def list_chunks(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str | None = Query(None),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """List vector-store chunks with pagination, optionally filtered by user_id."""
    return KnowledgeChunkListResponse(**service.list_chunks(limit=limit, offset=offset, user_id=user_id))


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_chunks(
    query: str = Query(..., min_length=1),
    k: int = Query(5, ge=1, le=20),
    user_id: str | None = Query(None),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """Search knowledge-base chunks, optionally scoped to a user's private+shared knowledge."""
    return KnowledgeSearchResponse(query=query, results=service.search_chunks(query=query, k=k, user_id=user_id))


@router.delete("/chunks/{doc_id}", response_model=KnowledgeDeleteResponse)
def delete_chunk(
    doc_id: str,
    user_id: str | None = Query(None),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """Delete one vector-store chunk by doc_id without deleting the source file."""
    result = service.delete_chunk(doc_id, user_id=user_id)
    return KnowledgeDeleteResponse(**result)


@router.post("/rebuild", response_model=KnowledgeRebuildResponse)
def rebuild_knowledge(service: KnowledgeService = Depends(get_knowledge_service)):
    """Clear the vector store and rebuild from configured knowledge files and uploads."""
    return KnowledgeRebuildResponse(**service.rebuild())


@router.get("/users/{user_id}/chunks", response_model=UserChunkListResponse)
def list_user_chunks(
    user_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """List chunks belonging to a specific user."""
    result = service.list_user_chunks(user_id, limit=limit, offset=offset)
    return UserChunkListResponse(user_id=user_id, **result)
