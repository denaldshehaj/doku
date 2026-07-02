"""Shared FastAPI dependencies: cookie-based sessions and role guards.

Reuses the existing `sessions` table via modules.auth — the API equivalent of
ui.current_user()/ui.require_admin(). The session token travels in an httpOnly
cookie instead of the URL, so it never appears in browser history or logs.
"""
import threading

from fastapi import Cookie, Depends, HTTPException

from modules import auth

COOKIE_NAME = "doku_sid"

# Only one LLM generation at a time: the local GPU (4GB VRAM) cannot hold two
# concurrent gemma2/qwen generations, and parallel calls would OOM Ollama.
LLM_LOCK = threading.Semaphore(1)


def user_dict(row) -> dict:
    """Public view of a users row (never expose password_hash)."""
    return {
        "id": row["id"],
        "username": row["username"],
        "full_name": row["full_name"] or "",
        "role": row["role"],
        "must_change_password": bool(row["must_change_password"]),
    }


def get_optional_user(doku_sid: str | None = Cookie(default=None)):
    """Resolve the session cookie to a live users row, or None when there is
    no valid session. Lets GET /api/auth/me answer 200/null on first load
    instead of a 401 that pollutes the browser console."""
    return auth.resolve_session(doku_sid or "")


def get_session_user(doku_sid: str | None = Cookie(default=None)):
    """Resolve the session cookie to a live users row (sliding expiry).
    Used directly only by auth endpoints, which must work even while a
    password change is still pending."""
    row = auth.resolve_session(doku_sid or "")
    if row is None:
        raise HTTPException(status_code=401, detail="Sesioni mungon ose ka skaduar. Hyni përsëri.")
    return row


def require_user(row=Depends(get_session_user)):
    """Any authenticated user whose forced password change is complete."""
    if row["must_change_password"]:
        raise HTTPException(
            status_code=403,
            detail={"code": "password_change_required",
                    "message": "Fjalëkalimi i parazgjedhur duhet ndryshuar përpara përdorimit."},
        )
    return row


def require_admin(row=Depends(require_user)):
    if row["role"] != auth.ADMIN:
        raise HTTPException(status_code=403, detail="Vetëm administratori ka akses në këtë veprim.")
    return row
