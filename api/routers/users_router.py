"""User management (admin-only). Mirrors the Streamlit page, including the
last-active-admin lockout guard, enforced here in the API — not in the UI."""
from fastapi import APIRouter, Depends, HTTPException

from api import deps, schemas
from modules import audit, auth

router = APIRouter(prefix="/api/users", tags=["users"],
                   dependencies=[Depends(deps.require_admin)])


def _row_out(u) -> dict:
    return {"id": u["id"], "username": u["username"],
            "full_name": u["full_name"] or "", "role": u["role"],
            "is_active": bool(u["is_active"]), "created_at": u["created_at"] or ""}


def _get_or_404(username: str):
    u = auth.get_user(username)
    if u is None:
        raise HTTPException(status_code=404, detail="Përdoruesi nuk u gjet.")
    return u


def _other_active_admins(username: str) -> int:
    return sum(1 for u in auth.list_users()
               if u["role"] == auth.ADMIN and u["is_active"]
               and u["username"] != username)


@router.get("", response_model=list[schemas.UserRowOut])
def list_users():
    return [_row_out(u) for u in auth.list_users()]


@router.post("", response_model=schemas.UserRowOut, status_code=201)
def create_user(body: schemas.UserCreateIn, admin=Depends(deps.require_admin)):
    try:
        auth.create_user(body.username, body.password, body.full_name,
                         body.role, must_change=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    audit.log(admin["id"], admin["username"], "create_user",
              f"{body.username} ({body.role})")
    return _row_out(auth.get_user(body.username))


@router.patch("/{username}", response_model=schemas.UserRowOut)
def patch_user(username: str, body: schemas.UserPatchIn,
               admin=Depends(deps.require_admin)):
    cur = _get_or_404(username)

    # Block any change that would leave the system without one active admin.
    new_role = body.role if body.role is not None else cur["role"]
    new_active = body.is_active if body.is_active is not None else bool(cur["is_active"])
    was_effective_admin = cur["role"] == auth.ADMIN and cur["is_active"]
    if was_effective_admin and (new_role != auth.ADMIN or not new_active) \
            and _other_active_admins(username) == 0:
        raise HTTPException(status_code=409,
                            detail="Sistemi do të mbetej pa asnjë administrator aktiv.")

    if body.full_name is not None and body.full_name.strip() != (cur["full_name"] or ""):
        auth.set_full_name(username, body.full_name)
    if body.role is not None and body.role != cur["role"]:
        try:
            auth.set_role(username, body.role)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        audit.log(admin["id"], admin["username"], "set_role", f"{username} -> {body.role}")
    if body.is_active is not None and bool(body.is_active) != bool(cur["is_active"]):
        auth.set_active(username, body.is_active)
        audit.log(admin["id"], admin["username"], "set_active",
                  f"{username}={body.is_active}")
    return _row_out(auth.get_user(username))


@router.post("/{username}/password")
def set_password(username: str, body: schemas.SetPasswordIn,
                 admin=Depends(deps.require_admin)):
    _get_or_404(username)
    try:
        auth.set_password(username, body.password, must_change=body.must_change)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    audit.log(admin["id"], admin["username"], "set_password", username)
    return {"ok": True}


@router.post("/{username}/reset-password")
def reset_password(username: str, admin=Depends(deps.require_admin)):
    _get_or_404(username)
    temp = auth.reset_password(username)
    audit.log(admin["id"], admin["username"], "reset_password", username)
    # Returned once so the admin can hand it over; forced change on first login.
    return {"temporary_password": temp}
