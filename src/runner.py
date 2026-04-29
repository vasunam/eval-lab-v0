"""Generate model outputs for all episodes × models."""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
import litellm

load_dotenv()

MODELS = {
    "claude-opus-4-5": "anthropic/claude-opus-4-5",
    "gpt-5.2": "openai/gpt-5.2",
    "gemini-3.1-pro": "gemini/gemini-3.1-pro",
}

SYSTEM_PROMPT = """You are a senior product manager summarizing a Lenny's Podcast episode for other PMs.

Output two things:
1. A 150-word executive summary capturing the most important ideas
2. Exactly 5 actionable takeaways for AI Product Managers

Constraints:
- Each takeaway must be specific (cite the guest by name and reference what they actually said)
- Each takeaway must be actionable (something a PM could DO Monday morning)
- Avoid generic advice (e.g., "be customer-obsessed")
- Output must be valid JSON: {"summary": str, "takeaways": [str, str, str, str, str]}"""

TRANSCRIPTS_DIR = Path("data/transcripts")
OUTPUTS_DIR = Path("data/outputs")
RUN_LOG = Path("data/run_log.json")


def load_transcript(guest_slug: str) -> str:
    path = TRANSCRIPTS_DIR / f"{guest_slug}.txt"
    return path.read_text(encoding="utf-8")


def run_model(model_key: str, model_id: str, guest_slug: str, transcript: str) -> dict:
    start = time.time()
    response = litellm.completion(
        model=model_id,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Summarize this episode transcript:\n\n{transcript}"},
        ],
        temperature=0.3,
    )
    latency = time.time() - start
    content = response.choices[0].message.content

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {"raw": content, "parse_error": True}

    return {
        "model": model_key,
        "guest_slug": guest_slug,
        "output": parsed,
        "latency_s": round(latency, 2),
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens,
        "cost_usd": litellm.completion_cost(completion_response=response),
    }


def main():
    guest_slugs = [p.stem for p in TRANSCRIPTS_DIR.glob("*.txt")]
    if not guest_slugs:
        print("No transcripts found in data/transcripts/. Add .txt files first.")
        return

    run_log = []

    for model_key, model_id in MODELS.items():
        out_dir = OUTPUTS_DIR / model_key
        out_dir.mkdir(parents=True, exist_ok=True)

        for slug in guest_slugs:
            out_path = out_dir / f"{slug}.json"
            if out_path.exists():
                print(f"  skipping {model_key}/{slug} (already done)")
                continue

            print(f"  running {model_key} on {slug}...")
            transcript = load_transcript(slug)
            result = run_model(model_key, model_id, slug, transcript)
            out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            run_log.append({k: v for k, v in result.items() if k != "output"})
            print(f"    done — {result['latency_s']}s, ${result['cost_usd']:.4f}")

    RUN_LOG.write_text(json.dumps(run_log, indent=2), encoding="utf-8")
    total_cost = sum(r["cost_usd"] for r in run_log)
    print(f"\nTotal cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
