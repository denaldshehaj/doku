"""Embedding model wrapper (bge-m3 via Sentence Transformers). Local-only.
Embeddings are L2-normalized, so cosine similarity == dot product."""
import config

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    vecs = get_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vecs.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
