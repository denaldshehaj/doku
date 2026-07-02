# DOKU — Sistem Inteligjent Lokal për Analizë Dokumentesh Institucionale

DOKU është një aplikacion **plotësisht lokal** në gjuhën shqipe që analizon dokumente
institucionale PDF/DOCX (Ligje, VKM, Strategji, Rregullore, Udhëzime, Raporte) duke përdorur
**RAG** (Retrieval-Augmented Generation) dhe një **LLM lokal** përmes Ollama. Pa shërbime
cloud. Punim Master Shkencor — Shkenca Kompjuterike dhe Inteligjencë Artificiale.

## Teknologjitë
**Backend:** Python 3.13 · FastAPI (vetëm 127.0.0.1) · SQLite · ChromaDB · PyMuPDF ·
Sentence Transformers (bge-m3) · Ollama (LLM lokal) · python-docx.
**Frontend:** React 19 · Vite · TypeScript · Tailwind CSS 4 · TanStack Query
(SPA e ndërtuar shërbehet nga vetë FastAPI — një proces, një port, zero CORS).

## Roli institucional
- **Administratori** ngarkon dhe mirëmban një korpus të centralizuar dokumentesh zyrtare,
  menaxhon përdoruesit, sheh raportet/statistikat, audit log-un dhe eksperimentet.
- **Punonjësi** kërkon, pyet, përmbledh dhe eksporton — pa të drejtë ndryshimi të korpusit.

## Instalimi (Windows)
Indeksi vektorial (ChromaDB), korpusi (13 ligje reale, 2179 copëza) dhe frontend-i i
ndërtuar (`frontend/dist`) janë **të përfshirë në repo**, ndaj pas `git clone` mjafton:
```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
ollama pull qwen2.5:3b         # modeli lokal (i rekomanduar)
python run_api.py              # -> http://127.0.0.1:8000
```
> **Varësitë jashtë-git:** venv-i (`pip install`) dhe modeli Ollama (`ollama pull`).
> Baza SQLite (`data/app.db`) **nuk** komitohet (mban hash-e fjalëkalimesh); krijohet
> automatikisht në nisjen e parë.

### Kredencialet (nisja e parë)
Në nisjen e parë krijohet automatikisht administratori. Fjalëkalimi fillestar merret,
sipas radhës, nga: `DOKU_ADMIN_USERNAME`/`DOKU_ADMIN_PASSWORD` (env), `secrets_local.py`
(shih `secrets_local.example.py`), ose gjenerohet rastësisht dhe **printohet një herë në
konsolë**. Në hyrjen e parë kërkohet ndryshimi i fjalëkalimit. Punonjësit krijohen nga
admini (faqja *Përdoruesit*); nuk ka vetë-regjistrim.

### Rindërtim i korpusit (opsional)
```powershell
python scripts\seed_sample_corpus.py --reset
```
> Modeli caktohet te `OLLAMA_MODEL` në `config.py` ose nga paneli anësor (vetëm admin;
> `qwen2.5:3b` më i shpejtë, `gemma2:9b` shqipe më e mirë por kërkon më shumë RAM).

## Zhvillimi i frontend-it
```powershell
cd frontend
npm install
npm run dev      # Vite në :5173, proxy /api -> :8000
npm run build    # tsc + vite -> frontend/dist (që shërben FastAPI)
npm run lint
```
Testet e API-së: `python -m pytest tests\` (DB e izoluar e përkohshme; s'kërkon Ollama).

## Përdorimi
- **Biseda (pyetje RAG):** filtro sipas tipit/vitit/institucionit ose zgjidh një dokument
  → shkruaj pyetjen. Përgjigja shfaq **citimet** (dokument, tip, institucion, faqe) dhe
  score-in e ngjashmërisë; paneli anësor liston fragmentet e cituara. Nëse s'ka informacion
  të mjaftueshëm, sistemi **refuzon** (pa e thirrur fare modelin) në vend që të shpikë.
- **Përmbledhje:** zgjidh dokumentin + formatin (E shkurtër / E detajuar / Pika kryesore /
  Për vendimmarrje institucionale) → *Gjenero* → eksport në Word.
- **Historiku:** pyetjet/përmbledhjet e tua me burime, kërkim dhe ri-eksport.
- **Dokumentet (admin):** ngarkim me drag & drop (PDF/DOCX), metadata, aktivizim/çaktivizim,
  riindeksim (një ose të gjithë, me progres), parapamje PDF, shkarkim, fshirje.
- **Raporte & Statistika (admin):** KPI me ndryshim ndaj periudhës paraardhëse, grafikë
  përdorimi, citime sipas tipit, dokumentet më të përdorura, aktiviteti për përdorues;
  eksport CSV (Excel) dhe printim/PDF. Të gjitha nga të dhënat reale të regjistruara.
- **Eksperimente (admin):** RAG kundrejt pa-RAG mbi `tests/sample_questions.csv`, vlerësim
  manual (saktësi 1–5, halucinacion Po/Jo), eksport CSV për kapitullin e Rezultateve.
- **Audit Log (admin):** çdo veprim i rëndësishëm, i kërkueshëm dhe i filtueshëm.

## Struktura
```
config.py             # parametrat (OLLAMA_MODEL, temperaturë, pragje, shtigje)
modules/              # bërthama: auth, database, document_processor, embeddings,
                      # vector_store, rag_pipeline, llm_client, documents, history,
                      # audit, export_docx, experiments
api/                  # shtresa FastAPI mbi modules/ (routers, deps, tasks, schemas)
run_api.py            # nisja e serverit (127.0.0.1:8000; SPA + /api + /api/docs)
frontend/             # React SPA (src/…) + dist/ (build i komituar)
data/                 # corpus/, uploads/, exports/, chroma_db/ (app.db krijohet vetë)
tests/                # sample_questions.csv + testet e API-së
```

## Kufizimet
- Pa OCR — dokumentet e skanuara (pa tekst) zbulohen dhe refuzohen.
- Cilësia e përgjigjeve varet nga modeli lokal; `gemma2:9b` jep shqipe më të mirë se `qwen2.5:3b`.
- Pragu i ngjashmërisë (`MIN_SIMILARITY`) mund të rikalibrohet mbi korpus real.

## Ide për zhvillim të mëtejshëm
OCR opsional, rirenditje (re-ranking) e rezultateve, vlerësim me gjykatës AI dytësor,
kontroll versionesh të dokumenteve.

## Shënim
Çdo përgjigje dhe përmbledhje gjenerohet automatikisht me RAG + LLM lokal dhe **duhet
verifikuar me dokumentin origjinal**, që mbetet burimi zyrtar.
