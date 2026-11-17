"""Talks to the AI service: Ollama (local) or any OpenAI-compatible API (hosted)."""
import requests

from . import config


def _headers():
    return {"Authorization": f"Bearer {config.OPENAI_API_KEY}"}


def embed(texts: list) -> list:
    vectors = []
    for i in range(0, len(texts), 32):  # small batches
        batch = texts[i:i + 32]
        if config.LLM_PROVIDER == "openai":
            r = requests.post(f"{config.OPENAI_BASE_URL}/embeddings", headers=_headers(),
                              json={"model": config.EMBED_MODEL, "input": batch}, timeout=120)
            r.raise_for_status()
            data = sorted(r.json()["data"], key=lambda d: d["index"])
            vectors.extend(d["embedding"] for d in data)
        else:
            r = requests.post(f"{config.OLLAMA_URL}/api/embed",
                              json={"model": config.EMBED_MODEL, "input": batch}, timeout=300)
            r.raise_for_status()
            vectors.extend(r.json()["embeddings"])
    return vectors


def chat(system: str, user: str) -> dict:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    if config.LLM_PROVIDER == "openai":
        body = {"model": config.CHAT_MODEL, "messages": messages}
        if config.LLM_TEMPERATURE != "":
            body["temperature"] = float(config.LLM_TEMPERATURE)
        r = requests.post(f"{config.OPENAI_BASE_URL}/chat/completions", headers=_headers(),
                          json=body, timeout=120)
        r.raise_for_status()
        d = r.json()
        usage = d.get("usage", {})
        return {"text": d["choices"][0]["message"]["content"].strip(),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens")}
    r = requests.post(f"{config.OLLAMA_URL}/api/chat",
                      json={"model": config.CHAT_MODEL, "stream": False,
                            "options": {"temperature": 0}, "messages": messages},
                      timeout=600)
    r.raise_for_status()
    d = r.json()
    return {"text": d["message"]["content"].strip(),
            "prompt_tokens": d.get("prompt_eval_count"),
            "completion_tokens": d.get("eval_count")}


def llm_ready() -> bool:
    """Cheap check used by /health (does NOT spend money on hosted APIs)."""
    if config.LLM_PROVIDER == "openai":
        return bool(config.OPENAI_API_KEY)
    try:
        requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=3).raise_for_status()
        return True
    except Exception:
        return False
