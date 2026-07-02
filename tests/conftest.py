"""API test fixtures.

The whole suite runs against a throwaway SQLite database in a temp directory —
the real data/app.db is never touched. Heavy externals are stubbed out:
embeddings/ChromaDB (vector_store.count/query) and Ollama (llm_client), so the
suite runs anywhere in seconds and asserts that the LLM is NOT called when the
refusal gate fires.
"""
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402

# Point the DB at a temp file BEFORE anything opens a connection.
_TMP = Path(tempfile.mkdtemp(prefix="doku_test_"))
config.DB_PATH = _TMP / "test_app.db"

from fastapi.testclient import TestClient  # noqa: E402

from modules import auth, database, llm_client, vector_store  # noqa: E402
from api import main as api_main  # noqa: E402
from api.routers import auth_router  # noqa: E402

# No bge-m3 warmup in tests.
api_main._warm_embeddings = lambda: None


class LLMCalled(AssertionError):
    """Raised if any test path reaches the local LLM — it must never happen."""


@pytest.fixture(scope="session")
def client():
    database._schema_ready = False

    # Stub the vector store: empty index -> every question hits the refusal gate.
    vector_store.count = lambda: 0
    vector_store.query = lambda *a, **k: []

    # The LLM must be unreachable from tests.
    def _no_llm(*a, **k):
        raise LLMCalled("LLM u thirr gjatë testeve — porta e refuzimit duhej ta ndalonte.")
    llm_client.generate = _no_llm
    llm_client.generate_stream = _no_llm
    llm_client.is_available = lambda: False
    llm_client.list_models = lambda: []

    with TestClient(api_main.app) as c:
        auth.create_user("testadmin", "admin123", "Test Admin", "admin",
                         must_change=False, department="IT")
        auth.create_user("testuser", "user1234", "Test User", "punonjes",
                         must_change=False, department="Financa")
        auth.create_user("newbie", "fillim1", "Newbie", "punonjes",
                         must_change=True)
        yield c


@pytest.fixture(autouse=True)
def _reset_login_throttle():
    auth_router._failures.clear()
    yield
    auth_router._failures.clear()


def login_headers(client: TestClient, username: str, password: str) -> dict:
    r = client.post("/api/auth/login",
                    json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    token = r.cookies.get("doku_sid")
    assert token, "login duhet të vendosë cookie doku_sid"
    client.cookies.clear()  # keep the shared client stateless between roles
    return {"Cookie": f"doku_sid={token}"}


@pytest.fixture()
def admin_headers(client):
    return login_headers(client, "testadmin", "admin123")


@pytest.fixture()
def user_headers(client):
    return login_headers(client, "testuser", "user1234")
