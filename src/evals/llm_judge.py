"""LLM-judge eval: 3 dimensions, majority vote across 3 runs."""
import json
import time
from pathlib import Path

from dotenv import load_dotenv
import litellm

load_dotenv()

JUDGE_MODEL = "anthropic/claude-opus-4-5"
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


def judge_once(prompt: str) -> dict:
    response = litellm.completion(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=JUDGE_TEMPERATURE,
    )
    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"score": None, "rationale": content, "parse_error": True}


def majority_vote(scores: list[int | None]) -> int | None:
    valid = [s for s in scores if s is not None]
    if not valid:
        return None
    return round(sum(valid) / len(valid))


def truncate(text: str, max_chars: int = 6000) -> str:
    return text[:max_chars] + "..." if len(text) > max_chars else text


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    all_results = {}

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
                ("completeness", COMPLETENESS_PROMPT, {"transcript": transcript, "output_summary": output.get("summary", "") if isinstance(output, dict) else ""}),
            ]:
                runs = []
                for _ in range(JUDGE_RUNS):
                    r = judge_once(prompt_template.format(**kwargs))
                    runs.append(r)
                    time.sleep(0.5)

                scores = [r.get("score") for r in runs]
                entry[dim] = {
                    "final_score": majority_vote(scores),
                    "runs": runs,
                }
                print(f"    {dim}: {scores} → {entry[dim]['final_score']}")

            all_results[model_key][slug] = entry

    out_path = RESULTS_DIR / "llm_judge.json"
    out_path.write_text(json.dumps(all_results, indent=2))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
