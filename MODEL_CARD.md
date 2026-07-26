# Model Card — CAUSAL-EHR-2026-VASO

_Auto-generated 2026-07-25 05:57 UTC from a frozen
pre-registration. This card documents a CAUSAL estimator, not a predictor: its
job is an unbiased treatment effect, and it is judged on assumptions + robustness,
not accuracy._

## 1. Intended use
- **Question:** effect of `early_vasopressor` on `mortality_28d` (risk_difference).
- **Population:** adult septic shock, first ICU stay.
- **Users:** clinical research leadership / trial design; decision support, NOT autonomous action.
- **Out of scope:** individual prescribing without clinician oversight; populations
  outside the modeled overlap region.

## 2. Headline result
| Metric | Value |
|---|---|
| ATE (risk difference) | -5.0pp |
| 95% CI | [-6.7pp, -3.3pp] |
| Naive (confounded) association | +2.5pp |
| Meets pre-registered threshold (≤ -3pp) | True |
| CI excludes null | True |
| **DECISION** | **NO-GO** |

The naive association and the causal estimate disagree in **direction** — the
model's entire value is correcting that confounding.

## 3. Method
- **Identification:** DoWhy backdoor adjustment on 6 confounders:
  age, sofa_score, lactate, mean_arterial_pressure, comorbidity_index, baseline_creatinine.
- **Estimation:** Double ML — `LinearDML` (ATE + CI), `CausalForestDML` (CATE),
  cross-fitted and Neyman-orthogonal. Stabilized IPW as an independent check.
- **Effect modifiers (pre-declared):** sofa_score, lactate.

## 4. Assumption checks
| Check | Result |
|---|---|
| Powered for MDE | True |
| Positivity / common support OK | True |
| Covariate balance after weighting | True |
| Refutation gate (placebo/RCC/subset) | True |

## 5. Sensitivity to unmeasured confounding
| Metric | Value |
|---|---|
| E-value (point) | 1.66 |
| E-value (CI bound) | 1.48 |
| Nullified by simulated confounder at strength | None |

An unmeasured confounder would need a risk ratio of 1.66 with BOTH treatment and outcome (above what measured confounders explain) to fully explain this effect; 1.48 to shift the CI to the null.

## 6. Guardrails (safety)
| Guardrail | Change vs control | Status |
|---|---|---|
| acute_kidney_injury | +3.7pp | FAIL |
| limb_ischemia | +0.8pp | PASS |

## 7. Known limitations & failure modes
- **Unmeasured confounding** is the primary threat on real EHR; the E-value above
  quantifies — but cannot eliminate — it. Report it alongside every effect.
- **Positivity** violations (patients who would never/always be treated) are trimmed;
  the estimand therefore applies to the overlap population only.
- **Synthetic validation** proves the *code* recovers a known truth; it does NOT
  prove the DAG is correct for real patients. Clinician review of the DAG is required.
- **Guardrail thresholds are policy, not statistics** — they need clinical sign-off.

## 8. Reproducibility
Seed `20260725`, n=12000. Run `python pipeline.py`.
