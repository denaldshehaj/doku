"""RAG question answering (plain + SSE streaming) + Word export of an answer.

Same flow as always: filter the active corpus (or a single document), run the
pipeline (refusal gate BEFORE the LLM), persist to history, audit. The LLM
semaphore serialises generations for the 4GB local GPU."""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

import config
from api import deps, schemas
from modules import (audit, database as db, documents, export_docx, history,
                     llm_client, rag_pipeline as rag)

router = APIRouter(prefix="/api/chat", tags=["chat"])

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _resolve_scope(body: schemas.AskIn) -> tuple[str, int | None, list[int] | None]:
    """Validate the question + resolve the retrieval scope (shared by both
    the plain and the streaming endpoint)."""
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Pyetja është bosh.")
    selected_doc_id = body.document_id
    active_ids = None
    if selected_doc_id is None:
        filtered = documents.list_documents(
            active_only=True, doc_type=body.doc_type, year=body.year,
            institution=body.institution, title_kw=body.title_kw or None)
        active_ids = [d["id"] for d in filtered]
    else:
        doc = documents.get_document(selected_doc_id)
        if doc is None or doc["status"] != config.STATUS_ACTIVE:
            raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet ose është joaktiv.")
    return question, selected_doc_id, active_ids


def _persist(user, question: str, ans, selected_doc_id) -> int:
    row_id = history.save(user["id"], user["username"], question, ans.text,
                          mode="rag", selected_document_id=selected_doc_id,
                          sources=ans.sources, response_time=ans.response_time)
    audit.log(user["id"], user["username"], "ask_question", question[:120])
    return row_id


def _answer_out(row_id: int, ans) -> dict:
    return {
        "row_id": row_id, "text": ans.text, "refused": ans.refused,
        "sources": ans.sources, "top_score": round(ans.top_score, 4),
        "response_time": ans.response_time, "chunks_used": ans.chunks_used,
        "min_similarity": config.MIN_SIMILARITY,
    }


@router.post("/ask", response_model=schemas.AnswerOut)
def ask(body: schemas.AskIn, user=Depends(deps.require_user)):
    question, selected_doc_id, active_ids = _resolve_scope(body)

    with deps.LLM_LOCK:
        ans = rag.answer_question(question, mode="rag",
                                  selected_document_id=selected_doc_id,
                                  active_doc_ids=active_ids)

    row_id = _persist(user, question, ans, selected_doc_id)
    return _answer_out(row_id, ans)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/ask-stream")
def ask_stream(body: schemas.AskIn, user=Depends(deps.require_user)):
    """Server-Sent Events variant: `delta` events carry generated text
    fragments as they arrive from the local model; a terminal `refusal`,
    `done` or `error` event closes the stream. Grounding is identical to
    /ask — the refusal gate still runs before any generation."""
    question, selected_doc_id, active_ids = _resolve_scope(body)

    def event_source():
        deps.LLM_LOCK.acquire()
        try:
            for kind, payload in rag.answer_question_stream(
                    question, mode="rag", selected_document_id=selected_doc_id,
                    active_doc_ids=active_ids):
                if kind == "delta":
                    yield _sse("delta", {"t": payload})
                elif kind == "refusal":
                    row_id = _persist(user, question, payload, selected_doc_id)
                    yield _sse("refusal", _answer_out(row_id, payload))
                else:  # final
                    row_id = _persist(user, question, payload, selected_doc_id)
                    yield _sse("done", _answer_out(row_id, payload))
        except llm_client.OllamaUnavailableError as exc:
            yield _sse("error", {"code": "ollama_unavailable", "message": str(exc)})
        except Exception as exc:  # noqa: BLE001 — the stream must end with a typed event
            yield _sse("error", {"code": "internal", "message": str(exc)})
        finally:
            deps.LLM_LOCK.release()

    return StreamingResponse(event_source(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store",
                                      "X-Accel-Buffering": "no"})


def _own_history_row(row_id: int, username: str):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM chat_history WHERE id = ?", (row_id,)).fetchone()
    if row is None or row["username"] != username:
        raise HTTPException(status_code=404, detail="Rekordi nuk u gjet në historikun tuaj.")
    return row


@router.post("/{row_id}/export")
def export_answer(row_id: int, user=Depends(deps.require_user)):
    row = _own_history_row(row_id, user["username"])
    if row["mode"] != "rag":
        raise HTTPException(status_code=400, detail="Vetëm përgjigjet e pyetjeve eksportohen këtu.")
    sources = json.loads(row["sources_json"] or "[]")
    path = export_docx.export_answer_to_docx(
        user["id"], user["username"], row["question"], row["answer"],
        sources, row["response_time"])
    history.mark_exported(row_id)
    audit.log(user["id"], user["username"], "export_answer_docx", row["question"][:80])
    filename = path.replace("\\", "/").rsplit("/", 1)[-1]
    return FileResponse(path, media_type=DOCX_MIME, filename=filename)
