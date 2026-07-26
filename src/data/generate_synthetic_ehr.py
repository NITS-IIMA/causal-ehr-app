"""
Synthetic septic-shock EHR generator with a KNOWN ground-truth treatment effect.

Because the true individual treatment effect (ITE) is baked in, this module lets
us validate that the causal pipeline recovers the truth *before* touching real
MIMIC-IV data. Confounding is intentional: sicker patients (high SOFA, high
lactate) are BOTH more likely to receive early vasopressors AND more likely to
die -- so naive correlation is biased, and only correct adjustment recovers the
real effect.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

CONFOUNDERS = [
    "age", "sofa_score", "lactate",
    "mean_arterial_pressure", "comorbidity_index", "baseline_creatinine",
]
TREATMENT = "early_vasopressor"
OUTCOME = "mortality_28d"


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def true_ite(df: pd.DataFrame) -> np.ndarray:
    """Ground-truth individual risk difference (negative = benefit).

    Effect is heterogeneous: sicker patients (high SOFA / lactate) benefit MORE
    from early vasopressors; low-severity patients benefit little.
    """
    sofa_z = (df["sofa_score"] - 6.0) / 3.0
    lact_z = (df["lactate"] - 3.0) / 2.0
    # Base benefit -0.04, amplified by severity, floored so it never harms much.
    ite = -0.04 - 0.03 * np.clip(sofa_z, 0, None) - 0.02 * np.clip(lact_z, 0, None)
    return np.clip(ite, -0.25, 0.02)


def generate(n: int = 20000, seed: int = 20260725) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    age = np.clip(rng.normal(64, 15, n), 18, 95)
    sofa_score = np.clip(rng.normal(6, 3, n), 0, 24).round()
    lactate = np.clip(rng.gamma(3.0, 1.0, n), 0.5, 20)
    mean_arterial_pressure = np.clip(rng.normal(70, 12, n), 40, 120)
    comorbidity_index = np.clip(rng.poisson(2.0, n), 0, 12)
    baseline_creatinine = np.clip(rng.gamma(2.0, 0.6, n), 0.3, 8)

    df = pd.DataFrame({
        "age": age, "sofa_score": sofa_score, "lactate": lactate,
        "mean_arterial_pressure": mean_arterial_pressure,
        "comorbidity_index": comorbidity_index,
        "baseline_creatinine": baseline_creatinine,
    })

    # --- Treatment assignment (CONFOUNDED by severity) ---------------------
    logit_t = (
        -0.5
        + 0.18 * (sofa_score - 6)
        + 0.25 * (lactate - 3)
        - 0.03 * (mean_arterial_pressure - 70)
        + 0.010 * (age - 64)
    )
    propensity = _sigmoid(logit_t)
    treat = rng.binomial(1, propensity)
    df[TREATMENT] = treat

    # --- Potential outcomes -------------------------------------------------
    base_logit = (
        -1.2
        + 0.14 * (sofa_score - 6)
        + 0.22 * (lactate - 3)
        + 0.015 * (age - 64)
        + 0.10 * comorbidity_index
        - 0.02 * (mean_arterial_pressure - 70)
    )
    p_control = _sigmoid(base_logit)                    # risk if untreated
    p_treat = np.clip(p_control + true_ite(df), 0.001, 0.999)  # risk if treated
    p_obs = np.where(treat == 1, p_treat, p_control)
    df[OUTCOME] = rng.binomial(1, p_obs)

    # --- Guardrail outcomes (safety signals) --------------------------------
    df["acute_kidney_injury"] = rng.binomial(
        1, _sigmoid(-2.0 + 0.15 * baseline_creatinine + 0.20 * treat)
    )
    df["limb_ischemia"] = rng.binomial(
        1, _sigmoid(-4.0 + 0.35 * treat + 0.05 * (lactate - 3))
    )

    # Stash oracle columns (drop before modeling; used only for validation).
    df["_true_ite"] = true_ite(df)
    df["_propensity_true"] = propensity
    return df


if __name__ == "__main__":
    d = generate()
    print(d.describe().round(3).T)
    print("\nTrue ATE (oracle):", round(d["_true_ite"].mean(), 4))
    print("Naive assoc (biased):",
          round(d.loc[d.early_vasopressor == 1, "mortality_28d"].mean()
                - d.loc[d.early_vasopressor == 0, "mortality_28d"].mean(), 4))
