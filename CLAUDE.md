# CLAUDE.md — DOKU Development Contract

> Working rules for any Claude session on this project. These are **strong defaults**:
> follow them unless the user explicitly overrides one in the moment.

## What DOKU is
A **fully-local** intelligent document-analysis system (Master's thesis, CS & AI).
RAG + a local LLM analyze institutional PDF documents **in Albanian**. It simulates a
government/institutional setting: an **admin** manages a central corpus; **employees**
query/summarize but cannot modify it.

**Thesis framing:** engineering artifact (the working, secure, local system is the
contribution). The RAG-vs-non-RAG experiment is a *built, demoable feature*, not a
research-grade empirical study.

## Tech stack (fixed)
Python 3.13 · Streamlit (UI, Albanian) · SQLite (users, logs, history, experiments) ·
ChromaDB (vectors) · PyMuPDF (PDF) · Sentence Transformers **bge-m3** embeddings (pending
M0 spike) · Ollama local LLM (`qwen2.5:3b` / `llama3.2:3b`) · python-docx (Word export).

## Hard constraints (strong defaults)
1. **LOCAL-ONLY** — no cloud APIs, no network calls for inference/embeddings. Ollama +
   local models only.
2. **NO SCOPE CREEP** — no Docker, FastAPI, React, microservices, OCR. New features need
   explicit sign-off.
3. **GROUNDING IS SACRED** — the RAG pipeline never answers beyond retrieved context.
   Below the confidence threshold it MUST refuse with *"Nuk u gjet në dokumente"*. Every
   factual claim cites a source chunk (document + page).
4. **VALIDATE BEFORE MOVING ON** — no milestone is "done" until its Definition-of-Done
   checks (see SPEC.md) pass.
5. **ROLE SECURITY** — employees are read-only. Enforced in code, not just hidden in UI.
6. **THINK FIRST** — ambiguity or risk → stop and ask, don't guess or invent features.

## Environment notes (Windows 11, 16GB RAM, RTX 3050)
- Use **`py -3.13`** to create/refresh the venv. The bare `python` on PATH resolves to a
  foreign user-profile Store stub — avoid it.
- Activate venv: `.venv\Scripts\activate` (PowerShell) — run all Python via the venv.
- **Ollama must be installed separately** (https://ollama.com) and running on :11434
  before the generation step works. Not required for the embedding spike.

## Current status
- [x] M0a — interview, goal, spec, constraints
- [x] M0b — scaffold + embedding spike script (bge-m3); Python 3.13 venv; deps installed
- [x] M1 — RAG pipeline (ingest→chunk→embed→retrieve→refusal gate→cited answer) in `doku/rag.py`
- [x] M2 — auth + RBAC + admin document management (`auth.py`, `documents.py`, UI guards)
- [x] M3 — metadata, summarization, Word export, audit logging
- [x] M4 — experiment module (RAG vs non-RAG), sample corpus, grounding tests, README
- [ ] FINAL VALIDATION — run smoke_test + grounding_test + spike; pull `qwen2.5:3b`; manual UI demo

## Run / validate
- Setup: `py -3.13 -m venv .venv` → `pip install -r requirements.txt` → `python seed.py`
  → `python scripts/make_sample_corpus.py`
- Model: `ollama pull qwen2.5:3b` (Ollama service must be up on :11434)
- App: `.venv\Scripts\streamlit run app.py`  (no default creds — register in-app; first account = admin)
- Tests: `python tests\smoke_test.py`, `python tests\grounding_test.py`

See **SPEC.md** for architecture, milestones, and per-module Definition of Done.
