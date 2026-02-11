from typing import Dict, List, Tuple

from src.types import EvaluationResult


def _avg(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def compute_summary(
    results: List[EvaluationResult],
) -> Tuple[
    Dict[str, float], Dict[str, float], Dict[str, float],
    Dict[str, float], Dict[str, float], Dict[str, float],
]:
    by_crawler: Dict[str, List[float]] = {}
    by_llm: Dict[str, List[float]] = {}
    by_combo: Dict[str, List[float]] = {}
    by_crawler_presence: Dict[str, List[float]] = {}
    by_llm_presence: Dict[str, List[float]] = {}
    by_combo_presence: Dict[str, List[float]] = {}

    for r in results:
        key = r.crawler.value
        by_crawler.setdefault(key, []).append(r.overall_accuracy)
        by_crawler_presence.setdefault(key, []).append(r.overall_presence_accuracy)

        key = r.llm.value
        by_llm.setdefault(key, []).append(r.overall_accuracy)
        by_llm_presence.setdefault(key, []).append(r.overall_presence_accuracy)

        key = f"{r.crawler.value}+{r.llm.value}"
        by_combo.setdefault(key, []).append(r.overall_accuracy)
        by_combo_presence.setdefault(key, []).append(r.overall_presence_accuracy)

    return (
        {k: _avg(v) for k, v in by_crawler.items()},
        {k: _avg(v) for k, v in by_llm.items()},
        {k: _avg(v) for k, v in by_combo.items()},
        {k: _avg(v) for k, v in by_crawler_presence.items()},
        {k: _avg(v) for k, v in by_llm_presence.items()},
        {k: _avg(v) for k, v in by_combo_presence.items()},
    )


def print_summary_stats(
    total_domains: int,
    total_combinations: int,
    summary_by_crawler: Dict[str, float],
    summary_by_llm: Dict[str, float],
    summary_by_combo: Dict[str, float],
    summary_by_crawler_presence: Dict[str, float],
    summary_by_llm_presence: Dict[str, float],
    summary_by_combo_presence: Dict[str, float],
):
    print("\n" + "=" * 70)
    print("  BENCHMARK RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Domains tested:  {total_domains}")
    print(f"  Combinations:    {total_combinations}")
    print()

    print("  Value Accuracy by Crawler:")
    for name, score in sorted(summary_by_crawler.items()):
        bar = "█" * int(score * 30) + "░" * (30 - int(score * 30))
        print(f"    {name:<12} {bar} {score:.1%}")
    print()

    print("  Value Accuracy by LLM:")
    for name, score in sorted(summary_by_llm.items()):
        bar = "█" * int(score * 30) + "░" * (30 - int(score * 30))
        print(f"    {name:<12} {bar} {score:.1%}")
    print()

    print("  Value Accuracy by Combination:")
    for combo, score in sorted(summary_by_combo.items(), key=lambda x: -x[1]):
        bar = "█" * int(score * 30) + "░" * (30 - int(score * 30))
        print(f"    {combo:<22} {bar} {score:.1%}")
    print()

    print("  Presence Accuracy by Crawler:")
    for name, score in sorted(summary_by_crawler_presence.items()):
        bar = "█" * int(score * 30) + "░" * (30 - int(score * 30))
        print(f"    {name:<12} {bar} {score:.1%}")
    print()

    print("  Presence Accuracy by LLM:")
    for name, score in sorted(summary_by_llm_presence.items()):
        bar = "█" * int(score * 30) + "░" * (30 - int(score * 30))
        print(f"    {name:<12} {bar} {score:.1%}")
    print()

    print("  Presence Accuracy by Combination:")
    for combo, score in sorted(summary_by_combo_presence.items(), key=lambda x: -x[1]):
        bar = "█" * int(score * 30) + "░" * (30 - int(score * 30))
        print(f"    {combo:<22} {bar} {score:.1%}")
    print("=" * 70 + "\n")
