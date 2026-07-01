# DOKU — Raport Teknik i Plotë i Projektit

> **Sistem Inteligjent Lokal për Analizë Dokumentesh Institucionale (RAG + LLM lokal, në gjuhën shqipe).**
> Punim Masteri, Shkenca Kompjuterike & Inteligjenca Artificiale.
>
> Ky dokument është hartuar në rolin e *Software Architect* dhe *Technical Writer*: analizon aplikacionin
> ekzistues dhe e dokumenton nga qëllimi te arkitektura, kodi, baza e të dhënave, siguria, performanca dhe
> puna e ardhshme. Për udhëzime të shpejta ekzekutimi shih [README.md](README.md); për kontratën e zhvillimit
> shih [CLAUDE.md](CLAUDE.md); për milestone-t shih [SPEC.md](SPEC.md).

---

## Përmbajtja
1. [Qëllimi dhe problemi që zgjidh](#1-qëllimi-dhe-problemi-që-zgjidh)
2. [Funksionalitetet kryesore](#2-funksionalitetet-kryesore)
3. [Arkitektura e sistemit dhe komunikimi i komponentëve](#3-arkitektura-e-sistemit-dhe-komunikimi-i-komponentëve)
4. [Teknologjitë, framework-et dhe arsyet e zgjedhjes](#4-teknologjitë-framework-et-dhe-arsyet-e-zgjedhjes)
5. [Struktura e projektit dhe organizimi i kodit](#5-struktura-e-projektit-dhe-organizimi-i-kodit)
6. [Baza e të dhënave: modelet dhe marrëdhëniet](#6-baza-e-të-dhënave-modelet-dhe-marrëdhëniet)
7. [Komunikimi frontend–backend dhe “endpoint-et” logjike](#7-komunikimi-frontendbackend-dhe-endpoint-et-logjike)
8. [Autentikimi, autorizimi dhe siguria](#8-autentikimi-autorizimi-dhe-siguria)
9. [Performanca, optimizimet dhe praktikat më të mira](#9-performanca-optimizimet-dhe-praktikat-më-të-mira)
10. [Procesi i zhvillimit dhe sfidat kryesore të zgjidhura](#10-procesi-i-zhvillimit-dhe-sfidat-kryesore-të-zgjidhura)
11. [Përmirësimet e mundshme dhe puna e ardhshme](#11-përmirësimet-e-mundshme-dhe-puna-e-ardhshme)

---

## 1. Qëllimi dhe problemi që zgjidh

### 1.1 Konteksti
Institucionet publike shqiptare (kuvend, këshill ministrash, ministri, agjenci) prodhojnë vëllime të mëdha
dokumentesh normative dhe raportuese: **Ligje, VKM, Strategji, Rregullore, Udhëzime, Raporte**. Këto
dokumente janë të gjata, të shkruara në gjuhë juridike-administrative shqipe dhe të vështira për t’u kërkuar.
Një punonjës që kërkon “çfarë parashikon neni X i ligjit Y” ose “përmblidhma këtë strategji” shpenzon kohë
duke lexuar manualisht.

### 1.2 Problemi
- **Kërkim joefikas**: kërkimi me fjalë-kyçe (Ctrl+F) nuk kupton kuptimin; humbet sinonimet dhe parafrazimet.
- **Rreziku i halucinacionit**: një LLM i përgjithshëm (ChatGPT etj.) “trillon” përgjigje bindëse por të
  pasakta — e papranueshme në kontekst institucional/ligjor.
- **Privatësia dhe sovraniteti i të dhënave**: dokumentet institucionale shpesh nuk lejohen të dërgohen te
  API cloud të palëve të treta. Nevojitet përpunim **plotësisht lokal**.
- **Kontroll aksesi**: korpusi duhet të jetë i centralizuar dhe i menaxhuar nga një administrator; punonjësit
  duhet ta konsultojnë por jo ta modifikojnë.

### 1.3 Zgjidhja që ofron DOKU
DOKU është një aplikacion **fully-local** që kombinon **RAG (Retrieval-Augmented Generation)** me një **LLM
lokal (Ollama)** dhe embeddings shumëgjuhëshe **bge-m3**, për t’u përgjigjur pyetjeve mbi një korpus
dokumentesh në shqip, me dy garanci themelore:

1. **Bazim strikt (grounding)** — çdo përgjigje ndërtohet vetëm nga fragmente të tërhequra realisht nga
   dokumentet, dhe **çdo pohim citohet** (skedar, tip, institucion, faqe).
2. **Refuzim në vend të trillimit** — nëse asgjë mjaftueshëm e ngjashme nuk gjendet në korpus, sistemi
   **refuzon** me një mesazh të paracaktuar dhe **nuk e thërret fare modelin**, duke e bërë fabrikimin
   *strukturalisht të pamundur* për pyetjet jashtë korpusit.

Sistemi simulon një mjedis qeveritar/institucional: një **admin** menaxhon korpusin e centralizuar; **punonjësit
(punonjes)** pyesin dhe përmbledhin por nuk mund ta modifikojnë atë.

---

## 2. Funksionalitetet kryesore

### 2.1 Për punonjësin (rol `punonjes`, vetëm-lexim)
| Funksion | Përshkrim |
|----------|-----------|
| **Paneli (Dashboard)** | Metrika: dokumente aktive, gjithsej, copëza në indeks, numri i pyetjeve të mia. |
| **Pyet Dokumentet** | Pyetje në shqip mbi gjithë korpusin aktiv ose mbi një dokument të vetëm; filtrim sipas tipit/institucionit/vitit/fjalë-kyçe në titull; përgjigje me citime ose refuzim; eksport i përgjigjes në Word. |
| **Përmbledhje Dokumenti** | Përmbledh një dokument të vetëm në 4 formate: *E shkurtër*, *E detajuar*, *Pika kryesore*, *Për vendimmarrje institucionale*; eksport në Word. |
| **Historiku im** | Pyetjet e mëparshme të përdoruesit me përgjigje, mode, burime, kohë. |

### 2.2 Për administratorin (rol `admin`, të gjitha të mësipërmet + menaxhim)
| Funksion | Përshkrim |
|----------|-----------|
| **Menaxhim Dokumentesh** | Ngarkim PDF/DOCX, editim metadatash, aktivizim/çaktivizim (status `active`/`inactive`), fshirje, **riindeksim** i një dokumenti ose i gjithë korpusit. |
| **Menaxhim Përdoruesish** | Krijim punonjësish/adminash, caktim roli, riemërtim, aktiv/joaktiv, reset fjalëkalimi (temporar, me ndryshim të detyruar). |
| **Audit Log** | Regjistër i çdo veprimi të rëndësishëm (login, upload, fshirje, pyetje, eksport…). |
| **Eksperimente** | Harness që ekzekuton pyetje testuese **me RAG vs pa RAG**, mat kohën/copëzat/citimet, lejon vlerësim manual (saktësi 1–5, halucinacion Po/Jo, shënime) dhe eksporton **CSV** për kapitullin e Rezultateve të tezës. |

### 2.3 Karakteristika ndër-funksionale
- **Gjuhë shqipe** në gjithë ndërfaqen dhe në prompt-et e sistemit.
- **Shënim ligjor automatik**: kur dokumenti është normativ (`Ligj`, `VKM`, `Rregullore`, `Udhëzim`), përgjigjes
  i shtohet një klauzolë që dokumenti origjinal mbetet burimi zyrtar.
- **Sesione të qëndrueshme**: token sesioni në URL që mbijeton rifreskimin e faqes (deri në 12 orë, me
  zgjatje sliding).
- **Zgjedhje modeli në kohë reale**: sidebar-i lejon ndërrimin e modelit lokal (p.sh. `gemma2:9b` ↔
  `qwen2.5:3b`) sipas RAM-it të disponueshëm.

---

## 3. Arkitektura e sistemit dhe komunikimi i komponentëve

### 3.1 Pamje e përgjithshme (monolit modular, tri shtresa)
DOKU është një **monolit modular** në një proces të vetëm Python — pa mikroshërbime, pa server API të veçantë.
Shtresat janë të ndara logjikisht:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SHTRESA E PREZANTIMIT (Streamlit)                                          │
│  app.py  → login · sesion · ndryshim fjalëkalimi · st.navigation (RBAC)    │
│  views/  → 1_Dashboard … 8_Eksperimente  (faqe multipage)                  │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 │  thirrje funksionesh (in-process)
┌───────────────────────────────┴──────────────────────────────────────────┐
│ SHTRESA E LOGJIKËS (modules/)                                              │
│                                                                            │
│   auth ──┐         rag_pipeline ──(porta e refuzimit)                       │
│   audit  │              │                                                   │
│   ui     │        vector_store ── embeddings (bge-m3, Sentence-Transf.)     │
│   history│              │                                                   │
│   export │        llm_client ── Ollama (HTTP localhost:11434)               │
│          │                                                                  │
│   documents ── document_processor (PyMuPDF / python-docx)                   │
│   experiments                                                               │
└───────────────┬───────────────────────────────────┬──────────────────────┘
                │                                     │
      ┌─────────┴──────────┐               ┌──────────┴───────────┐
      │ SQLite (data/app.db)│               │ ChromaDB (data/chroma_db)│
      │ users, documents,   │               │ koleksioni doku_chunks:  │
      │ chat_history,       │               │ copëzat + vektorët +     │
      │ audit_logs,         │               │ metadata e plotë         │
      │ sessions,           │               │ (hapësirë kosinus)       │
      │ experiment_results  │               └──────────────────────────┘
      └─────────────────────┘
```

### 3.2 Përgjegjësitë e moduleve
| Moduli | Përgjegjësia |
|--------|--------------|
| [config.py](config.py) | Parametrat qendrorë: `OLLAMA_MODEL`, temperaturë (0.2), shtigjet, `CHUNK_SIZE`/`OVERLAP`, `RETRIEVAL_K`, `MIN_SIMILARITY`, enum-et e domenit; përgatit runtime-in nativ në Windows. |
| [modules/database.py](modules/database.py) | Skema SQLite (6 tabela), lidhje me retry për “database is locked”, WAL, `busy_timeout`, init idempotent. |
| [modules/auth.py](modules/auth.py) | bcrypt, role admin/punonjes, admin default, ndryshim i detyruar, sesione të qëndrueshme. |
| [modules/audit.py](modules/audit.py) | Regjistrimi i veprimeve në `audit_logs`. |
| [modules/document_processor.py](modules/document_processor.py) | Nxjerrje teksti (PyMuPDF / python-docx), validim anti-skanim, copëzim i vetëdijshëm për nene. |
| [modules/embeddings.py](modules/embeddings.py) | Wrapper bge-m3; vektorë të L2-normalizuar (kosinus == dot product). |
| [modules/vector_store.py](modules/vector_store.py) | ChromaDB persistent; add/delete/query/reset; metadata e plotë; filtrim aktiv/dokument. |
| [modules/documents.py](modules/documents.py) | Orkestrim CRUD: ngarko→procesim→indeks, edito, status, fshi, riindekso (një ose të gjitha), purge. |
| [modules/rag_pipeline.py](modules/rag_pipeline.py) | Zemra e sistemit: retrieve → **porta e refuzimit** → prompt i bazuar → LLM → citime; përmbledhje; përgjigje pa-RAG (për eksperimente). |
| [modules/llm_client.py](modules/llm_client.py) | Klient Ollama me retry transparent dhe error i qartë në shqip. |
| [modules/history.py](modules/history.py) | Ruajtja/leximi i `chat_history`. |
| [modules/export_docx.py](modules/export_docx.py) | Eksport Word i përgjigjeve dhe përmbledhjeve. |
| [modules/experiments.py](modules/experiments.py) | Harness RAG vs pa-RAG, vlerësim manual, eksport CSV. |
| [modules/ui.py](modules/ui.py) | Mbrojtëset e sesionit (`current_user`, `require_admin`). |
| [views/](views/) | Tetë faqet Streamlit, të filtruara sipas rolit nga `app.py`. |

### 3.3 Dy rrjedhat kryesore të të dhënave

**A) Indeksimi (admin ngarkon një dokument)** — `documents.add_document`:
```
Skedar (PDF/DOCX)
  → emër i sigurt (safe_filename)  → ruaj në data/uploads/
  → nxjerrje teksti faqe-për-faqe (PyMuPDF) ose i tërë (python-docx)
  → validim: nëse < 100 karaktere → NoExtractableTextError (skanim; pa OCR)
  → copëzim (i vetëdijshëm për "Neni N", përndryshe dritare 800/120 karaktere)
  → embedding me bge-m3  → indeksim në ChromaDB me metadata të plotë
  → rreshti i dokumentit (tip, institucion, vit, num_pages, total_chunks) në SQLite
```

**B) Pyetja (anti-halucinim)** — `rag_pipeline.answer_question`:
```
pyetje (shqip)
  → embedding i pyetjes (bge-m3)
  → retrieve top-k nga ChromaDB (vetëm dokumentet 'active', ose një i zgjedhur)
  → PORTA E REFUZIMIT:  nëse s'ka copëza OSE score_maks < MIN_SIMILARITY (0.38)
         → kthe REFUSAL_MESSAGE  (LLM-ja NUK thirret kurrë)  ⛔
  → filtro kontekstin te copëzat me score ≥ MIN_SIMILARITY
  → ndërto prompt të bazuar (SYSTEM_PROMPT + konteksti i numëruar [1],[2]…)
  → thirr LLM-në lokale (Ollama, temperaturë 0.2)
  → nëse dokument normativ → shto shënimin ligjor
  → kthe përgjigje + burimet (citime: filename, tip, institucion, faqe, fragment, score)
  → ruaj në chat_history + audit log
```

### 3.4 Natyra e komunikimit
- **View ↔ Module**: thirrje direkte funksionesh brenda të njëjtit proces (jo HTTP).
- **Module ↔ SQLite**: `sqlite3` përmes një context-manager-i `get_conn()` (commit/close automatik).
- **Module ↔ ChromaDB**: `PersistentClient` lokal (embedded), pa server.
- **`llm_client` ↔ Ollama**: i vetmi kufi rrjeti — thirrje **HTTP lokale** te `http://localhost:11434`
  (asnjë dalje nga makina).

---

## 4. Teknologjitë, framework-et dhe arsyet e zgjedhjes

| Teknologjia | Roli | Arsyeja e zgjedhjes |
|-------------|------|---------------------|
| **Python 3.13** | Gjuha bazë | Ekosistem i pasur ML/NLP; kërkohet nga specifikimi. Përdoret `py -3.13` në Windows për të shmangur stub-in e Microsoft Store. |
| **Streamlit** | UI web (multipage, shqip) | Zhvillim i shpejtë i UI në Python të pastër, pa frontend të veçantë; `st.navigation` jep navigim sipas rolit. Ideal për prototip tezash nga një zhvillues i vetëm. |
| **SQLite** | Të dhëna relacionale | Zero-config, file i vetëm, pa server — përputhet me kërkesën “fully-local”. WAL lejon lexues+shkrues konkurrentë (Streamlit rihap lidhje në çdo ndërveprim). |
| **ChromaDB** | Vector store | Embedded/persistent, pa server, mbështet metadata-filtering dhe hapësirë kosinus — e nevojshme për filtrim sipas dokumenteve aktive. |
| **PyMuPDF (fitz)** | Nxjerrje teksti PDF | I shpejtë, tekst faqe-për-faqe (ruan numrin e faqes për citime), render në PNG për parapamje pa varësi shtesë. |
| **python-docx** | Lexim/shkrim DOCX | Lexon dokumente Word të ngarkuara dhe gjeneron eksportet Word. |
| **Sentence-Transformers + BAAI/bge-m3** | Embeddings | bge-m3 është shumëgjuhësh i fortë me mbulim të mirë të shqipes; embeddings L2-normalizuar → kosinus = dot product. |
| **Ollama** | Runtime LLM lokal | Ekzekuton modele lokalisht (localhost:11434), pa cloud; ndërrim i lehtë modelesh. |
| **gemma2:9b / qwen2.5:3b** | LLM gjeneruese | `gemma2:9b` jep shqipe më të mirë (parazgjedhje në kod) por kërkon ~6GB RAM të lirë; `qwen2.5:3b` është më i sigurt për 16GB RAM. Zgjidhen nga sidebar-i. |
| **bcrypt** | Hash fjalëkalimesh | Standard industrie me salt; përdoret direkt (jo passlib, i cili është i papërputhshëm me bcrypt ≥ 5). |
| **msvc-runtime** (vetëm Windows) | Runtime nativ VC++ | Zgjidh “WinError 1114 / c10.dll” duke sjellë një runtime aktual VC++ pranë python.exe për torch/onnxruntime. |

**Të ndaluara me qëllim (jashtë fushëveprimit)**: API cloud (OpenAI/Claude), Docker, FastAPI, React,
mikroshërbime, OCR. Kjo është zgjedhje arkitekturore për të mbajtur sistemin lokal, të thjeshtë dhe të
verifikueshëm për një tezë.

---

## 5. Struktura e projektit dhe organizimi i kodit

```
doku/
├── app.py                     # Entrypoint: login, sesion, RBAC navigation
├── config.py                  # Parametrat qendrorë + përgatitja e runtime-it nativ
├── requirements.txt           # Varësitë (local-only)
├── secrets_local.py           # (opsional, git-ignored) kredencialet e admin-it
│
├── modules/                   # SHTRESA E LOGJIKËS (pa Streamlit, e testueshme veç)
│   ├── database.py            # skema + lidhje SQLite
│   ├── auth.py                # autentikim, role, sesione
│   ├── audit.py               # audit logging
│   ├── document_processor.py  # nxjerrje + validim + copëzim
│   ├── embeddings.py          # bge-m3
│   ├── vector_store.py        # ChromaDB
│   ├── documents.py           # CRUD dokumentesh
│   ├── rag_pipeline.py        # RAG + refuzim + përmbledhje
│   ├── llm_client.py          # klient Ollama
│   ├── history.py             # chat history
│   ├── export_docx.py         # eksport Word
│   ├── experiments.py         # harness eksperimentesh
│   └── ui.py                  # guards sesioni
│
├── views/                     # SHTRESA E PREZANTIMIT (faqe Streamlit)
│   ├── 1_Dashboard.py
│   ├── 2_Pyet_Dokumentet.py
│   ├── 3_Permbledhje_Dokumenti.py
│   ├── 4_Historiku.py
│   ├── 5_Admin_Dokumentet.py
│   ├── 6_Admin_Perdoruesit.py
│   ├── 7_Admin_Audit_Log.py
│   └── 8_Eksperimente.py
│
├── scripts/                   # mjete jashtë UI
│   ├── seed_sample_corpus.py  # mbush korpusin shembull
│   ├── seed_random_users.py   # krijon përdorues test
│   └── capture_screenshots.py # pamje ekrani për tezën
│
├── tests/
│   └── sample_questions.csv   # pyetjet për eksperimentet
│
├── data/                      # (auto-krijohet) uploads/, exports/, corpus/, chroma_db/, app.db
│
└── docs: README.md · SPEC.md · DOKUMENTACIONI.md · CLAUDE.md · RAPORT_TEKNIK.md
```

### 5.1 Parimet e organizimit
- **Ndarje e qartë prezantim/logjikë**: `views/` përmban vetëm UI (Streamlit) dhe i delegon gjithçka
  moduleve; `modules/` s’ka varësi nga Streamlit (përjashtim `ui.py`, që është ndihmës UI). Kjo i bën modulet
  të testueshme dhe të riperdorshme (p.sh. `scripts/` dhe `experiments.py` i thërrasin drejtpërdrejt).
- **Konfigurim i centralizuar**: çdo parametër i akordueshëm jeton në `config.py` (parim single-source-of-truth).
- **Auto-krijim**: dosjet, DB-ja dhe admin-i default krijohen automatikisht në nisje — “clone-and-run”.
- **Emërtim me numra për faqet** (`1_…8_`) përcakton renditjen në navigim.

---

## 6. Baza e të dhënave: modelet dhe marrëdhëniet

Sistemi përdor **dy depo të ndara** sipas natyrës së të dhënave:
- **SQLite** (`data/app.db`) — të dhëna relacionale/transaksionale.
- **ChromaDB** (`data/chroma_db`) — vektorët e copëzave + metadata për kërkim semantik.

### 6.1 Skema relacionale (SQLite, 6 tabela)

**`users`** — llogaritë dhe rolet
| Kolona | Tip | Shënim |
|--------|-----|--------|
| id | INTEGER PK | |
| username | TEXT UNIQUE | |
| password_hash | TEXT | bcrypt |
| full_name | TEXT | |
| role | TEXT | CHECK ∈ {`admin`, `punonjes`} |
| must_change_password | INTEGER | ndryshim i detyruar në hyrjen e parë |
| is_active | INTEGER | llogari e çaktivizuar s’lejohet hyrje |
| created_at / updated_at | TEXT | timestamps |

**`documents`** — metadata e korpusit (copëzat rrinë në ChromaDB)
| Kolona | Tip | Shënim |
|--------|-----|--------|
| id | INTEGER PK | lidhet me `document_id` në ChromaDB |
| filename | TEXT UNIQUE | emri i sigurt në disk |
| original_filename, stored_path | TEXT | |
| title, institution, document_type, year, description | | metadata e domenit |
| uploaded_by | TEXT | username i admin-it |
| status | TEXT | CHECK ∈ {`active`, `inactive`} |
| num_pages, total_chunks | INTEGER | |
| created_at / updated_at | TEXT | |

**`chat_history`** — pyetje/përgjigje të përdoruesve
| Kolona | Tip | Shënim |
|--------|-----|--------|
| id | INTEGER PK | |
| user_id, username | | kush e bëri pyetjen |
| question, answer | TEXT | |
| mode | TEXT | `rag` / `no_rag` / `summary` |
| selected_document_id | INTEGER | dokumenti i vetëm nëse u zgjodh |
| sources_json | TEXT | citimet e serializuara në JSON |
| response_time | REAL | sekonda |
| exported_to_word | INTEGER | |
| created_at | TEXT | |

**`audit_logs`** — gjurma e veprimeve
`id, user_id, username, action, details, created_at`. Veprimet e njohura: `login_success`, `login_failed`,
`logout`, `upload_document`, `update_document_metadata`, `delete_document`, `activate/deactivate_document`,
`reindex_document`, `ask_question`, `generate_summary`, `export_*_docx`, `create_user`, `run_experiment`,
`password_change`.

**`sessions`** — token-a sesioni të qëndrueshëm
`token (PK), user_id, username, created_at, expires_at`. Mundësojnë mbijetesën e hyrjes pas rifreskimit të
browser-it (Streamlit e humb `session_state` në reload).

**`experiment_results`** — të dhënat e vlerësimit
`question, answer_without_rag, answer_with_rag, time_without_rag, time_with_rag, chunks_used, has_sources,
manual_accuracy_without_rag, manual_accuracy_with_rag, hallucination_without_rag, hallucination_with_rag,
notes, created_at`.

### 6.2 Marrëdhëniet
SQLite-i këtu përdoret **denormalizuar qëllimisht** (mban edhe `username` përveç `user_id`) për logging të
qëndrueshëm edhe nëse një përdorues riemërtohet, dhe pa `FOREIGN KEY` të imponuara mes tabelave të logut.
Lidhjet logjike:

```
users (1) ───< (N) chat_history        [user_id / username]
users (1) ───< (N) audit_logs          [user_id / username]
users (1) ───< (N) sessions            [user_id]
documents (1) ─< (N) chat_history      [selected_document_id, opsional]

documents.id  ⇄  ChromaDB metadata.document_id   (lidhje ndër-depo)
              └── një dokument → N copëza → N vektorë
```

### 6.3 Modeli i vektorëve (ChromaDB, koleksioni `doku_chunks`)
Çdo copëz ruhet me:
- **id**: `"{document_id}:{chunk_index}"` (deterministik — riindeksimi zëvendëson pastër).
- **document** (teksti i copëzës) dhe **embedding** (vektor bge-m3 i normalizuar).
- **metadata**: `document_id, filename, title, institution, document_type, year, page_number, chunk_index,
  status`. Kjo metadata mundëson **citimet** dhe **filtrimin** (sipas dokumentit ose sipas listës së
  dokumenteve aktive) pa e prekur SQLite-in gjatë kërkimit.
- **Hapësira e ngjashmërisë**: kosinus (`hnsw:space: cosine`); `similarity = 1 − distance`.

---

## 7. Komunikimi frontend–backend dhe “endpoint-et” logjike

DOKU **nuk ka REST/HTTP API** (kërkesë e qëllimshme e specifikimit — pa FastAPI). Frontend-i (Streamlit) dhe
“backend-i” (modulet) jetojnë në **të njëjtin proces**; “endpoint-et” janë funksionet publike të moduleve që
faqet thërrasin drejtpërdrejt. Të vetmet kufij rrjeti janë **lokalë**: Ollama (localhost:11434) dhe skedarët
lokalë.

### 7.1 Modeli i interaksionit Streamlit
Streamlit rri-ekzekuton skriptin e faqes në çdo ndërveprim (rerun). Rrjedhimisht:
- Gjendja mbahet në `st.session_state` (p.sh. `st.session_state["last_qa"]` që e bën përgjigjen të
  qëndrueshme mes rerun-eve).
- Punët e shtrenjta (bootstrap i skemës, admin default) mbrohen me `@st.cache_resource` që të ekzekutohen
  një herë për proces.
- Navigimi bëhet me `st.navigation(pages).run()`, ku lista e faqeve filtrohet sipas rolit në [app.py](app.py).

### 7.2 “Endpoint-et” logjike kryesore (kontrata funksionale)
| “Endpoint” (funksion) | Thirret nga | Roli |
|-----------------------|-------------|------|
| `auth.authenticate(username, password)` | login | verifikim kredencialesh |
| `auth.create_session / resolve_session / delete_session` | login, çdo faqe | sesion i qëndrueshëm në URL |
| `rag_pipeline.answer_question(q, …)` | Pyet Dokumentet | RAG me refuzim + citime |
| `rag_pipeline.summarize(text, fmt)` | Përmbledhje | përmbledhje e dokumentit |
| `rag_pipeline.answer_without_rag(q)` | Eksperimente | baseline pa retrieval |
| `documents.add_document(...)` | Admin Dokumentet | ngarko+procesim+indeks |
| `documents.set_status / delete_document / reindex_*` | Admin Dokumentet | menaxhim korpusi |
| `vector_store.query(q, …)` | rag_pipeline | retrieval top-k i filtruar |
| `llm_client.generate(prompt, system)` | rag_pipeline | thirrja e vetme HTTP (Ollama) |
| `history.save / recent` | Pyet / Historiku | persistencë bisede |
| `audit.log / recent` | kudo | gjurmim veprimesh |
| `export_docx.export_answer_to_docx / export_summary_to_docx` | Pyet / Përmbledhje | eksport Word |

### 7.3 Protokolli me Ollama
`llm_client.generate` ndërton `messages=[{system}, {user}]`, dërgon `chat(model, messages, options={temperature})`
te Ollama dhe kthen `resp["message"]["content"]`. Ka **një retry transparent** (rindërton klientin nëse
lidhja httpx ka mbetur “closed” pas një OOM/rinisjeje modeli); nëse dështon prapë, ngre
`OllamaUnavailableError` me udhëzim në shqip (`ollama pull …`).

---

## 8. Autentikimi, autorizimi dhe siguria

### 8.1 Autentikim
- **Fjalëkalime me bcrypt** (me salt), asnjëherë plain-text; input-i pritet në 72 byte (kufiri i bcrypt).
- **Admin default i auto-krijuar** nëse s’ekziston asnjë admin. Kredencialet **nuk komitohen kurrë**; zgjidhen
  në runtime sipas përparësisë: (1) env `DOKU_ADMIN_USERNAME`/`DOKU_ADMIN_PASSWORD`, (2) `secrets_local.py`
  (git-ignored), (3) përndryshe gjenerohet një fjalëkalim i rastësishëm një-përdorimësh dhe printohet një herë
  në konsolë.
- **Ndryshim i detyruar**: admin-i default dhe çdo përdorues i ri/reset-uar shënohen `must_change_password=1`;
  hyrja nuk konsiderohet e përfunduar (sidebar-i mbahet i fshehur) derisa fjalëkalimi të ndryshohet.
- **Sesione të qëndrueshme**: token opak `secrets.token_urlsafe(32)` ruhet në tabelën `sessions` dhe mbahet në
  URL (`?sid=`), me TTL 12 orë dhe **skadim sliding** (zgjatet në çdo përdorim). Token-at e skaduar pastrohen;
  një përdorues i çaktivizuar e humb sesionin menjëherë.

### 8.2 Autorizim (RBAC)
- Dy role: **`admin`** (menaxhon korpus, përdorues, audit, eksperimente) dhe **`punonjes`** (vetëm-lexim).
- Zbatohet **në kod, jo vetëm në UI**: faqet admin thërrasin `ui.require_admin()` që bën `st.stop()` nëse roli
  s’është admin; përveç kësaj, [app.py](app.py) as nuk i shfaq faqet admin në navigim për punonjësit
  (mbrojtje me dy shtresa).
- **Pa vetë-regjistrim publik**: vetëm admin-i krijon llogari të reja.

### 8.3 Masat e tjera të sigurisë
- **Emra file të sigurt** (`safe_filename`): normalizim NFKD → ASCII, pastrim karakteresh, ruajtja e prapashtesës
  `.pdf/.docx` — mbron nga path-traversal dhe emra problematikë.
- **Validim input-i**: username 3–32 karaktere `[A-Za-z0-9_.]`, fjalëkalim ≥ 6 karaktere, role/status të
  kontrolluara nga `CHECK` në DB dhe në kod.
- **Audit i plotë**: çdo veprim ndjeshëm regjistrohet me përdorues + detaje.
- **Izolim total nga cloud**: asnjë përpunim/embedding/inferencë s’del nga makina; i vetmi kufi rrjeti është
  localhost:Ollama.
- **Robustësi konkurrence**: WAL + `busy_timeout=30000` + retry për “database is locked”, që mbrojnë nga
  korruptimi/dështimet kur Streamlit rihap lidhje shpesh ose dy instanca nisen njëkohësisht.

---

## 9. Performanca, optimizimet dhe praktikat më të mira

### 9.1 Optimizime performance
- **Modele të ngarkuara vonë dhe të cache-uara**: `embeddings.get_model()` dhe klientët ChromaDB/Ollama
  ngarkohen një herë (lazy singletons), jo në çdo rerun.
- **Embeddings të normalizuar**: L2-normalizim → kosinus reduktohet në dot product (më i lirë) dhe rezultati
  bie natyrshëm në `[−1, 1]`.
- **Filtrim para retrieval-it**: kërkimi kufizohet paraprakisht te dokumentet `active` (ose një i vetëm) me
  metadata-filter të ChromaDB — më pak copëza për të vlerësuar.
- **Refuzim para LLM-së**: porta e refuzimit e shmang thirrjen e shtrenjtë të LLM-së kur s’ka kontekst
  relevant — kursen kohë dhe eliminon halucinacionin njëkohësisht.
- **Eksport Word i para-gjeneruar një herë** dhe i mbajtur në `session_state`, që download-i të mos rigjenerojë.
- **Vlerësim ETA në Eksperimente**: `avg_run_seconds()` nxjerr kohën mesatare nga historiku për një progres-bar
  realist.

### 9.2 Praktika më të mira të ndjekura
- **Grounding is sacred**: prompt-i e detyron modelin të përgjigjet vetëm nga konteksti; temperaturë e ulët
  (0.2) për qëndrueshmëri; shënim ligjor automatik për dokumente normative.
- **Copëzim i vetëdijshëm për strukturën**: ndarje mbi kufijtë “Neni N” që çdo copëz të jetë një nen koherent
  → retrieval më i saktë dhe citime më të pastra; fallback te dritare 800/120 për tekst jo-ligjor.
- **Konfigurim i centralizuar** dhe **single-source-of-truth** për të gjithë parametrat.
- **Idempotencë & auto-recovery**: `init_schema` shkruan vetëm në DB bosh; retry-t e lockut; retry i klientit
  Ollama pas OOM.
- **Ndarje e shtresave** që bën modulet të testueshme pa Streamlit.
- **Trajtim i qartë gabimesh në shqip** në UI (Ollama jo aktiv, PDF i skanuar, kredenciale të pasakta).

### 9.3 Kalibrimi i pragut të refuzimit
`MIN_SIMILARITY = 0.38` është akorduar empirikisht: pyetjet brenda korpusit me diakritikë të saktë shënojnë
~0.70, ato pa diakritikë ~0.40, ndërsa pyetjet jashtë korpusit ≤0.35. Pragu 0.38 lejon pyetjet legjitime pa
diakritikë e refuzon ato jashtë korpusit — ndarje e qartë që e bën sistemin njëkohësisht të përgjegjshëm dhe të
sigurt kundër trillimit.

---

## 10. Procesi i zhvillimit dhe sfidat kryesore të zgjidhura

### 10.1 Procesi
Zhvillimi ka ndjekur një kontratë të qartë ([CLAUDE.md](CLAUDE.md)) me **kufizime të forta** (local-only, pa
scope-creep, grounding i shenjtë, siguri rolesh) dhe milestone të validueshme ([SPEC.md](SPEC.md)). Kodi u
ristrukturua në ndarjen `modules/` + `views/` sipas specit të tezës, me çdo milestone të mbyllur vetëm pasi
kalojnë kontrollet e tij. Aplikacioni shpërndahet me gjendje të para-ndërtuar (DB + indeks vektorial + upload)
për ekzekutim “clone-and-run”.

### 10.2 Sfidat kryesore dhe zgjidhjet
| Sfida | Zgjidhja |
|-------|----------|
| **Halucinacioni i LLM-ve** në kontekst institucional/ligjor | Porta e refuzimit *para* LLM-së + prompt i bazuar + citime të detyrueshme + temperaturë e ulët. |
| **Cilësia e shqipes** në embeddings dhe gjenerim | bge-m3 (shumëgjuhësh i fortë) për retrieval; `gemma2:9b` për gjenerim, me `qwen2.5:3b` si alternativë RAM-friendly. |
| **Kufizimet e RAM-it (16GB, RTX 3050 4GB)** | Ndërrim modeli nga UI; retry i klientit pas OOM; shënim eksplicit në config për të parashikuar “failed to allocate buffer”. |
| **“database is locked” në Windows/WAL** | Aktivizim WAL + `busy_timeout=30000` + retry me backoff në `connect`/`init_schema`; shkrim skeme vetëm kur mungon një tabelë. |
| **DLL native në Windows (WinError 1114, c10.dll)** | Paketa `msvc-runtime` + preload i DLL-ve VC++ në `config._prepare_native_runtime`; import i `torch` PARA `chromadb` për renditje të saktë ngarkimi dhe pajtim OpenMP. |
| **Humbja e sesionit në rifreskim** | Token sesioni i qëndrueshëm në SQLite + mbajtje në URL (`?sid=`) me skadim sliding. |
| **PDF të skanuar (pa tekst)** | Validim `validate_has_text` që refuzon me mesazh të qartë (pa OCR në versionin bazë). |
| **Siguria e kredencialeve në repo** | Asnjë kredencial i hardkoduar; env var / `secrets_local.py` / fjalëkalim i rastësishëm një-përdorimësh + ndryshim i detyruar. |
| **Copëzim që prishte nenet ligjore** | Copëzim i vetëdijshëm për “Neni N” me fallback në dritare me mbivendosje. |

---

## 11. Përmirësimet e mundshme dhe puna e ardhshme

### 11.1 Afatshkurtër
- **OCR opsional** (p.sh. Tesseract) për PDF të skanuar — aktualisht refuzohen.
- **Re-ranking** i copëzave të tërhequra (cross-encoder) për saktësi më të lartë të kontekstit.
- **Highlight i fragmentit** në parapamjen e PDF-së (rendering ekziston tashmë në `render_pdf_images`).
- **Kërkim hibrid** (semantik + BM25/fjalë-kyçe) për terma teknikë/emra të përveçëm.

### 11.2 Afatmesëm
- **Gjykatës AI dytësor** që vlerëson automatikisht bazimin/halucinacionin (plotëson vlerësimin manual).
- **Kontroll versionesh dokumentesh** (histori ndryshimesh, krahasim versionesh).
- **Metrika automatike vlerësimi** (precision@k, recall, kohë mesatare) drejtpërdrejt në faqen Eksperimente.
- **Kalibrim dinamik i pragut** për korpus real (aktualisht i akorduar mbi korpusin shembull).

### 11.3 Afatgjatë
- **Multi-tenant / institucione të shumta** me korpuse të izoluar.
- **Rrjedhë pyetjesh me kujtesë bisede** (multi-turn) duke ruajtur bazimin.
- **Eksport i pasur** (PDF me citime të klikueshme, raporte të përmbledhura).
- **Optimizim modeli** (kuantizim/GPU offloading i akorduar) për latencë më të ulët në pajisje modeste.

---

## Shtojcë: parametrat kryesorë (config.py)
| Parametër | Vlera | Kuptimi |
|-----------|-------|---------|
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | modeli i embeddings (shumëgjuhësh) |
| `OLLAMA_MODEL` | `gemma2:9b` | LLM-ja e parazgjedhur (ndërrohet nga UI) |
| `LLM_TEMPERATURE` | `0.2` | temperaturë e ulët për bazim |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `120` | copëzim me mbivendosje (karaktere) |
| `RETRIEVAL_K` | `5` | copëza top-k për pyetje |
| `MIN_SIMILARITY` | `0.38` | pragu i portës së refuzimit |
| `SESSION_TTL_HOURS` | `12` | jetëgjatësia e sesionit (sliding) |

---

*Ky raport është nxjerrë nga analiza e kodit aktual të projektit. Vlerat dhe sjelljet e përshkruara pasqyrojnë
gjendjen e burimit në kohën e hartimit (shih [config.py](config.py) dhe modulet përkatëse për burimin
autoritativ).*
