"""Generate a MODEL_CARD.md from a pipeline report dict. Governance artifact."""
from __future__ import annotations
from datetime import datetime


def generate_model_card(report: dict, cfg: dict, path: str = "MODEL_CARD.md") -> str:
    e = cfg["estimand"]
    pk = report["primary_kpi"]
    dml = report["ate_dml"]
    sens = report.get("sensitivity", {})
    ev = sens.get("evalue", {})
    go = report["DECISION_GO"]
    verdict = "GO" if go else "NO-GO"

    def row(k, v):
        return f"| {k} | {v} |"

    guardrail_lines = "\n".join(
        f"| {g['col']} | +{g['increase']*100:.1f}pp | "
        f"{'PASS' if g['pass'] else 'FAIL'} |"
        for g in report["guardrails"]
    )

    md = f"""# Model Card — {cfg['meta']['study_id']}

_Auto-generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} from a frozen
pre-registration. This card documents a CAUSAL estimator, not a predictor: its
job is an unbiased treatment effect, and it is judged on assumptions + robustness,
not accuracy._

## 1. Intended use
- **Question:** effect of `{e['treatment']}` on `{e['outcome']}` ({e['effect_measure']}).
- **Population:** {e['target_population']}.
- **Users:** clinical research leadership / trial design; decision support, NOT autonomous action.
- **Out of scope:** individual prescribing without clinician oversight; populations
  outside the modeled overlap region.

## 2. Headline result
| Metric | Value |
|---|---|
{row("ATE (risk difference)", f"{dml['ate']*100:+.1f}pp")}
{row("95% CI", f"[{dml['ci'][0]*100:+.1f}pp, {dml['ci'][1]*100:+.1f}pp]")}
{row("Naive (confounded) association", f"{report['naive_association']*100:+.1f}pp")}
{row("Meets pre-registered threshold (≤ -3pp)", pk["meets_threshold"])}
{row("CI excludes null", pk["excludes_null"])}
{row("**DECISION**", f"**{verdict}**")}

The naive association and the causal estimate disagree in **direction** — the
model's entire value is correcting that confounding.

## 3. Method
- **Identification:** DoWhy backdoor adjustment on {len(e['confounders'])} confounders:
  {', '.join(e['confounders'])}.
- **Estimation:** Double ML — `LinearDML` (ATE + CI), `CausalForestDML` (CATE),
  cross-fitted and Neyman-orthogonal. Stabilized IPW as an independent check.
- **Effect modifiers (pre-declared):** {', '.join(e['effect_modifiers'])}.

## 4. Assumption checks
| Check | Result |
|---|---|
{row("Powered for MDE", report["power"]["powered"])}
{row("Positivity / common support OK", report["positivity"]["positivity_ok"])}
{row("Covariate balance after weighting", report.get("balance", {}).get("all_balanced", "n/a"))}
{row("Refutation gate (placebo/RCC/subset)", report.get("refutation", {}).get("all_passed", "n/a"))}

## 5. Sensitivity to unmeasured confounding
| Metric | Value |
|---|---|
{row("E-value (point)", f"{ev.get('evalue_point', float('nan')):.2f}")}
{row("E-value (CI bound)", f"{ev.get('evalue_ci_bound', float('nan')):.2f}")}
{row("Nullified by simulated confounder at strength", sens.get("nullified_at_strength", "not within tested range"))}

{ev.get('interpretation', '')}

## 6. Guardrails (safety)
| Guardrail | Change vs control | Status |
|---|---|---|
{guardrail_lines}

## 7. Known limitations & failure modes
- **Unmeasured confounding** is the primary threat on real EHR; the E-value above
  quantifies — but cannot eliminate — it. Report it alongside every effect.
- **Positivity** violations (patients who would never/always be treated) are trimmed;
  the estimand therefore applies to the overlap population only.
- **Synthetic validation** proves the *code* recovers a known truth; it does NOT
  prove the DAG is correct for real patients. Clinician review of the DAG is required.
- **Guardrail thresholds are policy, not statistics** — they need clinical sign-off.

## 8. Reproducibility
Seed `{cfg['repro']['seed']}`, n={cfg['repro']['n_patients']}. Run `python pipeline.py`.
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path
