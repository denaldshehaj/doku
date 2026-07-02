"""Auth endpoints: login/logout, current user, forced password change.
Session token lives in an httpOnly cookie (never in the URL)."""
import threading
import time

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response

from api import deps, schemas
from modules import audit, auth

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 12h sliding TTL matches auth.SESSION_TTL_HOURS; cookie max_age slightly longer
# so the server-side expiry (the authoritative one) always wins.
_COOKIE_MAX_AGE = (auth.SESSION_TTL_HOURS + 1) * 3600

# --- Login throttling (in-memory; the server is single-process) --------------
# Stops online brute force against the bcrypt hashes: after MAX_FAILURES failed
# attempts for the same username inside WINDOW seconds, login answers 429.
_MAX_FAILURES = 5
_FAILURE_WINDOW_S = 15 * 60
_failures: dict[str, list[float]] = {}
_failures_lock = threading.Lock()


def _throttled(username: str) -> bool:
    now = time.monotonic()
    with _failures_lock:
        recent = [t for t in _failures.get(username, []) if now - t < _FAILURE_WINDOW_S]
        _failures[username] = recent
        return len(recent) >= _MAX_FAILURES


def _record_failure(username: str) -> None:
    with _failures_lock:
        _failures.setdefault(username, []).append(time.monotonic())


def _clear_failures(username: str) -> None:
    with _failures_lock:
        _failures.pop(username, None)


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        deps.COOKIE_NAME, token, max_age=_COOKIE_MAX_AGE, httponly=True,
        samesite="lax", secure=False, path="/",  # local HTTP only (127.0.0.1)
    )


@router.post("/login", response_model=schemas.UserOut)
def login(body: schemas.LoginIn, response: Response):
    username = body.username.strip()
    if _throttled(username):
        audit.log(None, username or "?", "login_throttled")
        raise HTTPException(status_code=429, detail=(
            "Shumë përpjekje të dështuara. Prit 15 minuta ose kontakto administratorin."))
    user = auth.authenticate(username, body.password)
    if user is None:
        _record_failure(username)
        audit.log(None, username or "?", "login_failed")
        raise HTTPException(status_code=401,
                            detail="Kredenciale të pasakta ose llogari joaktive.")
    _clear_failures(username)
    token = auth.create_session(user["id"], user["username"])
    _set_cookie(response, token)
    audit.log(user["id"], user["username"], "login_success")
    return deps.user_dict(user)


@router.post("/logout")
def logout(response: Response,
           user=Depends(deps.get_session_user),
           doku_sid: str | None = Cookie(default=None)):
    audit.log(user["id"], user["username"], "logout")
    auth.delete_session(doku_sid or "")
    response.delete_cookie(deps.COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=schemas.UserOut | None)
def me(user=Depends(deps.get_optional_user)):
    """200 with the user, or 200/null when unauthenticated — the initial
    session probe on app load must not produce console-level 401 errors."""
    return deps.user_dict(user) if user is not None else None


@router.post("/change-password", response_model=schemas.UserOut)
def change_password(body: schemas.ChangePasswordIn,
                    user=Depends(deps.get_session_user)):
    try:
        auth.set_password(user["username"], body.new_password, must_change=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    audit.log(user["id"], user["username"], "password_change")
    return deps.user_dict(auth.get_user(user["username"]))
