"""Central configuration for DOKU. All tunables live here."""
from pathlib import Path

# --- Paths ---
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"        # source PDFs uploaded by admin
EXPORTS_DIR = DATA_DIR / "exports"        # generated .docx files
CHROMA_DIR = DATA_DIR / "chroma_db"       # persistent vector store
DB_PATH = DATA_DIR / "app.db"             # sqlite database

# --- Models (local only, no cloud) ---
EMBEDDING_MODEL = "BAAI/bge-m3"           # multilingual incl. Albanian
OLLAMA_MODEL = "qwen2.5:3b"               # local LLM via Ollama; i sigurt për 16GB RAM.
# Shënim: gemma2:9b jep shqipe më të mirë por kërkon ~6GB RAM të lirë (mund të dalë
# "failed to allocate buffer"). Zgjidhe nga dropdown-i kur ke RAM të mjaftueshëm.
OLLAMA_HOST = "http://localhost:11434"
LLM_TEMPERATURE = 0.2                      # low temperature for grounded answers

# --- Retrieval / chunking ---
CHUNK_SIZE = 800                           # characters per chunk (approx)
CHUNK_OVERLAP = 120
RETRIEVAL_K = 5                            # top-k chunks per query

# --- Grounding / refusal gate (never hallucinate) ---
MIN_SIMILARITY = 0.38                      # below this, the system refuses.
# 0.38 lejon pyetje pa diakritikë (që shënojnë ~0.40) ndërsa pyetjet jashtë-korpusi
# (≤0.35) refuzohen. Me diakritikë të saktë pyetjet brenda korpusit shënojnë ~0.70.
REFUSAL_MESSAGE = (
    "Nuk ka informacion të mjaftueshëm në dokumentet e ngarkuara "
    "për t'iu përgjigjur kësaj pyetjeje."
)

# --- Default administrator (auto-created if no admin exists) ---
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "***REMOVED-CREDENTIAL***"

# --- Domain enums ---
DOCUMENT_TYPES = ["Ligj", "VKM", "Strategji", "Rregullore", "Udhëzim", "Raport", "Tjetër"]
UPLOAD_TYPES = ["pdf", "docx"]            # formate të lejuara për ngarkim
INSTITUTIONS = [
    "Kuvendi i Shqipërisë",
    "Këshilli i Ministrave",
    "Ministria e Financave",
    "Ministria e Ekonomisë",
    "Ministria e Mbrojtjes",
    "Ministria e Brendshme",
    "Ministria e Drejtësisë",
    "Ministria e Arsimit dhe Sportit",
    "Ministria e Shëndetësisë",
    "Ministria e Infrastrukturës",
    "Ministria e Bujqësisë",
    "Ministria e Turizmit dhe Mjedisit",
    "AKSHI",
    "Agjencia e Prokurimit Publik",
    "Banka e Shqipërisë",
    "INSTAT",
    "Tjetër",
]
NORMATIVE_TYPES = {"Ligj", "VKM", "Rregullore", "Udhëzim"}  # trigger legal disclaimer
STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"

# Ensure required folders exist (auto-create).
for _d in (DATA_DIR, UPLOADS_DIR, EXPORTS_DIR, CHROMA_DIR):
    _d.mkdir(parents=True, exist_ok=True)
