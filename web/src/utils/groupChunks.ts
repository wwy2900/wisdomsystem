import type { KnowledgeChunk } from "@/types";

export interface GroupedFile {
  fileName: string;
  chunks: KnowledgeChunk[];
}

export function groupChunksBySourceFile(chunks: KnowledgeChunk[]): GroupedFile[] {
  const groups = new Map<string, KnowledgeChunk[]>();

  chunks.forEach((chunk) => {
    const fileName = String(chunk.metadata.source_file ?? "unknown");
    const items = groups.get(fileName) ?? [];
    items.push(chunk);
    groups.set(fileName, items);
  });

  return [...groups.entries()]
    .map(([fileName, groupedChunks]) => ({
      fileName,
      chunks: groupedChunks,
    }))
    .sort((left, right) => left.fileName.localeCompare(right.fileName, "zh-CN"));
}
