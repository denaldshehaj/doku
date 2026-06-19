"""SQLite layer: schema + connection. Stores users, audit log, query history,
document metadata, and experiment runs. Chunk vectors live in ChromaDB, not here."""
import sqlite3
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'employee')),
    must_change_password INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT UNIQUE NOT NULL,
    title       TEXT,
    doc_type    TEXT,
    institution TEXT,
    year        INTEGER,
    n_chunks    INTEGER NOT NULL DEFAULT 0,
    n_pages     INTEGER NOT NULL DEFAULT 0,
    indexed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    action   TEXT NOT NULL,
    detail   TEXT,
    ts       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS query_history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT,
    question  TEXT NOT NULL,
    answer    TEXT,
    refused   INTEGER NOT NULL DEFAULT 0,
    citations TEXT,
    ts        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS experiments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT,
    question    TEXT NOT NULL,
    rag_answer  TEXT,
    norag_answer TEXT,
    rag_refused INTEGER NOT NULL DEFAULT 0,
    ts          TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _migrate(conn) -> None:
    """Lightweight migrations for databases created by older versions."""
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)")]
    if "must_change_password" not in cols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN must_change_password "
            "INTEGER NOT NULL DEFAULT 0"
        )


def init_db() -> None:
    """Create all tables if they do not exist, then migrate. Idempotent."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
