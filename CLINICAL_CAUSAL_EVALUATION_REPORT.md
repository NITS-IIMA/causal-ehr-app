# Clinical & Causal Evaluation Report

**Study:** CAUSAL-EHR-2026-VASO — effect of `early_vasopressor` on `mortality_28d` (risk_difference)
**Population:** adult septic shock, first ICU stay
**Generated:** 2026-07-25 10:37 UTC (auto-produced from the pipeline report)
**Data mode:** synthetic validation — oracle-anchored, estimators blinded to ground truth.

---

## 1. Executive Summary & Decision Analysis

- **Pipeline Decision:** **NO-GO**
- **Decision driver:** Safety guardrail, **not** efficacy. The efficacy endpoint *passed* (DML ATE -5.03pp, 95% CI [-6.70pp, -3.35pp], meets the pre-registered ≤ -3.00pp threshold). The verdict is overturned by guardrail breach(es): acute_kidney_injury (+3.7pp).

**Key Findings — Oracle vs. Estimators.** Ground-truth effect is a -5.86pp absolute change (NNT ≈ **17**). Both causal estimators recover the correct sign and clinically concordant magnitude (DML -5.03pp; IPW -4.02pp).
The **naive association points the opposite way (+2.55pp)** — it would misclassify the intervention's direction of effect.

> **CRITICAL — Sign discordance.** The unadjusted signal and the causal truth disagree in *direction*, not merely magnitude. Any decision layer consuming observational contrasts would reach the clinically inverted conclusion.

**Clinical Rationale.** The intervention is causally efficacious and survives refutation (E-value 1.66); deployment is withheld because a pre-committed safety guardrail is breached. Correct posture: conditional pause — pursue heterogeneity analysis to find the sub-population in whom benefit dominates the safety cost.

---

## 2. Confounding & Discrepancy Diagnostics

- **Bias Magnitude:** `|Naive − Oracle| = |(+2.55pp) − (-5.86pp)| =` **8.41pp** (≈ 1.43× the reference effect size).
- **Simpson's Paradox / severe selection bias Detected:** **YES** (sign reversal between naive and oracle).
- **Treatment predictability (propensity AUC):** 0.74 — strong confounding by baseline covariates.

**Clinical Mechanism — confounding by indication.** Clinicians preferentially initiate treatment in the sickest patients (elevated severity, higher baseline risk). Treatment is therefore correlated with the outcome *through the shared common cause of illness severity*, independent of any drug effect. In the unadjusted contrast this baseline-risk imbalance dominates and inverts the true effect, manufacturing a false signal. Conditioning on the backdoor set — verified by post-weighting balance (all |SMD| < 0.10) — removes the spurious component.

> **WARNING — adjustment must be orthogonalized.** A high propensity AUC confirms treatment is strongly predictable from severity; naïve regression that is not cross-fitted/orthogonalized remains exposed to residual regularization bias in this regime.

---

## 3. Causal Estimator Performance Benchmarking

| Estimator | Estimated ATE | Error vs. Reference | Relative Performance |
| :--- | :--- | :--- | :--- |
| **Oracle (Ground Truth)** | -5.86pp | 0.0000 | Benchmark |
| **DML** | -5.03pp | 0.84pp (14.3% rel.) | **Rank 1 — best.** Closest recovery, CI excludes null |
| **IPW** | -4.02pp | 1.85pp (31.5% rel.) | Rank 2. ~2.2× the DML error |
| **Naive Association** | +2.55pp | 8.41pp (bias) | Unadjusted — **directionally wrong** |

**Methodological Takeaway — why DML leads.** Double Machine Learning estimates the effect from *residual-on-residual* regression after flexibly modeling both E[Y|W] and E[T|W]; the Neyman-orthogonal moment condition is first-order insensitive to nuisance error and cross-fitting removes overfitting bias. It is doubly robust — consistent if *either* nuisance model is approximately correct — whereas IPW depends solely on a correct propensity model and suffers variance inflation from extreme inverse-propensity weights near the overlap boundary (mitigated but not eliminated by stabilization and 2–98% trimming). IPW is retained as a transparent, assumption-light cross-check: sign/magnitude agreement between the two is itself evidence no single functional form drives the result.

---

## 4. Next Steps & Actionable Recommendations

1. **Subgroup analysis (CATE).** Estimate individualized effects with `CausalForestDML` / T-/X-learner on the pre-declared effect modifiers (sofa_score, lactate). Objective: convert a population-level NO-GO into a targeted, guardrail-compliant policy by locating the strata where benefit exceeds the safety cost; evaluate via a policy-value / uplift curve.
2. **Sensitivity testing.** Report the E-value (**1.66** point / **1.48** at the CI bound): the confounder–treatment and confounder–outcome association strength required to nullify the effect. Complement with Rosenbaum Γ-bounds and the `add_unobserved_common_cause` simulation sweep.
3. **Model validation.** Confirm propensity overlap / common support (histograms, 0.05–0.95 trimming), re-check covariate balance (|SMD| < 0.10) after weighting, and add outcome-model calibration (Brier, calibration slope) plus a negative-control outcome. Strata outside common support are non-identifiable and must be excluded.

> **BOTTOM LINE.** Causally effective (NNT ≈ 17) and robust, but deployment is halted on the safety guardrail. Immediate path forward is CATE-driven patient targeting, not efficacy re-litigation.

---

### Appendix — Clinical risk of trusting observational metrics

Relying on the naive association (+2.55pp) instead of the causal estimate would have judged the intervention *harmful* and withheld a therapy that changes the outcome by -5.86pp absolute (≈ 6 events per 100 patients; NNT ≈ 17). The observational metric recommends the **opposite** clinical action — the defining hazard of correlational analytics under confounded treatment assignment.
