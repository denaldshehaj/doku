"""API contract tests: auth, guards, RAG refusal gate, users, reports, headers.

Run:  .venv\\Scripts\\python -m pytest tests\\ -q
"""
from tests.conftest import login_headers


# --- Auth ---------------------------------------------------------------------

def test_me_unauthenticated_is_200_null(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json() is None


def test_login_wrong_password(client):
    r = client.post("/api/auth/login",
                    json={"username": "testuser", "password": "gabim"})
    assert r.status_code == 401


def test_login_throttled_after_5_failures(client):
    for _ in range(5):
        client.post("/api/auth/login",
                    json={"username": "sulmues", "password": "x"})
    r = client.post("/api/auth/login", json={"username": "sulmues", "password": "x"})
    assert r.status_code == 429


def test_login_and_me(client, user_headers):
    r = client.get("/api/auth/me", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "testuser"
    assert body["role"] == "punonjes"
    assert body["must_change_password"] is False


def test_logout_invalidates_session(client):
    headers = login_headers(client, "testuser", "user1234")
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/dashboard", headers=headers).status_code == 401


def test_forced_password_change_gate(client):
    headers = login_headers(client, "newbie", "fillim1")
    # Any normal endpoint is blocked with a typed 403 until the change happens.
    r = client.get("/api/dashboard", headers=headers)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "password_change_required"
    # The change itself is allowed, then the account works.
    r = client.post("/api/auth/change-password",
                    json={"new_password": "sekret9"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["must_change_password"] is False
    assert client.get("/api/dashboard", headers=headers).status_code == 200


# --- Role guards -----------------------------------------------------------------

def test_admin_endpoints_forbidden_for_employee(client, user_headers):
    for path in ("/api/users", "/api/audit", "/api/reports", "/api/experiments"):
        assert client.get(path, headers=user_headers).status_code == 403, path


def test_employee_cannot_see_inactive_documents(client, user_headers):
    r = client.get("/api/documents?active_only=false", headers=user_headers)
    assert r.status_code == 200
    assert all(d["status"] == "active" for d in r.json())


# --- Users management (admin) ------------------------------------------------------

def test_user_crud_with_department(client, admin_headers):
    r = client.post("/api/users", headers=admin_headers, json={
        "username": "eprovuar", "password": "provim1", "full_name": "E Provuar",
        "department": "Arkiva", "role": "punonjes"})
    assert r.status_code == 201
    assert r.json()["department"] == "Arkiva"

    r = client.patch("/api/users/eprovuar", headers=admin_headers,
                     json={"department": "Sekretaria", "full_name": "E Provuar 2"})
    assert r.status_code == 200
    assert r.json()["department"] == "Sekretaria"
    assert r.json()["full_name"] == "E Provuar 2"

    # New users must change the password on first login.
    h = login_headers(client, "eprovuar", "provim1")
    assert client.get("/api/dashboard", headers=h).status_code == 403


def test_last_active_admin_is_protected(client, admin_headers):
    # Deactivate every other active admin, keeping only testadmin.
    users = client.get("/api/users", headers=admin_headers).json()
    others = [u for u in users
              if u["role"] == "admin" and u["is_active"] and u["username"] != "testadmin"]
    for u in others:
        r = client.patch(f"/api/users/{u['username']}", headers=admin_headers,
                         json={"is_active": False})
        assert r.status_code == 200
    try:
        r = client.patch("/api/users/testadmin", headers=admin_headers,
                         json={"role": "punonjes"})
        assert r.status_code == 409  # would leave zero active admins
    finally:
        for u in others:
            client.patch(f"/api/users/{u['username']}", headers=admin_headers,
                         json={"is_active": True})


# --- RAG: the refusal gate never calls the LLM ----------------------------------------

def test_ask_refuses_without_calling_llm(client, user_headers):
    r = client.post("/api/chat/ask", headers=user_headers,
                    json={"question": "Sa është lartësia e Everestit?"})
    assert r.status_code == 200, r.text  # LLMCalled would surface as a 500
    body = r.json()
    assert body["refused"] is True
    assert body["sources"] == []
    assert body["chunks_used"] == 0


def test_ask_stream_refusal_event(client, user_headers):
    with client.stream("POST", "/api/chat/ask-stream", headers=user_headers,
                       json={"question": "Pyetje jashtë korpusit?"}) as r:
        assert r.status_code == 200
        payload = "".join(r.iter_text())
    assert "event: refusal" in payload
    assert "event: delta" not in payload  # gate fired before any generation


# --- Reports ------------------------------------------------------------------------

def test_reports_shape_and_counts(client, admin_headers):
    r = client.get("/api/reports?days=7", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    for key in ("kpi", "questions_per_day", "citations_by_type", "top_documents",
                "by_user", "by_department", "corpus_by_type", "activity_by_action"):
        assert key in data, key
    assert len(data["questions_per_day"]) == 7  # zero-filled series
    # The two refusal questions above are counted as questions + refusals.
    assert data["kpi"]["questions"]["value"] >= 2
    assert data["kpi"]["refused"]["value"] >= 2
    # Departments come from users.department.
    labels = {row["label"] for row in data["by_department"]}
    assert "Financa" in labels


def test_reports_csv_export(client, admin_headers):
    r = client.get("/api/reports/export.csv?days=7", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "Treguesit kryesorë" in r.text


# --- Misc ---------------------------------------------------------------------------

def test_meta_enums(client, user_headers):
    r = client.get("/api/meta", headers=user_headers)
    assert r.status_code == 200
    data = r.json()
    assert "Ligj" in data["document_types"]
    assert len(data["summary_formats"]) == 4
    assert 0 < data["min_similarity"] < 1


def test_system_status_degrades_gracefully(client, user_headers):
    r = client.get("/api/system/status", headers=user_headers)
    assert r.status_code == 200
    assert r.json()["ollama_online"] is False  # stubbed offline in tests


def test_model_switch_is_admin_only(client, user_headers):
    r = client.put("/api/system/model", headers=user_headers,
                   json={"model": "qwen2.5:3b"})
    assert r.status_code == 403


def test_security_headers_present(client):
    r = client.get("/api/auth/me")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert "default-src 'self'" in r.headers.get("content-security-policy", "")
    assert r.headers.get("cache-control") == "no-store"


def test_audit_records_logins(client, admin_headers):
    rows = client.get("/api/audit?limit=50", headers=admin_headers).json()
    assert any(row["action"] == "login_success" for row in rows)
