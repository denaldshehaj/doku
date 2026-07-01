# DOKU — Sistem Inteligjent Lokal për Analizë Dokumentesh Institucionale

DOKU është një aplikacion **plotësisht lokal** në gjuhën shqipe që analizon dokumente
institucionale PDF (Ligje, VKM, Strategji, Rregullore, Udhëzime, Raporte) duke përdorur
**RAG** (Retrieval-Augmented Generation) dhe një **LLM lokal** përmes Ollama. Pa shërbime
cloud. Punim Master Shkencor — Shkenca Kompjuterike dhe Inteligjencë Artificiale.

## Teknologjitë
Python · Streamlit (UI shqip, multipage) · SQLite · ChromaDB · PyMuPDF ·
Sentence Transformers (bge-m3) · Ollama (LLM lokal) · python-docx.

## Roli institucional
- **Administratori** ngarkon dhe mirëmban një korpus të centralizuar dokumentesh zyrtare.
- **Punonjësi** kërkon, pyet, përmbledh dhe eksporton — pa të drejtë ndryshimi të korpusit.

## Instalimi (Windows)
Baza e të dhënave, indeksi vektorial (ChromaDB) dhe korpusi janë **të përfshirë në repo**,
ndaj pas `git clone` mjafton të instalosh varësitë dhe të shkarkosh modelin lokal — **pa
rebuild**:
```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
ollama pull qwen2.5:3b         # modeli lokal (i rekomanduar); s'mund të përfshihet në git
streamlit run app.py
```
> **E vetmja varësi jashtë-git:** venv-i (`pip install`) dhe modeli Ollama (`ollama pull`).
> Korpusi (13 ligje reale), të 2179 copëzat e indeksuara, përdoruesit dhe konfigurimi vijnë
> gati brenda repos.

### Rindërtim i korpusit (opsional)
Nëse ndryshon dokumentet te `data/corpus/`, riindekso nga e para:
```powershell
python scripts\seed_sample_corpus.py --reset
```
> Modeli caktohet te `OLLAMA_MODEL` në `config.py` ose nga dropdown-i në sidebar
> (`qwen2.5:3b` më i shpejtë; `gemma2:9b` shqipe më e mirë por kërkon më shumë RAM).

## Kredencialet
Baza e përfshirë vjen me administratorin dhe disa përdorues demo:

| Përdoruesi | Fjalëkalimi | Roli  |
|------------|-------------|-------|
| `admin`    | `123456`    | admin |
| përdoruesit demo (`emri.mbiemri`) | `demo123` | punonjës/admin |

> ⚠️ **Siguri:** nëse e publikon repon, ndrysho fjalëkalimin e admin-it pas klonimit
> (faqja **Përdoruesit**), sepse baza e komituar përmban llogaritë me këto fjalëkalime.
> Nëse fshin `data/app.db`, në nisjen e parë rikrijohet admin-i default `admin`/`***REMOVED-CREDENTIAL***`
> (i detyruar të ndryshojë fjalëkalimin).

## Përdorimi
- **Ngarkim dokumenti (admin):** faqja *Dokumentet* → *Ngarko dokument të ri* → zgjidh PDF,
  vendos titullin, institucionin, tipin, vitin, përshkrimin → *Ngarko dhe indekso*.
- **Editim metadata (admin):** te çdo dokument → *✏️ Metadata* → ndrysho → *Ruaj*.
- **Aktivizo/Çaktivizo, Riindekso, Fshi (admin):** butonat te çdo dokument; *Riindekso korpusin*
  riindekson të gjithë.
- **Pyetje (punonjës):** faqja *Pyet Dokumentet* → filtro (tip/vit/institucion/fjalë kyçe) →
  zgjidh "të gjithë dokumentet aktive" ose një dokument → shkruaj pyetjen → *Kërko përgjigje*.
  Përgjigja shfaq **citimet** `[filename, tip, institucion, faqe]`. Nëse s'ka info të
  mjaftueshëm, sistemi e thotë qartë dhe nuk shpik.
- **Përmbledhje (punonjës):** faqja *Përmbledhje* → zgjidh dokumentin dhe formatin
  (E shkurtër / E detajuar / Pika kryesore / Për vendimmarrje institucionale) → *Gjenero*.
- **Eksport Word:** butonat *Shkarko në Word* për përgjigje dhe përmbledhje (ruhen te `data/exports/`).
- **Eksperiment RAG vs pa-RAG (admin):** faqja *Eksperimente* → *Ekzekuto pyetjet testuese*
  (`tests/sample_questions.csv`) → vlerëso manualisht saktësinë (1–5) dhe halucinacionin (Po/Jo)
  → *Eksporto në CSV* për kapitullin e Rezultateve.

## Struktura
```
app.py                # entrypoint: login, session, navigim sipas rolit
config.py             # parametrat (OLLAMA_MODEL, temperaturë, pragje, shtigje)
modules/              # auth, database, document_processor, embeddings, vector_store,
                      # rag_pipeline, llm_client, documents, history, audit, export_docx,
                      # experiments, ui
pages/                # 1_Dashboard … 8_Eksperimente (Streamlit multipage)
data/                 # uploads/, exports/, chroma_db/, app.db (krijohen automatikisht)
tests/sample_questions.csv
```

## Kufizimet
- Pa OCR — dokumentet e skanuara (pa tekst) zbulohen dhe refuzohen.
- Cilësia e përgjigjeve varet nga modeli lokal; `gemma2:9b` jep shqipe më të mirë se `qwen2.5:3b`.
- Pragu i ngjashmërisë (`MIN_SIMILARITY`) mund të rikalibrohet mbi korpus real.

## Ide për zhvillim të mëtejshëm
OCR opsional, rirenditje (re-ranking) e rezultateve, vlerësim me gjykatës AI dytësor,
mbështetje për formate të tjera (DOCX/HTML), kontroll versionesh të dokumenteve.

## Shënim
Çdo përgjigje dhe përmbledhje gjenerohet automatikisht me RAG + LLM lokal dhe **duhet
verifikuar me dokumentin origjinal**, që mbetet burimi zyrtar.
