import time
import numpy as np
from model.factory import embed_model
from utils.logger_handler import logger


class SemanticChecker:
    def __init__(self):
        self.embedding_model = embed_model
        self.max_retries = 3

    def _embed_with_retry(self, text: str) -> list[float]:
        """带重试的嵌入调用，处理 DashScope 瞬时错误（KeyError: 'request' 等）"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return self.embedding_model.embed_query(text)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s
                    logger.warning(
                        f"[SemanticChecker]嵌入失败(第{attempt+1}次)，"
                        f"{wait_time}s后重试: {type(e).__name__}: {str(e)}"
                    )
                    time.sleep(wait_time)
        logger.error(f"[SemanticChecker]嵌入失败，已达最大重试次数: {str(last_error)}")
        raise last_error

    def calculate_similarity(self, text1: str, text2: str) -> float:
        embedding1 = np.array(self._embed_with_retry(text1))
        embedding2 = np.array(self._embed_with_retry(text2))

        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def check_similarity(self, original: str, rewritten: str, threshold: float = 0.8) -> tuple:
        similarity = self.calculate_similarity(original, rewritten)
        return similarity >= threshold, similarity
