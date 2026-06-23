import type { AuthUser, RegisterPayload } from "@/types";
import { getJson, postJson } from "./http";

export interface AuthSessionResponse {
  authenticated: boolean;
  user: AuthUser;
}

export function login(username: string, password: string) {
  return postJson<AuthSessionResponse>("/api/v1/auth/login", { username, password });
}

export function register(payload: RegisterPayload) {
  return postJson<AuthSessionResponse>("/api/v1/auth/register", payload);
}

export function logout() {
  return postJson<{ ok: boolean; message: string }>("/api/v1/auth/logout");
}

export function getCurrentUser() {
  return getJson<AuthUser>("/api/v1/auth/me");
}
