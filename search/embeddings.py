from sentence_transformers import SentenceTransformer
import numpy as np


class ReviewEmbedder:
    def __init__(self, model_name: str = "intfloat/multilingual-e5-base"):
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        # e5 требует префикс "passage: " для документов, "query: " для запросов
        prefixed = [f"passage: {t}" for t in texts]
        return self.model.encode(
            prefixed,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,  # для cosine
            convert_to_numpy=True,
        )

    def encode_query(self, query: str) -> np.ndarray:
        return self.model.encode(
            f"query: {query}",
            normalize_embeddings=True,
            convert_to_numpy=True,
        )