import numpy as np
from model.factory import embed_model

class SemanticChecker:
    def __init__(self):
        self.embedding_model = embed_model

    def calculate_similarity(self, text1: str, text2: str) -> float:
        embedding1 = np.array(self.embedding_model.embed_query(text1))
        embedding2 = np.array(self.embedding_model.embed_query(text2))
        
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)

    def check_similarity(self, original: str, rewritten: str, threshold: float = 0.8) -> tuple:
        similarity = self.calculate_similarity(original, rewritten)
        return similarity >= threshold, similarity