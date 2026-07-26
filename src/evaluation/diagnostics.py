"""Overlap + covariate-balance diagnostics (assumption checks, not effects)."""
from __future__ import annotations
import numpy as np
from sklearn.metrics import roc_auc_score, brier_score_loss
from src.data.generate_synthetic_ehr import CONFOUNDERS, TREATMENT


def propensity_diagnostics(df, propensity) -> dict:
    t = df[TREATMENT].values
    return {
        "auc": float(roc_auc_score(t, propensity)),   # ~0.5 = no confounding signal
        "brier": float(brier_score_loss(t, propensity)),
    }


def standardized_mean_differences(df, propensity, confounders=CONFOUNDERS) -> dict:
    """SMD per confounder, unweighted vs IPW-weighted. |SMD|<0.1 = well balanced."""
    t = df[TREATMENT].values
    ps = np.clip(propensity, 0.02, 0.98)
    w = np.where(t == 1, 1 / ps, 1 / (1 - ps))
    out = {}
    for c in confounders:
        x = df[c].values.astype(float)
        m1, m0 = x[t == 1].mean(), x[t == 0].mean()
        sd = np.sqrt((x[t == 1].var() + x[t == 0].var()) / 2) + 1e-9
        smd_raw = (m1 - m0) / sd
        wm1 = np.average(x[t == 1], weights=w[t == 1])
        wm0 = np.average(x[t == 0], weights=w[t == 0])
        smd_w = (wm1 - wm0) / sd
        out[c] = {"smd_unweighted": float(smd_raw), "smd_weighted": float(smd_w),
                  "balanced": bool(abs(smd_w) < 0.1)}
    out["all_balanced"] = bool(all(v["balanced"] for v in out.values()
                                   if isinstance(v, dict)))
    return out
