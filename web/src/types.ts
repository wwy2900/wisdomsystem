export type UserRole = "user" | "admin";

export interface AuthUser {
  id: string;
  username: string;
  role: UserRole;
  display_name: string;
  is_active: boolean;
}

export interface RegisterPayload {
  username: string;
  password: string;
  display_name: string;
}

export interface AdminCreateUserPayload extends RegisterPayload {
  role: UserRole;
}

export interface UserSummary {
  id: string;
  username: string;
  role: UserRole;
  display_name: string;
  is_active: boolean;
  created_at: string;
}

export interface SessionSummary {
  session_id: string;
  preview: string;
  saved_at: string;
}

export interface SourceReference {
  source_type: "knowledge" | "business_tool";
  title: string;
  snippet: string;
  tool_name: string;
  doc_id?: string | null;
  record_id?: string | null;
  metadata: Record<string, unknown>;
}

export interface ChatMessage {
  role: string;
  content: string;
  sources?: SourceReference[];
}

export interface SessionDetail {
  session_id: string;
  user_id: string;
  messages: ChatMessage[];
}

export interface ChatStreamEvent {
  event: string;
  content?: string;
  session_id?: string;
  sources?: SourceReference[];
}

export interface KnowledgeChunk {
  doc_id: string;
  content: string;
  metadata: Record<string, unknown>;
}

export interface KnowledgeUploadResult {
  file_name: string;
  md5: string | null;
  skipped: boolean;
  reason: string;
  chunk_count: number;
  chunk_ids: string[];
  saved_path?: string | null;
}

export interface ChunkListResponse {
  total: number;
  limit: number;
  offset: number;
  chunks: KnowledgeChunk[];
}

export interface UserChunkListResponse extends ChunkListResponse {
  user_id: string;
}

export interface SearchResponse {
  query: string;
  results: KnowledgeChunk[];
}
