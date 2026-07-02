"""Local LLM client (Ollama). No cloud calls. If Ollama is not running, a clear
Albanian error is raised so the UI can show it."""
import config

_client = None
_active_model: str | None = None
_model_loaded = False  # settings row read at most once per process

_SETTING_KEY = "active_model"


class OllamaUnavailableError(Exception):
    """Ollama service is not reachable."""


def _get_client():
    global _client
    if _client is None:
        import ollama
        _client = ollama.Client(host=config.OLLAMA_HOST)
    return _client


def _reset_client() -> None:
    """Drop the cached client so the next call rebuilds a fresh connection.
    Needed because the underlying httpx client can end up permanently 'closed'
    after a dropped connection (e.g. an OOM that restarts the model), which
    would otherwise break every subsequent request in a batch run."""
    global _client
    _client = None


def get_active_model() -> str:
    """The admin-selected model, persisted in the settings table so it
    survives a server restart; falls back to config.OLLAMA_MODEL."""
    global _active_model, _model_loaded
    if not _model_loaded:
        _model_loaded = True
        try:
            from modules import database as db
            with db.get_conn() as conn:
                row = conn.execute("SELECT value FROM settings WHERE key = ?",
                                   (_SETTING_KEY,)).fetchone()
            if row is not None:
                _active_model = row["value"]
        except Exception:  # noqa: BLE001 — a missing setting must never break generation
            pass
    return _active_model or config.OLLAMA_MODEL


def set_active_model(model: str) -> None:
    global _active_model, _model_loaded
    _active_model = model
    _model_loaded = True
    try:
        from modules import database as db
        with db.get_conn() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = datetime('now')", (_SETTING_KEY, model))
    except Exception:  # noqa: BLE001 — persistence is best-effort; memory still wins
        pass


def list_models() -> list[str]:
    try:
        data = _get_client().list()
    except Exception:
        return []
    models = getattr(data, "models", None)
    if models is None and isinstance(data, dict):
        models = data.get("models", [])
    names = []
    for m in models or []:
        name = getattr(m, "model", None)
        if name is None and isinstance(m, dict):
            name = m.get("model") or m.get("name")
        if name:
            names.append(name)
    return names


def is_available() -> bool:
    try:
        _get_client().list()
        return True
    except Exception:
        return False


def _build_messages(prompt: str, system: str | None) -> list[dict]:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def generate_stream(prompt: str, system: str | None = None,
                    temperature: float | None = None):
    """Yield the answer token-by-token (Ollama streaming). Same retry-once
    semantics as generate() for a stale cached connection; once streaming has
    begun, errors propagate (a half-delivered answer cannot be retried)."""
    messages = _build_messages(prompt, system)
    options = {"temperature": config.LLM_TEMPERATURE if temperature is None
               else temperature}
    last_exc = None
    for _attempt in range(2):
        started = False
        try:
            stream = _get_client().chat(model=get_active_model(), messages=messages,
                                        options=options, stream=True)
            for part in stream:
                piece = part["message"]["content"]
                if piece:
                    started = True
                    yield piece
            return
        except Exception as exc:  # noqa: BLE001 — wrapped below
            _reset_client()
            if started:
                # Mid-stream failure: retrying would duplicate delivered text.
                raise OllamaUnavailableError(
                    f"Lidhja me modelin lokal u ndërpre gjatë gjenerimit: {exc}")
            last_exc = exc
    raise OllamaUnavailableError(
        "Shërbimi i modelit lokal (Ollama) nuk është aktiv ose modeli mungon. "
        "Sigurohu që Ollama po ekzekuton dhe modeli është shkarkuar "
        f"(`ollama pull {get_active_model()}`). Detaje: {last_exc}"
    )


def generate(prompt: str, system: str | None = None,
             temperature: float | None = None) -> str:
    messages = _build_messages(prompt, system)
    options = {"temperature": config.LLM_TEMPERATURE if temperature is None
               else temperature}
    # One transparent retry: if the cached connection has gone stale/closed
    # (e.g. after an OOM-driven model restart mid-batch), rebuild and try again.
    last_exc = None
    for _attempt in range(2):
        try:
            resp = _get_client().chat(model=get_active_model(),
                                      messages=messages, options=options)
            return resp["message"]["content"].strip()
        except Exception as exc:
            last_exc = exc
            _reset_client()
    raise OllamaUnavailableError(
        "Shërbimi i modelit lokal (Ollama) nuk është aktiv ose modeli mungon. "
        "Sigurohu që Ollama po ekzekuton dhe modeli është shkarkuar "
        f"(`ollama pull {get_active_model()}`). Detaje: {last_exc}"
    )
