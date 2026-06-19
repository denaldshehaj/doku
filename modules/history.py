"""Persistence for chat history (questions, answers, mode, sources, timing)."""
import json

from modules import database as db


def save(user_id, username, question, answer, mode="rag",
         selected_document_id=None, sources=None, response_time=None,
         exported_to_word=False) -> int:
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO chat_history (user_id, username, question, answer, mode, "
            "selected_document_id, sources_json, response_time, exported_to_word) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (user_id, username, question, answer, mode, selected_document_id,
             json.dumps(sources or [], ensure_ascii=False), response_time,
             int(exported_to_word)),
        )
        return cur.lastrowid


def mark_exported(row_id: int) -> None:
    with db.get_conn() as conn:
        conn.execute("UPDATE chat_history SET exported_to_word = 1 WHERE id = ?",
                     (row_id,))


def recent(username: str | None = None, limit: int = 50):
    sql = "SELECT * FROM chat_history"
    params = []
    if username:
        sql += " WHERE username = ?"; params.append(username)
    sql += " ORDER BY id DESC LIMIT ?"; params.append(limit)
    with db.get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def count_for_user(username: str) -> int:
    with db.get_conn() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM chat_history WHERE username = ?",
                            (username,)).fetchone()["c"]
