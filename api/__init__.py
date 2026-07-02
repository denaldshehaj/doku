"""DOKU HTTP API — a thin FastAPI layer over the existing `modules/` core.

The API adds no business logic of its own: every endpoint validates input,
delegates to a module function, and shapes the result for the React frontend.
Local-only by design: the server binds to 127.0.0.1 and talks exclusively to
local services (SQLite, ChromaDB, Ollama).
"""
