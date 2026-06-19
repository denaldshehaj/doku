"""Document management orchestration (admin-only at the UI layer): save an
uploaded PDF, ingest+index it, edit metadata, delete, and reindex. Document
metadata lives in SQLite; chunk vectors live in ChromaDB."""
import shutil
from pathlib import Path

import config
from doku import db, ingestion, vectorstore


def list_documents():
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT * FROM documents ORDER BY indexed_at DESC"
        ).fetchall()


def get_document(doc_id: int):
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()


def _store_pdf(src_path, filename: str) -> Path:
    dest = config.DOCUMENTS_DIR / filename
    if Path(src_path) != dest:
        shutil.copyfile(src_path, dest)
    return dest


def add_document(src_path, filename: str, title="", doc_type="", institution="", year=None):
    """Ingest a PDF from src_path into the corpus. Raises on duplicates or
    non-extractable (scanned) PDFs."""
    with db.get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM documents WHERE filename = ?", (filename,)
        ).fetchone()
    if exists:
        raise ValueError(f"Dokumenti '{filename}' ekziston tashmë.")

    dest = _store_pdf(src_path, filename)
    chunks, n_pages = ingestion.build_chunks(dest)  # may raise NoExtractableTextError

    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO documents (filename, title, doc_type, institution, year, "
            "n_chunks, n_pages) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (filename, title or filename, doc_type, institution, year, len(chunks), n_pages),
        )
        doc_id = cur.lastrowid

    n = vectorstore.add_document(doc_id, filename, title or filename, chunks)
    return doc_id, n


def update_metadata(doc_id: int, title=None, doc_type=None, institution=None, year=None):
    fields, values = [], []
    for col, val in (("title", title), ("doc_type", doc_type),
                     ("institution", institution), ("year", year)):
        if val is not None:
            fields.append(f"{col} = ?")
            values.append(val)
    if not fields:
        return
    values.append(doc_id)
    with db.get_conn() as conn:
        conn.execute(f"UPDATE documents SET {', '.join(fields)} WHERE id = ?", values)


def delete_document(doc_id: int) -> None:
    doc = get_document(doc_id)
    vectorstore.delete_document(doc_id)
    with db.get_conn() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    if doc:
        pdf = config.DOCUMENTS_DIR / doc["filename"]
        if pdf.exists():
            pdf.unlink()


def reindex_document(doc_id: int) -> int:
    """Re-extract and re-embed a document already stored on disk."""
    doc = get_document(doc_id)
    if not doc:
        raise ValueError("Dokumenti nuk u gjet.")
    pdf = config.DOCUMENTS_DIR / doc["filename"]
    if not pdf.exists():
        raise ValueError("Skedari PDF mungon në disk.")
    chunks, n_pages = ingestion.build_chunks(pdf)
    vectorstore.delete_document(doc_id)
    n = vectorstore.add_document(doc_id, doc["filename"], doc["title"], chunks)
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE documents SET n_chunks = ?, n_pages = ?, indexed_at = datetime('now') "
            "WHERE id = ?",
            (len(chunks), n_pages, doc_id),
        )
    return n
