# DOKU — Dokumentacioni Teknik

> Dokument teknik për punimin e Masterit: arkitektura, rrjedha e të dhënave, vendimet e
> dizajnit, mekanizmi anti-halucinim, siguria dhe vlerësimi. Për udhëzime ekzekutimi shih
> [README.md](README.md); për kontratën e zhvillimit shih [CLAUDE.md](CLAUDE.md).

## 1. Qëllimi
DOKU është një sistem **plotësisht lokal** për analizën e dokumenteve institucionale në
gjuhën shqipe, i bazuar te **RAG** dhe një LLM lokal (Ollama). Cilësia përcaktuese është
**bazimi strikt**: sistemi citon çdo pohim dhe **refuzon** kur korpusi nuk e mbështet
përgjigjen. Asnjë e dhënë nuk del nga makina lokale.

## 2. Arkitektura (modules/ + pages/)

```
┌───────────────────────────────────────────────────────────────┐
│  app.py — login, sesion, navigim sipas rolit (st.navigation)   │
│  pages/: Dashboard · Pyet · Përmbledhje · Historiku ·          │
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
   │ experiment_results│                 └────────────────┘
   └──────────────────┘
```

### Modulet
| Moduli | Përgjegjësia |
|--------|--------------|
| `config.py` | Parametrat: `OLLAMA_MODEL`, temperaturë 0.2, pragu i refuzimit, shtigjet, enum-et. |
| `modules/database.py` | Skema SQLite (5 tabela) + lidhje + auto-krijim. |
| `modules/auth.py` | bcrypt, role admin/punonjes, admin default, ndryshim i detyruar. |
| `modules/audit.py` | Regjistri i veprimeve. |
| `modules/document_processor.py` | PyMuPDF: nxjerrje, validim teksti (anti-skanim), copëzim. |
| `modules/embeddings.py` | bge-m3 (Sentence Transformers), vektorë të normalizuar. |
| `modules/vector_store.py` | ChromaDB; metadata e plotë e copëzës; filtrim sipas aktiv/dokument. |
| `modules/documents.py` | Menaxhim dokumentesh: ngarko/edito/status/fshi/riindekso(/të gjitha). |
| `modules/rag_pipeline.py` | Marrje → portë refuzimi → prompt i bazuar → LLM → citime; përmbledhje. |
| `modules/llm_client.py` | Klient Ollama (error i qartë në shqip nëse jo aktiv). |
| `modules/history.py` | Ruajtja e `chat_history`. |
| `modules/export_docx.py` | Eksport Word (përgjigje + përmbledhje) te `data/exports/`. |
| `modules/experiments.py` | Harness RAG vs pa-RAG + eksport CSV. |
| `modules/ui.py` | Mbrojtëset e sesionit (`current_user`, `require_admin`). |
| `pages/1..8` | Faqet Streamlit (multipage), të filtruara sipas rolit. |

## 3. Rrjedha e të dhënave

### 3.1 Indeksimi (admin ngarkon PDF)
1. Ruajtja e PDF-së në `data/uploads/` (emër i sigurt).
2. Nxjerrja e tekstit faqe-për-faqe (PyMuPDF).
3. Validimi: tekst < 100 karaktere → refuzohet (skanim; pa OCR).
4. Copëzimi (800/120 karaktere) me numrin e faqes.
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
- Dy role: **admin** (menaxhon korpusin, përdoruesit, audit, eksperimente) dhe **punonjes**
  (vetëm lexim). Kontroll në kod (`require_admin`), jo vetëm fshehje UI.
- Audit log për çdo veprim të rëndësishëm; emra file të sigurt në upload/eksport.

## 6. Vlerësimi (kapitulli i Rezultateve)
Moduli `experiments.py` + faqja *Eksperimente* ekzekuton `tests/sample_questions.csv` me dhe
pa RAG, dhe mat për çdo pyetje: kohën pa/me RAG, numrin e copëzave, praninë e citimeve,
vlerësimin manual të saktësisë (1–5) dhe halucinacionin (Po/Jo) për të dyja, plus shënime.
Rezultatet ruhen te `experiment_results` dhe eksportohen në **CSV** për tabelën krahasuese.

Gjetje paraprake (korpus shembull, bge-m3): pyetjet brenda korpusit shënojnë ngjashmëri
0.58–0.76 dhe marrin dokumentin e saktë; pyetjet jashtë korpusit ≤0.35 dhe refuzohen —
ndarje e qartë që e bën pragun 0.45 të sigurt.

## 7. Vendimet kryesore të dizajnit
- **bge-m3** për shqipen (shumëgjuhësh i fortë), i konfirmuar me teste.
- **ChromaDB + SQLite** të ndara (vektorë vs të dhëna relacionale), pa server.
- **Ollama lokal**: parazgjedhje `qwen2.5:3b` (i sigurt për 16GB); `gemma2:9b` jep cilësi
  më të lartë në shqip por kërkon më shumë RAM (mund të dalë OOM).
- **bcrypt drejtpërdrejt** (passlib i pamirëmbajtur me bcrypt ≥ 5).
- **Streamlit multipage** me `st.navigation` për navigim sipas rolit.

## 8. Kufizimet dhe puna e ardhshme
Pa OCR; cilësia varet nga modeli lokal dhe RAM-i; pragu rikalibrohet mbi korpus real.
E ardhmja: OCR opsional, rirenditje (re-ranking), gjykatës AI dytësor, kontroll versionesh.

## 9. Mjedisi
Windows 11 · Python 3.13 · 16GB RAM · RTX 3050 4GB · Ollama lokal.
