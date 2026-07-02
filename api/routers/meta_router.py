"""Static domain metadata (enums from config) + dashboard counters + system
status. Everything the frontend needs to render selects and stat cards."""
from fastapi import APIRouter, Depends, HTTPException

import config
from api import deps, schemas
from modules import audit, auth, documents, history, llm_client, rag_pipeline, vector_store

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta")
def meta(user=Depends(deps.require_user)):
    return {
        "document_types": config.DOCUMENT_TYPES,
        "institutions": config.INSTITUTIONS,
        "upload_types": config.UPLOAD_TYPES,
        "summary_formats": list(rag_pipeline.SUMMARY_FORMATS.keys()),
        "min_similarity": config.MIN_SIMILARITY,
        "refusal_message": config.REFUSAL_MESSAGE,
    }


@router.get("/dashboard")
def dashboard(user=Depends(deps.require_user)):
    active = documents.list_documents(active_only=True)
    all_docs = documents.list_documents()
    out = {
        "active_documents": len(active),
        "total_documents": len(all_docs),
        "chunks": vector_store.count(),
        "my_questions": history.count_for_user(user["username"]),
        "users_count": None,
    }
    if user["role"] == auth.ADMIN:
        out["users_count"] = auth.user_count()
    return out


@router.get("/system/status")
def system_status(user=Depends(deps.require_user)):
    online = llm_client.is_available()
    return {
        "ollama_online": online,
        "active_model": llm_client.get_active_model(),
        "models": llm_client.list_models() if online else [],
    }


@router.put("/system/model")
def set_model(body: schemas.ModelIn, user=Depends(deps.require_admin)):
    models = llm_client.list_models()
    if body.model not in models:
        raise HTTPException(status_code=400,
                            detail="Modeli nuk gjendet në Ollama (bëj `ollama pull` më parë).")
    llm_client.set_active_model(body.model)
    audit.log(user["id"], user["username"], "set_model", body.model)
    return {"active_model": llm_client.get_active_model()}
