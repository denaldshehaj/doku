# DOKU — Raport Auditi & Vlerësim Teze (MSc)

> Auditi i bazuar në kod me referenca `file:line`. Nuk supozohet që projekti është korrekt.
> Gjeneruar gjatë sesionit të zhvillimit; shoqërues i `docs/Teza_DOKU.docx`.

## Scorecard Final (0–100)

| Dimensioni | Pikë | Shënim |
|---|---:|---|
| Arkitektura & cilësia e kodit | 78 | Ndarje e pastër modulesh; ca global-state & logging gaps |
| Siguria | 55 | SQL i parametrizuar & bcrypt mirë; brute-force/session/default-creds gaps |
| RAG / inxhinieri AI | 64 | Grounding i fortë; retrieval bazë, pa rerank/hybrid |
| Dizajni i bazës së të dhënave | 66 | Skemë e pastër; mungojnë indekse, FK, migrime |
| Performanca | 58 | gemma2:9b ~5 min/përgjigje në këtë HW; reindex sekuencial |
| UI/UX | 72 | Konsistente, shqip, role-aware; udhëzim/aksesueshmëri e pakët |
| Testim/QA | 25 | **Asnjë test i automatizuar** |
| Dokumentacioni | 68 | CLAUDE.md/SPEC fortë; pa README/user/admin guide |
| Gatishmëria për tezë | 70 | Risi & sistem i fortë; mungojnë rezultate & literaturë |
| **Total** | **64/100** | Bazë solide MSc; ~3–4 javë punë drejt "mbrojtje e fortë" |

---

## PART 1 — Auditi sipas Severitetit

| # | Sev | Kategori | Gjetja & Evidenca | Rreziku | Fix |
|---|---|---|---|---|---|
| 1 | Critical* | Security | Default admin `admin/***REMOVED-CREDENTIAL***` hardcoded (`config.py:35-36`) + app live në tunnel publik me XSRF off. *Critical vetëm sa është tunnel-i lart. | Kushdo me URL-në provon login-in default. | Ulë tunnel-in kur s'demonstron; shto brute-force lockout (#2). |
| 2 | High | Security | Pa brute-force/rate-limit në login (`auth.authenticate`, `app.login_screen`). | Guessing i pakufizuar. | Numërues përpjekjesh + backoff/lockout. |
| 3 | High | Testing | **Zero teste të automatizuara** (vetëm `tests/sample_questions.csv`). | Regresione të padukshme. | Suitë pytest (Part 8). |
| 4 | High | Functionality | `_active_model` është proces-global (`llm_client.py:25-27`), jo per-session. | Një user ndryshon modelin për të gjithë. | Ruaj në `st.session_state`. |
| 5 | Medium | Security | Pa skadim sesioni (`app.py:42`). | Sesione të pambikëqyrura mbeten aktive. | `login_time` + skadim pas N min. |
| 6 | Medium | AI/RAG | Copëzim për-faqe me dritare karakteresh (`document_processor.py:99-105`). | Humbet kontekst ndërfaqësor. | Copëzim sentence/token-aware. |
| 7 | Medium | AI/RAG | Detektim refuzimi post-LLM me substring (`rag_pipeline.py:91-92`). | False "refused". | Mbështetu te gate-i para-LLM. |
| 8 | Medium | Security | Prompt-injection nga copëza të indeksuara (`rag_pipeline.py:88`). Zbutet: upload vetëm-admin. | Përgjigje të manipuluara. | Delimit kontekstin; sanitizo. |
| 9 | Medium | Database | Pa indekse përtej PK/UNIQUE; pa FK (`database.py`). | Ngadalësi në shkallë; rreshta jetimë. | Shto indekse + FK (Part 5). |
| 10 | Medium | Maintainability | Pa `logging`; gabime të gëlltitura (`documents.reindex_all:160-163`). | Dështime të heshtura. | `logging`; surface failures. |
| 11 | Low | Security | Pa MIME/magic-byte; tip nga emri (`document_processor._pages_for`). Path traversal trajtohet (`documents.safe_filename:14`). | Skedar i etiketuar gabim. | Validim magic bytes; limit madhësie. |
| 12 | Low | Security | Tekst përjashtimi i ekspozuar në UI (`llm_client.py:72`). | Info disclosure minor. | Logo detajin, shfaq gjenerik. |
| 13 | Low | AI/RAG | `status` metadata në Chroma s'përditësohet (`vector_store.py:60` vs `documents.set_status:119`). | Të dhëna të vdekura. | Hiqe ose përditësoje. |
| 14 | Low | Security | bcrypt prerje në 72 byte heshtazi (`auth.py:20,25`). | Passphrase të gjata priten. | Pre-hash SHA-256 ose paralajmëro. |
| 15 | Low | Performance | `reindex_all` re-embed sekuencial (`documents.py:157-164`). | Ngadalë për korpus të madh. | Batch embeddings. |

**Pozitive:** SQL i parametrizuar kudo; `distinct_values` whitelist-on kolonat (`documents.py:56`) → **pa SQL injection**; bcrypt me salt; **refusal-gate para LLM** (`rag_pipeline.py:82-85`) = anti-halucinacion strukturor; citime me dokument+faqe; shënim ligjor për dokumente normative.

