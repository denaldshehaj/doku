"""Document corpus endpoints. Reads are available to every authenticated user
(non-admins are forced to the active subset); every mutation is admin-only —
role security enforced server-side, not just hidden in the UI."""
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

import config
from api import deps, schemas, tasks
from modules import audit, auth, document_processor as dp, documents

router = APIRouter(prefix="/api/documents", tags=["documents"])

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # generous local limit; blocks runaway files


def _doc_out(d) -> dict:
    return {k: d[k] for k in (
        "id", "filename", "original_filename", "title", "institution",
        "document_type", "year", "description", "uploaded_by", "status",
        "num_pages", "total_chunks", "created_at", "updated_at")}


@router.get("", response_model=list[schemas.DocumentOut])
def list_docs(active_only: bool = False, doc_type: str | None = None,
              year: int | None = None, institution: str | None = None,
              q: str | None = None, user=Depends(deps.require_user)):
    if user["role"] != auth.ADMIN:
        active_only = True  # employees never see inactive documents
    rows = documents.list_documents(active_only=active_only, doc_type=doc_type,
                                    year=year, institution=institution,
                                    title_kw=q or None)
    return [_doc_out(d) for d in rows]


@router.get("/filters")
def filters(user=Depends(deps.require_user)):
    return {
        "document_types": documents.distinct_values("document_type"),
        "institutions": documents.distinct_values("institution"),
        "years": documents.distinct_values("year"),
    }


@router.post("", response_model=schemas.DocumentOut, status_code=201)
def upload(file: UploadFile,
           title: str = Form(default=""),
           institution: str = Form(default=""),
           document_type: str = Form(default="Tjetër"),
           year: int | None = Form(default=None),
           description: str = Form(default=""),
           user=Depends(deps.require_admin)):
    name = file.filename or "dokument.pdf"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in config.UPLOAD_TYPES:
        raise HTTPException(status_code=400,
                            detail="Lejohen vetëm skedarë PDF ose DOCX.")
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Skedari është shumë i madh (max 100MB).")

    tmp = Path(tempfile.gettempdir()) / documents.safe_filename(name)
    tmp.write_bytes(data)
    try:
        doc_id, n = documents.add_document(
            tmp, name, title=title, institution=institution,
            document_type=document_type, year=year, description=description,
            uploaded_by=user["username"])
    except dp.NoExtractableTextError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        tmp.unlink(missing_ok=True)

    audit.log(user["id"], user["username"], "upload_document", f"{name} ({n} copëza)")
    return _doc_out(documents.get_document(doc_id))


def _existing(doc_id: int):
    doc = documents.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet.")
    return doc


@router.patch("/{doc_id}", response_model=schemas.DocumentOut)
def patch_doc(doc_id: int, body: schemas.DocumentPatchIn,
              user=Depends(deps.require_admin)):
    doc = _existing(doc_id)
    documents.update_metadata(doc_id, **body.model_dump(exclude_none=True))
    audit.log(user["id"], user["username"], "update_document_metadata", doc["filename"])
    return _doc_out(documents.get_document(doc_id))


@router.post("/{doc_id}/status", response_model=schemas.DocumentOut)
def set_status(doc_id: int, body: schemas.StatusIn, user=Depends(deps.require_admin)):
    doc = _existing(doc_id)
    try:
        documents.set_status(doc_id, body.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    action = ("activate_document" if body.status == config.STATUS_ACTIVE
              else "deactivate_document")
    audit.log(user["id"], user["username"], action, doc["filename"])
    return _doc_out(documents.get_document(doc_id))


@router.delete("/{doc_id}")
def delete_doc(doc_id: int, user=Depends(deps.require_admin)):
    doc = _existing(doc_id)
    documents.delete_document(doc_id)
    audit.log(user["id"], user["username"], "delete_document", doc["filename"])
    return {"ok": True}


@router.post("/{doc_id}/reindex")
def reindex_one(doc_id: int, user=Depends(deps.require_admin)):
    doc = _existing(doc_id)
    try:
        n = documents.reindex_document(doc_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    audit.log(user["id"], user["username"], "reindex_document", doc["filename"])
    return {"chunks": n}


@router.post("/reindex-all", response_model=schemas.TaskOut)
def reindex_all(user=Depends(deps.require_admin)):
    if tasks.any_running("reindex"):
        raise HTTPException(status_code=409, detail="Një riindeksim është tashmë në ekzekutim.")
    uid, uname = user["id"], user["username"]

    def job(task):
        docs = documents.list_documents()
        total_chunks, done = 0, 0
        for i, d in enumerate(docs):
            task.update(progress=i / max(1, len(docs)),
                        message=f"Duke riindeksuar: {d['title'] or d['filename']}")
            try:
                total_chunks += documents.reindex_document(d["id"])
                done += 1
            except Exception:  # noqa: BLE001 — skip broken docs, keep going (parity with reindex_all)
                continue
        audit.log(uid, uname, "reindex_all_documents", f"{total_chunks} copëza")
        return {"documents": done, "chunks": total_chunks}

    return tasks.start("reindex-all", job).to_dict()


@router.get("/{doc_id}/file")
def download(doc_id: int, inline: bool = False, user=Depends(deps.require_admin)):
    doc = _existing(doc_id)
    path = Path(doc["stored_path"] or "")
    if not path.exists():
        raise HTTPException(status_code=409, detail="Skedari mungon në disk.")
    is_pdf = doc["filename"].lower().endswith(".pdf")
    media = PDF_MIME if is_pdf else DOCX_MIME
    disposition = "inline" if (inline and is_pdf) else "attachment"
    return FileResponse(path, media_type=media, filename=doc["filename"],
                        content_disposition_type=disposition)
