"""Authentication & role management. Passwords hashed with bcrypt (never plain
text). Two roles: admin / punonjes. A default admin is auto-created if none
exists, and is flagged to change its password on first login."""
import re

import bcrypt

import config
from modules import database as db

ADMIN = "admin"
PUNONJES = "punonjes"
ROLES = (ADMIN, PUNONJES)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,32}$")
MIN_PASSWORD_LEN = 6


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def get_user(username: str):
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()


def has_admin() -> bool:
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM users WHERE role = ? LIMIT 1", (ADMIN,)
        ).fetchone() is not None


def create_user(username: str, password: str, full_name: str, role: str,
                must_change: bool = False) -> None:
    """Validate and create a user. Raises ValueError on invalid input."""
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        raise ValueError("Përdoruesi duhet 3–32 karaktere (shkronja, numra, '_' ose '.').")
    if role not in ROLES:
        raise ValueError("Rol i pavlefshëm.")
    if not password or len(password) < MIN_PASSWORD_LEN:
        raise ValueError(f"Fjalëkalimi duhet të paktën {MIN_PASSWORD_LEN} karaktere.")
    if get_user(username) is not None:
        raise ValueError("Ky përdorues ekziston tashmë.")
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role, "
            "must_change_password) VALUES (?, ?, ?, ?, ?)",
            (username, hash_password(password), (full_name or "").strip(), role,
             int(must_change)),
        )


def ensure_default_admin() -> None:
    """Create the default admin (flagged to change password) if no admin exists."""
    if not has_admin():
        create_user(config.DEFAULT_ADMIN_USERNAME, config.DEFAULT_ADMIN_PASSWORD,
                    "Administratori", ADMIN, must_change=True)


def authenticate(username: str, password: str):
    row = get_user(username)
    if row is None or not row["is_active"]:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return row


def set_password(username: str, new_password: str) -> None:
    if not new_password or len(new_password) < MIN_PASSWORD_LEN:
        raise ValueError(f"Fjalëkalimi duhet të paktën {MIN_PASSWORD_LEN} karaktere.")
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 0, "
            "updated_at = datetime('now') WHERE username = ?",
            (hash_password(new_password), username.strip()),
        )


def needs_password_change(username: str) -> bool:
    row = get_user(username)
    return bool(row) and bool(row["must_change_password"])


def list_users():
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT id, username, full_name, role, is_active, created_at "
            "FROM users ORDER BY username"
        ).fetchall()


def set_active(username: str, active: bool) -> None:
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET is_active = ?, updated_at = datetime('now') "
            "WHERE username = ?", (int(active), username.strip()),
        )


def user_count() -> int:
    with db.get_conn() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
