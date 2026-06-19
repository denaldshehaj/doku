"""Audit logging. Records every important action with user, action, details."""
from modules import database as db

# Known action names (for reference / consistency).
ACTIONS = (
    "login_success", "login_failed", "logout",
    "upload_document", "update_document_metadata", "delete_document",
    "activate_document", "deactivate_document",
    "reindex_document", "reindex_all_documents",
    "ask_question", "generate_summary",
    "export_answer_docx", "export_summary_docx",
    "create_user", "run_experiment", "password_change",
)


def log(user_id, username: str, action: str, details: str = "") -> None:
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_logs (user_id, username, action, details) "
            "VALUES (?, ?, ?, ?)",
            (user_id, username, action, details),
        )


def recent(limit: int = 300):
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT user_id, username, action, details, created_at "
            "FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,),
        ).fetchall()
