"""Experiment module: run the same question through the RAG pipeline and through
the bare LLM (no retrieval), persist both, and expose history. This is a built,
demoable feature contrasting grounded vs ungrounded answers."""
from dataclasses import dataclass

import config
from doku import db, llm, rag


@dataclass
class ExperimentResult:
    question: str
    rag_answer: str
    rag_refused: bool
    norag_answer: str
    citations: list


_NORAG_SYSTEM = (
    "Ti je një asistent i përgjithshëm. Përgjigju shkurt në gjuhën shqipe. "
    "(Pa qasje në dokumente.)"
)


def run(username: str, question: str) -> ExperimentResult:
    rag_ans = rag.answer_question(question)
    try:
        norag = llm.generate(question, system=_NORAG_SYSTEM)
    except Exception as exc:
        norag = f"Shërbimi i modelit lokal nuk është i disponueshëm: {exc}"

    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO experiments (username, question, rag_answer, norag_answer, "
            "rag_refused) VALUES (?, ?, ?, ?, ?)",
            (username, question, rag_ans.text, norag, int(rag_ans.refused)),
        )
    return ExperimentResult(
        question=question,
        rag_answer=rag_ans.text,
        rag_refused=rag_ans.refused,
        norag_answer=norag,
        citations=rag_ans.citations,
    )


def history(limit: int = 50):
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT question, rag_answer, norag_answer, rag_refused, ts "
            "FROM experiments ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
