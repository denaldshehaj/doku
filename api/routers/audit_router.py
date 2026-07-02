"""Audit log (admin-only, read-only)."""
from fastapi import APIRouter, Depends, Query

from api import deps, schemas
from modules import audit

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[schemas.AuditRowOut])
def recent(limit: int = Query(default=500, ge=1, le=2000),
           admin=Depends(deps.require_admin)):
    return [{"username": r["username"], "action": r["action"],
             "details": r["details"], "created_at": r["created_at"]}
            for r in audit.recent(limit=limit)]
