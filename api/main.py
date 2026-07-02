"""DOKU API entrypoint.

    .venv\\Scripts\\python run_api.py          (or: uvicorn api.main:app)

- Binds to 127.0.0.1 only — the system stays fully local.
- Serves the built React frontend from frontend/dist (single process, single
  port, no CORS). In development the Vite dev server proxies /api here instead.
- On startup: ensures the SQLite schema + default admin exist (same bootstrap
  the Streamlit entrypoint performs) and pre-warms the embedding model in the
  background so the first question isn't paying the bge-m3 load time.
"""
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

import config
from modules import auth, database, llm_client

from api.routers import (audit_router, auth_router, chat_router,
                         documents_router, experiments_router, history_router,
                         meta_router, reports_router, summaries_router,
                         tasks_router, users_router)


def _warm_embeddings() -> None:
    """Load bge-m3 + open the Chroma collection off the request path."""
    try:
        from modules import embeddings, vector_store
        embeddings.embed_query("ngrohje e modelit")
        vector_store.count()
    except Exception as exc:  # noqa: BLE001 — warmup must never kill the server
        print(f"[DOKU] Paralajmërim: ngrohja e embeddings dështoi: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_schema()
    auth.ensure_default_admin()
    threading.Thread(target=_warm_embeddings, daemon=True).start()
    yield


app = FastAPI(title="DOKU API", version="1.0.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json")

for r in (auth_router, meta_router, chat_router, summaries_router,
          history_router, documents_router, users_router, audit_router,
          experiments_router, reports_router, tasks_router):
    app.include_router(r.router)


@app.middleware("http")
async def secure_headers(request: Request, call_next):
    """Baseline hardening headers + no caching of API responses (they carry
    per-user data; the browser must never serve them from cache)."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    # SAMEORIGIN (not DENY): the admin PDF preview embeds /api/documents/{id}/file
    # in an iframe on the same origin.
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(llm_client.OllamaUnavailableError)
async def ollama_unavailable(request: Request, exc: llm_client.OllamaUnavailableError):
    return JSONResponse(status_code=503,
                        content={"detail": {"code": "ollama_unavailable",
                                            "message": str(exc)}})


# --- React SPA (production build) -------------------------------------------
DIST = config.ROOT / "frontend" / "dist"


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    """Serve the built frontend; unknown paths fall back to index.html so
    client-side routes (/biseda, /admin/...) survive a browser refresh."""
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Endpoint i panjohur."})
    if not DIST.exists():
        return JSONResponse(status_code=503, content={"detail": (
            "Frontend-i nuk është ndërtuar ende. Ekzekuto `npm run build` në "
            "folderin frontend/, ose përdor `npm run dev` gjatë zhvillimit.")})
    candidate = (DIST / full_path).resolve()
    # Path-traversal guard: only files inside dist/ are ever served.
    if full_path and candidate.is_file() and candidate.is_relative_to(DIST.resolve()):
        return FileResponse(candidate)
    return FileResponse(DIST / "index.html")
