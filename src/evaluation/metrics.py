"""Decision metrics: primary KPI gate, guardrails, and CATE policy value."""
from __future__ import annotations
import numpy as np
import pandas as pd
from src.data.generate_synthetic_ehr import TREATMENT, OUTCOME


def primary_kpi_gate(ate: float, ci_high: float, threshold: float) -> dict:
    return {
        "ate": ate,
        "meets_threshold": bool(ate <= threshold),
        "excludes_null": bool(ci_high < 0),
        "GO": bool(ate <= threshold and ci_high < 0),
    }


def guardrail_check(df: pd.DataFrame, col: str, max_increase: float) -> dict:
    treated = df.loc[df[TREATMENT] == 1, col].mean()
    control = df.loc[df[TREATMENT] == 0, col].mean()
    diff = float(treated - control)
    return {"col": col, "treated_rate": float(treated), "control_rate": float(control),
            "increase": diff, "pass": bool(diff <= max_increase)}


def policy_value(cate: np.ndarray, df: pd.DataFrame, threshold: float = 0.0) -> dict:
    """Expected outcomes if we treat only patients with CATE < threshold.

    Compares a 'treat-all' vs 'treat-the-predicted-benefiters' policy using the
    oracle ITE when available (synthetic) for honest evaluation.
    """
    treat_mask = cate < threshold
    out = {"frac_recommended_treatment": float(treat_mask.mean())}
    if "_true_ite" in df.columns:
        ite = df["_true_ite"].values
        out["policy_mortality_delta_vs_none"] = float(np.sum(ite[treat_mask]) / len(df))
        out["treat_all_mortality_delta"] = float(np.mean(ite))
        out["targeting_gain"] = float(out["treat_all_mortality_delta"]
                                      - out["policy_mortality_delta_vs_none"])
    return out
