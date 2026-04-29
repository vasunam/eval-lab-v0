"""Human eval CLI: rate model outputs 1–5 against reference summaries."""
import json
import random
from pathlib import Path

OUTPUTS_DIR = Path("data/outputs")
RESULTS_DIR = Path("data/eval_results")
GROUND_TRUTH_PATH = Path("data/ground_truth.json")


def load_all_pairs() -> list[tuple[str, str]]:
    pairs = []
    for model_dir in OUTPUTS_DIR.iterdir():
        if model_dir.is_dir():
            for f in model_dir.glob("*.json"):
                pairs.append((model_dir.name, f.stem))
    return pairs


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_path = RESULTS_DIR / "human.json"
    results = json.loads(results_path.read_text()) if results_path.exists() else {}

    ground_truth = {}
    if GROUND_TRUTH_PATH.exists():
        ground_truth = json.loads(GROUND_TRUTH_PATH.read_text())

    pairs = load_all_pairs()
    random.shuffle(pairs)
    remaining = [(m, s) for m, s in pairs if results.get(m, {}).get(s) is None]

    print(f"\n=== Human Eval CLI ===")
    print(f"Rated: {len(pairs) - len(remaining)}/{len(pairs)}. Type 'done' to stop.\n")

    for model_key, slug in remaining:
        output_path = OUTPUTS_DIR / model_key / f"{slug}.json"
        result = json.loads(output_path.read_text())
        output = result.get("output", {})

        print(f"\n{'='*60}")
        print(f"Model: {model_key}  |  Episode: {slug}")
        print(f"{'='*60}")

        if slug in ground_truth:
            print(f"\n--- YOUR REFERENCE SUMMARY ---")
            print(ground_truth[slug].get("reference_summary", "(none)"))

        print(f"\n--- MODEL OUTPUT ---")
        if isinstance(output, dict):
            print(f"Summary: {output.get('summary', '')}")
            print("\nTakeaways:")
            for i, t in enumerate(output.get("takeaways", []), 1):
                print(f"  {i}. {t}")
        else:
            print(output)

        while True:
            rating = input("\nRate 1–5 (would you forward this to a PM friend?), or 'done' to stop: ").strip()
            if rating.lower() == "done":
                results_path.write_text(json.dumps(results, indent=2))
                print(f"\nSaved {sum(len(v) for v in results.values())} ratings to {results_path}")
                return
            if rating in {"1", "2", "3", "4", "5"}:
                results.setdefault(model_key, {})[slug] = int(rating)
                break
            print("  Please enter 1–5 or 'done'.")

    results_path.write_text(json.dumps(results, indent=2))
    print(f"\nAll {len(pairs)} outputs rated. Saved to {results_path}")


if __name__ == "__main__":
    main()
