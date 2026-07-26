"""
Sensitivity to UNMEASURED confounding -- the load-bearing evidence on real EHR.

On synthetic data we can check against ground truth; on MIMIC we cannot. The
E-value (VanderWeele & Ding, Ann Intern Med 2017) answers the only question a
skeptic really has: "How strong would an unmeasured confounder have to be -- in
its association with BOTH treatment and outcome -- to explain away your effect?"
A large E-value means an unmeasured confounder would need an implausibly strong
association to nullify the result; a small one means the finding is fragile.
"""
from __future__ import annotations
import numpy as np


def _evalue(rr: float) -> float:
    """E-value for a risk ratio (handles protective effects by symmetry)."""
    if rr <= 0:
        return float("nan")
    rr = max(rr, 1.0 / rr)          # map to >= 1 scale
    return rr + np.sqrt(rr * (rr - 1.0))


def evalue_risk_difference(rd: float, ci_high: float, baseline_risk: float) -> dict:
    """E-value for an absolute risk difference, via approximate risk ratio.

    rd, ci_high are on the risk-difference scale (negative = benefit).
    ci_high is the CI bound NEAREST the null (least favorable).
    """
    p_ctrl = baseline_risk
    rr_point = (p_ctrl + rd) / p_ctrl
    rr_bound = (p_ctrl + ci_high) / p_ctrl
    return {
        "risk_ratio_point": float(rr_point),
        "evalue_point": float(_evalue(rr_point)),
        "evalue_ci_bound": float(_evalue(rr_bound)),   # what must be beaten to reach null
        "interpretation": (
            f"An unmeasured confounder would need a risk ratio of "
            f"{_evalue(rr_point):.2f} with BOTH treatment and outcome (above what "
            f"measured confounders explain) to fully explain this effect; "
            f"{_evalue(rr_bound):.2f} to shift the CI to the null."
        ),
    }


def dowhy_unobserved_confounder(model, estimand, estimate,
                                effect_strengths=(0.0, 0.01, 0.02, 0.03, 0.05)) -> dict:
    """Simulate an unobserved common cause of increasing strength and record how
    the estimate moves. Returns the strength at which the effect crosses zero."""
    curve = []
    crossed_at = None
    for s in effect_strengths:
        r = model.refute_estimate(
            estimand, estimate,
            method_name="add_unobserved_common_cause",
            confounders_effect_on_treatment="binary_flip",
            confounders_effect_on_outcome="linear",
            effect_strength_on_treatment=s,
            effect_strength_on_outcome=s,
        )
        # new_effect may be scalar or (min,max) range depending on dowhy version.
        ne = r.new_effect
        ne = float(np.mean(ne)) if hasattr(ne, "__len__") else float(ne)
        curve.append({"strength": s, "new_effect": ne})
        if crossed_at is None and ne >= 0:      # protective effect nullified
            crossed_at = s
    return {"curve": curve, "nullified_at_strength": crossed_at,
            "robust": bool(crossed_at is None or crossed_at > 0.03)}
