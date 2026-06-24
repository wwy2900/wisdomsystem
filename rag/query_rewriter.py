from functools import lru_cache
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from model.factory import build_chat_model
from utils.logger_handler import logger


class QueryRewriter:
    def __init__(self):
        self.light_model = build_chat_model("qwen-turbo")
        self.prompt_template = PromptTemplate.from_template(
            """
Please rewrite the user question from three retrieval-friendly angles while preserving the original intent.

Question: {query}

Return exactly three lines in this format:
[SYNONYM]: ...
[STRUCTURE]: ...
[INTENT]: ...
"""
        )
        self.chain = self.prompt_template | self.light_model | StrOutputParser()

    @lru_cache(maxsize=1000)
    def rewrite(self, query: str) -> str:
        return self.chain.invoke({"query": query})

    def _parse_rewrites(self, output: str) -> list[dict[str, str]]:
        rewrites = []
        patterns = [
            (r"\[SYNONYM\]:\s*(.+?)(?=\n\[|$)", "synonym"),
            (r"\[STRUCTURE\]:\s*(.+?)(?=\n\[|$)", "structure"),
            (r"\[INTENT\]:\s*(.+?)(?=\n\[|$)", "intent"),
        ]

        for pattern, label in patterns:
            match = re.search(pattern, output, re.DOTALL)
            if match:
                rewrites.append({
                    "text": match.group(1).strip(),
                    "type": label,
                })

        return rewrites

    def rewrite_multi_with_filter(self, query: str, num_rewrites: int = 3, threshold: float = 0.8):
        from rag.semantic_checker import SemanticChecker

        del num_rewrites
        checker = SemanticChecker()
        valid_rewrites = []

        output = self.chain.invoke({"query": query})
        rewrites = self._parse_rewrites(output)

        for rewrite in rewrites:
            try:
                similarity = checker.calculate_similarity(query, rewrite["text"])
                if similarity >= threshold:
                    valid_rewrites.append(
                        {
                            "text": rewrite["text"],
                            "similarity": similarity,
                            "type": rewrite["type"],
                        }
                    )
            except Exception as error:
                logger.warning("[QueryRewriter] similarity check failed, keep rewrite without filtering: %s", error)
                valid_rewrites.append(
                    {
                        "text": rewrite["text"],
                        "similarity": 0.0,
                        "type": rewrite["type"],
                    }
                )

        return valid_rewrites
