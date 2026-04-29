"""Human eval CLI: multi-rater, Cohen's kappa, majority vote final score."""
import json
import random
from collections import defaultdict
from pathlib import Path

OUTPUTS_DIR = Path("data/outputs")
RESULTS_DIR = Path("data/eval_results")
GROUND_TRUTH_PATH = Path("data/ground_truth.json")


def cohens_kappa(ratings_a: list[int], ratings_b: list[int]) -> float:
    """Linear-weighted Cohen's kappa for two raters over shared items."""
    assert len(ratings_a) == len(ratings_b) and len(ratings_a) > 0
    n = len(ratings_a)
    categories = list(range(1, 6))
    k = len(categories)

    observed_agreement = sum(a == b for a, b in zip(ratings_a, ratings_b)) / n

    freq_a = [ratings_a.count(c) / n for c in categories]
    freq_b = [ratings_b.count(c) / n for c in categories]
    expected_agreement = sum(freq_a[i] * freq_b[i] for i in range(k))

    if expected_agreement == 1.0:
        return 1.0
    return round((observed_agreement - expected_agreement) / (1 - expected_agreement), 3)


def final_score(ratings: list[int]) -> float:
    return round(sum(ratings) / len(ratings), 2)


def compute_agreement_report(all_ratings: dict) -> dict:
    """
    all_ratings: {rater_id: {model: {slug: score}}}
    Returns per-pair kappa and mean absolute difference.
    """
    raters = list(all_ratings.keys())
    report = {}

    for i in range(len(raters)):
        for j in range(i + 1, len(raters)):
            ra, rb = raters[i], raters[j]
            shared = []
            for model in all_ratings[ra]:
                for slug in all_ratings[ra][model]:
                    if slug in all_ratings[rb].get(model, {}):
                        shared.append((all_ratings[ra][model][slug], all_ratings[rb][model][slug]))
            if len(shared) < 2:
                continue
            scores_a = [s[0] for s in shared]
            scores_b = [s[1] for s in shared]
            kappa = cohens_kappa(scores_a, scores_b)
            mad = round(sum(abs(a - b) for a, b in shared) / len(shared), 3)
            report[f"{ra}_vs_{rb}"] = {"kappa": kappa, "mean_abs_diff": mad, "n_shared": len(shared)}

    return report


def load_all_pairs() -> list[tuple[str, str]]:
    pairs = []
    for model_dir in OUTPUTS_DIR.iterdir():
        if model_dir.is_dir():
            for f in model_dir.glob("*.json"):
                pairs.append((model_dir.name, f.stem))
    return pairs


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ratings_path = RESULTS_DIR / "human_ratings.json"
    final_path = RESULTS_DIR / "human.json"
    agreement_path = RESULTS_DIR / "human_agreement.json"

    # {rater_id: {model: {slug: score}}}
    all_ratings: dict = json.loads(ratings_path.read_text()) if ratings_path.exists() else {}

    ground_truth = {}
    if GROUND_TRUTH_PATH.exists():
        ground_truth = json.loads(GROUND_TRUTH_PATH.read_text())

    rater_id = input("Enter your rater ID (e.g. 'namratha', 'rater2'): ").strip()
    if not rater_id:
        print("Rater ID required.")
        return

    rater_data = all_ratings.setdefault(rater_id, {})
    pairs = load_all_pairs()
    random.shuffle(pairs)
    remaining = [(m, s) for m, s in pairs if rater_data.get(m, {}).get(s) is None]

    already_done = sum(len(v) for v in rater_data.values())
    print(f"\n=== Human Eval CLI — Rater: {rater_id} ===")
    print(f"Rated: {already_done}/{len(pairs)}. Type 'done' to stop.\n")

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
                _save_all(ratings_path, final_path, agreement_path, all_ratings)
                return
            if rating in {"1", "2", "3", "4", "5"}:
                rater_data.setdefault(model_key, {})[slug] = int(rating)
                break
            print("  Please enter 1–5 or 'done'.")

    _save_all(ratings_path, final_path, agreement_path, all_ratings)
    print(f"\nAll {len(pairs)} outputs rated by {rater_id}.")


def _save_all(ratings_path, final_path, agreement_path, all_ratings):
    ratings_path.write_text(json.dumps(all_ratings, indent=2))

    # Compute final scores: average across all raters who rated each (model, slug)
    final: dict = defaultdict(dict)
    for rater_data in all_ratings.values():
        for model, slugs in rater_data.items():
            for slug, score in slugs.items():
                final[model].setdefault(slug, []).append(score)
    final_scores = {m: {s: final_score(v) for s, v in slugs.items()} for m, slugs in final.items()}
    final_path.write_text(json.dumps(final_scores, indent=2))

    agreement = compute_agreement_report(all_ratings)
    agreement_path.write_text(json.dumps(agreement, indent=2))

    n_rated = sum(len(v) for rater in all_ratings.values() for v in rater.values())
    print(f"\nSaved {n_rated} total ratings across {len(all_ratings)} rater(s).")
    if agreement:
        print("Inter-rater agreement:")
        for pair, stats in agreement.items():
            print(f"  {pair}: kappa={stats['kappa']}, MAD={stats['mean_abs_diff']} (n={stats['n_shared']})")


if __name__ == "__main__":
    main()
