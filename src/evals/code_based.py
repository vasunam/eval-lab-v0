"""Deterministic code-based eval: 5 checks per output."""
import json
import re
from pathlib import Path

OUTPUTS_DIR = Path("data/outputs")
RESULTS_DIR = Path("data/eval_results")

FILLER_PHRASES = [
    "in conclusion",
    "it's important to note",
    "in today's fast-paced world",
    "as an ai",
    "it is worth noting",
    "needless to say",
]

GROUND_TRUTH = json.loads(Path("data/ground_truth.json").read_text()) if Path("data/ground_truth.json").exists() else {}


def check_output(result: dict) -> dict:
    output = result.get("output", {})
    guest_slug = result.get("guest_slug", "")
    passed, failed = [], []

    summary = output.get("summary", "") if isinstance(output, dict) else ""
    takeaways = output.get("takeaways", []) if isinstance(output, dict) else []
    word_count = len(summary.split())

    if 130 <= word_count <= 170:
        passed.append("summary_length_ok")
    else:
        failed.append(f"summary_length_ok (got {word_count} words)")

    if isinstance(output, dict) and "summary" in output and "takeaways" in output:
        passed.append("valid_json")
    else:
        failed.append("valid_json")

    if len(takeaways) == 5:
        passed.append("takeaway_count_correct")
    else:
        failed.append(f"takeaway_count_correct (got {len(takeaways)})")

    guest_name = GROUND_TRUTH.get(guest_slug, {}).get("guest", "")
    if guest_name and guest_name.split()[0].lower() in summary.lower():
        passed.append("mentions_guest_name")
    elif not guest_name:
        passed.append("mentions_guest_name")  # can't check without ground truth
    else:
        failed.append(f"mentions_guest_name (expected '{guest_name}')")

    full_text = (summary + " " + " ".join(takeaways)).lower()
    found_filler = [p for p in FILLER_PHRASES if p in full_text]
    if not found_filler:
        passed.append("no_filler_phrases")
    else:
        failed.append(f"no_filler_phrases (found: {found_filler})")

    score = len(passed) / (len(passed) + len(failed))
    return {"score": round(score, 2), "passed_checks": passed, "failed_checks": failed}


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
            eval_result = check_output(result)
            all_results[model_key][slug] = eval_result
            print(f"  {model_key}/{slug}: {eval_result['score']:.2f} — passed: {eval_result['passed_checks']}")

    out_path = RESULTS_DIR / "code_based.json"
    out_path.write_text(json.dumps(all_results, indent=2))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
