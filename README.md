# Causal ML & Measurement Framework for Clinical Interventions

> Individualized treatment-effect estimation with a pre-registered GO/NO-GO decision gate — evaluating **early vasopressor timing in septic shock** on MIMIC-IV.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Build](https://github.com/NITS-IIMA/causal-ehr-app/actions/workflows/ci.yml/badge.svg)](https://github.com/NITS-IIMA/causal-ehr-app/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-9%20passing-brightgreen.svg)](tests/test_pipeline.py)
[![Causal](https://img.shields.io/badge/causal-DoWhy%20%7C%20EconML-8A2BE2.svg)](#causal-inference--ml-framework)
[![Stars](https://img.shields.io/github/stars/NITS-IIMA/causal-ehr-app?style=social)](https://github.com/NITS-IIMA/causal-ehr-app/stargazers)
[![Forks](https://img.shields.io/github/forks/NITS-IIMA/causal-ehr-app?style=social)](https://github.com/NITS-IIMA/causal-ehr-app/network/members)
[![Downloads](https://img.shields.io/github/downloads/NITS-IIMA/causal-ehr-app/total.svg)](https://github.com/NITS-IIMA/causal-ehr-app/releases)


---

## Executive Summary

**The clinical core.** In adult septic shock, does initiating vasopressors **early (<= 6h from shock onset)** reduce **28-day mortality** — and *for whom*? The timing decision is made thousands of times a day with thin trial evidence, making it a high-value target for causal analysis.

**The causal trap.** The sickest patients (high SOFA, high lactate, low MAP) are the ones clinicians treat soonest, so treatment is entangled with baseline risk. A naive treated-vs-untreated comparison therefore reports that early vasopressors *increase* mortality by **+2.55pp** — it labels a life-saving therapy as harmful. After Neyman-orthogonal adjustment via Double Machine Learning, the true effect emerges: a **-5.03pp mortality reduction** (oracle ground truth -5.86pp; NNT ~ 17). **Same data, opposite conclusion.** That gap is the entire value proposition.

**The measurement discipline.** Every threshold — primary KPI, minimum detectable effect, safety guardrails, refutation gate — is **frozen in a pre-registration file (`config/experiment.yaml`) before modeling**, so "proof" cannot be redefined after seeing the outcomes. The pipeline emits a single auditable **GO / NO-GO** verdict plus a JSON record, an auto-generated model card, and a circulation-ready PDF.

---

## System Architecture & DAG

```
        +------------------------------+
        |  Data Ingestion              |   MIMIC-IV v3.1 schema
        |  (100-pt demo / synthetic)   |   6 confounders + T + Y
        +---------------+--------------+
                        v
        +------------------------------+
        |  DoWhy Identification        |   backdoor adjustment set
        |  (explicit causal DAG)       |   assumptions made testable
        +---------------+--------------+
                        v
        +------------------------------+
        |  DML Estimation              |   LinearDML       -> ATE + CI
        |  (Neyman-orthogonal, x-fit)  |   CausalForestDML -> CATE
        +---------------+--------------+   IPW -> transparent cross-check
                        v
        +------------------------------+
        |  Refutation Gate             |   placebo . random common cause .
        |  + E-value sensitivity       |   data subset . unobserved confounder
        +---------------+--------------+
                        v
        +------------------------------+
        |  Guardrail Audit             |   AKI . limb ischemia . positivity .
        |  (safety + assumptions)      |   post-weighting covariate balance
        +---------------+--------------+
                        v
        +------------------------------+
        |  Decision Output             |   GO / NO-GO  +  decision_report.json
        |                              |   +  MODEL_CARD.md  +  PDF report
        +------------------------------+
```

The pipeline is a **dependency graph of phases** (`data -> power/propensity/estimate/refute -> diagnostics/sensitivity -> kpi/guardrails -> decision -> report -> pdf`). Both the full run and any single phase resolve the same graph — one source of truth, no duplicated logic.

---

## Causal Inference & ML Framework

| Layer | Tool / Method | Why |
|---|---|---|
| Identification | **DoWhy** (backdoor) | Encodes the DAG so causal assumptions are explicit and refutable |
| ATE inference | **EconML `LinearDML`** | Neyman-orthogonal, cross-fitted -> tight, calibrated confidence interval |
| Heterogeneity | **EconML `CausalForestDML`** | Individualized CATE for patient-level targeting |
| Transparent check | **Stabilized IPW** | Second, assumption-light estimator so no single functional form drives the result |
| Robustness | **DoWhy refuters** | Placebo, random common cause, data-subset must all pass |
| Unmeasured confounding | **E-value** (VanderWeele & Ding) | Quantifies how strong a hidden confounder must be to nullify the effect |
| Governance | **Auto model card + PDF** | Intended use, assumptions, limitations, failure modes on every run |

---

## Key Empirical Results

_Verified run, synthetic-validation cohort (n = 12,000), seed 20260725._

| Metric | Value | Interpretation |
|---|---|---|
| **Naive association** | **+2.55pp** | Confounded — wrong *direction* (looks harmful) |
| **DML ATE (primary)** | **-5.03pp**  (95% CI -6.70, -3.35) | True benefit; CI excludes null; meets <= -3pp threshold |
| IPW ATE (cross-check) | -4.02pp | Same sign/magnitude -> estimate not an artifact of one model |
| Oracle ATE (ground truth) | -5.86pp | DML error 0.83pp vs. IPW 1.84pp |
| **Confounding bias** | **8.41pp** | Naive is off by 1.44x the true effect size |
| **E-value** | **1.66** point / **1.48** at CI bound | Confounder-T and confounder-Y RR needed to explain away the effect |
| **Propensity AUC** | **0.738** | Treatment strongly predictable from severity -> real confounding |
| **Post-weighting balance** | **all \|SMD\| < 0.10** | IPW weighting achieves covariate balance |
| Number needed to treat | **17** | ~1 death averted per 17 patients treated early |

---

## Automated Governance Gate

```
DECISION: NO-GO   (red)
```

The verdict is a **safety veto, not an efficacy failure.** The efficacy endpoint *passed* every gate — the DML mortality benefit is -5.03pp, the 95% CI excludes null, it clears the pre-registered -3pp threshold, and it survives all three refutations (E-value 1.66). The pipeline still returns **NO-GO** because early vasopressor initiation **breaches the acute-kidney-injury guardrail: +3.7pp vs. a +2.0pp tolerance.**

`DECISION_GO` is `True` **only if every pre-registered condition holds**:

```python
DECISION_GO = (primary_kpi.GO            # -5.03pp, CI excludes null  [pass]
               and guardrails_pass       # AKI +3.7pp > +2.0pp        [FAIL] <- veto
               and power.powered         # 4,680 >= 3,697/arm         [pass]
               and positivity_ok         # common support            [pass]
               and balance.all_balanced  # |SMD| < 0.10              [pass]
               and refutation.all_passed)# placebo/RCC/subset        [pass]
```

This is the framework working as designed: a benefit on the primary endpoint **does not override a safety guardrail**. The recommended next step is CATE-driven patient targeting — find the sub-population where the mortality benefit dominates the nephrotoxic cost — rather than blanket deployment.

---

## Data: MIMIC-IV Demo (zero-refactoring integration)

This repository is **1:1 schema-aligned with the full MIMIC-IV v3.1** clinical database. Development and CI use the **openly-licensed 100-patient MIMIC-IV Demo** (no credentialing required) purely to verify that ingestion, the causal graph, and every gate run against the real schema **without a single line of refactoring**. A deterministic synthetic generator with a *known* ground-truth effect is used for statistical validation (so we can prove the estimators recover a planted truth before trusting them on real patients).

Moving to the full dataset changes **exactly one file** — `src/data/load_mimic.py` — to return the same column contract (`REQUIRED_COLUMNS`). Everything downstream (identification, estimation, refutation, guardrails, decision, reporting) runs unchanged.

| Tier | Access | Use here |
|---|---|---|
| Synthetic generator | none | Ground-truth statistical validation |
| **MIMIC-IV Demo (100 pts)** | **open (ODbL)** | Schema / integration verification |
| MIMIC-IV v3.1 (full) | PhysioNet credential + CITI training | Production analysis (drop-in) |

> Patient data is **never** committed — see `.gitignore` (excludes `.csv`, `.parquet`, `.sqlite`, etc.). Full MIMIC-IV access requires a signed PhysioNet Data Use Agreement.

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/NITS-IIMA/causal-ehr-app.git
cd causal-ehr-app

# 2. Create an isolated environment + install (Python >= 3.10)
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# or install as a package (adds the `causal-ehr` command):
# pip install -e ".[app,dev]"

# 3. Run the full pipeline (all phases -> JSON + model card + report + PDF)
python pipeline.py

# 4. Run one phase only (prerequisites resolve automatically)
python -m pipeline --list            # show phases + dependencies
python -m pipeline --phase sensitivity

# 5. Run the QA test suite
pytest -q

# 6. Launch the interactive CATE explorer
streamlit run src/app/app.py
```

Full run ~ 25-30s on a laptop (synthetic n = 12k); all randomness is seeded.

**Artifacts produced by a full run:** `decision_report.json`, `MODEL_CARD.md`, `CLINICAL_CAUSAL_EVALUATION_REPORT.md`, and `CLINICAL_CAUSAL_EVALUATION_REPORT.pdf`.

---

## Repository Structure

```
causal-ehr-app/
|-- config/experiment.yaml          Frozen pre-registration (KPI, MDE, guardrails, gate)
|-- pipeline.py                     Phase dependency graph + CLI (--phase / --list)
|-- src/
|   |-- data/                       Synthetic generator + MIMIC-IV loader contract
|   |-- causal/                     DAG . DoWhy identification . DML/IPW estimators . refutation
|   |-- evaluation/                 Power/MDE . diagnostics (AUC, SMD) . E-value sensitivity . metrics
|   |-- reporting/                  Model card . evaluation report . PDF renderer
|   `-- app/app.py                  Streamlit individualized-effect explorer
|-- tests/test_pipeline.py          QA suite (schema . balance . governance NO-GO gate)
|-- .github/workflows/ci.yml        CI: pytest on Python 3.10-3.12
`-- requirements.txt . LICENSE . .gitignore . MODEL_CARD.md
```

---

## Limitations

Unmeasured confounding is the primary threat on real EHR data; the E-value quantifies but cannot eliminate it. The estimand applies only to the region of propensity overlap (positivity-trimmed). Synthetic validation proves the *code* recovers a known truth — it does not prove the DAG is correct for real patients, which requires clinician review. Guardrail thresholds are policy decisions, not statistical ones, and need clinical sign-off. See `MODEL_CARD.md` for the full failure-mode register.

## Cross-platform

Hardened for Windows, macOS, and Linux: UTF-8 I/O everywhere, `pathlib`-based Unicode font resolution, `.gitattributes` line-ending determinism, `spawn`-safe multiprocessing, and `pytest.approx` tolerances for BLAS float variance. See [`docs/PLATFORM.md`](docs/PLATFORM.md).

## Repository analytics

GitHub exposes aggregate traffic (views/clones) and identifiable engagement (stars/forks), but **not** the identity of viewers or cloners. A bundled GitHub Action snapshots traffic daily into `traffic/*.csv` (GitHub keeps only 14 days). See [`docs/ANALYTICS.md`](docs/ANALYTICS.md).

## Changelog

Release history in [`CHANGELOG.md`](CHANGELOG.md) (`v1.0.0` core engine → `v1.0.1` packaging/analytics → `v1.0.2` cross-platform hardening).

## License

Released under the [MIT License](LICENSE).

## Citation

If this framework informs your work, please cite the repository together with the foundational methods, software, and data it builds on.

**This repository**

```bibtex
@software{nitin_causal_ehr_framework_2026,
  author  = {Nitin, Dr.},
  title   = {Causal ML \& Measurement Framework for Clinical Interventions},
  year    = {2026},
  version = {1.0.2},
  url     = {https://github.com/NITS-IIMA/causal-ehr-app}
}
```

**Causal identification & framework**

- Pearl, J. (2009). *Causality: Models, Reasoning, and Inference* (2nd ed.). Cambridge University Press.
- Hernán, M. A., & Robins, J. M. (2020). *Causal Inference: What If*. Boca Raton: Chapman & Hall/CRC.

**Estimation methods**

- Rosenbaum, P. R., & Rubin, D. B. (1983). The central role of the propensity score in observational studies for causal effects. *Biometrika*, 70(1), 41–55.
- Robins, J. M., Hernán, M. Á., & Brumback, B. (2000). Marginal structural models and causal inference in epidemiology. *Epidemiology*, 11(5), 550–560.
- Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W., & Robins, J. (2018). Double/debiased machine learning for treatment and structural parameters. *The Econometrics Journal*, 21(1), C1–C68.
- Wager, S., & Athey, S. (2018). Estimation and inference of heterogeneous treatment effects using random forests. *Journal of the American Statistical Association*, 113(523), 1228–1242.
- Athey, S., Tibshirani, J., & Wager, S. (2019). Generalized random forests. *The Annals of Statistics*, 47(2), 1148–1178.

**Sensitivity analysis**

- Rosenbaum, P. R. (2002). *Observational Studies* (2nd ed.). New York: Springer.
- VanderWeele, T. J., & Ding, P. (2017). Sensitivity analysis in observational research: introducing the E-value. *Annals of Internal Medicine*, 167(4), 268–274.

**Software**

- Sharma, A., & Kiciman, E. (2020). DoWhy: An end-to-end library for causal inference. *arXiv:2011.04216*.
- Battocchi, K., Dillon, E., Hei, M., Lewis, G., Oka, P., Oprescu, M., & Syrgkanis, V. (2019). *EconML: A Python Package for ML-Based Heterogeneous Treatment Effects Estimation*. Microsoft Research. https://github.com/py-why/EconML

**Clinical data & definitions**

- Johnson, A. E. W., Bulgarelli, L., Shen, L., et al. (2023). MIMIC-IV, a freely accessible electronic health record dataset. *Scientific Data*, 10, 1. https://doi.org/10.1038/s41597-022-01899-x
- Singer, M., Deutschman, C. S., Seymour, C. W., et al. (2016). The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3). *JAMA*, 315(8), 801–810.
