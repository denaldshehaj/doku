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
    try:
        resp = _get_client().chat(
            model=get_active_model(), messages=messages,
            options={"temperature": config.LLM_TEMPERATURE if temperature is None
                     else temperature},
        )
    except Exception as exc:
        raise OllamaUnavailableError(
            "Shërbimi i modelit lokal (Ollama) nuk është aktiv ose modeli mungon. "
            "Sigurohu që Ollama po ekzekuton dhe modeli është shkarkuar "
            f"(`ollama pull {get_active_model()}`). Detaje: {exc}"
        )
    return resp["message"]["content"].strip()
