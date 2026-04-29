# Eval Lab v0

> "If the model is the product, the eval is the PRD." — Brendan Foody, Mercor

I tested **Claude Opus 4.5**, **GPT-5.2**, and **Gemini 3.1 Pro** on summarizing 8 Lenny's Podcast episodes for AI PMs. I built three eval types from scratch and benchmarked them against my own human ratings.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## TL;DR

*(To be filled in after results are in — headline finding goes here.)*

## The cost-quality frontier

*(Chart will appear here after running `make report`.)*

## What I learned about evals

1. *(Specific insight from the calibration analysis)*
2. *(Specific insight about LLM-judge weakness)*
3. *(Specific insight about the reference dataset)*

---

## Reproducing

```bash
git clone https://github.com/namrathavasu/eval-lab-v0
cd eval-lab-v0
cp .env.example .env  # add your API keys

make install
make eval     # ~$5 in API costs, generates data/outputs/
make report   # generates results/leaderboard.md + charts
```

For the human eval step:
```bash
make human-eval
```

---

## What's in here

| Path | What it is |
|---|---|
| `data/ground_truth.json` | 8 reference summaries + takeaways — fork these, they're useful |
| `data/transcripts/` | Raw episode transcripts |
| `src/runner.py` | Generates 24 model outputs (8 episodes × 3 models) |
| `src/evals/code_based.py` | 5 deterministic checks per output |
| `src/evals/llm_judge.py` | 3-dimension LLM judge using Claude Opus 4.5 |
| `src/evals/human.py` | CLI for rating outputs 1–5 |
| `src/viz.py` | Cost-quality frontier + calibration charts |
| `src/report.py` | Leaderboard generator |
| `results/leaderboard.md` | Auto-generated model comparison table |
| `PRD.md` | Full product requirements document for this eval |

---

## The 8 episodes

All episodes are about AI product work — the summaries are useful for PM interview prep.

| Guest | Topic |
|---|---|
| Cat Wu (Anthropic) | How Anthropic's product team moves fast |
| Kevin Weil (OpenAI CPO) | Model maximalism + eval skills |
| Aman Khan (Arize AI) | Evals deep dive |
| Marily Nika (Google Gen AI PM) | AI product sense + MVQ framework |
| Brendan Foody (Mercor CEO) | Eval = PRD framing |
| Hamel Husain & Shreya Shankar | The other evals masterclass |
| Aishwarya Naresh Reganti & Kiriti Badam | Non-determinism in AI products |
| Itamar Gilad (Gmail/YouTube) | Evidence-guided PM + Wizard of Oz |

---

## What's next

v2 will add prompt sensitivity analysis — run each model with 3 prompt variants to test how much results change. PRs welcome.

---

*Built by [Namratha Vasu](https://github.com/vasunam) | See the full [PRD](PRD.md)*
