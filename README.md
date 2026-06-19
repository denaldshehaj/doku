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

## Instalimi (Windows 11)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
ollama pull gemma2:9b          # ose: ollama pull qwen2.5:3b (më i shpejtë)
python scripts\seed_sample_corpus.py   # opsionale: korpus shembull
streamlit run app.py
```
> Variabli i modelit: `OLLAMA_MODEL` te `config.py` (temperaturë e ulët 0.2).
> Nëse Ollama nuk është aktive, sistemi shfaq error të kuptueshëm në shqip.

## Kredencialet default
Në nisjen e parë krijohet automatikisht administratori:

| Përdoruesi | Fjalëkalimi | Roli  |
|------------|-------------|-------|
| `admin`    | `***REMOVED-CREDENTIAL***`  | admin |

> ⚠️ Në hyrjen e parë, admin-i **detyrohet të ndryshojë fjalëkalimin**. Punonjësit krijohen
> nga administratori (faqja **Përdoruesit**) dhe gjithashtu ndryshojnë fjalëkalimin në hyrje.

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
