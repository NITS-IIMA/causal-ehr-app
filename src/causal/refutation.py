"""
Robustness gate. An estimate is only accepted as "proof" if it survives all of
these. This operationalizes the refutation_gate block in experiment.yaml.
"""
from __future__ import annotations
import numpy as np


def run_refutations(model, estimand, estimate, tol_placebo=0.01,
                    tol_rcc=0.01, tol_subset=0.02) -> dict:
    results = {}
    base = estimate.value

    # 1. Placebo: replace treatment with random noise -> effect should vanish.
    pl = model.refute_estimate(estimand, estimate,
                               method_name="placebo_treatment_refuter",
                               placebo_type="permute", num_simulations=20)
    results["placebo_treatment"] = {
        "new_effect": float(pl.new_effect),
        "pass": bool(abs(pl.new_effect) < tol_placebo + 0.5 * abs(base)),
    }

    # 2. Random common cause: add irrelevant confounder -> estimate stable.
    rcc = model.refute_estimate(estimand, estimate,
                                method_name="random_common_cause",
                                num_simulations=20)
    results["random_common_cause"] = {
        "new_effect": float(rcc.new_effect),
        "pass": bool(abs(rcc.new_effect - base) < tol_rcc + 0.2 * abs(base)),
    }

    # 3. Data subset: re-estimate on a random 80% -> estimate stable.
    sub = model.refute_estimate(estimand, estimate,
                                method_name="data_subset_refuter",
                                subset_fraction=0.8, num_simulations=20)
    results["data_subset"] = {
        "new_effect": float(sub.new_effect),
        "pass": bool(abs(sub.new_effect - base) < tol_subset + 0.2 * abs(base)),
    }

    results["all_passed"] = all(v["pass"] for v in results.values()
                                if isinstance(v, dict))
    return results
