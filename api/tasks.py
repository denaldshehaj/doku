"""In-memory registry for long-running admin operations (reindex-all, experiment
batches). Streamlit could block a page for minutes; an HTTP API cannot, so these
run in a daemon thread and the frontend polls GET /api/tasks/{id}.

Single-process by design (uvicorn runs one worker), so a plain dict + lock is
enough — no broker, no external queue, consistent with the local-only stack.
"""
import threading
import uuid
from dataclasses import dataclass, field


@dataclass
class Task:
    id: str
    name: str
    status: str = "running"           # running | done | error
    progress: float = 0.0             # 0..1 (best effort)
    message: str = ""
    result: dict | None = None
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update(self, progress: float | None = None, message: str | None = None):
        with self._lock:
            if progress is not None:
                self.progress = max(0.0, min(1.0, progress))
            if message is not None:
                self.message = message

    def to_dict(self) -> dict:
        with self._lock:
            return {"id": self.id, "name": self.name, "status": self.status,
                    "progress": round(self.progress, 4), "message": self.message,
                    "result": self.result, "error": self.error}


_tasks: dict[str, Task] = {}
_registry_lock = threading.Lock()
_MAX_KEPT = 50


def start(name: str, fn) -> Task:
    """Run `fn(task)` in a daemon thread; fn updates task.progress/message and
    returns a dict result. Returns the Task immediately."""
    task = Task(id=uuid.uuid4().hex, name=name)
    with _registry_lock:
        # Drop oldest finished tasks so the registry cannot grow unbounded.
        if len(_tasks) >= _MAX_KEPT:
            for tid in [t.id for t in _tasks.values() if t.status != "running"][: len(_tasks) - _MAX_KEPT + 1]:
                _tasks.pop(tid, None)
        _tasks[task.id] = task

    def worker():
        try:
            result = fn(task)
            with task._lock:
                task.result = result or {}
                task.progress = 1.0
                task.status = "done"
        except Exception as exc:  # noqa: BLE001 — surfaced to the polling client
            with task._lock:
                task.error = str(exc)
                task.status = "error"

    threading.Thread(target=worker, daemon=True).start()
    return task


def get(task_id: str) -> Task | None:
    with _registry_lock:
        return _tasks.get(task_id)


def any_running(name_prefix: str = "") -> bool:
    with _registry_lock:
        return any(t.status == "running" and t.name.startswith(name_prefix)
                   for t in _tasks.values())
