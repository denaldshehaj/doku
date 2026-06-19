"""Audit logging. Every login and privileged action writes an auditable row
(CLAUDE.md rule 5 / DoD for logging)."""
from doku import db


def log(username: str, action: str, detail: str = "") -> None:
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (username, action, detail) VALUES (?, ?, ?)",
            (username, action, detail),
        )


def recent(limit: int = 200):
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT username, action, detail, ts FROM audit_log "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
