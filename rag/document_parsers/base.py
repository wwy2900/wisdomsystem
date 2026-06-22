from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.documents import Document


class BaseDocumentParser(ABC):
    supported_extensions: tuple[str, ...] = ()

    @abstractmethod
    def parse(self, file_path: str) -> list[Document]:
        raise NotImplementedError

    @staticmethod
    def create_document(file_path: str, page_content: str, **metadata) -> Document:
        doc_metadata = {"source": file_path}
        doc_metadata.update(metadata)
        return Document(page_content=page_content, metadata=doc_metadata)
