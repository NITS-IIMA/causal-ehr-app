# Changelog

All notable changes to the **Causal ML & Measurement Framework** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/); the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-07-26
### Added
- Dynamic, cross-platform font resolution in `src/reporting/pdf_report.py` — searches
  matplotlib's bundled DejaVu Sans (present on every OS) plus system font dirs via
  `pathlib.Path`, with a Helvetica fallback, so PDFs render Unicode glyphs on
  Windows, macOS, and Linux.
- `pytest.approx()` tolerance bounds in `tests/test_pipeline.py` to absorb
  BLAS/LAPACK floating-point rounding differences (OpenBLAS / MKL / Accelerate).
- `.gitattributes` enforcing `LF` line endings for code/config, `CRLF` for
  Windows scripts, and binary markers for assets (`.pdf`, `.png`, `.zip`, `.ttf`).
- `docs/PLATFORM.md` documenting the cross-platform hardening measures.
### Changed
- Standardized `encoding="utf-8"` across all text `open()` handles (reporting,
  config, analytics, tests) — prevents Windows `cp1252` `UnicodeEncodeError` on
  report symbols (em-dash, `≈`, `≤`).

## [1.0.1] - 2026-07-26
### Added
- Packaging: `pyproject.toml` (`pip install -e ".[app,dev]"`) exposing the
  `causal-ehr` console command.
- Community files: `CONTRIBUTING.md`, issue templates, and a pull-request template.
- Repository traffic analytics — a scheduled GitHub Action + `scripts/collect_traffic.py`
  that snapshots views/clones into `traffic/*.csv` (GitHub retains only 14 days),
  documented in `docs/ANALYTICS.md`.
### Fixed
- `.gitignore`: added `!traffic/*.csv` exception so the global `*.csv` rule no
  longer blocks analytics snapshots; added `*.log` and removed stray `run.log`.

## [1.0.0] - 2026-07-25
### Added
- Core causal engine: DoWhy backdoor identification + EconML Double Machine
  Learning (`LinearDML` for ATE, `CausalForestDML` for CATE), with stabilized IPW
  as a transparent cross-check.
- Pre-registered governance gate (`config/experiment.yaml`): power/MDE, positivity,
  covariate balance, refutation (placebo / random common cause / subset), E-value
  sensitivity, and safety guardrails — emitting a single GO/NO-GO decision
  (28-day mortality benefit vetoed by the +3.7pp AKI guardrail).
- MIMIC-IV v3.1 schema-aligned loader contract + deterministic synthetic generator
  with a known ground-truth effect for statistical validation.
- Reporting: auto `MODEL_CARD.md`, `decision_report.json`, Markdown + PDF
  evaluation reports, and an interactive Streamlit CATE explorer (`src/app/app.py`).
- Phase-graph pipeline with a `--phase` CLI, QA test suite, CI workflow, MIT
  `LICENSE`, and an enterprise `README.md`.
