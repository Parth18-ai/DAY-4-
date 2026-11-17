"""Run the eval set and show the weakest questions.
Run from the project root (backend must be running):
    python evals/run_evals.py --tag before    (saves evals/eval_results_before.csv)
    python evals/run_evals.py --tag after     (saves evals/eval_results_after.csv)
    python evals/run_evals.py evals/my.json --tag before   (use another eval file)

Each item: id, question, expected_keywords (list), expected_file (or null), should_answer (true/false)
 - should_answer=false  -> the assistant must say it can't find it (or the guard must block it)
Score = 70% keywords found in answer + 30% correct source file retrieved."""
import csv
import json
import os
import sys
from pathlib import Path

import requests

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
HEADERS = {"X-API-Key": os.getenv("API_KEY", "")} if os.getenv("API_KEY") else {}
HERE = Path(__file__).resolve().parent
REFUSALS = ["could not find", "can't follow instructions", "cannot follow instructions"]


def score(item, resp):
    ans = resp["answer"].lower()
    srcs = [s.get("file", "") for s in resp.get("sources", [])]
    if not item.get("should_answer", True):
        ok = any(p in ans for p in REFUSALS)
        return {"keyword_hit": float(ok), "source_hit": float(ok), "score": 1.0 if ok else 0.0}
    kws = item.get("expected_keywords", [])
    kw_hit = sum(k.lower() in ans for k in kws) / max(1, len(kws))
    exp = item.get("expected_file")
    src_hit = 1.0 if (exp is None or exp in srcs) else 0.0
    return {"keyword_hit": kw_hit, "source_hit": src_hit, "score": 0.7 * kw_hit + 0.3 * src_hit}


def main(path=None, tag="latest"):
    path = Path(path) if path else HERE / "evals.json"
    items = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for it in items:
        try:
            r = requests.post(f"{API_URL}/ask", json={"question": it["question"]}, headers=HEADERS, timeout=600)
            r.raise_for_status()
            resp = r.json()
        except Exception as e:
            print(f"Could not call backend: {e}")
            return
        s = score(it, resp)
        rows.append({"id": it["id"], "question": it["question"][:70], **s,
                     "latency_s": resp.get("latency_s", 0), "answer": resp["answer"][:150]})
        print(f'Q{it["id"]:>2}  score={s["score"]:.2f}  src={s["source_hit"]:.0f}  '
              f'{resp.get("latency_s", 0):>5.1f}s  {it["question"][:50]}')

    avg = sum(r["score"] for r in rows) / len(rows)
    avg_lat = sum(r["latency_s"] for r in rows) / len(rows)
    print(f"\nAVERAGE SCORE: {avg:.2f}   AVERAGE LATENCY: {avg_lat:.1f}s")
    print("\nWEAKEST 5:")
    for r in sorted(rows, key=lambda x: x["score"])[:5]:
        print(f'  Q{r["id"]}: {r["score"]:.2f}  {r["question"]}\n        -> {r["answer"]}')
    out = HERE / f"eval_results_{tag}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"\nSaved {out}")


if __name__ == "__main__":
    args = sys.argv[1:]
    tag = "latest"
    if "--tag" in args:
        i = args.index("--tag")
        tag = args[i + 1]
        del args[i:i + 2]
    main(args[0] if args else None, tag)
