# Scrap Test

A web‑scraping benchmark that compares multiple crawlers and LLMs against curated ground truth. It crawls company sites, extracts structured features, evaluates accuracy, and supports cached re‑evaluation and LLM‑based value comparison.

## What It Does
- Crawls a domain (homepage first, then internal links discovered on homepage).
- Parses and cleans content into Markdown.
- Extracts structured features via LLMs.
- Compares against ground truth with value and presence scoring.
- Optionally runs an LLM‑based comparison of extracted vs ground truth values.
- Saves intermediate artifacts for re‑evaluation without re‑crawling.

## Quick Start

### 1) Install
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure
Create `.env` from `.env.example` and add your API keys.

### 3) Run a small test
```bash
python3 run_benchmark.py --domain-list example.com --max-pages 2
```

### 4) Save intermediates (default)
Intermediates are saved by default. To disable:
```bash
python3 run_benchmark.py --domain-list example.com --dont-save-intermediate
```

## Crawlers
- `firecrawl` (API)
- `crawl4ai` (local)
- `jina` (API)
- `scrapingbee` (API)
- `scraperapi` (API)
- `custom_html` (local HTML + Trafilatura)

## Key CLI Flags
```bash
python3 run_benchmark.py --domains domains.csv
python3 run_benchmark.py --domain-list example.com another.com
python3 run_benchmark.py --crawlers firecrawl crawl4ai
python3 run_benchmark.py --llms openai claude
python3 run_benchmark.py --max-pages 10
python3 run_benchmark.py --llm-compare
```

## LLM Compare (Value Similarity)
`--llm-compare` uses cached crawl/extraction results and asks OpenAI + Claude to compare extracted values vs ground truth.
- Requires cached intermediates to exist for each crawler/LLM combo.
- Outputs compare JSON into:
  `results/intermediate/<domain>/<crawler>/<llm>_llm_compare.json`

## Re‑evaluate From Cache
Use `compare_intermediate.py` to compute results without crawling:
```bash
python3 compare_intermediate.py --domain ALL
python3 compare_intermediate.py --domain cheerscash.com --show-diffs
python3 compare_intermediate.py --domain ALL --output results/reeval.json
```

## Outputs
- Benchmark report: `results/benchmark_YYYYMMDD_HHMMSS.json`
- Optional CSV: `results/benchmark_YYYYMMDD_HHMMSS.csv`
- Intermediate artifacts:
  `results/intermediate/<domain>/<crawler>/<llm>.json`

## Ground Truth
- Default: `verified_data.jsonl`
- Newer versions: `verified_data_v4.jsonl`
- Excel: `web_scraping_ground_truth_dataset_v4.xlsx`

## Repo Structure
- `src/crawlers/` — crawler implementations
- `src/parser/` — markdown cleanup
- `src/llm/` — LLM extractors + value compare
- `src/evaluator/` — scoring logic
- `src/pipeline/` — benchmark runner & summary

## Notes
- Homepage link discovery ignores image/static file types.
- Auth/login paths are skipped during discovery.
- For local crawlers, link discovery uses raw HTML when available.

