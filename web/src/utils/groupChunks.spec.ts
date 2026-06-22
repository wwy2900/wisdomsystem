import { describe, expect, it } from "vitest";

import { groupChunksBySourceFile } from "./groupChunks";

describe("groupChunksBySourceFile", () => {
  it("groups chunks by source_file and sorts by file name", () => {
    const result = groupChunksBySourceFile([
      {
        doc_id: "doc_2",
        content: "beta",
        metadata: { source_file: "b.txt" },
      },
      {
        doc_id: "doc_1",
        content: "alpha",
        metadata: { source_file: "a.txt" },
      },
      {
        doc_id: "doc_3",
        content: "alpha-2",
        metadata: { source_file: "a.txt" },
      },
    ]);

    expect(result).toHaveLength(2);
    expect(result[0].fileName).toBe("a.txt");
    expect(result[0].chunks.map((chunk) => chunk.doc_id)).toEqual(["doc_1", "doc_3"]);
  });
});
