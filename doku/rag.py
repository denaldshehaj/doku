"""The RAG pipeline — the heart of DOKU's "never hallucinate" contract.

Flow:  retrieve top-k  ->  REFUSAL GATE (similarity threshold)  ->  grounded
prompt with cited sources  ->  local LLM  ->  cited answer.

The refusal gate runs BEFORE the LLM: if nothing is retrieved or the best chunk
scores below config.MIN_SIMILARITY, we refuse without ever calling the model.
This makes fabrication structurally impossible for out-of-corpus questions.
"""
from dataclasses import dataclass, field

import config
from doku import llm, vectorstore

SYSTEM_PROMPT = (
    "Ti je një asistent që analizon dokumente zyrtare në gjuhën shqipe. "
    "Përgjigju VETËM duke u bazuar te burimet e dhëna nga përdoruesi. "
    "Mos shto asnjë informacion nga njohuritë e tua të jashtme. "
    "Jep një përgjigje TË PLOTË dhe të strukturuar: përfshi të gjithë "
    "informacionin përkatës që gjendet në burime, duke përmendur detaje si "
    "afate, shifra, kushte ose nene kur ekzistojnë. "
    "Cito çdo pohim me numrin e burimit në kllapa katrore, p.sh. [1]. "
    "Nëse burimet nuk përmbajnë informacion të mjaftueshëm për pyetjen, "
    f"përgjigju saktësisht me fjalinë: \"{config.REFUSAL_MESSAGE}\" "
    "Përgjigju gjithmonë në gjuhë shqipe të saktë, të rrjedhshme dhe gramatikisht "
    "korrekte, me fjali të plota e të qarta."
)

_PROMPT = (
    "Burimet:\n{context}\n\n"
    "Pyetja: {question}\n\n"
    "Përgjigju në mënyrë të plotë dhe të qartë, duke përdorur të gjithë "
    "informacionin përkatës nga burimet më sipër, me citime [n]:"
)

_SUMMARY_FORMATS = {
    "I shkurtër": "Shkruaj një përmbledhje të shkurtër prej 3-4 fjalish.",
    "Pika kryesore": "Shkruaj përmbledhjen si listë me pika kryesore.",
    "Ekzekutive": "Shkruaj një përmbledhje ekzekutive të strukturuar me titujt: "
                  "Qëllimi, Pikat kryesore, Përfundimi.",
}


@dataclass
class Answer:
    text: str
    refused: bool
    citations: list = field(default_factory=list)
    retrieved: list = field(default_factory=list)
    top_score: float = 0.0


def _format_context(chunks) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        blocks.append(f"[{i}] (Dokumenti: {c.title}, faqe {c.page})\n{c.text}")
    return "\n\n".join(blocks)


def _citations(chunks) -> list[dict]:
    return [
        {
            "n": i,
            "title": c.title,
            "filename": c.filename,
            "page": c.page,
            "score": round(c.score, 3),
        }
        for i, c in enumerate(chunks, start=1)
    ]


def answer_question(question: str, k: int | None = None, where: dict | None = None) -> Answer:
    chunks = vectorstore.query(question, k=k, where=where)
    top = chunks[0].score if chunks else 0.0

    # --- REFUSAL GATE: enforce grounding before touching the LLM ---
    if not chunks or top < config.MIN_SIMILARITY:
        return Answer(config.REFUSAL_MESSAGE, refused=True, retrieved=chunks, top_score=top)

    # Keep only relevant chunks in the context so off-topic documents (when the
    # filter is "all documents") do not dilute or shorten the answer.
    relevant = [c for c in chunks if c.score >= config.MIN_SIMILARITY] or chunks[:1]

    prompt = _PROMPT.format(context=_format_context(relevant), question=question)
    try:
        text = llm.generate(prompt, system=SYSTEM_PROMPT)
    except Exception as exc:
        return Answer(
            f"Shërbimi i modelit lokal (Ollama) nuk është i disponueshëm: {exc}",
            refused=False, retrieved=relevant, top_score=top,
        )

    refused = config.REFUSAL_MESSAGE.rstrip(".").lower() in text.lower()
    citations = [] if refused else _citations(relevant)
    return Answer(text, refused=refused, citations=citations, retrieved=relevant, top_score=top)


def summarize(text: str, fmt: str = "I shkurtër", max_chars: int = 8000) -> str:
    """Summarize raw document text in the requested Albanian format. Grounded by
    construction (the text itself is the only source)."""
    instruction = _SUMMARY_FORMATS.get(fmt, _SUMMARY_FORMATS["I shkurtër"])
    body = text.strip()[:max_chars]
    system = (
        "Ti je një asistent që përmbledh dokumente zyrtare në gjuhën shqipe. "
        "Përmbledh VETËM përmbajtjen e dhënë, pa shtuar informacion nga jashtë."
    )
    prompt = f"{instruction}\n\nDokumenti:\n{body}\n\nPërmbledhja:"
    return llm.generate(prompt, system=system)
