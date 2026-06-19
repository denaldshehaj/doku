# DOKU — Dokumentacioni Teknik

> Dokument teknik për punimin e Masterit. Përshkruan arkitekturën, rrjedhën e të
> dhënave, vendimet e dizajnit, mekanizmin anti-halucinim, sigurinë dhe vlerësimin.
> Për udhëzime instalimi/ekzekutimi shih [README.md](README.md); për kontratën e
> zhvillimit shih [CLAUDE.md](CLAUDE.md) dhe [SPEC.md](SPEC.md).

## 1. Qëllimi
DOKU është një sistem **plotësisht lokal** për analizën e dokumenteve institucionale
në gjuhën shqipe, i bazuar te **Retrieval-Augmented Generation (RAG)** dhe një model
gjuhësor lokal (Ollama). Cilësia përcaktuese është **bazimi strikt**: sistemi citon
çdo pohim dhe **refuzon** kur korpusi nuk e mbështet përgjigjen. Asnjë e dhënë nuk
del jashtë makinës lokale.

## 2. Arkitektura

```
┌───────────────────────────────────────────────────────────────┐
│                     UI (Streamlit, shqip)                      │
│   Login → (ndryshim fjalëkalimi) → faqe sipas rolit            │
│   Pyetje · Përmbledhje · Dokumentet · Eksperimente · Audit     │
└───────────────┬───────────────────────────────────────────────┘
                │
   ┌────────────┼───────────────────────────────────────────────┐
   │ auth       │ rag (porta e refuzimit)   │ documents          │
   │ (RBAC,     │   ↓                       │ (ngarko/fshi/      │
   │  bcrypt)   │ vectorstore ── embeddings │  riindekso)        │
   │            │   (ChromaDB)   (bge-m3)   │   ↓                │
   │            │   ↓                       │ ingestion (PyMuPDF)│
   │            │ llm (Ollama, qwen2.5:3b)  │                    │
   └────────────┴───────────────────────────┴────────────────────┘
                │                                   │
        ┌───────┴────────┐                  ┌───────┴────────┐
        │ SQLite         │                  │ ChromaDB       │
        │ users, audit,  │                  │ copëzat +      │
        │ history, docs, │                  │ vektorët       │
        │ experiments    │                  │ (kosinus)      │
        └────────────────┘                  └────────────────┘
```

### Modulet
| Moduli | Përgjegjësia |
|--------|--------------|
| `config.py` | Të gjithë parametrat: modele, prag refuzimi, k, madhësi copëze. |
| `doku/db.py` | SQLite: skema + migrime + lidhje. |
| `doku/auth.py` | Autentikim, hash bcrypt, role, ndryshim fjalëkalimi. |
| `doku/ingestion.py` | Nxjerrje teksti (PyMuPDF), validim (anti-skanim), copëzim. |
| `doku/embeddings.py` | Embeddings bge-m3 (Sentence Transformers), të normalizuar. |
| `doku/vectorstore.py` | ChromaDB (kosinus), distancë→ngjashmëri. |
| `doku/rag.py` | Pipeline RAG, porta e refuzimit, prompt i bazuar, përmbledhje. |
| `doku/llm.py` | Klient Ollama lokal, zgjedhje modeli. |
| `doku/documents.py` | Menaxhim dokumentesh (admin). |
| `doku/export.py` | Eksport Word (.docx). |
| `doku/experiment.py` | Krahasim RAG vs LLM pa dokumente. |
| `doku/audit.py`, `doku/history.py` | Regjistër veprimesh dhe historik pyetjesh. |
| `app.py` | UI Streamlit (shqip), me role. |

## 3. Rrjedha e të dhënave

### 3.1 Indeksimi (admin ngarkon PDF)
1. **Ruajtja** e PDF-së në `data/documents/`.
2. **Nxjerrja** e tekstit faqe-për-faqe me PyMuPDF.
3. **Validimi**: nëse teksti i lexueshëm < 100 karaktere → refuzohet (ndoshta skanim;
   versioni bazë nuk ka OCR).
4. **Copëzimi** në dritare me mbivendosje (800 / 120 karaktere), ruhet faqja burimore.
5. **Embedding** me bge-m3 (vektorë të normalizuar).
6. **Indeksimi** në ChromaDB; metadata e dokumentit në SQLite.

