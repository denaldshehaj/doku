"""M0 embedding spike — does bge-m3 retrieve Albanian institutional text correctly?

Run: .venv\\Scripts\\python.exe spikes\\embedding_spike.py

Goal: validate (1) Albanian retrieval quality and (2) the gap between similarity
scores for RELEVANT vs IRRELEVANT (out-of-corpus) queries, so we can calibrate the
refusal threshold (config.MIN_SIMILARITY) that enforces "never hallucinate".
"""
import sys
from sentence_transformers import SentenceTransformer
import numpy as np

MODEL = "BAAI/bge-m3"

# Mini Albanian institutional corpus (stand-ins for real document chunks).
CORPUS = [
    ("ligj_tatime",
     "Çdo tatimpagues është i detyruar të paraqesë deklaratën tatimore brenda datës "
     "31 mars të vitit pasardhës. Mospagimi në afat sjell gjoba dhe kamatëvonesa."),
    ("rregullore_pushimet",
     "Punonjësi ka të drejtën e pushimit vjetor të paguar prej të paktën 28 ditësh "
     "kalendarike në vit. Pushimi planifikohet në marrëveshje me eprorin direkt."),
    ("strategji_dixhitalizimi",
     "Strategjia kombëtare e dixhitalizimit synon ofrimin e shërbimeve publike online "
     "deri në vitin 2030, duke reduktuar barrën administrative për qytetarët."),
    ("ligj_prokurimi",
     "Prokurimi publik realizohet përmes procedurave të hapura dhe transparente. "
     "Vlera mbi pragun e përcaktuar kërkon publikim në sistemin elektronik."),
    ("raport_buxheti",
     "Raporti vjetor i buxhetit pasqyron të ardhurat dhe shpenzimet e institucionit. "
     "Tejkalimet buxhetore duhet të justifikohen dhe miratohen nga këshilli drejtues."),
]

# (query, expected_doc_id). Last one is OUT-OF-CORPUS → should score low everywhere.
QUERIES = [
    ("Kur duhet të dorëzohet deklarata tatimore?", "ligj_tatime"),
    ("Sa ditë pushim vjetor ka punonjësi?", "rregullore_pushimet"),
    ("Cili është objektivi i dixhitalizimit të shërbimeve?", "strategji_dixhitalizimi"),
    ("Si bëhet prokurimi publik për vlera të mëdha?", "ligj_prokurimi"),
    ("Sa kushton një biletë avioni për në Romë?", None),  # out-of-corpus → expect refusal
]


def main():
    print(f"Loading {MODEL} (first run downloads ~2GB)...", flush=True)
    model = SentenceTransformer(MODEL)

    ids = [c[0] for c in CORPUS]
    corpus_emb = model.encode([c[1] for c in CORPUS], normalize_embeddings=True)

    passed = 0
    for query, expected in QUERIES:
        q_emb = model.encode([query], normalize_embeddings=True)[0]
        sims = corpus_emb @ q_emb  # cosine, since normalized
        order = np.argsort(-sims)
        top_id, top_score = ids[order[0]], float(sims[order[0]])

        if expected is None:
            ok = top_score < 0.55  # heuristic: out-of-corpus should NOT score high
            verdict = "REFUSE (low score expected)"
        else:
            ok = top_id == expected
            verdict = f"expected={expected}"
        passed += ok

        print(f"\nQ: {query}")
        print(f"   {verdict}  -> top={top_id} score={top_score:.3f}  {'PASS' if ok else 'FAIL'}")
        for rank in order[:3]:
            print(f"      {ids[rank]:<26} {float(sims[rank]):.3f}")

    print(f"\n=== {passed}/{len(QUERIES)} checks passed ===")
    print("Use the relevant-vs-irrelevant score gap above to set config.MIN_SIMILARITY.")
    return 0 if passed == len(QUERIES) else 1


if __name__ == "__main__":
    sys.exit(main())
