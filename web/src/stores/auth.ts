import { defineStore } from "pinia";

import * as authApi from "@/api/auth";
import type { AuthUser } from "@/types";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null as AuthUser | null,
    restoring: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.user),
    isAdmin: (state) => state.user?.role === "admin",
  },
  actions: {
    async restoreSession() {
      if (this.restoring) {
        return;
      }
      this.restoring = true;
      try {
        this.user = await authApi.getCurrentUser();
      } catch {
        this.user = null;
      } finally {
        this.restoring = false;
      }
    },
    async login(username: string, password: string) {
      const response = await authApi.login(username, password);
      this.user = response.user;
      return response.user;
    },
    async logout() {
      try {
        await authApi.logout();
      } finally {
        this.user = null;
      }
    },
  },
});
