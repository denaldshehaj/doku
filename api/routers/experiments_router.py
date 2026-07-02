"""RAG vs no-RAG experiment harness (admin-only): batch runs as a background
task with real progress, manual scoring, aggregate metrics, CSV export."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from api import deps, schemas, tasks
from modules import audit, database as db, experiments

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


def _row_out(r) -> dict:
    return {
        "id": r["id"], "question": r["question"],
        "answer_without_rag": r["answer_without_rag"],
        "answer_with_rag": r["answer_with_rag"],
        "time_without_rag": r["time_without_rag"],
        "time_with_rag": r["time_with_rag"],
        "chunks_used": r["chunks_used"], "has_sources": bool(r["has_sources"]),
        "manual_accuracy_without_rag": r["manual_accuracy_without_rag"],
        "manual_accuracy_with_rag": r["manual_accuracy_with_rag"],
        "hallucination_without_rag": r["hallucination_without_rag"],
        "hallucination_with_rag": r["hallucination_with_rag"],
        "notes": r["notes"], "created_at": r["created_at"],
    }


@router.get("", response_model=list[schemas.ExperimentRowOut])
def list_results(limit: int = Query(default=500, ge=1, le=5000),
                 admin=Depends(deps.require_admin)):
    return [_row_out(r) for r in experiments.list_results(limit=limit)]


@router.get("/samples")
def sample_questions(admin=Depends(deps.require_admin)):
    return {"questions": experiments.load_sample_questions(),
            "avg_run_seconds": round(experiments.avg_run_seconds(), 1)}


@router.get("/summary")
def summary(admin=Depends(deps.require_admin)):
    """Aggregates over all runs — fuels the metric cards and the thesis table."""
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total, "
            "AVG(time_without_rag) AS avg_t_no, AVG(time_with_rag) AS avg_t_rag, "
            "AVG(manual_accuracy_without_rag) AS avg_acc_no, "
            "AVG(manual_accuracy_with_rag) AS avg_acc_rag, "
            "AVG(CASE hallucination_without_rag WHEN 'Po' THEN 1.0 WHEN 'Jo' THEN 0.0 END) AS hall_no, "
            "AVG(CASE hallucination_with_rag WHEN 'Po' THEN 1.0 WHEN 'Jo' THEN 0.0 END) AS hall_rag, "
            "AVG(CASE WHEN has_sources THEN 1.0 ELSE 0.0 END) AS with_sources "
            "FROM experiment_results").fetchone()
    rnd = lambda v, n=2: round(v, n) if v is not None else None  # noqa: E731
    return {
        "total": row["total"],
        "avg_time_without_rag": rnd(row["avg_t_no"]),
        "avg_time_with_rag": rnd(row["avg_t_rag"]),
        "avg_accuracy_without_rag": rnd(row["avg_acc_no"]),
        "avg_accuracy_with_rag": rnd(row["avg_acc_rag"]),
        "hallucination_rate_without_rag": rnd(row["hall_no"], 3),
        "hallucination_rate_with_rag": rnd(row["hall_rag"], 3),
        "with_sources_rate": rnd(row["with_sources"], 3),
    }


@router.post("/run", response_model=schemas.TaskOut)
def run(body: schemas.ExperimentRunIn, admin=Depends(deps.require_admin)):
    questions = [q.strip() for q in body.questions if q.strip()]
    if not questions:
        raise HTTPException(status_code=400, detail="Nuk ka pyetje për të ekzekutuar.")
    if tasks.any_running("experiment"):
        raise HTTPException(status_code=409, detail="Një eksperiment është tashmë në ekzekutim.")
    uid, uname = admin["id"], admin["username"]

    def job(task):
        done, failed = 0, []
        n = len(questions)
        for i, q in enumerate(questions):
            task.update(progress=i / n, message=f"Pyetja {i + 1}/{n}: {q[:70]}")
            try:
                with deps.LLM_LOCK:
                    experiments.run_one(q)
                done += 1
            except Exception as exc:  # noqa: BLE001 — reported per-question
                failed.append({"question": q, "error": str(exc)[:200]})
        audit.log(uid, uname, "run_experiment", f"{done} pyetje")
        return {"done": done, "failed": failed}

    return tasks.start("experiment-batch", job).to_dict()


@router.patch("/{row_id}", response_model=schemas.ExperimentRowOut)
def patch(row_id: int, body: schemas.ExperimentPatchIn,
          admin=Depends(deps.require_admin)):
    experiments.update_manual_eval(
        row_id,
        acc_no_rag=body.manual_accuracy_without_rag,
        acc_rag=body.manual_accuracy_with_rag,
        hall_no_rag=body.hallucination_without_rag,
        hall_rag=body.hallucination_with_rag,
        notes=body.notes)
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM experiment_results WHERE id = ?",
                           (row_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Rezultati nuk u gjet.")
    return _row_out(row)


@router.delete("/{row_id}")
def delete(row_id: int, admin=Depends(deps.require_admin)):
    experiments.delete_result(row_id)
    return {"ok": True}


@router.get("/export.csv")
def export_csv(admin=Depends(deps.require_admin)):
    path = experiments.export_csv()
    filename = path.replace("\\", "/").rsplit("/", 1)[-1]
    return FileResponse(path, media_type="text/csv", filename=filename)
