"""FastAPI request/response schemas."""
from pydantic import BaseModel, Field


class SourceReferenceResponse(BaseModel):
    source_type: str
    title: str
    snippet: str
    tool_name: str
    doc_id: str | None = None
    record_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class Message(BaseModel):
    role: str
    content: str
    sources: list[SourceReferenceResponse] | None = None


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


class MeSessionListResponse(BaseModel):
    sessions: list[SessionInfo]


class SessionDetailResponse(BaseModel):
    session_id: str
    user_id: str
    messages: list[Message]


class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str


class MeChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str


class MeChatStreamEvent(BaseModel):
    event: str
    content: str | None = None
    session_id: str | None = None
    sources: list[SourceReferenceResponse] | None = None


class HealthResponse(BaseModel):
    status: str
    agent_ready: bool
    cache_backend: str


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1)


class CurrentUserResponse(BaseModel):
    id: str
    username: str
    role: str
    display_name: str
    is_active: bool


class AuthSessionResponse(BaseModel):
    authenticated: bool = True
    user: CurrentUserResponse


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1)
    role: str = Field(..., pattern="^(user|admin)$")


class UserSummary(BaseModel):
    id: str
    username: str
    role: str
    display_name: str
    is_active: bool
    created_at: str


class UserListResponse(BaseModel):
    users: list[UserSummary]


class OperationStatusResponse(BaseModel):
    ok: bool = True
    message: str = ""


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


class AdminKnowledgeChunkListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    chunks: list[KnowledgeChunk]


class UserChunkListResponse(BaseModel):
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
