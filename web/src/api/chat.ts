import type { SessionDetail, SessionSummary } from "@/types";
import { getJson, postJson } from "./http";

export function createSession() {
  return postJson<{ session_id: string }>("/api/v1/me/sessions");
}

export function listSessions() {
  return getJson<{ sessions: SessionSummary[] }>("/api/v1/me/sessions");
}

export function getSession(sessionId: string) {
  return getJson<SessionDetail>(`/api/v1/me/sessions/${sessionId}`);
}
