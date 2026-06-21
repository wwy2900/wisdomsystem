"""FastAPI 请求/响应 Pydantic 模型"""
from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class CreateSessionRequest(BaseModel):
    user_id: str


class CreateSessionResponse(BaseModel):
    session_id: str


class SessionInfo(BaseModel):
    session_id: str
    preview: str
    saved_at: str


class SessionListResponse(BaseModel):
    sessions: list[SessionInfo]


class SessionDetailResponse(BaseModel):
    session_id: str
    user_id: str
    messages: list[Message]


class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str


class HealthResponse(BaseModel):
    status: str
    agent_ready: bool
    cache_backend: str


class KnowledgeUploadResponse(BaseModel):
    file_name: str
    md5: str | None
    skipped: bool
    reason: str
    chunk_count: int
    chunk_ids: list[str]
    saved_path: str | None = None


class KnowledgeChunk(BaseModel):
    doc_id: str
    content: str
    metadata: dict


class KnowledgeChunkListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    chunks: list[KnowledgeChunk]


class UserChunkListResponse(BaseModel):
    """某用户的私有 chunk 列表"""
    user_id: str
    total: int
    limit: int
    offset: int
    chunks: list[KnowledgeChunk]


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeChunk]


class KnowledgeDeleteResponse(BaseModel):
    doc_id: str
    deleted: bool
    before_total: int
    after_total: int


class KnowledgeRebuildFileResult(BaseModel):
    file_name: str
    md5: str | None
    skipped: bool
    reason: str
    chunk_count: int
    chunk_ids: list[str]


class KnowledgeRebuildResponse(BaseModel):
    file_count: int
    skipped_count: int
    chunk_count: int
    results: list[KnowledgeRebuildFileResult]
