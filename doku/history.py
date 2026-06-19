"""Persistence for Q&A history (who asked what, was it refused, with citations)."""
import json

from doku import db


def save(username: str, question: str, answer: str, refused: bool, citations: list) -> None:
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO query_history (username, question, answer, refused, citations) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, question, answer, int(refused), json.dumps(citations, ensure_ascii=False)),
        )


def recent(username: str | None = None, limit: int = 50):
    sql = "SELECT username, question, answer, refused, ts FROM query_history"
    params: tuple = ()
    if username:
        sql += " WHERE username = ?"
        params = (username,)
    sql += " ORDER BY id DESC LIMIT ?"
    params = params + (limit,)
    with db.get_conn() as conn:
        return conn.execute(sql, params).fetchall()
