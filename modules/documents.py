"""Document management orchestration (admin-only at the UI layer): store an
uploaded PDF safely, process + index it, edit metadata, activate/deactivate,
delete, reindex one or the whole corpus. Document rows live in SQLite; chunk
vectors live in ChromaDB."""
import re
import shutil
import unicodedata
from pathlib import Path

import config
from modules import database as db, document_processor as dp, vector_store as vs


def safe_filename(name: str) -> str:
    """Produce a filesystem-safe filename, preserving a .pdf/.docx extension."""
    parts = (name or "").rsplit(".", 1)
    ext = "." + parts[1].lower() if len(parts) == 2 and parts[1].lower() in ("pdf", "docx") else ".pdf"
    stem = unicodedata.normalize("NFKD", parts[0]).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "dokument"
    return stem + ext


def list_documents(active_only=False, doc_type=None, year=None, institution=None,
                   title_kw=None):
    sql = "SELECT * FROM documents WHERE 1=1"
    params = []
    if active_only:
        sql += " AND status = ?"; params.append(config.STATUS_ACTIVE)
    if doc_type:
        sql += " AND document_type = ?"; params.append(doc_type)
    if year:
        sql += " AND year = ?"; params.append(int(year))
    if institution:
        sql += " AND institution = ?"; params.append(institution)
    if title_kw:
        sql += " AND LOWER(title) LIKE ?"; params.append(f"%{title_kw.lower()}%")
    sql += " ORDER BY created_at DESC"
    with db.get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def get_document(doc_id: int):
    with db.get_conn() as conn:
        return conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()


def active_document_ids() -> list[int]:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT id FROM documents WHERE status = ?", (config.STATUS_ACTIVE,)
        ).fetchall()
    return [r["id"] for r in rows]


def distinct_values(column: str) -> list:
    if column not in ("document_type", "institution", "year"):
        return []
    with db.get_conn() as conn:
        rows = conn.execute(
            f"SELECT DISTINCT {column} FROM documents WHERE {column} IS NOT NULL "
            f"AND {column} != '' ORDER BY {column}").fetchall()
    return [r[column] for r in rows]


def _chunk_meta(filename, title, institution, document_type, year, status):
    return {"filename": filename, "title": title, "institution": institution,
            "document_type": document_type, "year": year, "status": status}


def add_document(src_path, original_filename, title="", institution="",
                 document_type="Tjetër", year=None, description="", uploaded_by=""):
    """Store + process + index a PDF. Raises ValueError on duplicates,
    NoExtractableTextError on scanned PDFs."""
    filename = safe_filename(original_filename)
    dest = config.UPLOADS_DIR / filename
    if dest.exists() or get_document_by_filename(filename) is not None:
        raise ValueError(f"Dokumenti '{filename}' ekziston tashmë.")

    if Path(src_path) != dest:
        shutil.copyfile(src_path, dest)

    chunks, n_pages = dp.process_document(dest)  # may raise NoExtractableTextError

    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO documents (filename, original_filename, stored_path, title, "
            "institution, document_type, year, description, uploaded_by, status, "
            "num_pages, total_chunks) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (filename, original_filename, str(dest), title or filename, institution,
             document_type, year, description, uploaded_by, config.STATUS_ACTIVE,
             n_pages, len(chunks)),
        )
        doc_id = cur.lastrowid

    n = vs.add_document(doc_id, _chunk_meta(filename, title or filename, institution,
                        document_type, year, config.STATUS_ACTIVE), chunks)
    return doc_id, n


def get_document_by_filename(filename: str):
    with db.get_conn() as conn:
        return conn.execute("SELECT * FROM documents WHERE filename = ?",
                            (filename,)).fetchone()


def update_metadata(doc_id: int, **fields):
    cols, vals = [], []
    for col in ("title", "institution", "document_type", "year", "description"):
        if col in fields and fields[col] is not None:
            cols.append(f"{col} = ?"); vals.append(fields[col])
    if not cols:
        return
    vals.append(doc_id)
    with db.get_conn() as conn:
        conn.execute(f"UPDATE documents SET {', '.join(cols)}, "
                     f"updated_at = datetime('now') WHERE id = ?", vals)


def set_status(doc_id: int, status: str):
    if status not in (config.STATUS_ACTIVE, config.STATUS_INACTIVE):
        raise ValueError("Status i pavlefshëm.")
    with db.get_conn() as conn:
        conn.execute("UPDATE documents SET status = ?, updated_at = datetime('now') "
                     "WHERE id = ?", (status, doc_id))


def delete_document(doc_id: int):
    doc = get_document(doc_id)
    vs.delete_document(doc_id)
    with db.get_conn() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    if doc and doc["stored_path"]:
        p = Path(doc["stored_path"])
        if p.exists():
            p.unlink()


def reindex_document(doc_id: int) -> int:
    doc = get_document(doc_id)
    if not doc:
        raise ValueError("Dokumenti nuk u gjet.")
    pdf = Path(doc["stored_path"])
    if not pdf.exists():
        raise ValueError("Skedari mungon në disk.")
    chunks, n_pages = dp.process_document(pdf)
    vs.delete_document(doc_id)
    n = vs.add_document(doc_id, _chunk_meta(doc["filename"], doc["title"],
                        doc["institution"], doc["document_type"], doc["year"],
                        doc["status"]), chunks)
    with db.get_conn() as conn:
        conn.execute("UPDATE documents SET num_pages = ?, total_chunks = ?, "
                     "updated_at = datetime('now') WHERE id = ?",
                     (n_pages, len(chunks), doc_id))
    return n


def reindex_all() -> int:
    total = 0
    for doc in list_documents():
        try:
            total += reindex_document(doc["id"])
        except Exception:
            continue
    return total
