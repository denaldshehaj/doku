# DOKU — Specification & Milestones

## Goal (locked)
A fully-local, role-secured RAG system for Albanian institutional PDFs whose defining
quality is **strict groundedness**: it cites every claim and refuses when the corpus
doesn't support an answer. RAG-vs-non-RAG comparison is a built feature. Target: working
end-to-end in under a month. Engineering-artifact thesis.

## Architecture — modules
| # | Module          | Responsibility |
|---|-----------------|----------------|
| 1 | `config`        | Central settings: paths, model names, chunk size, retrieval-k, **refusal threshold**. |
| 2 | `auth`          | SQLite users, hashed passwords (passlib/bcrypt), admin/employee roles, Streamlit session gating. |
| 3 | `ingestion`     | PyMuPDF extract → **text-presence validation** (reject/flag scanned PDFs, no OCR) → chunking → metadata. |
| 4 | `vectorstore`   | ChromaDB collection, bge-m3 embeddings, metadata-filtered retrieval. |
| 5 | `rag`           | Retrieve → **refusal gate** (confidence threshold) → grounded prompt → Ollama → cited answer. Summarization. |
| 6 | `export`        | python-docx: answers & summaries → Word. |
| 7 | `experiment`    | Same question through RAG vs bare LLM, side-by-side, saved to SQLite. |
| 8 | `logging`       | Audit trail (user, action, timestamp) to SQLite. |
| — | `ui` (Streamlit)| Albanian UI, role-gated views; ties modules together. |

## Milestones (~4 weeks)
**M0 — Skeleton + spike (Day 1–2).** Repo structure, `config.py`, this spec, CLAUDE.md.
Embedding spike: index ~5 Albanian paragraphs, query, confirm bge-m3 retrieves correctly.
→ *Decision: embedding model confirmed.*

**M1 — Vertical slice (Week 1) — make-or-break.** One PDF → ingest → chunk → embed →
Chroma → retrieve top-k → refusal gate → Ollama → answer with inline citations, in a bare
Streamlit page. No auth yet. *Proves Albanian RAG + no-hallucination.*

**M2 — Auth + admin document management (Week 2).** Login, roles, admin upload/delete/
reindex/metadata-edit, real ingestion w/ validation. Employees: read-only query view.

**M3 — Features + grounding polish (Week 3).** Metadata filtering, summarization (multiple
formats), Word export, audit logging wired throughout.

**M4 — Experiment + demo polish (Week 4).** RAG-vs-non-RAG comparison view saved to SQLite,
seed users/data, UI cleanup, demo script for defense.

## Definition of Done (per module)
- **rag / grounding** — answerable question → answer with ≥1 citation (doc+page) to a real
  chunk; out-of-scope question → refusal *"Nuk u gjet në dokumente"* with **0 fabricated
  facts**; a fixed **~10 Q&A test set** passes (correct answers cited, out-of-scope refused).
- **auth / RBAC** — employee session cannot reach any admin action even via direct call;
  passwords hashed (never plaintext); every privileged action logged.
- **ingestion** — scanned/no-text PDF is detected and flagged/rejected, never silently
  indexed as empty; chunk metadata carries source doc + page.
- **vectorstore** — retrieval returns top-k with scores; metadata filters apply correctly.
- **export** — answer/summary round-trips to a valid .docx incl. citations.
- **experiment** — one question yields paired RAG/non-RAG outputs persisted with timestamp.
- **logging** — every login + privileged action produces an auditable SQLite row.
- **config** — all tunables (models, thresholds, k, chunk size) live in one file.
