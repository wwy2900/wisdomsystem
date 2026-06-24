from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from model.factory import build_chat_model


class ContextualEnhancer:
    def __init__(self):
        self.model = build_chat_model("qwen-turbo")
        self.prompt_template = PromptTemplate.from_template(
            """
Generate one short context summary for the document chunk below.
Document title: {document_title}
Chunk content: {chunk_content}

Return a concise summary that can improve retrieval.
"""
        )
        self.chain = self.prompt_template | self.model | StrOutputParser()

    def enhance(self, document_title: str, chunk_content: str) -> str:
        context = self.chain.invoke(
            {
                "document_title": document_title,
                "chunk_content": chunk_content,
            }
        )
        return f"{context}\n{chunk_content}"
