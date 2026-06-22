"""Admin-only knowledge management routes for the Vue frontend."""
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from api.dependencies import get_knowledge_service, require_admin
from api.schemas import (
    AdminKnowledgeChunkListResponse,
    KnowledgeDeleteResponse,
    KnowledgeRebuildResponse,
    KnowledgeSearchResponse,
    KnowledgeUploadResponse,
)


router = APIRouter(prefix="/api/v1/admin/knowledge", tags=["admin"])


@router.get("/chunks", response_model=AdminKnowledgeChunkListResponse)
def list_chunks(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str | None = Query(None),
    current_user: dict = Depends(require_admin),
    service=Depends(get_knowledge_service),
):
    del current_user
    return AdminKnowledgeChunkListResponse(**service.list_chunks(limit=limit, offset=offset, user_id=user_id))


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_chunks(
    query: str = Query(..., min_length=1),
    k: int = Query(5, ge=1, le=20),
    user_id: str | None = Query(None),
    current_user: dict = Depends(require_admin),
    service=Depends(get_knowledge_service),
):
    del current_user
    return KnowledgeSearchResponse(query=query, results=service.search_chunks(query=query, k=k, user_id=user_id))


@router.post("/documents/upload", response_model=KnowledgeUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
    service=Depends(get_knowledge_service),
):
    del current_user
    try:
        content = await file.read()
        result = service.add_uploaded_document(file.filename or "knowledge", content, user_id="__shared__")
        return KnowledgeUploadResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/chunks/{doc_id}", response_model=KnowledgeDeleteResponse)
def delete_chunk(
    doc_id: str,
    user_id: str | None = Query(None),
    current_user: dict = Depends(require_admin),
    service=Depends(get_knowledge_service),
):
    del current_user
    result = service.delete_chunk(doc_id, user_id=user_id)
    return KnowledgeDeleteResponse(**result)


@router.post("/rebuild", response_model=KnowledgeRebuildResponse)
def rebuild_knowledge(
    current_user: dict = Depends(require_admin),
    service=Depends(get_knowledge_service),
):
    del current_user
    return KnowledgeRebuildResponse(**service.rebuild())
