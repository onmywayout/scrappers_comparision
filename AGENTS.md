# AGENTS.md

This file documents how to work on this repository safely and consistently.

## Purpose

- Provide quick context for maintainers and automation agents.
- Record conventions and key entry points.

## Key Files

- `run_benchmark.py` — main CLI entry point.
- `compare_intermediate.py` — cached re‑evaluation and summaries.
- `src/pipeline/runner.py` — orchestrates crawl → parse → extract → evaluate.
- `src/evaluator/comparator.py` — scoring logic.
- `src/llm/value_compare.py` — LLM‑based value comparison.
- `verified_data.jsonl` — default ground truth.
- `verified_data_v5.jsonl` — latest ground truth variant.

## Commands

- Create venv + install:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```
- Run benchmark:
  ```bash
  python3 run_benchmark.py --domain-list example.com --max-pages 2
  ```
- Re‑evaluate from cache:
  ```bash
  python3 compare_intermediate.py --domain ALL
  ```

## Behavior Notes

- Intermediate artifacts are saved by default (disable with `--dont-save-intermediate`).
- `--llm-compare` uses cached crawl/extraction and calls LLMs to compare values.
- Link discovery skips auth/login paths and image/static files.
- Local crawlers provide raw HTML for link discovery; API crawlers do not.

## Editing Conventions

- Prefer `python3` over `python` in docs and commands.
- Keep changes minimal and explicit.
- Update `README.md` or `AGENTS.md` if behavior or entry points change.
