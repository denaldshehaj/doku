# DOKU — Dokumentacioni Teknik

> Dokument teknik për punimin e Masterit: arkitektura, rrjedha e të dhënave, vendimet e
> dizajnit, mekanizmi anti-halucinim, siguria dhe vlerësimi. Për udhëzime ekzekutimi shih
> [README.md](README.md); për kontratën e zhvillimit shih [CLAUDE.md](CLAUDE.md); për një
> raport të zgjeruar sipas seksioneve shih [RAPORT_TEKNIK.md](RAPORT_TEKNIK.md).

## 1. Qëllimi
DOKU është një sistem **plotësisht lokal** për analizën e dokumenteve institucionale në
gjuhën shqipe, i bazuar te **RAG** dhe një LLM lokal (Ollama). Cilësia përcaktuese është
**bazimi strikt**: sistemi citon çdo pohim dhe **refuzon** kur korpusi nuk e mbështet
përgjigjen. Asnjë e dhënë nuk del nga makina lokale.

## 2. Arkitektura (modules/ + views/)

```
┌───────────────────────────────────────────────────────────────┐
│  app.py — login, sesion, navigim sipas rolit (st.navigation)   │
│  views/: Dashboard · Pyet · Përmbledhje · Historiku ·          │
│          Admin(Dokumentet · Përdoruesit · Audit) · Eksperimente│
└───────────────┬───────────────────────────────────────────────┘
                │
   ┌────────────┼──────────────────────────────────────────────┐
   │ auth       │ rag_pipeline (porta e refuzimit)  │ documents │
   │ (RBAC,     │   ↓                               │ (CRUD,    │
   │  bcrypt,   │ vector_store ── embeddings (bge-m3)│ status,   │
   │  admin     │   (ChromaDB, kosinus)             │ reindex)  │
   │  default)  │   ↓                               │   ↓       │
   │            │ llm_client (Ollama)               │ document_ │
   │ audit      │                                   │ processor │
   └────────────┴───────────────────────────────────┴───────────┘
        │ history · export_docx · experiments
   ┌────┴─────────────┐                  ┌────────────────┐
   │ SQLite (app.db)  │                  │ ChromaDB        │
   │ users, documents,│                  │ copëzat +       │
   │ chat_history,    │                  │ vektorët +      │
   │ audit_logs,      │                  │ metadata e plotë│
   │ sessions,        │                  └────────────────┘
   │ experiment_results│
   └──────────────────┘
```

### Modulet
| Moduli | Përgjegjësia |
|--------|--------------|
| `config.py` | Parametrat: `OLLAMA_MODEL`, temperaturë 0.2, pragu i refuzimit, shtigjet, enum-et; përgatit runtime-in nativ VC++ në Windows. |
| `modules/database.py` | Skema SQLite (6 tabela) + lidhje + auto-krijim; WAL, `busy_timeout`, retry për “database is locked”. |
| `modules/auth.py` | bcrypt, role admin/punonjes, admin default, ndryshim i detyruar, sesione të qëndrueshme. |
| `modules/audit.py` | Regjistri i veprimeve. |
| `modules/document_processor.py` | PyMuPDF/python-docx: nxjerrje, validim teksti (anti-skanim), copëzim i vetëdijshëm për nene. |
| `modules/embeddings.py` | bge-m3 (Sentence Transformers), vektorë të normalizuar. |
| `modules/vector_store.py` | ChromaDB; metadata e plotë e copëzës; filtrim sipas aktiv/dokument. |
| `modules/documents.py` | Menaxhim dokumentesh: ngarko/edito/status/fshi/riindekso(/të gjitha). |
| `modules/rag_pipeline.py` | Marrje → portë refuzimi → prompt i bazuar → LLM → citime; përmbledhje. |
| `modules/llm_client.py` | Klient Ollama (error i qartë në shqip nëse jo aktiv). |
| `modules/history.py` | Ruajtja e `chat_history`. |
| `modules/export_docx.py` | Eksport Word (përgjigje + përmbledhje) te `data/exports/`. |
| `modules/experiments.py` | Harness RAG vs pa-RAG + eksport CSV. |
| `api/*` | Shtresa HTTP (FastAPI) mbi modulet — shih §2.1. |

