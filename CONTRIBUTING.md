# Contributing

Thanks for your interest in improving the Causal ML & Measurement Framework.

## Ground rules
- **Never commit patient data.** MIMIC-IV is credentialed; `.gitignore` blocks
  `.csv`, `.parquet`, `.sqlite`, etc. Use the synthetic generator or the open
  100-patient MIMIC-IV Demo for examples and tests.
- Keep the **pre-registration discipline**: thresholds, KPIs, guardrails, and the
  refutation gate live in `config/experiment.yaml` and are frozen *before*
  modeling. PRs that tune thresholds to change a decision will be declined.
- Every phase is a node in the dependency graph in `pipeline.py`. Add new logic
  as a phase function + entry in `PHASES` / `PHASE_OUTPUT_KEYS`, not as a
  side-effect elsewhere.

## Dev setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[app,dev]"
pytest -q
```

## Before opening a PR
1. `pytest -q` passes (all tests green).
2. New behavior has a test in `tests/test_pipeline.py`.
3. `python pipeline.py` still runs end-to-end and produces the artifacts.
4. No secrets, credentials, or absolute/local paths in the diff.

## Commit style
Short imperative subject lines (e.g. `Add TMLE cross-check estimator`).

## Reporting issues
Use the issue templates (bug report / feature request). For security concerns,
please avoid filing a public issue with sensitive detail.
