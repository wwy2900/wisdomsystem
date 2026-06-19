import re
from langchain_core.documents import Document
from rag.contextual_enhancer import ContextualEnhancer


class QuestionBasedSplitter:
    """按问题切分文档，保证语义连贯性"""

    def split_text(self, text: str) -> list[str]:
        """按问题切分文本"""
        # 识别问题格式：数字. **问题内容**
        question_pattern = r'(\d+)\.\s+\*\*([^*]+)\*\*'

        # 找到所有问题的位置
        matches = list(re.finditer(question_pattern, text))

        if not matches:
            # 如果没有问题格式，按段落切分
            return self._split_by_paragraph(text)

        chunks = []
        for i, match in enumerate(matches):
            # 问题起始位置
            start = match.start()
            # 下一个问题起始位置（或文本结尾）
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            # 提取完整问答
            chunk_text = text[start:end].strip()

            # 如果内容太长（超过 500 字），按段落切分
            if len(chunk_text) > 500:
                sub_chunks = self._split_by_paragraph(chunk_text, max_len=500)
                chunks.extend(sub_chunks)
            else:
                chunks.append(chunk_text)

        # 添加上下覆盖（20%）
        chunks = self._add_overlap(chunks, overlap_ratio=0.2)

        return chunks

    def _split_by_paragraph(self, text: str, max_len: int = 500) -> list[str]:
        """按段落切分，保持句子完整"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) <= max_len:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # 如果段落本身太长，按句子切分
                if len(para) > max_len:
                    sentences = self._split_by_sentence(para, max_len)
                    chunks.extend(sentences)
                    current_chunk = ""
                else:
                    current_chunk = para + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_by_sentence(self, text: str, max_len: int = 500) -> list[str]:
        """按句子切分，保持句子完整"""
        # 句子分隔符：。？！
        sentence_enders = ['。', '？', '！', '.', '?', '!']
        sentences = []
        current = ""

        for char in text:
            current += char
            if char in sentence_enders:
                if len(current) >= max_len:
                    sentences.append(current.strip())
                    current = ""

        if current:
            sentences.append(current.strip())

        return sentences

    def _add_overlap(self, chunks: list[str], overlap_ratio: float = 0.2) -> list[str]:
        """添加上下覆盖"""
        result = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                # 上一个 chunk 的最后 20%
                prev_chunk = chunks[i - 1]
                overlap_len = int(len(prev_chunk) * overlap_ratio)
                overlap_text = prev_chunk[-overlap_len:]
                chunk = overlap_text + "\n" + chunk
            result.append(chunk)
        return result

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """切分文档列表"""
        results = []
        chunk_id = 1
        enhancer = ContextualEnhancer()

        for doc in documents:
            chunks = self.split_text(doc.page_content)
            document_title = doc.metadata.get("source", "").split("\\")[-1].replace(".txt", "")
            
            for chunk_text in chunks:
                enhanced_content = enhancer.enhance(document_title, chunk_text)
                
                results.append(Document(
                    page_content=enhanced_content,
                    metadata={
                        "doc_id": f"chunk_{chunk_id:04d}",
                        "source": doc.metadata.get("source", ""),
                    }
                ))
                chunk_id += 1

        return results