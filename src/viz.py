"""Generate cost-quality frontier and calibration charts."""
import json
from pathlib import Path

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

RESULTS_DIR = Path("results")
RUN_LOG = Path("data/run_log.json")
EVAL_DIR = Path("data/eval_results")

MODELS = ["claude-opus-4-5", "gpt-5.2", "gemini-3.1-pro"]
COLORS = {"claude-opus-4-5": "#cc785c", "gpt-5.2": "#10a37f", "gemini-3.1-pro": "#4285f4"}


def load_scores() -> dict:
    scores = {m: {"code": [], "actionability": [], "specificity": [], "completeness": [], "human": []} for m in MODELS}

    code_path = EVAL_DIR / "code_based.json"
    if code_path.exists():
        code = json.loads(code_path.read_text())
        for m in MODELS:
            if m in code:
                scores[m]["code"] = [v["score"] for v in code[m].values()]

    judge_path = EVAL_DIR / "llm_judge.json"
    if judge_path.exists():
        judge = json.loads(judge_path.read_text())
        for m in MODELS:
            if m in judge:
                for dim in ["actionability", "specificity", "completeness"]:
                    scores[m][dim] = [
                        v[dim]["final_score"] for v in judge[m].values()
                        if v.get(dim, {}).get("final_score") is not None
                    ]

    human_path = EVAL_DIR / "human.json"
    if human_path.exists():
        human = json.loads(human_path.read_text())
        for m in MODELS:
            if m in human:
                scores[m]["human"] = list(human[m].values())

    return scores


def avg(lst: list) -> float | None:
    return round(sum(lst) / len(lst), 2) if lst else None


def cost_quality_frontier():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    scores = load_scores()

    run_log = []
    if RUN_LOG.exists():
        run_log = json.loads(RUN_LOG.read_text())

    cost_per_model = {}
    for entry in run_log:
        m = entry["model"]
        cost_per_model.setdefault(m, []).append(entry["cost_usd"])
    avg_cost = {m: avg(v) for m, v in cost_per_model.items()}

    rows = []
    for m in MODELS:
        s = scores[m]
        dims = [avg(s[d]) for d in ["actionability", "specificity", "completeness", "human"] if avg(s[d]) is not None]
        composite = round(sum(dims) / len(dims), 2) if dims else None
        rows.append({"model": m, "cost": avg_cost.get(m, 0), "composite": composite})

    df = pd.DataFrame(rows).dropna()

    fig = go.Figure()
    for _, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["cost"]], y=[row["composite"]],
            mode="markers+text",
            marker=dict(size=18, color=COLORS.get(row["model"], "grey")),
            text=[row["model"]],
            textposition="top center",
            name=row["model"],
        ))

    fig.update_layout(
        title="Cost-Quality Frontier",
        xaxis_title="Cost per run (USD)",
        yaxis_title="Composite eval score (1–5)",
        yaxis=dict(range=[1, 5]),
        template="plotly_white",
        showlegend=False,
    )

    out = RESULTS_DIR / "cost_quality_frontier.png"
    fig.write_image(str(out))
    print(f"Saved {out}")


def calibration_chart():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    scores = load_scores()

    rows = []
    for m in MODELS:
        human_scores = scores[m]["human"]
        action_scores = scores[m]["actionability"]
        for h, a in zip(human_scores, action_scores):
            if h is not None and a is not None:
                rows.append({"model": m, "human": h, "llm_judge": a})

    if not rows:
        print("No calibration data yet.")
        return

    df = pd.DataFrame(rows)
    fig = px.scatter(
        df, x="human", y="llm_judge", color="model",
        color_discrete_map=COLORS,
        title="Calibration: Human vs LLM-Judge (Actionability)",
        labels={"human": "Human score (1–5)", "llm_judge": "LLM-judge score (1–5)"},
        template="plotly_white",
    )
    fig.add_shape(type="line", x0=1, y0=1, x1=5, y1=5, line=dict(dash="dash", color="grey"))
    fig.add_annotation(x=3, y=3.4, text="Perfect calibration", showarrow=False, font=dict(color="grey"))

    out = RESULTS_DIR / "calibration.png"
    fig.write_image(str(out))
    print(f"Saved {out}")


if __name__ == "__main__":
    cost_quality_frontier()
    calibration_chart()
