import type {
  ChunkListResponse,
  KnowledgeUploadResult,
  SearchResponse,
  UserChunkListResponse,
} from "@/types";
import { deleteJson, getJson, postForm, postJson } from "./http";

export function listPrivateChunks(limit = 200, offset = 0) {
  return getJson<UserChunkListResponse>(`/api/v1/me/knowledge/chunks?limit=${limit}&offset=${offset}`);
}

export function uploadPrivateDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return postForm<KnowledgeUploadResult>("/api/v1/me/knowledge/documents/upload", formData);
}

export function deletePrivateChunk(docId: string) {
  return deleteJson<{ doc_id: string; deleted: boolean; before_total: number; after_total: number }>(
    `/api/v1/me/knowledge/chunks/${docId}`,
  );
}

export function listAdminChunks(limit = 20, offset = 0, userId?: string) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (userId) {
    query.set("user_id", userId);
  }
  return getJson<ChunkListResponse>(`/api/v1/admin/knowledge/chunks?${query.toString()}`);
}

export function searchAdminChunks(query: string, k = 5, userId?: string) {
  const params = new URLSearchParams({
    query,
    k: String(k),
  });
  if (userId) {
    params.set("user_id", userId);
  }
  return getJson<SearchResponse>(`/api/v1/admin/knowledge/search?${params.toString()}`);
}

export function uploadAdminDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return postForm<KnowledgeUploadResult>("/api/v1/admin/knowledge/documents/upload", formData);
}

export function deleteAdminChunk(docId: string, userId?: string) {
  const params = new URLSearchParams();
  if (userId) {
    params.set("user_id", userId);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return deleteJson<{ doc_id: string; deleted: boolean; before_total: number; after_total: number }>(
    `/api/v1/admin/knowledge/chunks/${docId}${suffix}`,
  );
}

export function rebuildKnowledge() {
  return postJson<{ file_count: number; skipped_count: number; chunk_count: number; results: unknown[] }>(
    "/api/v1/admin/knowledge/rebuild",
  );
}
