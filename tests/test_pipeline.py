"""Smoke + validity tests. Run: pytest -q

Cross-platform note: float outputs from EconML/DoWhy depend on the BLAS/LAPACK
backend (OpenBLAS on Linux, MKL on Windows, Accelerate on macOS), so estimates
can differ in the last digits across OSes. Tests therefore use tolerance-based
checks (`pytest.approx` / inequalities), never exact float equality.
"""
import numpy as np
import pytest
from src.data.generate_synthetic_ehr import generate
from src.evaluation.power import required_n_per_arm
from src.causal.estimators import ate_ipw, ate_and_cate_dml, estimate_propensity


def test_generator_has_confounding():
    df = generate(n=5000, seed=1)
    naive = (df.loc[df.early_vasopressor == 1, "mortality_28d"].mean()
             - df.loc[df.early_vasopressor == 0, "mortality_28d"].mean())
    oracle = df["_true_ite"].mean()
    # Naive association should be MORE positive (biased) than the true benefit.
    assert naive > oracle


def test_ipw_recovers_sign_and_magnitude():
    df = generate(n=12000, seed=2)
    oracle = df["_true_ite"].mean()
    res = ate_ipw(df)
    assert res.ate < 0                                    # correct sign (benefit)
    # Tolerance-based, not exact: robust to BLAS/LAPACK differences across OSes.
    assert res.ate == pytest.approx(oracle, abs=0.03)     # within 3pp of truth


def test_dml_recovers_effect_and_heterogeneity():
    df = generate(n=12000, seed=3)
    res = ate_and_cate_dml(df)
    assert res.ate < 0
    # Sicker (high SOFA) patients should show larger benefit -> CATE more negative.
    hi = res.cate[df.sofa_score.values >= 9].mean()
    lo = res.cate[df.sofa_score.values <= 4].mean()
    assert hi < lo


def test_power_formula_sane():
    n = required_n_per_arm(p_control=0.32, mde=0.03)
    assert 3000 < n < 6000                       # ballpark for 3pp at 80% power
    # Deterministic closed form; tiny scipy.norm.ppf differences tolerated.
    assert n == pytest.approx(3697, abs=3)


def test_evalue_monotonic_and_sane():
    from src.evaluation.sensitivity import evalue_risk_difference
    # Bigger effect -> bigger E-value (harder to explain away).
    small = evalue_risk_difference(-0.02, -0.01, 0.32)["evalue_point"]
    big = evalue_risk_difference(-0.08, -0.05, 0.32)["evalue_point"]
    assert big > small > 1.0


def test_evaluation_report_generates(tmp_path):
    import yaml
    from src.reporting.evaluation_report import generate_evaluation_report
    cfg = yaml.safe_load(open("config/experiment.yaml", encoding="utf-8"))
    rep = {"study_id": "T", "naive_association": 0.0255, "oracle_ate": -0.0586,
           "ate_ipw": {"ate": -0.040, "ci": [-0.058, -0.020]},
           "ate_dml": {"ate": -0.050, "ci": [-0.067, -0.033]},
           "primary_kpi": {"GO": True}, "DECISION_GO": False,
           "guardrails": [{"col": "aki", "increase": 0.037, "pass": False}],
           "guardrails_pass": False,
           "sensitivity": {"evalue": {"evalue_point": 1.66, "evalue_ci_bound": 1.48}},
           "propensity_diagnostics": {"auc": 0.74}}
    p = generate_evaluation_report(rep, cfg, path=str(tmp_path / "r.md"))
    txt = open(p, encoding="utf-8").read()
    assert "Simpson's Paradox" in txt and "YES" in txt   # sign flip detected
    assert "8.41pp" in txt                                # bias computed correctly
    assert "NO-GO" in txt and "Safety guardrail" in txt   # decision driver


# ===========================================================================
# QA suite (public-release gate): schema, balance checks, governance NO-GO
# ===========================================================================
def test_ingestion_schema_matches_expected():
    """Phase 1 output must match the MIMIC-IV loader column contract, so real
    data is a zero-refactoring drop-in for the synthetic generator."""
    from src.data.load_mimic import REQUIRED_COLUMNS
    df = generate(n=200, seed=7)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    assert not missing, f"schema mismatch — missing columns: {missing}"


def test_propensity_balance_check_runs():
    """Covariate-balance diagnostic must execute and demonstrate that IPW
    weighting reduces confounder imbalance vs. the raw cohort."""
    from src.evaluation.diagnostics import standardized_mean_differences
    df = generate(n=4000, seed=8)
    ps = estimate_propensity(df)
    bal = standardized_mean_differences(df, ps)
    assert "all_balanced" in bal
    # Severity (SOFA) is the strongest confounder; weighting must shrink its SMD.
    assert abs(bal["sofa_score"]["smd_weighted"]) < abs(bal["sofa_score"]["smd_unweighted"])


def test_governance_gate_triggers_nogo_on_safety_breach():
    """The decision gate must return NO-GO when efficacy PASSES but a safety
    guardrail is breached — and GO only when every pre-registered gate passes."""
    import pipeline
    base = {
        "primary_kpi": {"GO": True},   # 28-day mortality benefit is real
        "guardrails_pass": False,      # ...but AKI guardrail breached (+3.7pp)
        "power": {"powered": True},
        "positivity": {"positivity_ok": True},
        "balance": {"all_balanced": True},
        "refutation": {"all_passed": True},
    }
    ctx = {"cfg": {}, "report": dict(base)}
    pipeline._p_decision(ctx)
    assert ctx["report"]["DECISION_GO"] is False   # safety veto -> NO-GO

    ctx = {"cfg": {}, "report": {**base, "guardrails_pass": True}}
    pipeline._p_decision(ctx)
    assert ctx["report"]["DECISION_GO"] is True     # all gates pass -> GO