### 3.2 Pyetja (anti-halucinim)
```
pyetje → embedding → marrje top-k (ChromaDB)
        → PORTA E REFUZIMIT: nëse ngjashmëria më e lartë < MIN_SIMILARITY
              → "Nuk u gjet në dokumente."  (LLM-ja nuk thirret kurrë)
        → filtrim i kontekstit te copëzat përkatëse
        → prompt i bazuar me burime të numëruara
        → LLM lokal (Ollama)
        → përgjigje me citime [n]
```

## 4. Mekanizmi anti-halucinim
- **Porta e refuzimit ekzekutohet PARA modelit.** Nëse asnjë copëz nuk e kalon
  pragun `MIN_SIMILARITY` (0.45), sistemi refuzon pa e thirrur fare LLM-në — kështu
  fabrikimi bëhet strukturalisht i pamundur për pyetje jashtë korpusit.
- **Prompt i kufizuar**: modeli udhëzohet të përgjigjet vetëm nga burimet, të citojë
  me `[n]`, dhe të kthejë fjalinë e refuzimit nëse informacioni mungon.
- **Temperaturë 0** për përgjigje deterministike.
- **Filtrim konteksti**: kur filtri është "të gjitha dokumentet", copëzat jashtë teme
  hiqen nga konteksti që përgjigja të mos hollohet.

## 5. Siguria dhe RBAC
- Fjalëkalimet ruhen me **bcrypt** (asnjëherë në tekst të thjeshtë).
- Dy role: **admin** (menaxhon korpusin, përdoruesit, audit) dhe **punonjës**
  (vetëm lexim: pyetje, përmbledhje, eksperimente, historik).
- Kontrolli i rolit bëhet **në kod** (`require_admin`), jo vetëm duke fshehur UI-në.
- **Ndryshim i detyruar i fjalëkalimit** në hyrjen e parë të admin-it.
- Çdo hyrje dhe veprim i privilegjuar shkruhet në regjistrin e auditimit.

## 6. Vlerësimi
Suita `tests/grounding_test.py` (10 pyetje + 1 gjenerim) mbi korpusin shembull:

| Lloji i pyetjes | Ngjashmëria | Rezultati |
|-----------------|-------------|-----------|
| Brenda korpusit (8) | 0.586 – 0.761 | ✅ dokumenti i saktë u mor |
| Jashtë korpusit (2) | 0.242, 0.330 | ✅ u refuzua |
| Gjenerim me citime (1) | — | ✅ përgjigje e bazuar dhe e cituar |

**Rezultati: 11/11.** Ndarja e qartë mes përkatëses (≥0.586) dhe jo-përkatëses
(≤0.330) e vendos pragun 0.45 në një zonë të sigurt. Kjo konfirmon bge-m3 si zgjedhjen
e duhur për shqipen dhe vlefshmërinë e portës së refuzimit.

`tests/smoke_test.py` validon logjikën bazë (copëzim, validim teksti, hash fjalëkalimi)
pa varësi nga Ollama.

## 7. Vendimet kryesore të dizajnit
- **bge-m3** (jo modele njëgjuhëshe angleze): mbështetje e fortë shumëgjuhëshe përfshirë
  shqipen; e konfirmuar me spike + teste.
- **ChromaDB + SQLite** (jo një bazë e vetme): vektorët në Chroma, të dhënat relacionale
  (përdorues, audit, metadata) në SQLite — secila mjet për qëllimin e vet, pa server.
- **Ollama lokal** (jo API cloud): kërkesë thelbësore privatësie/lokaliteti.
- **bcrypt drejtpërdrejt** (jo passlib): passlib është i pamirëmbajtur dhe prishet me
  bcrypt ≥ 5.
- **Streamlit** (jo FastAPI/React): UI e shpejtë, e demonstrueshme, akademike.

## 8. Kufizimet dhe puna e ardhshme
- **Pa OCR**: dokumentet e skanuara nuk mbështeten (zbulohen dhe refuzohen).
- **Modele 3B**: përgjigjet janë të sakta por të përmbledhura; modele më të mëdha do të
  jepnin përgjigje më të pasura (me kosto RAM/GPU).
- **Pragu** mund të rikalibohet mbi dokumente reale (vlera 0.45 është pikënisje e mirë).
- E ardhmja: rirenditje (re-ranking), OCR opsional, vlerësim me gjykatës AI dytësor.

## 9. Mjedisi
Windows 11 · Python 3.13 · ~16GB RAM · RTX 3050 (opsionale) · Ollama lokal.
