"""Experiment module: run the same questions through the bare LLM (no RAG) and
through the RAG pipeline, measure timing / chunks / sources, persist to SQLite,
allow manual scoring (accuracy 1-5, hallucination yes/no, notes), and export the
comparison table to CSV for the thesis Results chapter."""
import csv
from datetime import datetime
from pathlib import Path

import config
from modules import database as db, documents, rag_pipeline as rag

SAMPLE_QUESTIONS = Path(__file__).resolve().parent.parent / "tests" / "sample_questions.csv"


def load_sample_questions() -> list[str]:
    if not SAMPLE_QUESTIONS.exists():
        return []
    with open(SAMPLE_QUESTIONS, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row["question"].strip() for row in reader if row.get("question", "").strip()]


def run_one(question: str) -> int:
    """Run a single question both ways and persist. Returns the new row id."""
    active = documents.active_document_ids()
    no_rag_text, t_no = rag.answer_without_rag(question)
    rag_ans = rag.answer_question(question, mode="rag", active_doc_ids=active)

    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO experiment_results (question, answer_without_rag, "
            "answer_with_rag, time_without_rag, time_with_rag, chunks_used, "
            "has_sources) VALUES (?,?,?,?,?,?,?)",
            (question, no_rag_text, rag_ans.text, t_no, rag_ans.response_time,
             rag_ans.chunks_used, int(bool(rag_ans.sources))),
        )
        return cur.lastrowid


def run_batch(questions: list[str]) -> list[int]:
    return [run_one(q) for q in questions if q.strip()]


def avg_run_seconds(default: float = 90.0) -> float:
    """Average wall-clock seconds a single question takes (no-RAG + RAG), from
    past runs. Used to drive the UI progress estimate; falls back to `default`
    when there is no history yet."""
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT AVG(COALESCE(time_without_rag,0)+COALESCE(time_with_rag,0)) AS a "
            "FROM experiment_results WHERE time_with_rag IS NOT NULL"
        ).fetchone()
    return float(row["a"]) if row and row["a"] else default


def list_results(limit: int = 500):
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT * FROM experiment_results ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def update_manual_eval(row_id: int, acc_no_rag=None, acc_rag=None,
                       hall_no_rag=None, hall_rag=None, notes=None):
    cols, vals = [], []
    for col, val in (("manual_accuracy_without_rag", acc_no_rag),
                     ("manual_accuracy_with_rag", acc_rag),
                     ("hallucination_without_rag", hall_no_rag),
                     ("hallucination_with_rag", hall_rag),
                     ("notes", notes)):
        if val is not None:
            cols.append(f"{col} = ?"); vals.append(val)
    if not cols:
        return
    vals.append(row_id)
    with db.get_conn() as conn:
        conn.execute(f"UPDATE experiment_results SET {', '.join(cols)} WHERE id = ?", vals)


def delete_result(row_id: int):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM experiment_results WHERE id = ?", (row_id,))


_CSV_FIELDS = [
    "id", "question", "answer_without_rag", "answer_with_rag", "time_without_rag",
    "time_with_rag", "chunks_used", "has_sources", "manual_accuracy_without_rag",
    "manual_accuracy_with_rag", "hallucination_without_rag", "hallucination_with_rag",
    "notes", "created_at",
]


def export_csv() -> str:
    rows = list_results(limit=100000)
    out = config.EXPORTS_DIR / f"experiments_{datetime.now():%Y%m%d_%H%M%S}.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r[k] for k in _CSV_FIELDS})
    return str(out)
