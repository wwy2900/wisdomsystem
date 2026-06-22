import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

const fetchEventSourceMock = vi.fn();
const listSessionsMock = vi.fn();

vi.mock("@microsoft/fetch-event-source", () => ({
  fetchEventSource: (...args: unknown[]) => fetchEventSourceMock(...args),
}));

vi.mock("@/api/chat", () => ({
  createSession: vi.fn(),
  getSession: vi.fn(),
  listSessions: (...args: unknown[]) => listSessionsMock(...args),
}));

import { useChatStore } from "./chat";
import { useSessionStore } from "./session";

describe("chatStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    listSessionsMock.mockResolvedValue({
      sessions: [
        {
          session_id: "session_1",
          preview: "Need help",
          saved_at: "2026-06-22T00:00:00",
        },
      ],
    });
  });

  it("appends the assistant response after a successful SSE stream", async () => {
    fetchEventSourceMock.mockImplementation(async (_url: string, options: Record<string, any>) => {
      await options.onmessage({
        event: "session",
        data: JSON.stringify({ session_id: "session_1" }),
      });
      await options.onmessage({
        event: "tool_event",
        data: JSON.stringify({ content: "retriever:start" }),
      });
      await options.onmessage({
        event: "answer_delta",
        data: JSON.stringify({ content: "Hello there." }),
      });
      await options.onmessage({
        event: "done",
        data: JSON.stringify({ session_id: "session_1" }),
      });
    });

    const chatStore = useChatStore();
    const sessionStore = useSessionStore();

    await chatStore.sendMessage("Need help");

    expect(sessionStore.currentSessionId).toBe("session_1");
    expect(chatStore.toolEvents).toEqual(["retriever:start"]);
    expect(chatStore.messages).toEqual([
      { role: "user", content: "Need help" },
      { role: "assistant", content: "Hello there." },
    ]);
    expect(chatStore.lastFailedPrompt).toBe("");
    expect(chatStore.isStreaming).toBe(false);
  });

  it("adds an assistant error message and preserves the failed prompt", async () => {
    fetchEventSourceMock.mockImplementation(async (_url: string, options: Record<string, any>) => {
      await options.onmessage({
        event: "error",
        data: JSON.stringify({ content: "Upstream failed" }),
      });
    });

    const chatStore = useChatStore();

    await expect(chatStore.sendMessage("Need help")).rejects.toThrow("Upstream failed");

    expect(chatStore.messages).toHaveLength(2);
    expect(chatStore.messages[0]).toEqual({ role: "user", content: "Need help" });
    expect(chatStore.messages[1]?.role).toBe("assistant");
    expect(chatStore.messages[1]?.content).toContain("Upstream failed");
    expect(chatStore.lastFailedPrompt).toBe("Need help");
    expect(chatStore.streamingAssistantText).toBe("");
    expect(chatStore.isStreaming).toBe(false);
  });
});
