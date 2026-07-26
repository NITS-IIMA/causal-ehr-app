"""
Causal estimation layer.

Design principle: IDENTIFY with DoWhy (make the backdoor assumption explicit),
ESTIMATE the ATE two independent ways (IPW + Double ML) so a single functional-
form choice cannot drive the result, then estimate heterogeneity (CATE) with a
Causal Forest. Double Machine Learning (Chernozhukov et al., 2018) gives us
Neyman-orthogonal, sqrt(n)-consistent effects that are robust to ML nuisance
misspecification -- the crux of separating causation from mere correlation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegressionCV

from src.data.generate_synthetic_ehr import CONFOUNDERS, TREATMENT, OUTCOME


@dataclass
class CausalResult:
    ate: float
    ci_low: float
    ci_high: float
    method: str
    cate: np.ndarray | None = None
    diagnostics: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Propensity + positivity (common-support) check
# --------------------------------------------------------------------------- #
def estimate_propensity(df: pd.DataFrame, confounders=CONFOUNDERS) -> np.ndarray:
    clf = GradientBoostingClassifier(random_state=0)
    clf.fit(df[confounders], df[TREATMENT])
    return clf.predict_proba(df[confounders])[:, 1]


def positivity_report(propensity: np.ndarray, lo=0.05, hi=0.95) -> dict:
    off = np.mean((propensity < lo) | (propensity > hi))
    return {
        "min_propensity": float(propensity.min()),
        "max_propensity": float(propensity.max()),
        "frac_outside_common_support": float(off),
        "positivity_ok": bool(off < 0.10),
    }


# --------------------------------------------------------------------------- #
# ATE #1 -- IPW (stabilized) as a transparent baseline
# --------------------------------------------------------------------------- #
def ate_ipw(df: pd.DataFrame, confounders=CONFOUNDERS) -> CausalResult:
    ps = estimate_propensity(df, confounders)
    ps = np.clip(ps, 0.02, 0.98)
    t, y = df[TREATMENT].values, df[OUTCOME].values
    w = np.where(t == 1, 1 / ps, 1 / (1 - ps))
    y1 = np.sum(w * t * y) / np.sum(w * t)
    y0 = np.sum(w * (1 - t) * y) / np.sum(w * (1 - t))
    ate = y1 - y0
    # Bootstrap CI
    rng = np.random.default_rng(0)
    boot = []
    n = len(df)
    for _ in range(300):
        idx = rng.integers(0, n, n)
        tt, yy, pp = t[idx], y[idx], ps[idx]
        ww = np.where(tt == 1, 1 / pp, 1 / (1 - pp))
        b1 = np.sum(ww * tt * yy) / np.sum(ww * tt)
        b0 = np.sum(ww * (1 - tt) * yy) / np.sum(ww * (1 - tt))
        boot.append(b1 - b0)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return CausalResult(ate, float(lo), float(hi), "IPW (stabilized)",
                        diagnostics=positivity_report(ps))


# --------------------------------------------------------------------------- #
# ATE #2 + CATE -- Double ML via DoWhy identification + EconML estimation
# --------------------------------------------------------------------------- #
def ate_and_cate_dml(df: pd.DataFrame, confounders=CONFOUNDERS,
                     effect_modifiers=("sofa_score", "lactate")) -> CausalResult:
    """Double ML, two complementary estimators sharing the same orthogonality:

      - LinearDML       -> population ATE with a tight, calibrated CI (inference).
      - CausalForestDML -> individualized CATE for targeting (heterogeneity).

    Both are Neyman-orthogonal: nuisance functions (E[Y|W], E[T|W]) are learned by
    flexible ML and cross-fitted, so the effect estimate is first-order insensitive
    to nuisance error -- the key to separating causation from correlation.
    """
    from econml.dml import LinearDML, CausalForestDML
    from sklearn.ensemble import (
        HistGradientBoostingRegressor, HistGradientBoostingClassifier,
    )

    X = df[list(effect_modifiers)].values          # heterogeneity dims
    W = df[[c for c in confounders if c not in effect_modifiers]].values
    T = df[TREATMENT].values
    Y = df[OUTCOME].values

    # --- ATE + CI (LinearDML, cross-fitted) ---------------------------------
    lin = LinearDML(
        model_y=HistGradientBoostingRegressor(max_iter=150, random_state=0),
        model_t=HistGradientBoostingClassifier(max_iter=150, random_state=0),
        discrete_treatment=True, cv=3, random_state=0,
    )
    lin.fit(Y, T, X=None, W=df[list(confounders)].values)
    ate = float(lin.ate())
    ci_low, ci_high = (float(v) for v in lin.ate_interval(alpha=0.05))

    # --- CATE (Causal Forest) for targeting ---------------------------------
    forest = CausalForestDML(
        model_y=RandomForestRegressor(n_estimators=200, min_samples_leaf=20, random_state=0),
        model_t=GradientBoostingClassifier(random_state=0),
        discrete_treatment=True, n_estimators=400, min_samples_leaf=25, random_state=0,
    )
    forest.fit(Y, T, X=X, W=W)
    cate = forest.effect(X)

    return CausalResult(ate, ci_low, ci_high, "LinearDML(ATE)+CausalForestDML(CATE)",
                        cate=cate,
                        diagnostics={"n_effect_modifiers": len(effect_modifiers)})


def dowhy_identified_ate(df: pd.DataFrame):
    """Return (dowhy_model, identified_estimand, estimate) for refutation."""
    from dowhy import CausalModel
    from src.causal.dag import gml_graph

    model = CausalModel(
        data=df,
        treatment=TREATMENT,
        outcome=OUTCOME,
        graph=gml_graph(),
    )
    estimand = model.identify_effect(proceed_when_unidentifiable=True)
    estimate = model.estimate_effect(
        estimand,
        method_name="backdoor.linear_regression",
        target_units="ate",
    )
    return model, estimand, estimate