### 2.1 Ndërfaqja: React SPA + shtresa API FastAPI (korrik 2026)

Ndërfaqja Streamlit u zëvendësua plotësisht nga një frontend modern **React** (kodi
Streamlit — `app.py`, `views/`, `modules/ui.py` — u hoq më 2026-07-02 pas konfirmimit
të paritetit), me një shtresë të hollë **FastAPI** mbi `modules/` ekzistues. Bërthama
(RAG, indeksimi, citimet, porta e refuzimit, autentikimi bcrypt, SQLite/ChromaDB)
mbetet **e pandryshuar** — API-ja vetëm
përkthen HTTP ↔ funksionet e moduleve, pa logjikë biznesi të vetën.

```
Shfletuesi ──► FastAPI (VETËM 127.0.0.1:8000)
               ├── /api/*  ──► modules/  (të pandryshuara)
               └── /       ──► frontend/dist (React SPA e ndërtuar)
```

| Komponenti | Detaje |
|-----------|--------|
| `api/deps.py` | Sesione me **cookie httpOnly** (ripërdor tabelën `sessions`; tokeni s'shfaqet më në URL) + `require_user`/`require_admin` të zbatuara në server + semafor LLM (1 gjenerim njëkohësisht — GPU 4GB). |
| `api/routers/*` | auth, meta/dashboard/system, chat (RAG + eksport .docx), summaries, history, documents (upload/status/reindex/parapamje), users (me mbrojtjen e admin-it të fundit), audit, experiments, tasks. |
| `api/tasks.py` | Operacionet e gjata (riindeksim korpusi, batch eksperimentesh) ekzekutohen në sfond; frontend-i ndjek progresin me polling te `GET /api/tasks/{id}`. |
| `frontend/` | React 19 + Vite + TypeScript strikt + Tailwind 4 + TanStack Query. Faqe lazy-loaded (code splitting për route), dark/light mode, responsive (drawer në mobile), WCAG (label-e, fokus i dukshëm, ARIA). |
| Faqet | Login → ndryshim i detyruar fjalëkalimi → Paneli, **Biseda** (chat me citime, score ngjashmërie, panel burimesh, refuzimi i stilizuar si gjendje e sistemit), Përmbledhje (4 formate + .docx), Historiku, dhe për adminin: Dokumentet, Përdoruesit, Audit Log, Eksperimentet (vlerësim manual inline + CSV). |
| Siguria | Bind vetëm `127.0.0.1`; cookie `SameSite=Lax`; asnjë burim i jashtëm (fonte/CDN); guard-et e UI-së janë vetëm UX — kontrolli real bëhet në API. |

Ekzekutimi: `python run_api.py` (shërben SPA + API në një port); zhvillimi i frontend-it:
`npm run dev` në `frontend/` (proxy `/api` → :8000). Dokumentimi automatik i API-së:
`/api/docs` (OpenAPI).

## 3. Rrjedha e të dhënave

### 3.1 Indeksimi (admin ngarkon PDF/DOCX)
1. Ruajtja e skedarit në `data/uploads/` (emër i sigurt).
2. Nxjerrja e tekstit faqe-për-faqe (PyMuPDF) ose i tërë (python-docx për .docx).
3. Validimi: tekst < 100 karaktere → refuzohet (skanim; pa OCR).
4. Copëzimi i vetëdijshëm për nene ("Neni N"), përndryshe dritare 800/120 karaktere, me numrin e faqes.
5. Embedding me bge-m3; indeksimi në ChromaDB me metadata të plotë.
6. Metadata e dokumentit (tip, institucion, vit, përshkrim, status) në SQLite.

### 3.2 Pyetja (anti-halucinim)
```
pyetje → embedding → marrje top-k (vetëm dokumentet active ose një i zgjedhur)
        → PORTA E REFUZIMIT: nëse ngjashmëria më e lartë < MIN_SIMILARITY
              → mesazhi i refuzimit (LLM-ja nuk thirret kurrë)
        → filtrim i kontekstit te copëzat përkatëse
        → prompt i bazuar → LLM lokal → përgjigje me citime [filename, tip, institucion, faqe]
        → shënim ligjor nëse dokumenti është normativ (Ligj/VKM/Rregullore/Udhëzim)
```

## 4. Mekanizmi anti-halucinim
- **Porta e refuzimit ekzekutohet PARA modelit** → fabrikimi strukturalisht i pamundur
  për pyetje jashtë korpusit. Mesazhi i saktë: *"Nuk ka informacion të mjaftueshëm…"*.
- Prompt i kufizuar te konteksti; temperaturë 0.2; filtrim konteksti te copëzat përkatëse.

## 5. Siguria dhe RBAC
- Fjalëkalime me **bcrypt** (asnjëherë plain-text); admin default me ndryshim të detyruar.
  Kredencialet e admin-it nuk komitohen kurrë: env var / `secrets_local.py` (git-ignored) /
  fjalëkalim i rastësishëm një-përdorimësh i printuar në konsolë.
- Dy role: **admin** (menaxhon korpusin, përdoruesit, audit, eksperimente) dhe **punonjes**
  (vetëm lexim). Kontroll në kod (`require_admin`), jo vetëm fshehje UI.
- Sesione të qëndrueshme: token opak në tabelën `sessions`, i mbajtur në URL (`?sid=`), TTL 12h
  me skadim sliding; përdorues i çaktivizuar e humb sesionin menjëherë.
- Audit log për çdo veprim të rëndësishëm; emra file të sigurt në upload/eksport.

## 6. Vlerësimi (kapitulli i Rezultateve)
Moduli `experiments.py` + faqja *Eksperimente* ekzekuton `tests/sample_questions.csv` me dhe
pa RAG, dhe mat për çdo pyetje: kohën pa/me RAG, numrin e copëzave, praninë e citimeve,
vlerësimin manual të saktësisë (1–5) dhe halucinacionin (Po/Jo) për të dyja, plus shënime.
Rezultatet ruhen te `experiment_results` dhe eksportohen në **CSV** për tabelën krahasuese.

Gjetje paraprake (korpus shembull, bge-m3): pyetjet brenda korpusit me diakritikë të saktë
shënojnë ~0.70, ato pa diakritikë ~0.40, ndërsa pyetjet jashtë korpusit ≤0.35 dhe refuzohen —
ndarje e qartë që e bën pragun **`MIN_SIMILARITY = 0.38`** të sigurt (lejon pyetjet legjitime
pa diakritikë, refuzon ato jashtë korpusit).

## 7. Vendimet kryesore të dizajnit
- **bge-m3** për shqipen (shumëgjuhësh i fortë), i konfirmuar me teste.
- **ChromaDB + SQLite** të ndara (vektorë vs të dhëna relacionale), pa server.
- **Ollama lokal**: parazgjedhje në kod `gemma2:9b` (cilësi më e lartë në shqip) me `qwen2.5:3b`
  si alternativë RAM-friendly (16GB); modeli ndërrohet nga dropdown-i në sidebar sipas RAM-it të lirë.
- **bcrypt drejtpërdrejt** (passlib i pamirëmbajtur me bcrypt ≥ 5).
- **Streamlit multipage** me `st.navigation` për navigim sipas rolit.

## 8. Kufizimet dhe puna e ardhshme
Pa OCR; cilësia varet nga modeli lokal dhe RAM-i; pragu rikalibrohet mbi korpus real.
E ardhmja: OCR opsional, rirenditje (re-ranking), gjykatës AI dytësor, kontroll versionesh.

## 9. Mjedisi
Windows 11 · Python 3.13 · 16GB RAM · RTX 3050 4GB · Ollama lokal.
