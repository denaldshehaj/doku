"""Central configuration for DOKU. All tunables live here."""
import os
import sys
from pathlib import Path


def _prepare_native_runtime() -> None:
    """Windows: make PyTorch / onnxruntime native DLLs load reliably.

    Their c10.dll / onnxruntime_pybind11_state need a current Microsoft Visual C++
    runtime; an older system copy causes "WinError 1114" load failures. The
    `msvc-runtime` package (see requirements.txt) drops a current runtime next to
    python.exe (the Scripts dir). We preload those DLLs here — before torch or
    chromadb import anywhere — so every later native load finds the good runtime.
    We also allow duplicate OpenMP runtimes (torch + onnxruntime) instead of
    aborting the process. All best-effort: failures never block startup."""
    if sys.platform != "win32":
        return
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    try:
        import ctypes
        scripts_dir = os.path.dirname(sys.executable)
        for name in (
            "vcruntime140.dll", "vcruntime140_1.dll", "concrt140.dll",
            "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll",
            "msvcp140_atomic_wait.dll", "msvcp140_codecvt_ids.dll",
        ):
            dll = os.path.join(scripts_dir, name)
            if os.path.exists(dll):
                try:
                    ctypes.WinDLL(dll)
                except OSError:
                    pass
    except Exception:
        pass


_prepare_native_runtime()

# --- Paths ---
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CORPUS_DIR = DATA_DIR / "corpus"          # master knowledge-base PDFs (seed source)
UPLOADS_DIR = DATA_DIR / "uploads"        # working copies indexed by the system
EXPORTS_DIR = DATA_DIR / "exports"        # generated .docx files
CHROMA_DIR = DATA_DIR / "chroma_db"       # persistent vector store
DB_PATH = DATA_DIR / "app.db"             # sqlite database

# --- Models (local only, no cloud) ---
EMBEDDING_MODEL = "BAAI/bge-m3"           # multilingual incl. Albanian
OLLAMA_MODEL = "gemma2:9b"                # local LLM via Ollama; shqipe më e mirë.
# Shënim: gemma2:9b jep shqipe më të mirë por kërkon ~6GB RAM të lirë (mund të dalë
# "failed to allocate buffer" në 16GB RAM kur bge-m3 është ngarkuar). Nëse del OOM,
# zgjidh `qwen2.5:3b` nga dropdown-i në sidebar — më i sigurt për RAM të kufizuar.
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
# For security the real credentials are NEVER committed to the repo. They are
# resolved at runtime from, in order of precedence:
#   1. Environment variables  DOKU_ADMIN_USERNAME / DOKU_ADMIN_PASSWORD
#   2. A git-ignored  secrets_local.py  (ADMIN_USERNAME / ADMIN_PASSWORD)
#   3. If neither is set, auth.ensure_default_admin() generates a random one-time
#      password and prints it once to the console.
# The default admin is always forced to change its password on first login, so
# this bootstrap value is only ever used a single time.
def _local_secret(name: str):
    try:
        import secrets_local
    except Exception:
        return None
    return getattr(secrets_local, name, None)

DEFAULT_ADMIN_USERNAME = (
    os.environ.get("DOKU_ADMIN_USERNAME") or _local_secret("ADMIN_USERNAME") or "admin"
)
DEFAULT_ADMIN_PASSWORD = (
    os.environ.get("DOKU_ADMIN_PASSWORD") or _local_secret("ADMIN_PASSWORD") or None
)

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
for _d in (DATA_DIR, CORPUS_DIR, UPLOADS_DIR, EXPORTS_DIR, CHROMA_DIR):
    _d.mkdir(parents=True, exist_ok=True)
