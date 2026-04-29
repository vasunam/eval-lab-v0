# Eval Lab v0 — Product Requirements Document

> "If the model is the product, the eval is the PRD." — Brendan Foody, Mercor

---

## Problem

PMs at AI-native companies need to choose models for content tasks. The dominant approach is "vibe checks" — read 3 outputs, pick the one that feels best. This breaks at scale, fails on subjective dimensions, and ignores cost.

## User

A PM evaluating 3 frontier models on a content summarization task with limited budget and limited time.

## Capability ladder

* **v1 (this project):** Comparison across 3 models on a fixed task with 3 eval types
* **v2:** Add automatic re-runs with different prompts to test prompt sensitivity
* **v3:** Generalize to any task — user provides their own dataset and eval criteria

## Eval criteria

### Type 1: Code-based (deterministic)

5 checks per output:

1. `summary_length_ok` — 130 ≤ word count ≤ 170
2. `valid_json` — parses as JSON with required keys (`summary`, `takeaways`)
3. `takeaway_count_correct` — exactly 5 takeaways
4. `mentions_guest_name` — guest name appears in summary
5. `no_filler_phrases` — does NOT contain: "in conclusion", "it's important to note", "in today's fast-paced world"

Score: 0.0–1.0 (fraction of checks passed)

### Type 2: LLM-judge (Claude Opus 4.5 as judge)

3 dimensions, each scored 1–5. Each prompt run 3× at temperature 0.3; majority vote taken.

**Actionability** — Can a PM act on these takeaways Monday morning? Score 5 = all takeaways cite a specific person/framework and imply a concrete action.

**Specificity** — Do takeaways accurately reflect what the guest actually said? Score 5 = every takeaway grounded in guest-specific content.

**Completeness** — Does the summary capture the 3 most important ideas? Score 5 = covers the ideas any PM should walk away with.

Judge model choice: Claude Opus 4.5 — strongest available reasoning model, best for nuanced qualitative judgment.

### Type 3: Human eval (CLI)

Rubric: "Would I forward this to a PM friend?" (1–5)

* 1: Would not share — generic, inaccurate, or misleading
* 3: Would share with caveats — useful but not memorable
* 5: Would share immediately — specific, actionable, I learned something

All 24 outputs rated (8 episodes × 3 models) by the project author.

## MVQ thresholds (Marily Nika's framework)

| Tier | Criteria |
| --- | --- |
| **Acceptable** | Composite score ≥ 3.5, code-based pass rate ≥ 0.85 |
| **Delight** | Composite score ≥ 4.2, calibration error < 1.0 |
| **Do-not-ship** | Code-based pass rate < 0.7 OR systematic hallucination detected |

## Cost envelope

* Total project budget: $35
* Per-output cost target: < $0.50
* Eval budget per run: < $5

## Success metric

A user can clone the repo, run `make eval`, and get a defensible model recommendation in under 10 minutes for under $5.

## Out of scope (v1)

* Prompt sensitivity analysis (v2)
* Multi-task generalization (v3)
* Real-time / streaming outputs
* Non-English episodes
