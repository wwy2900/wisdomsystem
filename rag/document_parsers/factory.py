from __future__ import annotations

import os

from langchain_core.documents import Document

from rag.document_parsers.base import BaseDocumentParser
from rag.document_parsers.parsers import (
    CsvParser,
    DocxParser,
    JsonParser,
    MarkdownParser,
    PdfParser,
    TxtParser,
    XlsxParser,
)


class DocumentParserFactory:
    _parser_classes = (
        TxtParser,
        PdfParser,
        DocxParser,
        XlsxParser,
        CsvParser,
        MarkdownParser,
        JsonParser,
    )
    _parsers_by_extension = {
        extension: parser_class()
        for parser_class in _parser_classes
        for extension in parser_class.supported_extensions
    }

    @classmethod
    def get_parser(cls, file_path: str) -> BaseDocumentParser:
        extension = os.path.splitext(file_path)[1].lower()
        parser = cls._parsers_by_extension.get(extension)
        if parser is None:
            raise ValueError(f"Unsupported file type: {extension or 'none'}")
        return parser

    @classmethod
    def parse(cls, file_path: str) -> list[Document]:
        return cls.get_parser(file_path).parse(file_path)
