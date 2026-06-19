"""Grounding test harness (Definition of Done for the RAG module).

Validates the "never hallucinate" contract on the sample corpus:
  * in-corpus questions  -> the correct document is retrieved above threshold
  * out-of-corpus questions -> the system REFUSES (refusal gate, no LLM needed)
  * if Ollama is running   -> answers are produced, cited, and not refused

Run:  .venv\\Scripts\\python.exe tests\\grounding_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import doku  # noqa: F401,E402  (sets sys.path)
import config  # noqa: E402
from doku import db, llm, rag, vectorstore  # noqa: E402
from scripts.make_sample_corpus import main as build_corpus  # noqa: E402

# (question, expected_filename or None for out-of-corpus)
IN_CORPUS = [
    ("Kur duhet të dorëzohet deklarata tatimore?", "ligj_tatimor_2023.pdf"),
    ("Çfarë ndodh nëse nuk paguhen tatimet në afat?", "ligj_tatimor_2023.pdf"),
    ("Ku mund të ankohet tatimpaguesi?", "ligj_tatimor_2023.pdf"),
    ("Sa ditë pushim vjetor ka punonjësi?", "rregullore_punes_2022.pdf"),
    ("Sa orë është orari normal i punës?", "rregullore_punes_2022.pdf"),
    ("Sa është afati i njoftimit për zgjidhjen e kontratës?", "rregullore_punes_2022.pdf"),
    ("Cili është objektivi i strategjisë dixhitale për 2030?", "strategjia_dixhitale_2030.pdf"),
    ("Ku do të përqendrohen investimet dixhitale?", "strategjia_dixhitale_2030.pdf"),
]
OUT_OF_CORPUS = [
    "Sa kushton një biletë avioni për në Romë?",
    "Kush e fitoi Kupën e Botës në futboll në 2018?",
]


def ensure_corpus():
    db.init_db()
    if vectorstore.count() == 0:
        print("Po ndërtoj korpusin shembull...")
        build_corpus()


def run():
    ensure_corpus()
    passed = 0
    total = 0

    print("\n--- Test 1: marrja e duhur (in-corpus) ---")
    for question, expected in IN_CORPUS:
        total += 1
        hits = vectorstore.query(question, k=config.RETRIEVAL_K)
        filenames = [h.filename for h in hits]
        top = hits[0].score if hits else 0.0
        ok = bool(hits) and expected in filenames and top >= config.MIN_SIMILARITY
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {question[:50]:<50} "
              f"top={top:.3f} doc={filenames[0] if filenames else '-'}")

    print("\n--- Test 2: refuzimi (out-of-corpus) ---")
    for question in OUT_OF_CORPUS:
        total += 1
        ans = rag.answer_question(question)
        ok = ans.refused
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {question[:50]:<50} "
              f"top={ans.top_score:.3f} refused={ans.refused}")

    print("\n--- Test 3: gjenerimi me citime (kërkon Ollama) ---")
    if llm.is_available():
        q = IN_CORPUS[0][0]
        ans = rag.answer_question(q)
        ok = (not ans.refused) and len(ans.citations) > 0
        total += 1
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] përgjigje e cituar për: {q[:40]}")
        print(f"        -> {ans.text[:120]}")
    else:
        print("  (anashkaluar — Ollama nuk është aktiv)")

    print(f"\n=== {passed}/{total} teste kaluan ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run())
