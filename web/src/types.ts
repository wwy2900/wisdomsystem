export type UserRole = "user" | "admin";

export interface AuthUser {
  id: string;
  username: string;
  role: UserRole;
  display_name: string;
  is_active: boolean;
}

export interface SessionSummary {
  session_id: string;
  preview: string;
  saved_at: string;
}

export interface ChatMessage {
  role: string;
  content: string;
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
