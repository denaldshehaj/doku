"""ChromaDB persistent vector store. Cosine space; we pass precomputed embeddings
in and convert distance -> similarity (similarity = 1 - distance).

Each chunk carries full source metadata so the RAG layer can build citations and
filter by active documents / a specific document. The vector store is created
automatically if missing."""
from dataclasses import dataclass

import chromadb

import config
from modules import embeddings

_client = None
_collection = None
COLLECTION = "doku_chunks"


@dataclass
class Retrieved:
    text: str
    score: float
    document_id: int
    filename: str
    title: str
    institution: str
    document_type: str
    year: int
    page_number: int
    chunk_index: int


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        _collection = _client.get_or_create_collection(
            name=COLLECTION, metadata={"hnsw:space": "cosine"})
    return _collection


def add_document(doc_id: int, meta: dict, chunks) -> int:
    """Embed and index a document's chunks. `meta` carries filename, title,
    institution, document_type, year, status. Returns number of chunks indexed."""
    if not chunks:
        return 0
    col = _get_collection()
    ids = [f"{doc_id}:{c.chunk_index}" for c in chunks]
    docs = [c.text for c in chunks]
    metadatas = [
        {
            "document_id": doc_id,
            "filename": meta.get("filename", ""),
            "title": meta.get("title", ""),
            "institution": meta.get("institution", ""),
            "document_type": meta.get("document_type", ""),
            "year": int(meta.get("year") or 0),
            "page_number": c.page_number,
            "chunk_index": c.chunk_index,
            "status": meta.get("status", config.STATUS_ACTIVE),
        }
        for c in chunks
    ]
    vectors = embeddings.embed_texts(docs)
    col.add(ids=ids, documents=docs, metadatas=metadatas, embeddings=vectors)
    return len(ids)


def delete_document(doc_id: int) -> None:
    _get_collection().delete(where={"document_id": doc_id})


def _build_where(active_doc_ids, document_id):
    if document_id is not None:
        return {"document_id": int(document_id)}
    if active_doc_ids is not None:
        ids = [int(i) for i in active_doc_ids]
        if not ids:
            return None  # signal: nothing to search
        return {"document_id": {"$in": ids}}
    return {}


def query(question: str, k: int | None = None, active_doc_ids=None,
          document_id=None) -> list[Retrieved]:
    """Retrieve top-k chunks. Filter to a specific document, or to the set of
    active document ids (the authoritative source of 'status active')."""
    col = _get_collection()
    if col.count() == 0:
        return []
    where = _build_where(active_doc_ids, document_id)
    if where is None:
        return []
    qvec = embeddings.embed_query(question)
    res = col.query(query_embeddings=[qvec], n_results=k or config.RETRIEVAL_K,
                    where=where or None,
                    include=["documents", "metadatas", "distances"])
    out = []
    if not res["ids"] or not res["ids"][0]:
        return out
    for doc, m, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        out.append(Retrieved(
            text=doc, score=1.0 - float(dist),
            document_id=int(m.get("document_id", 0)),
            filename=m.get("filename", "?"), title=m.get("title", "?"),
            institution=m.get("institution", ""), document_type=m.get("document_type", ""),
            year=int(m.get("year", 0)), page_number=int(m.get("page_number", 0)),
            chunk_index=int(m.get("chunk_index", 0)),
        ))
    return out


def count() -> int:
    return _get_collection().count()
