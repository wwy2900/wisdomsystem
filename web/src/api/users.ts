import type { AdminCreateUserPayload, UserSummary } from "@/types";
import { getJson, postJson } from "./http";

export interface UserListResponse {
  users: UserSummary[];
}

export function listUsers() {
  return getJson<UserListResponse>("/api/v1/admin/users");
}

export function createUser(payload: AdminCreateUserPayload) {
  return postJson<UserSummary>("/api/v1/admin/users", payload);
}
