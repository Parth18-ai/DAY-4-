"""Builds SUBMISSION_REPORT.md: eval scores before vs after tuning + per-request log table.
Run from the project root after you have run the evals twice:
    python scripts/make_report.py --before "CHUNK_SIZE=800, TOP_K=4" --after "CHUNK_SIZE=1000, TOP_K=6"
"""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def avg(rows, key):
    return sum(float(r[key]) for r in rows) / len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default="(describe settings before tuning)")
    ap.add_argument("--after", default="(describe settings after tuning)")
    a = ap.parse_args()

    before = read_csv(ROOT / "evals" / "eval_results_before.csv")
    after = read_csv(ROOT / "evals" / "eval_results_after.csv")
    b = {r["id"]: r for r in before}
    f = {r["id"]: r for r in after}

    out = ["# Submission Report: Document Intelligence Assistant\n"]
    out.append("## 1. Eval scores before vs after tuning\n")
    out.append("| | Before | After |\n|---|---|---|")
    out.append(f"| Settings | {a.before} | {a.after} |")
    out.append(f"| Average score (0-1) | {avg(before, 'score'):.2f} | {avg(after, 'score'):.2f} |")
    out.append(f"| Average latency (s) | {avg(before, 'latency_s'):.1f} | {avg(after, 'latency_s'):.1f} |")
    out.append(f"| Questions scoring 1.00 | {sum(float(r['score']) >= 0.999 for r in before)}/{len(before)} "
               f"| {sum(float(r['score']) >= 0.999 for r in after)}/{len(after)} |\n")

    out.append("### Questions that changed\n")
    out.append("| Q | Question | Before | After |\n|---|---|---|---|")
    changed = False
    for i in b:
        if i in f and abs(float(b[i]["score"]) - float(f[i]["score"])) > 0.001:
            changed = True
            out.append(f"| {i} | {b[i]['question']} | {float(b[i]['score']):.2f} | {float(f[i]['score']):.2f} |")
    if not changed:
        out.append("| - | No question changed score | - | - |")

    out.append("\n## 2. Per-request log (tokens / cost / latency)\n")
    log = ROOT / "logs" / "requests.jsonl"
    rows = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()] if log.exists() else []
    out.append("| Time | Question | Blocked | Latency (s) | Prompt tok | Completion tok | Est. cost if hosted (USD) |\n|---|---|---|---|---|---|---|")
    for r in rows:
        out.append(f"| {r['ts']} | {r['question'][:55]} | {'yes' if r['blocked'] else 'no'} | {r['latency_s']} | "
                   f"{r['prompt_tokens']} | {r['completion_tokens']} | {r['est_cost_usd_if_hosted']} |")
    ans = [r for r in rows if not r["blocked"]]
    if ans:
        out.append(f"\n**Totals:** {len(rows)} requests ({len(rows) - len(ans)} blocked by guard), "
                   f"avg latency {sum(r['latency_s'] for r in ans) / len(ans):.1f}s, "
                   f"{sum(r['prompt_tokens'] + r['completion_tokens'] for r in rows)} tokens, "
                   f"est. cost if hosted ${sum(r['est_cost_usd_if_hosted'] for r in rows):.4f} (local Ollama actual cost: $0).")

    (ROOT / "SUBMISSION_REPORT.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("Saved SUBMISSION_REPORT.md")


if __name__ == "__main__":
    main()
