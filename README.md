# DOKU — Analizë Inteligjente e Dokumenteve (RAG lokal, shqip)

Sistem **plotësisht lokal** për analizën e dokumenteve institucionale në gjuhën
shqipe, i ndërtuar me **RAG** (Retrieval-Augmented Generation) dhe një **model
gjuhësor lokal** (Ollama). Pa shërbime cloud. Punim Master në Shkenca Kompjuterike
dhe Inteligjencë Artificiale.

## Veçoritë
- 🔐 Autentikim me role: **admin** (menaxhon dokumentet) / **punonjës** (vetëm lexim)
- 📄 Menaxhim dokumentesh (vetëm admin): ngarko, fshi, riindekso, ndrysho metadata
- ❓ Pyetje-përgjigje mbi korpusin me **citime** dhe **bazim strikt** te dokumentet
- 🛑 **Nuk halucinon**: nëse informacioni nuk gjendet → _"Nuk u gjet në dokumente."_
- 📝 Përmbledhje dokumentesh në disa formate
- 📤 Eksport në Word (.docx) për përgjigje dhe përmbledhje
- 🧪 Modul eksperimenti: krahasim **RAG kundrejt LLM pa dokumente**
- 📋 Regjistër veprimesh (audit log)

## Si funksionon bazimi (anti-halucinim)
Pipeline-i: `marrje top-k → portë refuzimi → prompt i bazuar me burime → LLM → përgjigje e cituar`.
Porta e refuzimit (shih `config.MIN_SIMILARITY`) ekzekutohet **para** modelit: nëse
asnjë copëzë nuk e kalon pragun e ngjashmërisë, sistemi refuzon pa e thirrur fare
modelin — kështu fabrikimi bëhet strukturalisht i pamundur për pyetje jashtë korpusit.

## Kërkesat
- Windows 11, Python 3.13 (përdoret `py -3.13`)
- [Ollama](https://ollama.com) i instaluar dhe aktiv
- ~16GB RAM (RTX 3050 opsionale për përshpejtim)

## Instalimi
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Modeli lokal (në një terminal të ri, që Ollama të jetë në PATH):
ollama pull qwen2.5:3b

# Inicializo bazën dhe (opsionale) korpusin shembull:
.\.venv\Scripts\python.exe seed.py
.\.venv\Scripts\python.exe scripts\make_sample_corpus.py
```

## Ekzekutimi
```powershell
.\.venv\Scripts\streamlit run app.py
```

### Llogaria e parë
Nuk ka kredenciale të parazgjedhura. Te aplikacioni, përdor skedën **“Regjistrohu”**:
**llogaria e parë e regjistruar bëhet administrator**, ndërsa regjistrimet e mëvonshme
bëhen **punonjës**. Administratori mund të krijojë përdorues të tjerë nga paneli.

## Testimi
```powershell
.\.venv\Scripts\python.exe tests\smoke_test.py       # logjika bazë (pa Ollama)
.\.venv\Scripts\python.exe tests\grounding_test.py   # bazimi + refuzimi (10 Q&A)
.\.venv\Scripts\python.exe spikes\embedding_spike.py # cilësia e embeddings shqip
```

## Struktura
```
config.py            # të gjitha parametrat (modele, pragje, k, madhësia e copëzës)
app.py               # UI Streamlit (shqip), me role
doku/
  db.py              # SQLite: users, documents, audit, history, experiments
  auth.py            # autentikim, hash bcrypt, role, ndryshim fjalëkalimi
  ingestion.py       # PyMuPDF: nxjerrje, validim teksti, copëzim
  embeddings.py      # bge-m3 (Sentence Transformers)
  vectorstore.py     # ChromaDB (kosinus, distancë→ngjashmëri)
  rag.py             # pipeline RAG + porta e refuzimit + përmbledhje
  llm.py             # klient Ollama lokal
  documents.py       # menaxhim dokumentesh (admin)
  export.py          # eksport Word
  experiment.py      # RAG vs jo-RAG
  audit.py / history.py
scripts/make_sample_corpus.py   # korpus shembull shqip
tests/               # smoke + grounding
spikes/              # spike i embeddings
```

## Dokumentacioni
- [DOKUMENTACIONI.md](DOKUMENTACIONI.md) — dokument teknik (arkitektura, vlerësimi, vendimet)
- [SPEC.md](SPEC.md) — arkitektura, milestone-t, kriteret e "done"
- [CLAUDE.md](CLAUDE.md) — kontrata e zhvillimit / kufizimet
