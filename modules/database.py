"""SQLite layer: schema, connection, auto-creation. Holds users, documents,
chat history, audit logs, and experiment results. Chunk vectors live in ChromaDB.

If the DB or its folder is missing, it is created automatically.
"""
import sqlite3
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'punonjes')),
    must_change_password INTEGER NOT NULL DEFAULT 0,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    filename          TEXT UNIQUE NOT NULL,
    original_filename TEXT,
    stored_path       TEXT,
    title             TEXT,
    institution       TEXT,
    document_type     TEXT,
    year              INTEGER,
    description       TEXT,
    uploaded_by       TEXT,
    status            TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
    num_pages         INTEGER NOT NULL DEFAULT 0,
    total_chunks      INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER,
    username            TEXT,
    question            TEXT NOT NULL,
    answer              TEXT,
    mode                TEXT NOT NULL DEFAULT 'rag',  -- rag / no_rag / summary
    selected_document_id INTEGER,
    sources_json        TEXT,
    response_time       REAL,
    exported_to_word    INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    username   TEXT,
    action     TEXT NOT NULL,
    details    TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    username   TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiment_results (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    question                   TEXT NOT NULL,
    answer_without_rag         TEXT,
    answer_with_rag            TEXT,
    time_without_rag           REAL,
    time_with_rag              REAL,
    chunks_used                INTEGER,
    has_sources                INTEGER,
    manual_accuracy_without_rag INTEGER,
    manual_accuracy_with_rag    INTEGER,
    hallucination_without_rag   TEXT,
    hallucination_with_rag      TEXT,
    notes                      TEXT,
    created_at                 TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # busy_timeout first: makes every subsequent statement wait (up to 30s) for a
    # lock instead of failing instantly with "database is locked".
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL lets readers and a writer work concurrently — essential because Streamlit
    # re-runs the script (and reopens connections) on every interaction. Switching
    # journal mode needs a brief exclusive lock; if another connection holds it we
    # tolerate the failure (the DB simply stays in its current mode this time).
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError:
        pass
    return conn


@contextmanager
def get_conn():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


_schema_ready = False


def init_schema() -> None:
    """Create all tables if they do not exist. Idempotent, and runs its write
    transaction only once per process — Streamlit re-executes the entrypoint on
    every rerun, and repeating the schema write caused lock contention."""
    global _schema_ready
    if _schema_ready:
        return
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    _schema_ready = True
