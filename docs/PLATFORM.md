# Cross-Platform Portability Notes (Windows / macOS / Linux)

This project is developed on Linux CI but is designed to run identically on
Windows and macOS. The specific hardening measures:

## 1. File paths & separators
Relative paths are passed to Python's `open()` / `pathlib`, which accept `/` on
all platforms — no hardcoded backslashes anywhere. The only OS-specific path was
the PDF font lookup; it now searches matplotlib's **bundled** DejaVu Sans (present
on every OS because matplotlib is a dependency) plus standard system font dirs via
`pathlib.Path`, falling back to Helvetica. See `src/reporting/pdf_report.py`.

## 2. Encoding
Every text `open()` specifies `encoding="utf-8"`. Without this, Windows' cp1252
default raises `UnicodeEncodeError` on the reports' em-dashes / `≈` / `≤`.

## 3. Line endings (CRLF vs LF)
`.gitattributes` forces `eol=lf` for all text/source (so Linux runners and Docker
never choke on `\r`), `eol=crlf` for `.bat`/`.ps1`/`.cmd`, and marks binaries
(`.pdf`, `.png`, `.zip`, `.ttf`, ...) so Git never rewrites them.

## 4. Multiprocessing (`fork` vs `spawn`)
Windows/macOS use the `spawn` start method, which re-imports modules and pickles
worker callables. This repo is safe because: (a) the entry point is guarded by
`if __name__ == "__main__":` (`pipeline.py`), (b) all worker/phase functions are
defined at module top level (no lambdas/closures handed to parallel backends),
and (c) we rely on EconML/scikit-learn's own joblib defaults rather than custom
`multiprocessing` pools.

## 5. Floating-point / BLAS backend variance
Estimates can differ in the last digits across OpenBLAS (Linux), MKL (Windows),
and Accelerate (macOS). Tests therefore use `pytest.approx(...)` tolerances and
inequalities — never exact float `==` on model outputs.

## 6. Compiled dependencies
No LightGBM/XGBoost native binaries are used; base learners are scikit-learn's
`HistGradientBoosting*`/`RandomForest*` and EconML's `CausalForestDML`, which ship
platform wheels. Requirement: **Python ≥ 3.10** with wheels available for numpy,
scipy, scikit-learn, econml, dowhy (all provide manylinux/macOS/Windows wheels).

## Quick verification on a new machine
```bash
pip install -e ".[app,dev]"
pytest -q            # tolerance-based, should pass on any OS
python pipeline.py   # produces identical GO/NO-GO decision
```
