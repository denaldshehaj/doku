"""Local LLM client (Ollama). No cloud calls. If Ollama is not running, a clear
Albanian error is raised so the UI can show it."""
import config

_client = None
_active_model: str | None = None


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
    return _active_model or config.OLLAMA_MODEL


def set_active_model(model: str) -> None:
    global _active_model
    _active_model = model


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


def generate(prompt: str, system: str | None = None,
             temperature: float | None = None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
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
