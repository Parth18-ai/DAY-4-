"""Cost + latency logging. One JSON line per /ask call -> logs/requests.jsonl
Ollama is free, so we also log an 'if hosted' cost estimate."""
import json
import time
from contextlib import contextmanager

from . import config


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # rough rule: 1 token ~ 4 characters


def log_request(question, answer, prompt_text, latency_s, retrieve_s, generate_s,
                top_k, blocked=False, prompt_tokens=None, completion_tokens=None):
    pt = prompt_tokens or (est_tokens(prompt_text) if prompt_text else 0)
    ct = completion_tokens or (est_tokens(answer) if answer and not blocked else 0)
    row = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "question": question[:200],
        "blocked": blocked,
        "top_k": top_k,
        "latency_s": round(latency_s, 3),
        "retrieve_s": round(retrieve_s, 3),
        "generate_s": round(generate_s, 3),
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "est_cost_usd_if_hosted": round(
            pt / 1e6 * config.PRICE_IN_PER_M + ct / 1e6 * config.PRICE_OUT_PER_M, 6),
    }
    config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def summary() -> dict:
    """Totals and averages from the log file (used by /metrics and the UI)."""
    if not config.LOG_FILE.exists():
        return {"requests": 0}
    rows = [json.loads(l) for l in config.LOG_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    answered = [r for r in rows if not r["blocked"]]
    lat = sorted(r["latency_s"] for r in answered)
    return {
        "requests": len(rows),
        "blocked_by_guard": sum(r["blocked"] for r in rows),
        "avg_latency_s": round(sum(lat) / len(lat), 2) if lat else 0,
        "p95_latency_s": lat[int(0.95 * (len(lat) - 1))] if lat else 0,
        "total_tokens": sum(r["prompt_tokens"] + r["completion_tokens"] for r in rows),
        "est_cost_usd_if_hosted": round(sum(r["est_cost_usd_if_hosted"] for r in rows), 4),
    }


@contextmanager
def timer():
    t = {"start": time.perf_counter(), "elapsed": 0.0}
    try:
        yield t
    finally:
        t["elapsed"] = time.perf_counter() - t["start"]
