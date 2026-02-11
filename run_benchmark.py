#!/usr/bin/env python3
"""
Web Scraping Benchmark — compare crawlers × LLMs against ground truth.

Usage:
    # Full benchmark (all 6 crawlers × 2 LLMs × 21 domains)
    python run_benchmark.py --domains domains.csv

    # Quick test with specific crawlers/LLMs
    python run_benchmark.py --domain-list resend.com plausible.io --crawlers firecrawl --llms openai

    # Choose output format
    python run_benchmark.py --domains domains.csv --output-format csv
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from src.config import Config
from src.types import CrawlerType, LLMType
from src.pipeline.runner import BenchmarkRunner
from src.pipeline.summary import print_summary_stats
from src.pipeline.data_loader import load_domains_csv


def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def print_summary(report):
    print_summary_stats(
        total_domains=report.total_domains,
        total_combinations=report.total_combinations,
        summary_by_crawler=report.summary_by_crawler,
        summary_by_llm=report.summary_by_llm,
        summary_by_combo=report.summary_by_combo,
        summary_by_crawler_presence=report.summary_by_crawler_presence,
        summary_by_llm_presence=report.summary_by_llm_presence,
        summary_by_combo_presence=report.summary_by_combo_presence,
    )

def _mask(value: str) -> str:
    if not value:
        return "MISSING"
    if len(value) <= 6:
        return value[0] + "***"
    return f"{value[:3]}...{value[-3:]}"


def main():
    parser = argparse.ArgumentParser(
        description="Run web scraping benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input
    input_grp = parser.add_mutually_exclusive_group(required=True)
    input_grp.add_argument("--domains", type=Path, help="CSV file with 'domain' column")
    input_grp.add_argument("--domain-list", nargs="+", help="Space-separated domains")

    # Crawlers & LLMs
    parser.add_argument(
        "--crawlers", nargs="+",
        choices=["firecrawl", "crawl4ai", "jina", "scrapingbee", "scraperapi", "custom_html"],
        default=["firecrawl", "crawl4ai", "jina", "scrapingbee", "scraperapi", "custom_html"],
        help="Crawlers to benchmark (default: all six)",
    )
    parser.add_argument(
        "--llms", nargs="+",
        choices=["openai", "claude"],
        default=["openai", "claude"],
        help="LLMs to use for extraction (default: both)",
    )

    # Page discovery
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Max internal pages to crawl per domain (excluding homepage)",
    )

    # Output
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument(
        "--output-format",
        choices=["json", "csv", "all"],
        default="json",
    )
    parser.add_argument(
        "--dont-save-intermediate",
        action="store_true",
        help="Disable saving per-domain/crawler/LLM intermediate artifacts",
    )
    parser.add_argument(
        "--llm-compare",
        action="store_true",
        help="Use OpenAI and Claude to compare extracted values vs ground truth",
    )

    # Config
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args()
    setup_logging(args.log_level)
    logger = logging.getLogger("benchmark")

    # Load config
    config = Config.from_env(str(args.env_file))
    config.output_dir = args.output_dir
    logger.info("API keys: firecrawl=%s, jina=%s, scrapingbee=%s, scraperapi=%s, openai=%s, anthropic=%s",
                _mask(config.firecrawl_api_key),
                _mask(config.jina_api_key),
                _mask(config.scrapingbee_api_key),
                _mask(config.scraperapi_api_key),
                _mask(config.openai_api_key),
                _mask(config.anthropic_api_key))

    # Parse enums
    crawlers = [CrawlerType(c) for c in args.crawlers]
    llms = [LLMType(l) for l in args.llms]

    # Validate keys
    try:
        config.validate(crawlers, llms)
    except ValueError as e:
        print(f"\nConfiguration error:\n{e}\n", file=sys.stderr)
        print("Copy .env.example to .env and fill in your API keys.", file=sys.stderr)
        sys.exit(1)

    # Load domains
    if args.domains:
        domains = load_domains_csv(args.domains)
    else:
        domains = [d if d.startswith("http") else f"https://{d}" for d in args.domain_list]

    logger.info(f"Benchmark: {len(domains)} domains × {len(crawlers)} crawlers × {len(llms)} LLMs")
    logger.info(f"  Crawlers: {[c.value for c in crawlers]}")
    logger.info(f"  LLMs: {[l.value for l in llms]}")
    logger.info(f"  Max pages: {args.max_pages}")

    # Run
    runner = BenchmarkRunner(config)
    report = asyncio.run(
        runner.run(
            domains,
            crawlers,
            llms,
            max_pages=args.max_pages,
            save_intermediate=not args.dont_save_intermediate,
            llm_compare=args.llm_compare,
        )
    )

    # Save & print
    runner.save_results(report, args.output_dir, args.output_format)
    print_summary(report)


if __name__ == "__main__":
    main()
