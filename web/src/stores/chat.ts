import { fetchEventSource } from "@microsoft/fetch-event-source";
import { defineStore } from "pinia";

import { getSession } from "@/api/chat";
import type { ChatMessage, SourceReference } from "@/types";
import { useSessionStore } from "./session";

function normalizeErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Unknown request error.";
}

function buildAssistantErrorMessage(error: unknown) {
  return [
    "Request reached the backend, but the model response did not complete.",
    `Error: ${normalizeErrorMessage(error)}`,
    "You can edit the question and try again.",
  ].join("\n\n");
}

export const useChatStore = defineStore("chat", {
  state: () => ({
    messages: [] as ChatMessage[],
    toolEvents: [] as string[],
    streamingAssistantText: "",
    isStreaming: false,
    lastFailedPrompt: "",
  }),
  actions: {
    async loadSession(sessionId: string) {
      const data = await getSession(sessionId);
      this.messages = data.messages;
      this.streamingAssistantText = "";
      this.toolEvents = [];
      this.lastFailedPrompt = "";
    },
    reset() {
      this.messages = [];
      this.toolEvents = [];
      this.streamingAssistantText = "";
      this.isStreaming = false;
      this.lastFailedPrompt = "";
    },
    finalizeFailure(message: string, error: unknown) {
      this.streamingAssistantText = "";
      this.isStreaming = false;
      this.lastFailedPrompt = message;
      this.messages.push({
        role: "assistant",
        content: buildAssistantErrorMessage(error),
      });
    },
    async sendMessage(message: string) {
      const sessionStore = useSessionStore();
      this.messages.push({ role: "user", content: message });
      this.streamingAssistantText = "";
      this.toolEvents = [];
      this.isStreaming = true;
      this.lastFailedPrompt = "";

      let resolvedSessionId = sessionStore.currentSessionId || undefined;
      let completed = false;
      let failureHandled = false;
      let terminatedByError = false;
      let resolvedSources: SourceReference[] = [];

      const handleFailure = (error: unknown) => {
        if (failureHandled) {
          return;
        }
        failureHandled = true;
        this.finalizeFailure(message, error);
      };

      try {
        await fetchEventSource("/api/v1/me/chat/stream", {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message,
            session_id: resolvedSessionId,
          }),
          onmessage: async (event) => {
            const payload = event.data ? JSON.parse(event.data) : {};

            if (event.event === "session" && payload.session_id) {
              resolvedSessionId = payload.session_id;
              sessionStore.setCurrentSession(payload.session_id);
            }

            if (event.event === "answer_delta") {
              this.streamingAssistantText += payload.content ?? "";
            }

            if (event.event === "tool_event") {
              this.toolEvents.push(payload.content ?? "");
            }

            if (event.event === "error") {
              terminatedByError = true;
              throw new Error(payload.content || "Stream failed");
            }

            if (event.event === "done") {
              completed = true;
              resolvedSources = Array.isArray(payload.sources) ? payload.sources : [];
              if (this.streamingAssistantText.trim()) {
                this.messages.push({
                  role: "assistant",
                  content: this.streamingAssistantText,
                  sources: resolvedSources,
                });
              }
              this.streamingAssistantText = "";
              this.isStreaming = false;
              this.lastFailedPrompt = "";
              await sessionStore.refresh();
            }
          },
          onclose: () => {
            if (!completed && !terminatedByError) {
              throw new Error("The response stream closed before completion.");
            }
          },
          onerror: (error) => {
            handleFailure(error);
            throw error;
          },
        });

        if (resolvedSessionId) {
          sessionStore.setCurrentSession(resolvedSessionId);
        }
      } catch (error) {
        handleFailure(error);
        throw error;
      }
    },
  },
});
