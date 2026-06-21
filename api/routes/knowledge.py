"""Knowledge base management routes."""
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from api.dependencies import get_knowledge_service, verify_api_key
from api.schemas import (
    KnowledgeChunkListResponse,
    KnowledgeDeleteResponse,
    KnowledgeRebuildResponse,
    KnowledgeSearchResponse,
    KnowledgeUploadResponse,
)
from services.knowledge_service import KnowledgeService


router = APIRouter(prefix="/api/v1/knowledge", dependencies=[Depends(verify_api_key)])


@router.post("/documents/upload", response_model=KnowledgeUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """Upload a txt/pdf document and index it immediately."""
    try:
        content = await file.read()
        result = service.add_uploaded_document(file.filename or "knowledge", content)
        return KnowledgeUploadResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/chunks", response_model=KnowledgeChunkListResponse)
def list_chunks(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """List vector-store chunks with pagination."""
    return KnowledgeChunkListResponse(**service.list_chunks(limit=limit, offset=offset))


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_chunks(
    query: str = Query(..., min_length=1),
    k: int = Query(5, ge=1, le=20),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """Search knowledge-base chunks."""
    return KnowledgeSearchResponse(query=query, results=service.search_chunks(query=query, k=k))


@router.delete("/chunks/{doc_id}", response_model=KnowledgeDeleteResponse)
def delete_chunk(doc_id: str, service: KnowledgeService = Depends(get_knowledge_service)):
    """Delete one vector-store chunk by doc_id without deleting the source file."""
    result = service.delete_chunk(doc_id)
    return KnowledgeDeleteResponse(**result)


@router.post("/rebuild", response_model=KnowledgeRebuildResponse)
def rebuild_knowledge(service: KnowledgeService = Depends(get_knowledge_service)):
    """Clear the vector store and rebuild from configured knowledge files and uploads."""
    return KnowledgeRebuildResponse(**service.rebuild())
