"""Document summaries (4 formats) + Word export — same flow as the Streamlit
page: extract full text, summarize with the local LLM, persist to history."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

import config
from api import deps, schemas
from modules import (audit, document_processor as dp, documents, export_docx,
                     history, rag_pipeline as rag)

router = APIRouter(prefix="/api/summaries", tags=["summaries"])

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _active_document(document_id: int):
    doc = documents.get_document(document_id)
    if doc is None or doc["status"] != config.STATUS_ACTIVE:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet ose është joaktiv.")
    path = Path(doc["stored_path"] or "")
    if not path.exists():
        raise HTTPException(status_code=409, detail="Skedari i dokumentit mungon në disk.")
    return doc, path


@router.post("", response_model=schemas.SummaryOut)
def summarize(body: schemas.SummarizeIn, user=Depends(deps.require_user)):
    if body.format not in rag.SUMMARY_FORMATS:
        raise HTTPException(status_code=400, detail="Format i panjohur përmbledhjeje.")
    doc, path = _active_document(body.document_id)

    text = dp.extract_text(path)
    with deps.LLM_LOCK:
        summary = rag.summarize(text, fmt=body.format)

    history.save(user["id"], user["username"], f"[Përmbledhje: {doc['title']}]",
                 summary, mode="summary", selected_document_id=doc["id"])
    audit.log(user["id"], user["username"], "generate_summary", doc["filename"])
    return {"document_id": doc["id"], "title": doc["title"] or "",
            "filename": doc["filename"], "format": body.format, "summary": summary}


@router.post("/export")
def export_summary(body: schemas.SummaryExportIn, user=Depends(deps.require_user)):
    doc = documents.get_document(body.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet.")
    meta = {k: doc[k] for k in ("id", "title", "filename", "institution",
                                "document_type", "year")}
    path = export_docx.export_summary_to_docx(meta, body.summary, body.format)
    audit.log(user["id"], user["username"], "export_summary_docx", doc["filename"])
    filename = path.replace("\\", "/").rsplit("/", 1)[-1]
    return FileResponse(path, media_type=DOCX_MIME, filename=filename)
