"""Authentication & role management. Passwords are hashed with bcrypt directly
(passlib is unmaintained and breaks with bcrypt>=5); plaintext is never stored
(CLAUDE.md rule 5)."""
import re

import bcrypt

from doku import db

ADMIN = "admin"
EMPLOYEE = "employee"
ROLES = (ADMIN, EMPLOYEE)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,32}$")
MIN_PASSWORD_LEN = 6


def hash_password(password: str) -> str:
    # bcrypt limits input to 72 bytes; truncate explicitly.
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_user(username: str, password: str, role: str, must_change: bool = False) -> None:
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")
    username = username.strip()
    if not username or not password:
        raise ValueError("Username and password are required")
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, must_change_password) "
            "VALUES (?, ?, ?, ?)",
            (username, hash_password(password), role, int(must_change)),
        )


def set_password(username: str, new_password: str) -> None:
    """Update a user's password and clear the must-change flag."""
    if not new_password or len(new_password) < 6:
        raise ValueError("Fjalëkalimi duhet të ketë të paktën 6 karaktere.")
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 0 "
            "WHERE username = ?",
            (hash_password(new_password), username.strip()),
        )


def needs_password_change(username: str) -> bool:
    row = get_user(username)
    return bool(row) and bool(row["must_change_password"])


def get_user(username: str):
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
    return row


def authenticate(username: str, password: str):
    """Return the user row on success, else None."""
    row = get_user(username)
    if row is None:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return row


def is_admin(user) -> bool:
    return user is not None and user["role"] == ADMIN


def list_users():
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY username"
        ).fetchall()


def user_count() -> int:
    with db.get_conn() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]


def has_admin() -> bool:
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE role = ? LIMIT 1", (ADMIN,)
        ).fetchone()
    return row is not None


def register(username: str, password: str, confirm: str) -> str:
    """Self-registration with validation. The first account (when no admin exists)
    becomes admin to bootstrap the system; later accounts are employees.
    Returns the assigned role. Raises ValueError on invalid input."""
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        raise ValueError(
            "Përdoruesi duhet të jetë 3–32 karaktere (shkronja, numra, '_' ose '.')."
        )
    if get_user(username) is not None:
        raise ValueError("Ky përdorues ekziston tashmë. Zgjidh një emër tjetër.")
    if not password or len(password) < MIN_PASSWORD_LEN:
        raise ValueError(
            f"Fjalëkalimi duhet të ketë të paktën {MIN_PASSWORD_LEN} karaktere."
        )
    if password != confirm:
        raise ValueError("Fjalëkalimet nuk përputhen.")
    role = ADMIN if not has_admin() else EMPLOYEE
    create_user(username, password, role, must_change=False)
    return role
