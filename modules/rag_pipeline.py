"""RAG pipeline — the heart of DOKU's grounding contract.

retrieve top-k  ->  REFUSAL GATE (similarity threshold)  ->  grounded prompt
with cited sources  ->  local LLM  ->  cited answer. The refusal gate runs BEFORE
the LLM: if nothing relevant is retrieved, we refuse without calling the model,
so fabrication is structurally impossible for out-of-corpus questions.

Documents are filtered to active ones (or a specific document chosen by the user).
"""
import time
from dataclasses import dataclass, field

import config
from modules import llm_client, vector_store as vs

SYSTEM_PROMPT = (
    "Ti je një asistent inteligjent për analizë dokumentesh institucionale në "
    "gjuhën shqipe. Përgjigju vetëm duke u bazuar në kontekstin e dhënë. Nëse "
    "konteksti nuk e përmban përgjigjen, thuaj qartë që informacioni nuk gjendet "
    "në dokumentet e ngarkuara. Mos shpik informacion. Jep përgjigje të "
    "strukturuar dhe profesionale, në gjuhë shqipe të saktë dhe gramatikisht "
    "korrekte. Kur dokumenti është ligjor ose normativ, sqaro që përgjigjja është "
    "ndihmëse dhe dokumenti origjinal mbetet burimi zyrtar."
)

_USER_PROMPT = ("Konteksti:\n{context}\n\nPyetja: {question}\n\n"
                "Përgjigju në mënyrë të plotë e të strukturuar, vetëm nga konteksti "
                "më sipër:")

LEGAL_NOTE = ("\n\n*Shënim: Kjo përgjigje është ndihmëse dhe e gjeneruar "
              "automatikisht; dokumenti origjinal mbetet burimi zyrtar.*")

SUMMARY_FORMATS = {
    "E shkurtër": "Shkruaj një përmbledhje të shkurtër prej 3-4 fjalish.",
    "E detajuar": "Shkruaj një përmbledhje të detajuar dhe gjithëpërfshirëse.",
    "Pika kryesore": "Shkruaj përmbledhjen si listë me pikat kryesore.",
    "Për vendimmarrje institucionale": (
        "Shkruaj një përmbledhje të orientuar drejt vendimmarrjes institucionale, "
        "me titujt: Qëllimi, Detyrimet/Implikimet kryesore, Rekomandime."),
}


@dataclass
class Answer:
    text: str
    refused: bool
    sources: list = field(default_factory=list)   # list of dicts for citations
    retrieved: list = field(default_factory=list)
    top_score: float = 0.0
    response_time: float = 0.0
    chunks_used: int = 0


def _format_context(chunks) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        blocks.append(f"[{i}] (Dokumenti: {c.title}, {c.document_type}, "
                      f"{c.institution}, faqe {c.page_number})\n{c.text}")
    return "\n\n".join(blocks)


def _sources(chunks) -> list[dict]:
    out = []
    for i, c in enumerate(chunks, start=1):
        fragment = c.text.strip().replace("\n", " ")
        out.append({
            "n": i, "filename": c.filename, "title": c.title,
            "document_type": c.document_type, "institution": c.institution,
            "page": c.page_number, "score": round(c.score, 3),
            "fragment": (fragment[:160] + "…") if len(fragment) > 160 else fragment,
        })
    return out


def answer_question(question: str, mode="rag", selected_document_id=None,
                    active_doc_ids=None, k=None) -> Answer:
    t0 = time.perf_counter()
    chunks = vs.query(question, k=k, active_doc_ids=active_doc_ids,
                      document_id=selected_document_id)
    top = chunks[0].score if chunks else 0.0

    # --- REFUSAL GATE ---
    if not chunks or top < config.MIN_SIMILARITY:
        return Answer(config.REFUSAL_MESSAGE, refused=True, retrieved=chunks,
                      top_score=top, response_time=round(time.perf_counter() - t0, 3))

    relevant = [c for c in chunks if c.score >= config.MIN_SIMILARITY] or chunks[:1]
    prompt = _USER_PROMPT.format(context=_format_context(relevant), question=question)
    text = llm_client.generate(prompt, system=SYSTEM_PROMPT)

    refused = config.REFUSAL_MESSAGE[:30].lower() in text.lower() \
        or "nuk gjendet" in text.lower()
    if not refused and any(c.document_type in config.NORMATIVE_TYPES for c in relevant):
        text += LEGAL_NOTE

    return Answer(
        text, refused=refused,
        sources=[] if refused else _sources(relevant),
        retrieved=relevant, top_score=top,
        response_time=round(time.perf_counter() - t0, 3),
        chunks_used=0 if refused else len(relevant),
    )


def answer_question_stream(question: str, mode="rag", selected_document_id=None,
                           active_doc_ids=None, k=None):
    """Streaming twin of answer_question with the identical grounding contract:
    the refusal gate still runs BEFORE the LLM. Yields tuples:

        ("refusal", Answer)  — gate refused; nothing was generated
        ("delta", str)       — next generated text fragment
        ("final", Answer)    — complete Answer (same fields as answer_question)
    """
    t0 = time.perf_counter()
    chunks = vs.query(question, k=k, active_doc_ids=active_doc_ids,
                      document_id=selected_document_id)
    top = chunks[0].score if chunks else 0.0

    # --- REFUSAL GATE (identical to the non-streaming path) ---
    if not chunks or top < config.MIN_SIMILARITY:
        yield ("refusal", Answer(config.REFUSAL_MESSAGE, refused=True,
                                 retrieved=chunks, top_score=top,
                                 response_time=round(time.perf_counter() - t0, 3)))
        return

    relevant = [c for c in chunks if c.score >= config.MIN_SIMILARITY] or chunks[:1]
    prompt = _USER_PROMPT.format(context=_format_context(relevant), question=question)

    parts: list[str] = []
    for piece in llm_client.generate_stream(prompt, system=SYSTEM_PROMPT):
        parts.append(piece)
        yield ("delta", piece)
    text = "".join(parts).strip()

    refused = config.REFUSAL_MESSAGE[:30].lower() in text.lower() \
        or "nuk gjendet" in text.lower()
    if not refused and any(c.document_type in config.NORMATIVE_TYPES for c in relevant):
        text += LEGAL_NOTE

    yield ("final", Answer(
        text, refused=refused,
        sources=[] if refused else _sources(relevant),
        retrieved=relevant, top_score=top,
        response_time=round(time.perf_counter() - t0, 3),
        chunks_used=0 if refused else len(relevant),
    ))


def answer_without_rag(question: str) -> tuple[str, float]:
    """Bare LLM answer (no retrieval) — used by the experiment module."""
    t0 = time.perf_counter()
    system = ("Ti je një asistent i përgjithshëm. Përgjigju shkurt në gjuhën shqipe. "
              "(Pa qasje në dokumente.)")
    text = llm_client.generate(question, system=system)
    return text, round(time.perf_counter() - t0, 3)


def summarize(text: str, fmt="E shkurtër", max_chars=8000) -> str:
    instruction = SUMMARY_FORMATS.get(fmt, SUMMARY_FORMATS["E shkurtër"])
    system = ("Ti je një asistent që përmbledh dokumente zyrtare në gjuhën shqipe. "
              "Përmbledh VETËM përmbajtjen e dhënë, pa shtuar informacion nga jashtë.")
    prompt = f"{instruction}\n\nDokumenti:\n{text.strip()[:max_chars]}\n\nPërmbledhja:"
    return llm_client.generate(prompt, system=system)
