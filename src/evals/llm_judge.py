"""LLM-judge eval: 3 dimensions, two judge models, majority vote + agreement check."""
import json
import time
from pathlib import Path

from dotenv import load_dotenv
import litellm

load_dotenv()

JUDGE_MODELS = {
    "claude-opus-4-5": "anthropic/claude-opus-4-5",
    "gpt-4o-mini": "openai/gpt-4o-mini",
}
JUDGE_TEMPERATURE = 0.3
JUDGE_RUNS = 3

OUTPUTS_DIR = Path("data/outputs")
RESULTS_DIR = Path("data/eval_results")
TRANSCRIPTS_DIR = Path("data/transcripts")

ACTIONABILITY_PROMPT = """ROLE: You are evaluating PM-focused podcast summaries for actionability.
CONTEXT: Below is an AI-generated summary + 5 takeaways from a Lenny's Podcast episode.
GOAL: Score the takeaways on a scale of 1–5 for ACTIONABILITY.
  - 1: Vague platitudes a PM couldn't act on
  - 3: Mix of generic and specific advice
  - 5: All 5 takeaways are specific, named, and a PM could do something Monday morning
TERMINOLOGY: "Actionable" means: (a) cites a specific framework, person, or example;
  (b) implies a concrete action; (c) doesn't just restate common knowledge.

Summary and takeaways:
{output}

Return JSON only: {{"score": int, "rationale": str, "weakest_takeaway_index": int}}"""

SPECIFICITY_PROMPT = """ROLE: You are evaluating PM-focused podcast summaries for faithfulness to the guest.
CONTEXT: Below is a podcast transcript excerpt and an AI-generated summary + takeaways.
GOAL: Score on a scale of 1–5 for SPECIFICITY — how accurately the takeaways reflect what the guest actually said.
  - 1: Takeaways could apply to any podcast, no guest-specific content
  - 3: Some guest-specific references but others are generic
  - 5: Every takeaway is grounded in something the guest specifically said or did

Transcript (excerpt):
{transcript}

Summary and takeaways:
{output}

Return JSON only: {{"score": int, "rationale": str, "weakest_takeaway_index": int}}"""

COMPLETENESS_PROMPT = """ROLE: You are evaluating PM-focused podcast summaries for completeness.
CONTEXT: Below is a podcast transcript excerpt and an AI-generated summary.
GOAL: Score on a scale of 1–5 for COMPLETENESS — whether the summary captures the 3 most important ideas.
  - 1: Summary misses the main point of the episode
  - 3: Captures some key ideas but misses at least one important theme
  - 5: Summary covers the 3 most important ideas any PM should take away

Transcript (excerpt):
{transcript}

Summary:
{output_summary}

Return JSON only: {{"score": int, "rationale": str, "missing_ideas": [str]}}"""


def judge_once(model_id: str, prompt: str) -> tuple[dict, float, float]:
    """Returns (parsed_result, latency_s, cost_usd)."""
    start = time.time()
    response = litellm.completion(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        temperature=JUDGE_TEMPERATURE,
    )
    latency = round(time.time() - start, 2)
    cost = litellm.completion_cost(completion_response=response)
    content = response.choices[0].message.content
    try:
        return json.loads(content), latency, cost
    except json.JSONDecodeError:
        return {"score": None, "rationale": content, "parse_error": True}, latency, cost


def majority_vote(scores: list) -> int | None:
    valid = [s for s in scores if s is not None]
    return round(sum(valid) / len(valid)) if valid else None


def truncate(text: str, max_chars: int = 6000) -> str:
    return text[:max_chars] + "..." if len(text) > max_chars else text


def judge_agreement(score_a: int | None, score_b: int | None) -> float | None:
    if score_a is None or score_b is None:
        return None
    return abs(score_a - score_b)


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    all_results = {}
    judge_cost_log = {m: {"total_cost": 0.0, "total_latency": 0.0, "calls": 0} for m in JUDGE_MODELS}

    for model_dir in OUTPUTS_DIR.iterdir():
        if not model_dir.is_dir():
            continue
        model_key = model_dir.name
        all_results[model_key] = {}

        for output_file in model_dir.glob("*.json"):
            slug = output_file.stem
            result = json.loads(output_file.read_text())
            output = result.get("output", {})
            output_str = json.dumps(output, indent=2)

            transcript_path = TRANSCRIPTS_DIR / f"{slug}.txt"
            transcript = truncate(transcript_path.read_text()) if transcript_path.exists() else ""

            print(f"  judging {model_key}/{slug}...")
            entry = {}

            for dim, prompt_template, kwargs in [
                ("actionability", ACTIONABILITY_PROMPT, {"output": output_str}),
                ("specificity", SPECIFICITY_PROMPT, {"transcript": transcript, "output": output_str}),
                ("completeness", COMPLETENESS_PROMPT, {
                    "transcript": transcript,
                    "output_summary": output.get("summary", "") if isinstance(output, dict) else "",
                }),
            ]:
                per_judge = {}
                for judge_key, judge_id in JUDGE_MODELS.items():
                    runs, latencies, costs = [], [], []
                    for _ in range(JUDGE_RUNS):
                        r, lat, cost = judge_once(judge_id, prompt_template.format(**kwargs))
                        runs.append(r)
                        latencies.append(lat)
                        costs.append(cost)
                        time.sleep(0.3)
                        judge_cost_log[judge_key]["total_cost"] += cost
                        judge_cost_log[judge_key]["total_latency"] += lat
                        judge_cost_log[judge_key]["calls"] += 1

                    scores = [r.get("score") for r in runs]
                    per_judge[judge_key] = {
                        "final_score": majority_vote(scores),
                        "runs": runs,
                        "avg_latency_s": round(sum(latencies) / len(latencies), 2),
                        "total_cost_usd": round(sum(costs), 5),
                    }

                opus_score = per_judge["claude-opus-4-5"]["final_score"]
                mini_score = per_judge["gpt-4o-mini"]["final_score"]
                entry[dim] = {
                    "final_score": opus_score,  # primary judge
                    "per_judge": per_judge,
                    "agreement_delta": judge_agreement(opus_score, mini_score),
                }
                print(f"    {dim}: opus={opus_score} mini={mini_score} delta={entry[dim]['agreement_delta']}")

            all_results[model_key][slug] = entry

    out_path = RESULTS_DIR / "llm_judge.json"
    out_path.write_text(json.dumps(all_results, indent=2))

    cost_path = RESULTS_DIR / "judge_cost_log.json"
    cost_path.write_text(json.dumps(judge_cost_log, indent=2))

    print(f"\nJudge cost summary:")
    for jk, stats in judge_cost_log.items():
        avg_lat = stats["total_latency"] / stats["calls"] if stats["calls"] else 0
        print(f"  {jk}: ${stats['total_cost']:.4f} total, {avg_lat:.2f}s avg latency")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
