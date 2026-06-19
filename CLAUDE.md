# CLAUDE.md — DOKU Development Contract

> Working rules for any Claude session on this project. These are **strong defaults**:
> follow them unless the user explicitly overrides one in the moment.

## What DOKU is
A **fully-local** intelligent document-analysis system (Master's thesis, CS & AI).
RAG + a local LLM analyze institutional PDF documents **in Albanian**. It simulates a
government/institutional setting: an **admin** manages a centralized corpus; **employees
(punonjes)** query/summarize but cannot modify it.

## Tech stack (fixed — do not replace without explicit approval)
Python 3.13 · Streamlit (UI, Albanian, multipage) · SQLite (users, documents, chat
history, audit logs, experiments) · ChromaDB (vectors) · PyMuPDF (PDF) · Sentence
Transformers **bge-m3** embeddings · Ollama local LLM (`OLLAMA_MODEL`) · python-docx.
NOT allowed: cloud APIs, OpenAI/Claude APIs, Docker, FastAPI, React, microservices, OCR.

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
pages/                # 1_Dashboard … 8_Eksperimente (Streamlit multipage)
data/                 # uploads/, exports/, chroma_db/, app.db (auto-created)
tests/sample_questions.csv
scripts/seed_sample_corpus.py
```

## Hard constraints (strong defaults)
1. **LOCAL-ONLY** — no cloud APIs/network for inference/embeddings. Ollama + local models.
2. **NO SCOPE CREEP** — no Docker/FastAPI/React/microservices/OCR. New features need sign-off.
3. **GROUNDING IS SACRED** — RAG never answers beyond retrieved context. Below
   `MIN_SIMILARITY` it refuses with the exact `REFUSAL_MESSAGE`. Every claim cites a chunk.
4. **VALIDATE BEFORE MOVING ON** — no milestone is "done" until its checks pass.
5. **ROLE SECURITY** — punonjes is read-only. Enforced in code (`ui.require_admin`), not
   just hidden in the UI. Admin manages users; **no public self-registration**.
6. **THINK FIRST** — ambiguity/risk → stop and ask.
7. **ASK BEFORE PUSH** — never `git push` without explicit user approval.

## Auth model
Default admin (`admin`/`***REMOVED-CREDENTIAL***`) is auto-created if no admin exists, flagged to change
password on first login. Admin creates employees (also forced to change on first login).

## Environment notes (Windows 11, 16GB RAM, RTX 3050 4GB)
- Use **`py -3.13`** for the venv. Bare `python` on PATH may be a foreign Store stub.
- Ollama must run on :11434. **`gemma2:9b` gives better Albanian but can OOM on 16GB**
  (model ~5.4GB + bge-m3 ~2.3GB); default is `qwen2.5:3b` (reliable). Switch in the UI.
- Run from repo root so `import config` / `from modules import ...` resolve.

## Run / validate
- Setup: `py -3.13 -m venv .venv` → `pip install -r requirements.txt`
- Model: `ollama pull qwen2.5:3b` (and optionally `ollama pull gemma2:9b`)
- Seed demo corpus (optional): `python scripts\seed_sample_corpus.py`
- App: `.venv\Scripts\streamlit run app.py`  (login: admin/***REMOVED-CREDENTIAL*** → set new password)

## Current status
- [x] Restructured to modules/ + pages/ per thesis spec; 5 DB tables; admin-managed auth
- [x] Status active/inactive, full metadata, reindex-all, filtering, citations, legal note
- [x] Summaries (4 formats), Word export to spec, experiment harness (manual eval + CSV)

See **SPEC.md** for milestones and **DOKUMENTACIONI.md** for the technical write-up.
