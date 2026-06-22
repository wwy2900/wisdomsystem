import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

const listAdminChunksMock = vi.fn();

vi.mock("@/api/knowledge", () => ({
  listPrivateChunks: vi.fn(),
  uploadPrivateDocument: vi.fn(),
  deletePrivateChunk: vi.fn(),
  listAdminChunks: (...args: unknown[]) => listAdminChunksMock(...args),
  searchAdminChunks: vi.fn(),
  uploadAdminDocument: vi.fn(),
  deleteAdminChunk: vi.fn(),
  rebuildKnowledge: vi.fn(),
}));

import { useKnowledgeStore } from "./knowledge";

function buildChunk(docId: string) {
  return {
    doc_id: docId,
    content: `content-${docId}`,
    metadata: { user_id: "__shared__", source_file: `${docId}.txt` },
  };
}

describe("knowledgeStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("loads the first admin page with the default limit", async () => {
    listAdminChunksMock.mockResolvedValue({
      total: 35,
      limit: 20,
      offset: 0,
      chunks: [buildChunk("doc-1")],
    });

    const store = useKnowledgeStore();
    await store.refreshAdminChunks();

    expect(listAdminChunksMock).toHaveBeenCalledWith(20, 0, undefined);
    expect(store.adminCurrentPage).toBe(1);
    expect(store.adminPageSize).toBe(20);
    expect(store.adminTotal).toBe(35);
  });

  it("uses page and page size state to calculate the next offset", async () => {
    listAdminChunksMock.mockResolvedValue({
      total: 60,
      limit: 20,
      offset: 20,
      chunks: [buildChunk("doc-21")],
    });

    const store = useKnowledgeStore();
    await store.refreshAdminChunks({ page: 2 });

    expect(listAdminChunksMock).toHaveBeenCalledWith(20, 20, undefined);
    expect(store.adminCurrentPage).toBe(2);
  });

  it("applies trimmed user filters and resets to page one when page size changes", async () => {
    listAdminChunksMock.mockResolvedValue({
      total: 5,
      limit: 50,
      offset: 0,
      chunks: [buildChunk("doc-1")],
    });

    const store = useKnowledgeStore();
    await store.refreshAdminChunks({ page: 1, pageSize: 50, userId: " user_1 " });

    expect(listAdminChunksMock).toHaveBeenCalledWith(50, 0, "user_1");
    expect(store.adminPageSize).toBe(50);
    expect(store.adminFilterUserId).toBe("user_1");
    expect(store.adminCurrentPage).toBe(1);
  });

  it("falls back to the last valid admin page after deletions shrink the dataset", async () => {
    listAdminChunksMock
      .mockResolvedValueOnce({
        total: 21,
        limit: 20,
        offset: 40,
        chunks: [],
      })
      .mockResolvedValueOnce({
        total: 21,
        limit: 20,
        offset: 20,
        chunks: [buildChunk("doc-21")],
      });

    const store = useKnowledgeStore();
    await store.refreshAdminChunks({ page: 3 });

    expect(listAdminChunksMock).toHaveBeenNthCalledWith(1, 20, 40, undefined);
    expect(listAdminChunksMock).toHaveBeenNthCalledWith(2, 20, 20, undefined);
    expect(store.adminCurrentPage).toBe(2);
    expect(store.adminChunks[0]?.doc_id).toBe("doc-21");
  });
});
