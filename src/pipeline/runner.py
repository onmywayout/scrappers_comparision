import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.config import Config
from src.types import (
    CrawlerType, LLMType, BenchmarkReport,
    EvaluationResult, CrawlResult, ParsedContent, ExtractedFeatures,
)
from src.crawlers.registry import get_crawler
from src.parser.markdown_parser import MarkdownParser
from src.llm.registry import get_extractor
from src.llm.value_compare import LLMValueComparator
from src.evaluator.comparator import GroundTruthComparator
from src.pipeline.summary import compute_summary

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    def __init__(self, config: Config):
        self.config = config
        self.parser = MarkdownParser()
        self.comparator = GroundTruthComparator(config.ground_truth_path)

    async def run(
        self,
        domains: List[str],
        crawlers: List[CrawlerType],
        llms: List[LLMType],
        pages: Optional[List[str]] = None,
        max_pages: int = 10,
        save_intermediate: bool = False,
        llm_compare: bool = False,
        use_cache_only: bool = True,
    ) -> BenchmarkReport:
        all_results: List[EvaluationResult] = []
        total = len(domains) * len(crawlers) * len(llms)
        done = 0
        llm_value_comparator = None
        if llm_compare:
            llm_value_comparator = LLMValueComparator(
                openai_api_key=self.config.openai_api_key,
            )

        for domain in domains:
            logger.info(f"{'='*60}")
            logger.info(f"Domain: {domain}")

            # If LLM compare is enabled, require cached crawl+extraction artifacts
            if llm_compare:
                async def _process_cached_combo(ct: CrawlerType, llm_type: LLMType):
                    try:
                        cached = self._load_cached_artifact(
                            domain, ct.value, llm_type.value, self.config.output_dir
                        )
                        if cached is None:
                            raise ValueError(
                                f"Missing cached intermediate for {domain} "
                                f"{ct.value}/{llm_type.value}"
                            )
                        crawl_result, parsed, extraction = cached

                        eval_result = self.comparator.evaluate(extraction)
                        eval_result.homepage_internal_links = crawl_result.homepage_internal_links
                        eval_result.homepage_internal_links_crawled = crawl_result.homepage_internal_links_crawled
                        eval_result.homepage_total_links = crawl_result.homepage_total_links
                        eval_result.homepage_external_links = crawl_result.homepage_external_links

                        gt_map = self.comparator.get_normalized_ground_truth(extraction.domain)
                        if gt_map:
                            extracted_vals = extraction.features
                            gt_vals = {k: v["value"] for k, v in gt_map.items()}
                            openai_scores = self._load_llm_comparison(
                                extraction.domain,
                                ct.value,
                                llm_type.value,
                                self.config.output_dir,
                            )
                            if openai_scores is None:
                                openai_scores = await llm_value_comparator.compare_openai(
                                    extracted_vals, gt_vals
                                )
                                if save_intermediate:
                                    self._save_llm_comparison(
                                        extraction.domain,
                                        ct.value,
                                        llm_type.value,
                                        openai_scores,
                                        self.config.output_dir,
                                    )
                            self._apply_llm_compare_scores(eval_result, openai_scores)

                        return {
                            "ok": True,
                            "crawler": ct,
                            "llm": llm_type,
                            "eval_result": eval_result,
                            "page_count": len(crawl_result.page_contents),
                            "char_count": parsed.char_count,
                            "duration_seconds": crawl_result.duration_seconds,
                        }
                    except Exception as e:
                        return {
                            "ok": False,
                            "crawler": ct,
                            "llm": llm_type,
                            "error": str(e),
                        }

                tasks = [
                    asyncio.create_task(_process_cached_combo(ct, llm_type))
                    for ct in crawlers
                    for llm_type in llms
                ]

                for completed in asyncio.as_completed(tasks):
                    result = await completed
                    if result["ok"]:
                        eval_result = result["eval_result"]
                        all_results.append(eval_result)
                        logger.info(
                            f"  {result['crawler'].value} (cached): "
                            f"{result['page_count']} pages, "
                            f"{result['char_count']} chars, "
                            f"{result['duration_seconds']:.1f}s"
                        )
                        logger.info(
                            f"    {result['llm'].value}: "
                            f"accuracy={eval_result.overall_accuracy:.0%} "
                            f"({eval_result.features_correct}/{len(eval_result.feature_scores)} correct)"
                        )
                    else:
                        logger.error(
                            f"  {result['crawler'].value}+{result['llm'].value} cached run failed: "
                            f"{result['error']}"
                        )
                        all_results.append(EvaluationResult(
                            domain=domain,
                            crawler=result["crawler"],
                            llm=result["llm"],
                            overall_accuracy=0.0,
                            features_found=0,
                            features_correct=0,
                            overall_presence_accuracy=0.0,
                            features_present_correct=0,
                            errors=[result["error"]],
                        ))
                    done += 1
                    logger.info(f"  Progress: {done}/{total}")
                continue

            # Phase 1: Crawl with all crawlers (unless cache-only)
            crawl_results = []
            if not use_cache_only:
                crawl_results = await self._crawl_domain(domain, crawlers, pages, max_pages)
            else:
                # Load cached crawl/parse for each crawler (any llm) and skip crawling
                for ct in crawlers:
                    cached_any = self._load_any_cached_artifact(
                        domain, ct.value, self.config.output_dir
                    )
                    if cached_any is None:
                        logger.error(f"  {ct.value} cached run failed: Missing cached artifact for {domain}")
                        for llm_type in llms:
                            all_results.append(EvaluationResult(
                                domain=domain,
                                crawler=ct,
                                llm=llm_type,
                                overall_accuracy=0.0,
                                features_found=0,
                                features_correct=0,
                                overall_presence_accuracy=0.0,
                                features_present_correct=0,
                                errors=[f"Missing cached artifact for {domain} {ct.value}"],
                            ))
                            done += 1
                            logger.info(f"  Progress: {done}/{total}")
                        continue
                    crawl_result, parsed_cached, _ = cached_any
                    crawl_results.append((crawl_result, parsed_cached))

            for item in crawl_results:
                if use_cache_only:
                    crawl_result, parsed = item
                else:
                    crawl_result = item
                if crawl_result.error and not crawl_result.raw_content:
                    logger.warning(f"  {crawl_result.crawler.value} failed: {crawl_result.error}")
                    for llm_type in llms:
                        all_results.append(EvaluationResult(
                            domain=domain,
                            crawler=crawl_result.crawler,
                            llm=llm_type,
                            overall_accuracy=0.0,
                            features_found=0,
                            features_correct=0,
                            overall_presence_accuracy=0.0,
                            features_present_correct=0,
                            errors=[f"Crawl failed: {crawl_result.error}"],
                        ))
                        done += 1
                    continue

                # Phase 2: Parse (skip if cache-only and we already have parsed)
                if not use_cache_only:
                    parsed = self.parser.parse(crawl_result)
                logger.info(
                    f"  {crawl_result.crawler.value}: "
                    f"{len(crawl_result.page_contents)} pages, "
                    f"{parsed.char_count} chars, "
                    f"{crawl_result.duration_seconds:.1f}s, "
                    f"links: {crawl_result.homepage_internal_links} internal "
                    f"({crawl_result.homepage_internal_links_crawled} crawled), "
                    f"{crawl_result.homepage_external_links} external, "
                    f"{crawl_result.homepage_total_links} total"
                )

                # Phase 3: Extract with each LLM
                for llm_type in llms:
                    try:
                        cached = self._load_cached_artifact(
                            domain, crawl_result.crawler.value, llm_type.value, self.config.output_dir
                        )
                        if cached is not None:
                            _, _, extraction = cached
                            logger.info(f"    {llm_type.value}: using cached extraction")
                        else:
                            extractor = get_extractor(llm_type, self.config)
                            extraction = await extractor.extract(parsed)

                        if extraction.error:
                            logger.warning(f"    {llm_type.value} error: {extraction.error}")

                        # Phase 4: Evaluate
                        eval_result = self.comparator.evaluate(extraction)
                        eval_result.homepage_internal_links = crawl_result.homepage_internal_links
                        eval_result.homepage_internal_links_crawled = crawl_result.homepage_internal_links_crawled
                        eval_result.homepage_total_links = crawl_result.homepage_total_links
                        eval_result.homepage_external_links = crawl_result.homepage_external_links
                        all_results.append(eval_result)

                        logger.info(
                            f"    {llm_type.value}: "
                            f"accuracy={eval_result.overall_accuracy:.0%} "
                            f"({eval_result.features_correct}/{len(eval_result.feature_scores)} correct)"
                        )

                        if llm_compare:
                            gt_map = self.comparator.get_normalized_ground_truth(extraction.domain)
                            if gt_map:
                                extracted_vals = extraction.features
                                gt_vals = {k: v["value"] for k, v in gt_map.items()}
                                try:
                                    openai_scores = self._load_llm_comparison(
                                        extraction.domain,
                                        crawl_result.crawler.value,
                                        llm_type.value,
                                        self.config.output_dir,
                                    )
                                    if openai_scores is None:
                                        openai_scores = await llm_value_comparator.compare_openai(
                                            extracted_vals, gt_vals
                                        )
                                        if save_intermediate:
                                            self._save_llm_comparison(
                                                extraction.domain,
                                                crawl_result.crawler.value,
                                                llm_type.value,
                                                openai_scores,
                                                self.config.output_dir,
                                            )
                                    self._apply_llm_compare_scores(eval_result, openai_scores)
                                except Exception as e:
                                    logger.warning(f"    LLM compare failed: {e}")
                        if save_intermediate and cached is None:
                            self._save_intermediate_artifacts(
                                crawl_result, parsed, extraction, self.config.output_dir
                            )
                    except Exception as e:
                        logger.error(f"    {llm_type.value} failed: {e}")
                        all_results.append(EvaluationResult(
                            domain=domain,
                            crawler=crawl_result.crawler,
                            llm=llm_type,
                            overall_accuracy=0.0,
                            features_found=0,
                            features_correct=0,
                            overall_presence_accuracy=0.0,
                            features_present_correct=0,
                            errors=[str(e)],
                        ))
                    done += 1
                    logger.info(f"  Progress: {done}/{total}")

        return self._build_report(all_results)

    async def _crawl_domain(
        self, domain: str, crawler_types: List[CrawlerType], pages: Optional[List[str]], max_pages: int
    ) -> List[CrawlResult]:
        # Separate API-based crawlers (their infrastructure) from local crawlers (our IP)
        api_crawlers = [
            ct for ct in crawler_types
            if ct in (CrawlerType.FIRECRAWL, CrawlerType.JINA, CrawlerType.SCRAPINGBEE, CrawlerType.SCRAPERAPI)
        ]
        local_crawlers = [
            ct for ct in crawler_types
            if ct in (CrawlerType.CRAWL4AI, CrawlerType.CUSTOM_HTML)
        ]

        results = []

        # API crawlers: Run in full parallel (no rate limiting needed)
        if api_crawlers:
            logger.debug(f"  Running {len(api_crawlers)} API crawlers in parallel")
            api_tasks = []
            for ct in api_crawlers:
                try:
                    crawler = get_crawler(ct, self.config)
                    task = crawler.crawl(domain, pages, max_pages=max_pages)
                    api_tasks.append((ct, task))
                except Exception as e:
                    logger.error(f"  {ct.value} init error: {e}")
                    results.append(CrawlResult(
                    domain=domain,
                    crawler=ct,
                    raw_content="",
                    page_contents={},
                    crawled_at=datetime.now(),
                    error=str(e),
                ))

            # Execute all API crawlers concurrently
            if api_tasks:
                completed = await asyncio.gather(*[task for _, task in api_tasks], return_exceptions=True)
                for (ct, _), result in zip(api_tasks, completed):
                    if isinstance(result, Exception):
                        logger.error(f"  {ct.value} crawl error: {result}")
                        results.append(CrawlResult(
                            domain=domain,
                            crawler=ct,
                            raw_content="",
                            page_contents={},
                            crawled_at=datetime.now(),
                            error=str(result),
                        ))
                    else:
                        results.append(result)

        # Local crawlers: Run with rate limiting to avoid blocks
        if local_crawlers:
            logger.debug(f"  Running {len(local_crawlers)} local crawlers with rate limiting")
            for ct in local_crawlers:
                try:
                    crawler = get_crawler(ct, self.config)
                    result = await crawler.crawl(domain, pages, max_pages=max_pages)
                    results.append(result)
                except Exception as e:
                    logger.error(f"  {ct.value} crawl error: {e}")
                    results.append(CrawlResult(
                        domain=domain,
                        crawler=ct,
                        raw_content="",
                        page_contents={},
                        crawled_at=datetime.now(),
                        error=str(e),
                    ))

        return results

    def _build_report(self, results: List[EvaluationResult]) -> BenchmarkReport:
        (
            summary_by_crawler,
            summary_by_llm,
            summary_by_combo,
            summary_by_crawler_presence,
            summary_by_llm_presence,
            summary_by_combo_presence,
        ) = compute_summary(results)

        return BenchmarkReport(
            timestamp=datetime.now(),
            total_domains=len(set(r.domain for r in results)),
            total_combinations=len(results),
            results=results,
            summary_by_crawler=summary_by_crawler,
            summary_by_llm=summary_by_llm,
            summary_by_combo=summary_by_combo,
            summary_by_crawler_presence=summary_by_crawler_presence,
            summary_by_llm_presence=summary_by_llm_presence,
            summary_by_combo_presence=summary_by_combo_presence,
        )

    def save_results(self, report: BenchmarkReport, output_dir: Path, fmt: str = "json"):
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = report.timestamp.strftime("%Y%m%d_%H%M%S")

        if fmt in ("json", "all"):
            self._save_json(report, output_dir / f"benchmark_{ts}.json")

        if fmt in ("csv", "all"):
            self._save_csv(report, output_dir / f"benchmark_{ts}.csv")

        logger.info(f"Results saved to {output_dir}/")

    def _save_intermediate_artifacts(
        self,
        crawl_result: CrawlResult,
        parsed: ParsedContent,
        extraction: ExtractedFeatures,
        output_dir: Path,
    ):
        import re

        def slugify(text: str) -> str:
            return re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_")

        domain_key = slugify(crawl_result.domain.replace("https://", "").replace("http://", ""))
        base_dir = output_dir / "intermediate" / domain_key / crawl_result.crawler.value
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / f"{extraction.llm.value}.json"

        payload = {
            "domain": crawl_result.domain,
            "crawler": crawl_result.crawler.value,
            "llm": extraction.llm.value,
            "crawled_at": crawl_result.crawled_at.isoformat(),
            "extracted_at": extraction.extracted_at.isoformat(),
            "crawl": {
                "error": crawl_result.error,
                "duration_seconds": crawl_result.duration_seconds,
                "page_contents": crawl_result.page_contents,
                "raw_content": crawl_result.raw_content,
                "homepage_internal_links": crawl_result.homepage_internal_links,
                "homepage_internal_links_crawled": crawl_result.homepage_internal_links_crawled,
                "homepage_external_links": crawl_result.homepage_external_links,
                "homepage_total_links": crawl_result.homepage_total_links,
            },
            "parsed": {
                "char_count": parsed.char_count,
                "markdown": parsed.markdown,
                "page_sections": parsed.page_sections,
            },
            "extraction": {
                "features": extraction.features,
                "raw_llm_response": extraction.raw_llm_response,
                "error": extraction.error,
            },
        }

        with open(path, "w") as f:
            json.dump(payload, f, indent=2, default=str)

    def _load_cached_artifact(
        self, domain: str, crawler: str, llm: str, output_dir: Path
    ) -> Optional[tuple[CrawlResult, ParsedContent, ExtractedFeatures]]:
        import re

        def slugify(text: str) -> str:
            return re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_")

        domain_key = slugify(domain.replace("https://", "").replace("http://", ""))
        path = output_dir / "intermediate" / domain_key / crawler / f"{llm}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())

        crawl = data.get("crawl", {})
        parsed = data.get("parsed", {})
        extraction = data.get("extraction", {})

        crawl_result = CrawlResult(
            domain=data.get("domain", domain),
            crawler=CrawlerType(crawler),
            raw_content=crawl.get("raw_content", ""),
            page_contents=crawl.get("page_contents", {}),
            crawled_at=datetime.now(),
            error=crawl.get("error"),
            duration_seconds=crawl.get("duration_seconds", 0.0),
            homepage_internal_links=crawl.get("homepage_internal_links", 0),
            homepage_internal_links_crawled=crawl.get("homepage_internal_links_crawled", 0),
            homepage_external_links=crawl.get("homepage_external_links", 0),
            homepage_total_links=crawl.get("homepage_total_links", 0),
        )

        parsed_content = ParsedContent(
            domain=crawl_result.domain,
            crawler=crawl_result.crawler,
            markdown=parsed.get("markdown", ""),
            page_sections=parsed.get("page_sections", {}),
            char_count=parsed.get("char_count", 0),
        )

        extraction_obj = ExtractedFeatures(
            domain=crawl_result.domain,
            crawler=crawl_result.crawler,
            llm=LLMType(llm),
            extracted_at=datetime.now(),
            features=extraction.get("features", {}),
            raw_llm_response=extraction.get("raw_llm_response", ""),
            error=extraction.get("error"),
        )

        return crawl_result, parsed_content, extraction_obj

    def _load_any_cached_artifact(
        self, domain: str, crawler: str, output_dir: Path
    ) -> Optional[tuple[CrawlResult, ParsedContent, ExtractedFeatures]]:
        import re

        def slugify(text: str) -> str:
            return re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_")

        domain_key = slugify(domain.replace("https://", "").replace("http://", ""))
        base_dir = output_dir / "intermediate" / domain_key / crawler
        if not base_dir.exists():
            return None
        for path in sorted(base_dir.glob("*.json")):
            if path.name.endswith("_llm_compare.json"):
                continue
            llm = path.stem
            return self._load_cached_artifact(domain, crawler, llm, output_dir)
        return None

    def _save_json(self, report: BenchmarkReport, path: Path):
        data = {
            "timestamp": report.timestamp.isoformat(),
            "total_domains": report.total_domains,
            "total_combinations": report.total_combinations,
            "summary_by_crawler": report.summary_by_crawler,
            "summary_by_llm": report.summary_by_llm,
            "summary_by_combo": report.summary_by_combo,
            "summary_by_crawler_presence": report.summary_by_crawler_presence,
            "summary_by_llm_presence": report.summary_by_llm_presence,
            "summary_by_combo_presence": report.summary_by_combo_presence,
            "results": [
                {
                    "domain": r.domain,
                    "crawler": r.crawler.value,
                    "llm": r.llm.value,
                    "overall_accuracy": round(r.overall_accuracy, 4),
                    "features_found": r.features_found,
                    "features_correct": r.features_correct,
                    "overall_presence_accuracy": round(r.overall_presence_accuracy, 4),
                    "features_present_correct": r.features_present_correct,
                    "feature_scores": {
                        fs.feature_name: {
                            "score": round(fs.score, 2),
                            "match_type": fs.match_type,
                            "extracted": fs.extracted_value,
                            "ground_truth": fs.ground_truth_value
                                if not isinstance(fs.ground_truth_value, (dict,))
                                else str(fs.ground_truth_value),
                        }
                        for fs in r.feature_scores
                    },
                    "crawl_link_stats": {
                        "homepage_internal_links": r.homepage_internal_links,
                        "homepage_internal_links_crawled": r.homepage_internal_links_crawled,
                        "homepage_external_links": r.homepage_external_links,
                        "homepage_total_links": r.homepage_total_links,
                    },
                    "presence_scores": {
                        ps.feature_name: {
                            "score": round(ps.score, 2),
                            "match_type": ps.match_type,
                            "extracted_present": ps.extracted_present,
                            "ground_truth_present": ps.ground_truth_present,
                        }
                        for ps in r.presence_scores
                    },
                    "errors": r.errors,
                }
                for r in report.results
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"  JSON: {path}")

    def _save_llm_comparison(
        self,
        domain: str,
        crawler: str,
        llm: str,
        openai_scores: list,
        output_dir: Path,
    ):
        import re
        def slugify(text: str) -> str:
            return re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_")

        domain_key = slugify(domain.replace("https://", "").replace("http://", ""))
        base_dir = output_dir / "intermediate" / domain_key / crawler
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / f"{llm}_llm_compare.json"
        payload = {
            "domain": domain,
            "crawler": crawler,
            "llm": llm,
            "openai": openai_scores,
        }
        with open(path, "w") as f:
            json.dump(payload, f, indent=2, default=str)

    def _load_llm_comparison(
        self,
        domain: str,
        crawler: str,
        llm: str,
        output_dir: Path,
    ) -> Optional[list]:
        import re

        def slugify(text: str) -> str:
            return re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_")

        domain_key = slugify(domain.replace("https://", "").replace("http://", ""))
        path = output_dir / "intermediate" / domain_key / crawler / f"{llm}_llm_compare.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return data.get("openai")

    def _apply_llm_compare_scores(self, eval_result: EvaluationResult, openai_scores: list):
        if not openai_scores:
            return
        score_map = {}
        for item in openai_scores:
            feature = item.get("feature")
            similarity = item.get("similarity")
            if feature is None or similarity is None:
                continue
            try:
                score_map[feature] = float(similarity)
            except (TypeError, ValueError):
                continue
        if not score_map:
            return

        for fs in eval_result.feature_scores:
            if fs.feature_name in score_map:
                fs.score = score_map[fs.feature_name]
                fs.match_type = "llm_similarity"

        if eval_result.feature_scores:
            eval_result.overall_accuracy = sum(fs.score for fs in eval_result.feature_scores) / len(eval_result.feature_scores)
            eval_result.features_correct = sum(1 for fs in eval_result.feature_scores if fs.score >= 0.8)


    def _save_csv(self, report: BenchmarkReport, path: Path):
        import csv
        from src.types import FEATURES

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            header = [
                "domain", "crawler", "llm",
                "overall_accuracy", "features_found", "features_correct",
                "overall_presence_accuracy", "features_present_correct",
                "homepage_internal_links", "homepage_internal_links_crawled",
                "homepage_external_links", "homepage_total_links",
            ]
            header += [f"{feat}_score" for feat in FEATURES]
            header += [f"{feat}_extracted" for feat in FEATURES]
            writer.writerow(header)

            for r in report.results:
                row = [
                    r.domain, r.crawler.value, r.llm.value,
                    round(r.overall_accuracy, 4), r.features_found, r.features_correct,
                    round(r.overall_presence_accuracy, 4), r.features_present_correct,
                    r.homepage_internal_links, r.homepage_internal_links_crawled,
                    r.homepage_external_links, r.homepage_total_links,
                ]
                score_map = {fs.feature_name: fs for fs in r.feature_scores}
                for feat in FEATURES:
                    fs = score_map.get(feat)
                    row.append(round(fs.score, 2) if fs else 0.0)
                for feat in FEATURES:
                    fs = score_map.get(feat)
                    row.append(fs.extracted_value if fs else None)
                writer.writerow(row)
        logger.info(f"  CSV: {path}")
