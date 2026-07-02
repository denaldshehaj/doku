"""Personal question/answer history (each user sees only their own rows)."""
import json

from fastapi import APIRouter, Depends, Query

from api import deps, schemas
from modules import history

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[schemas.HistoryRowOut])
def my_history(limit: int = Query(default=100, ge=1, le=500),
               user=Depends(deps.require_user)):
    rows = history.recent(user["username"], limit=limit)
    return [{
        "id": r["id"], "question": r["question"], "answer": r["answer"],
        "mode": r["mode"], "selected_document_id": r["selected_document_id"],
        "sources": json.loads(r["sources_json"] or "[]"),
        "response_time": r["response_time"],
        "exported_to_word": bool(r["exported_to_word"]),
        "created_at": r["created_at"],
    } for r in rows]