---

## PART 2 — Arkitektura
Ndarje textbook (config/modules/pages); kohezion i lartë; UI s'prek SQL direkt; role guards të centralizuara (`ui.require_admin`). Dobësi: module globals (`_active_model` bug #4), pa logging/error-handling qendror, config i hardcoded (pa env vars), tavan skalueshmërie single-node (i qëllimshëm për premisën air-gapped).

## PART 3 — Siguria (OWASP)
Mirë: bcrypt+salt, AuthZ server-side, SQL i parametrizuar. Dobët: pa brute-force (#2), pa skadim sesioni (#5), default creds në burim, prompt-injection (#8), XSRF i çaktivizuar për tunnel. **Top 3 para mbrojtjes:** lockout, session timeout, hiq/parametrizo default creds + rikthe XSRF.

## PART 4 — RAG
bge-m3 (✅ shumëgjuhësh), top-k cosine + filtër aktiv, **refusal-gate para LLM** (✅✅), citime me faqe. Mungon rerank/hybrid; prag 0.38 i ndjeshëm ndaj diakritikave. **Pikë:** maturitet RAG **64**, retrieval **65**, explainability **82**, përshtatshmëri teze **80**. Përmirësime: chunking semantik, retrieval hibrid (BM25+dense), cross-encoder reranker, normalizim diakritikash, metrika Recall@k/MRR.

## PART 5 — Baza e të Dhënave
Skemë e pastër, timestamps UTC, CHECK constraints. Mungojnë: indekse (status, user_id, created_at), FK constraints, framework migrimi, `PRAGMA journal_mode=WAL`. Normalizim: institution/document_type denormalizuar (OK në këtë shkallë).

## PART 6 — Performanca
Bottleneck = vonesa LLM: **~323s (5.4 min) për gemma2:9b** në RTX 3050 4GB (matur); qwen2.5:3b = sekonda. Memorie: bge-m3 (~2.3GB)+gemma2:9b (~5.4GB) → ~0.6GB headroom në 16GB. Reindex sekuencial; pa cache embeddings. Rekomandim: qwen2.5:3b si default demo.

## PART 7 — UI/UX
Konsistente, shqip, role-aware, spinner-a, citime, refuzim. **Rreziku më i madh UX:** fshirje me një klik pa konfirmim (`5_Admin_Dokumentet.py:86-89`). Aksesueshmëri: pa alt-text, status vetëm me ngjyrë. Demo: shto confirm-dialog, dashboard metrics, shënim "si funksionon grounding".

## PART 8 — Testimi
Aktualisht **asnjë**. Minimumi: `test_auth`, `test_chunking`, `test_refusal_gate` (LLM i mock-uar), `test_documents`, `test_db`, `test_rag_integration`. Kriter pranimi p.sh.: "Pyetje jashtë korpusit → `REFUSAL_MESSAGE`, `refused=True`, LLM s'thirret".

## PART 9 — Dokumentacioni
CLAUDE.md/SPEC fortë. Mungojnë: README i mirëfilltë, user/admin guide, diagrama arkitekture (tani te teza).

## PART 10 — Gatishmëria për Tezë: **70/100**
Pikë të forta: risi (RAG lokal shqip për sektorin publik), grounding i mbrojtshëm, inxhinieri e pastër. Mungojnë para mbrojtjes: teste, rezultate reale (✅ tani të prodhuara), literaturë, hardening sigurie, diagrama UML (✅ te teza), teza e shkruar (✅).

---

## Roadmap i Përmirësimeve
- **P0 (para çdo demo publik):** ulë tunnel-in kur idle / rikthe XSRF; brute-force lockout; confirm-dialog për fshirje; default demo = qwen2.5:3b.
- **P1 (para mbrojtjes):** suitë pytest; indekse+FK+WAL; session timeout; fix `_active_model`; logging; rezultate reale (✅).
- **P2 (polish/risi):** retrieval hibrid + reranker; chunking semantik; metrika retrieval; README + guide + UML.
- **P3 (e ardhmja):** OCR, multi-node, ACL per-dokument.

## Pyetje–Përgjigje për Mbrojtjen (shembuj)
- *"Si e garantoni mos-halucinacionin?"* → Refusal-gate para LLM: nëse top cosine < 0.38 kthejmë refuzimin pa thirrur modelin (`rag_pipeline.py:82-85`); çdo përgjigje citon copëz+faqe.
- *"Pse lokal?"* → Sovranitet/privatësi i të dhënave institucionale; premisë air-gapped; Ollama + bge-m3 offline.
- *"Pse bge-m3?"* → Shumëgjuhësh incl. shqip, i fortë në gjuhë me burime të kufizuara, L2-normalized për cosine.
- *"Kufizimi më i madh?"* → Vonesa e modeleve të mëdha në GPU konsumatori (~5 min për 9B); pa OCR; single-node.
- *"Si zgjidhet pragu?"* → Empirikisht (i ndjeshëm ndaj diakritikave); i ndershëm për brishtësinë — normalizim diakritikash si punë e ardhshme.
