"""Generate the leaderboard markdown from eval results."""
import json
from pathlib import Path

EVAL_DIR = Path("data/eval_results")
RUN_LOG = Path("data/run_log.json")
RESULTS_DIR = Path("results")

MODELS = ["claude-opus-4-5", "gpt-5.2", "gemini-3.1-pro"]


def avg(lst):
    return round(sum(lst) / len(lst), 2) if lst else None


def load_all():
    code, judge, human, costs = {}, {}, {}, {}

    if (EVAL_DIR / "code_based.json").exists():
        code = json.loads((EVAL_DIR / "code_based.json").read_text())
    if (EVAL_DIR / "llm_judge.json").exists():
        judge = json.loads((EVAL_DIR / "llm_judge.json").read_text())
    if (EVAL_DIR / "human.json").exists():
        human = json.loads((EVAL_DIR / "human.json").read_text())
    if RUN_LOG.exists():
        for entry in json.loads(RUN_LOG.read_text()):
            costs.setdefault(entry["model"], []).append(entry["cost_usd"])

    return code, judge, human, {m: avg(v) for m, v in costs.items()}


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    code, judge, human, costs = load_all()

    rows = []
    for m in MODELS:
        code_score = avg([v["score"] for v in code.get(m, {}).values()])
        action = avg([v.get("actionability", {}).get("final_score") for v in judge.get(m, {}).values() if v.get("actionability", {}).get("final_score")])
        spec = avg([v.get("specificity", {}).get("final_score") for v in judge.get(m, {}).values() if v.get("specificity", {}).get("final_score")])
        comp = avg([v.get("completeness", {}).get("final_score") for v in judge.get(m, {}).values() if v.get("completeness", {}).get("final_score")])
        human_score = avg(list(human.get(m, {}).values()))
        cost = costs.get(m)

        rows.append({
            "model": m,
            "code": code_score,
            "actionability": action,
            "specificity": spec,
            "completeness": comp,
            "human": human_score,
            "cost": cost,
        })

    header = "# Eval Lab v0 — Leaderboard\n\n"
    header += "| Model | Code-based | Actionability | Specificity | Completeness | Human | Cost/run |\n"
    header += "|---|---|---|---|---|---|---|\n"

    def fmt(v):
        return str(v) if v is not None else "—"

    lines = [header]
    for r in rows:
        lines.append(
            f"| {r['model']} | {fmt(r['code'])} | {fmt(r['actionability'])} | "
            f"{fmt(r['specificity'])} | {fmt(r['completeness'])} | {fmt(r['human'])} | "
            f"${r['cost']:.4f} |\n" if r["cost"] else
            f"| {r['model']} | {fmt(r['code'])} | {fmt(r['actionability'])} | "
            f"{fmt(r['specificity'])} | {fmt(r['completeness'])} | {fmt(r['human'])} | — |\n"
        )

    out = RESULTS_DIR / "leaderboard.md"
    out.write_text("".join(lines))
    print(f"Saved {out}")
    print("".join(lines))


if __name__ == "__main__":
    main()
