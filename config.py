"""Central configuration for DOKU. All tunables live here (CLAUDE.md rule)."""
from pathlib import Path

# --- Paths ---
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"      # uploaded source PDFs
CHROMA_DIR = DATA_DIR / "chroma"            # persistent vector store
DB_PATH = DATA_DIR / "doku.db"              # sqlite: users, logs, history, experiments

# --- Models (local only) ---
EMBEDDING_MODEL = "BAAI/bge-m3"             # multilingual, incl. Albanian; pending M0 spike
LLM_MODEL = "qwen2.5:3b"                    # via Ollama; alt: llama3.2:3b
OLLAMA_HOST = "http://localhost:11434"

# --- Retrieval / chunking ---
CHUNK_SIZE = 800                            # characters per chunk (approx)
CHUNK_OVERLAP = 120
RETRIEVAL_K = 5                             # top-k chunks per query

# --- Grounding / refusal gate (the "never hallucinate" contract) ---
# bge-m3 cosine similarity in [0,1]; below this, the system refuses.
# Calibrated during M0/M1 against the Albanian test set.
MIN_SIMILARITY = 0.45
REFUSAL_MESSAGE = "Nuk u gjet në dokumente."

# --- Language ---
UI_LANGUAGE = "sq"  # Albanian

for _d in (DATA_DIR, DOCUMENTS_DIR, CHROMA_DIR):
    _d.mkdir(parents=True, exist_ok=True)
