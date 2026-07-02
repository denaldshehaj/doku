"""Polling endpoint for long-running admin tasks (reindex-all, experiments)."""
from fastapi import APIRouter, Depends, HTTPException

from api import deps, schemas, tasks

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: str, admin=Depends(deps.require_admin)):
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task-u nuk u gjet.")
    return task.to_dict()
