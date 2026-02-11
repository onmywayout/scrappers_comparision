#!/usr/bin/env python3
"""
Compare extracted features vs ground truth using saved intermediate artifacts.

Usage:
  python compare_intermediate.py --domain cheerscash.com
  python compare_intermediate.py --domain cheerscash.com --ground-truth verified_data.jsonl
  python compare_intermediate.py --domain ALL --ground-truth verified_data.jsonl --output results/reeval.json
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from src.evaluator.comparator import GroundTruthComparator
from src.types import CrawlerType, LLMType, ExtractedFeatures
from src.pipeline.summary import compute_summary, print_summary_stats


def _resolve_domain_dir(base_dir: Path, domain: str) -> Path:
    domain_dir = base_dir / domain
    if domain_dir.exists():
        return domain_dir
    domain_dir = base_dir / domain.replace("https://", "").replace("http://", "")
    return domain_dir


def load_intermediate_files(base_dir: Path, domain: str) -> list[Path]:
    domain_dir = _resolve_domain_dir(base_dir, domain)
    if not domain_dir.exists():
        raise FileNotFoundError(f"No intermediate data found for {domain_dir}")
    return sorted(domain_dir.glob("*/*.json"))


def load_all_intermediate_files(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        return []
    return sorted(base_dir.glob("*/*/*.json"))


def main():
    parser = argparse.ArgumentParser(description="Compare intermediate extracted features vs ground truth")
    parser.add_argument("--domain", required=True, help="Domain to evaluate (e.g., cheerscash.com) or ALL")
    parser.add_argument("--intermediate-dir", default="results/intermediate", type=Path)
    parser.add_argument("--ground-truth", default="verified_data_v5.jsonl", type=Path)
    parser.add_argument("--show-diffs", action="store_true", help="Show per-feature diffs")
    parser.add_argument("--show-all", action="store_true", help="Show all features (not just diffs)")
    parser.add_argument("--output", type=Path, help="Write results to JSON file")
    args = parser.parse_args()

    comparator = GroundTruthComparator(args.ground_truth)
    if args.domain.upper() == "ALL":
        files = load_all_intermediate_files(args.intermediate_dir)
    else:
        files = load_intermediate_files(args.intermediate_dir, args.domain)

    out = {
        "generated_at": datetime.now().isoformat(),
        "ground_truth": str(args.ground_truth),
        "results": [],
    }
    eval_results = []

    for path in files:
        data = json.loads(path.read_text())
        crawler = CrawlerType(data["crawler"])
        llm = LLMType(data["llm"])
        extraction = ExtractedFeatures(
            domain=data["domain"],
            crawler=crawler,
            llm=llm,
            extracted_at=datetime.now(),
            features=data.get("extraction", {}).get("features", {}),
            raw_llm_response=data.get("extraction", {}).get("raw_llm_response", ""),
            error=data.get("extraction", {}).get("error"),
        )
        result = comparator.evaluate(extraction)
        eval_results.append(result)

        rows = result.feature_scores if args.show_all else [
            fs for fs in result.feature_scores if fs.score < 0.8
        ]
        presence_rows = [ps for ps in result.presence_scores if ps.score < 1.0]

        entry = {
            "domain": data["domain"],
            "crawler": crawler.value,
            "llm": llm.value,
            "accuracy": result.overall_accuracy,
            "presence_accuracy": result.overall_presence_accuracy,
            "features_correct": result.features_correct,
            "features_present_correct": result.features_present_correct,
            "features_total": len(result.feature_scores),
            "diffs": [
                {
                    "feature": fs.feature_name,
                    "score": fs.score,
                    "match_type": fs.match_type,
                    "extracted": fs.extracted_value,
                    "ground_truth": fs.ground_truth_value,
                }
                for fs in rows
            ],
            "presence_diffs": [
                {
                    "feature": ps.feature_name,
                    "extracted_present": ps.extracted_present,
                    "ground_truth_present": ps.ground_truth_present,
                }
                for ps in presence_rows
            ],
        }
        out["results"].append(entry)

        if not args.output and args.show_diffs:
            print("=" * 80)
            print(f"{data['domain']} | {crawler.value} | {llm.value}")
            print(f"Accuracy: {result.overall_accuracy:.0%} "
                  f"({result.features_correct}/{len(result.feature_scores)} correct)")

            if not entry["diffs"]:
                print("No diffs (all correct or no ground truth).")
            else:
                for fs in entry["diffs"]:
                    print(f"- {fs['feature']}: score={fs['score']:.2f} "
                          f"match={fs['match_type']}")
                    print(f"  extracted: {fs['extracted']}")
                    print(f"  ground_truth: {fs['ground_truth']}")

            if entry["presence_diffs"]:
                print("Presence diffs:")
                for ps in entry["presence_diffs"]:
                    print(f"- {ps['feature']}: extracted_present={ps['extracted_present']} "
                          f"ground_truth_present={ps['ground_truth_present']}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=2, default=str))
        print(f"Wrote {args.output}")
    else:
        total_domains = len({r.domain for r in eval_results})
        total_combinations = len(eval_results)
        (
            summary_by_crawler,
            summary_by_llm,
            summary_by_combo,
            summary_by_crawler_presence,
            summary_by_llm_presence,
            summary_by_combo_presence,
        ) = compute_summary(eval_results)
        print_summary_stats(
            total_domains=total_domains,
            total_combinations=total_combinations,
            summary_by_crawler=summary_by_crawler,
            summary_by_llm=summary_by_llm,
            summary_by_combo=summary_by_combo,
            summary_by_crawler_presence=summary_by_crawler_presence,
            summary_by_llm_presence=summary_by_llm_presence,
            summary_by_combo_presence=summary_by_combo_presence,
        )


if __name__ == "__main__":
    main()
