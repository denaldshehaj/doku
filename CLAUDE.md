# CLAUDE.md — DOKU Development Contract

> Working rules for any Claude session on this project. These are **strong defaults**:
> follow them unless the user explicitly overrides one in the moment.

## What DOKU is
A **fully-local** intelligent document-analysis system (Master's thesis, CS & AI).
RAG + a local LLM analyze institutional PDF documents **in Albanian**. It simulates a
government/institutional setting: an **admin** manages a centralized corpus; **employees
(punonjes)** query/summarize but cannot modify it.

## Tech stack (fixed — do not replace without explicit approval)
Python 3.13 · SQLite (users, documents, chat history, audit logs, experiments) ·
ChromaDB (vectors) · PyMuPDF (PDF) · Sentence Transformers **bge-m3** embeddings ·
Ollama local LLM (`OLLAMA_MODEL`) · python-docx.
**UI/API (approved 2026-07-01, replacing Streamlit):** FastAPI (localhost-only, thin
layer over `modules/`) + React 19 / Vite / TypeScript / Tailwind 4 / TanStack Query
in `frontend/`. The legacy Streamlit UI (`app.py` + `views/`) remains runnable until
full parity is confirmed, then gets removed.
NOT allowed: cloud APIs, OpenAI/Claude APIs, Docker, microservices, OCR, SSR/Next.js.

## Architecture (restructured to thesis spec)
```
app.py                # entrypoint: login, session, role-based st.navigation
config.py             # OLLAMA_MODEL, temperature, paths, thresholds, enums
modules/
  database.py         # SQLite schema (5 tables) + connection
  auth.py             # bcrypt, roles (admin/punonjes), default admin, forced change
  audit.py            # audit logging
  document_processor.py  # PyMuPDF extract + text validation + chunking
  embeddings.py       # bge-m3
  vector_store.py     # ChromaDB, full chunk metadata, active/doc-id filtering
  documents.py        # document CRUD: upload/edit/status/delete/reindex(/all)
  rag_pipeline.py     # retrieve -> refusal gate -> grounded prompt -> LLM -> cites
  llm_client.py       # Ollama client (OllamaUnavailableError on failure)
  history.py          # chat_history persistence
  export_docx.py      # Word export (answers + summaries) to data/exports/
  experiments.py      # RAG vs no-RAG harness + CSV export
  ui.py               # session guards (current_user, require_admin)
views/                # 1_Dashboard … 8_Eksperimente (legacy Streamlit multipage)
api/                  # FastAPI layer over modules/ (no business logic of its own)
  main.py             # app + lifespan (schema/admin bootstrap, embeddings warmup) + SPA static
  deps.py             # cookie-session deps: require_user/require_admin + LLM semaphore
  schemas.py          # Pydantic request/response models
  tasks.py            # in-memory background tasks (reindex-all, experiment batches)
  routers/            # auth, meta/dashboard/system, chat, summaries, history,
                      # documents, users, audit, experiments, tasks
run_api.py            # uvicorn launcher — binds 127.0.0.1:8000 ONLY
frontend/             # React SPA (Vite + TS + Tailwind 4 + TanStack Query)
  src/api/            # typed client + endpoints (mirrors api/schemas.py)
  src/providers/      # Auth / Theme / Toast contexts
  src/components/     # ui/ primitives · layout/ AppShell · shared/
  src/features/       # auth, dashboard, chat, summaries, history, admin/*
data/                 # uploads/, exports/, chroma_db/, app.db (auto-created)
tests/sample_questions.csv
scripts/seed_sample_corpus.py
```

## Hard constraints (strong defaults)
1. **LOCAL-ONLY** — no cloud APIs/network for inference/embeddings. Ollama + local models.
2. **NO SCOPE CREEP** — no Docker/microservices/OCR/new frameworks. New features need sign-off.
3. **GROUNDING IS SACRED** — RAG never answers beyond retrieved context. Below
   `MIN_SIMILARITY` it refuses with the exact `REFUSAL_MESSAGE`. Every claim cites a chunk.
4. **VALIDATE BEFORE MOVING ON** — no milestone is "done" until its checks pass.
5. **ROLE SECURITY** — punonjes is read-only. Enforced server-side (`api.deps.require_admin`
   on every mutating endpoint; legacy `ui.require_admin` in Streamlit), never just hidden
   in the UI. Admin manages users; **no public self-registration**.
6. **THINK FIRST** — ambiguity/risk → stop and ask.
7. **ASK BEFORE PUSH** — never `git push` without explicit user approval.
8. **LOCALHOST BINDING** — the API server binds `127.0.0.1` only; never `0.0.0.0`.

## Auth model
Default admin (`admin`/`***REMOVED-CREDENTIAL***`) is auto-created if no admin exists, flagged to change
password on first login. Admin creates employees (also forced to change on first login).

## Environment notes (Windows 11, 16GB RAM, RTX 3050 4GB)
- Use **`py -3.13`** for the venv. Bare `python` on PATH may be a foreign Store stub.
- Ollama must run on :11434. **`gemma2:9b` gives better Albanian but can OOM on 16GB**
  (model ~5.4GB + bge-m3 ~2.3GB); default is `qwen2.5:3b` (reliable). Switch in the UI.
- Run from repo root so `import config` / `from modules import ...` resolve.
- Node.js LTS is a **portable install at `%USERPROFILE%\tools\node`** (added to user
  PATH) — no system-wide install. Needed only to develop/rebuild the frontend.
- The repo lives at `C:\Users\denal\Desktop\Projects\doku` — deliberately **outside
  OneDrive** (a OneDrive migration once split the ChromaDB index files from the repo;
  SQLite/ChromaDB must never sit inside a syncing folder). If Windows ever re-enables
  OneDrive Desktop backup, move the repo out again before running the server.

## Run / validate
- Setup: `py -3.13 -m venv .venv` → `pip install -r requirements.txt`
- Model: `ollama pull qwen2.5:3b` (and optionally `ollama pull gemma2:9b`)
- Seed demo corpus (optional): `python scripts\seed_sample_corpus.py`
- **App (React UI): `.venv\Scripts\python run_api.py`** → http://127.0.0.1:8000
  (serves the built SPA from `frontend/dist` + the API under `/api`; docs at `/api/docs`)
- Frontend dev loop: `cd frontend` → `npm run dev` (Vite on :5173, proxies `/api` to :8000)
- Frontend checks: `npm run build` (tsc + vite) and `npm run lint` — both must pass
- Legacy Streamlit UI (until removal): `.venv\Scripts\streamlit run app.py`

## Current status
- [x] Restructured to modules/ + pages/ per thesis spec; 5 DB tables; admin-managed auth
- [x] Status active/inactive, full metadata, reindex-all, filtering, citations, legal note
- [x] Summaries (4 formats), Word export to spec, experiment harness (manual eval + CSV)
- [x] FastAPI layer over modules/ (cookie sessions, role guards, background tasks) +
      React SPA (all 8 pages + login/forced-change) — E2E-tested 2026-07-02; Streamlit
      still present, remove after user confirms parity

See **SPEC.md** for milestones and **DOKUMENTACIONI.md** for the technical write-up.
