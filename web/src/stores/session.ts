import { defineStore } from "pinia";

import * as chatApi from "@/api/chat";
import type { SessionSummary } from "@/types";

export const useSessionStore = defineStore("sessions", {
  state: () => ({
    sessions: [] as SessionSummary[],
    currentSessionId: "" as string,
    loading: false,
  }),
  actions: {
    async refresh() {
      this.loading = true;
      try {
        const response = await chatApi.listSessions();
        this.sessions = response.sessions;
        if (!this.currentSessionId && this.sessions.length > 0) {
          this.currentSessionId = this.sessions[0].session_id;
        }
      } finally {
        this.loading = false;
      }
    },
    async create() {
      const response = await chatApi.createSession();
      this.currentSessionId = response.session_id;
      await this.refresh();
      return response.session_id;
    },
    setCurrentSession(sessionId: string) {
      this.currentSessionId = sessionId;
    },
    clear() {
      this.sessions = [];
      this.currentSessionId = "";
      this.loading = false;
    },
  },
});
