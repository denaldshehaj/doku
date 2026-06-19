"""ChromaDB persistent vector store. Cosine space; we pass precomputed
embeddings in and convert distance -> similarity (similarity = 1 - distance).

A retrieval result carries the chunk text plus source metadata (filename, title,
page) so the RAG layer can build citations and the refusal gate can threshold on
similarity (DoD for vectorstore)."""
from dataclasses import dataclass

import chromadb

import config
from doku import embeddings

_client = None
_collection = None
COLLECTION = "doku_chunks"


@dataclass
class Retrieved:
    text: str
    score: float       # cosine similarity in [~0, 1]
    filename: str
    title: str
    page: int
    chunk_index: int


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        _collection = _client.get_or_create_collection(
            name=COLLECTION, metadata={"hnsw:space": "cosine"}
        )
    return _collection


def add_document(doc_id: int, filename: str, title: str, chunks) -> int:
    """Embed and index a document's chunks. Returns number of chunks indexed."""
    if not chunks:
        return 0
    col = _get_collection()
    ids = [f"{doc_id}:{c.chunk_index}" for c in chunks]
    docs = [c.text for c in chunks]
    metas = [
        {
            "doc_id": doc_id,
            "filename": filename,
            "title": title or filename,
            "page": c.page,
            "chunk_index": c.chunk_index,
        }
        for c in chunks
    ]
    vectors = embeddings.embed_texts(docs)
    col.add(ids=ids, documents=docs, metadatas=metas, embeddings=vectors)
    return len(ids)


def delete_document(doc_id: int) -> None:
    col = _get_collection()
    col.delete(where={"doc_id": doc_id})


def query(question: str, k: int | None = None, where: dict | None = None) -> list[Retrieved]:
    col = _get_collection()
    if col.count() == 0:
        return []
    k = k or config.RETRIEVAL_K
    qvec = embeddings.embed_query(question)
    res = col.query(
        query_embeddings=[qvec],
        n_results=k,
        where=where or None,
        include=["documents", "metadatas", "distances"],
    )
    out: list[Retrieved] = []
    if not res["ids"] or not res["ids"][0]:
        return out
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        out.append(
            Retrieved(
                text=doc,
                score=1.0 - float(dist),
                filename=meta.get("filename", "?"),
                title=meta.get("title", meta.get("filename", "?")),
                page=int(meta.get("page", 0)),
                chunk_index=int(meta.get("chunk_index", 0)),
            )
        )
    return out


def count() -> int:
    return _get_collection().count()
