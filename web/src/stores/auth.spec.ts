import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

vi.mock("@/api/auth", () => ({
  getCurrentUser: vi.fn().mockResolvedValue({
    id: "user_1",
    username: "demo_user",
    role: "user",
    display_name: "Demo User",
    is_active: true,
  }),
  login: vi.fn().mockResolvedValue({
    authenticated: true,
    user: {
      id: "admin_1",
      username: "admin",
      role: "admin",
      display_name: "System Admin",
      is_active: true,
    },
  }),
  register: vi.fn().mockResolvedValue({
    authenticated: true,
    user: {
      id: "user_2",
      username: "new_user",
      role: "user",
      display_name: "New User",
      is_active: true,
    },
  }),
  logout: vi.fn().mockResolvedValue({ ok: true, message: "Logged out" }),
}));

import { useAuthStore } from "./auth";

describe("authStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("restores the current user from /auth/me", async () => {
    const store = useAuthStore();
    await store.restoreSession();
    expect(store.user?.username).toBe("demo_user");
  });

  it("updates the store after login", async () => {
    const store = useAuthStore();
    await store.login("admin", "Admin12345!");
    expect(store.user?.role).toBe("admin");
  });

  it("updates the store after registration", async () => {
    const store = useAuthStore();
    await store.register({
      username: "new_user",
      display_name: "New User",
      password: "Password123",
    });
    expect(store.user?.username).toBe("new_user");
  });
});
