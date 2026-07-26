"""Pre-code power / minimum-detectable-effect calculation for a risk difference."""
from __future__ import annotations
import numpy as np
from scipy import stats


def required_n_per_arm(p_control: float, mde: float,
                       alpha: float = 0.05, power: float = 0.80) -> int:
    """Two-proportion z-test sample size per arm for an absolute risk diff."""
    p_treat = p_control - mde  # mde is the reduction we want to detect
    p_bar = (p_control + p_treat) / 2
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    num = (z_a * np.sqrt(2 * p_bar * (1 - p_bar))
           + z_b * np.sqrt(p_control * (1 - p_control) + p_treat * (1 - p_treat))) ** 2
    return int(np.ceil(num / mde ** 2))


def power_check(n_treated: int, n_control: int, p_control: float, mde: float,
                alpha: float = 0.05, power: float = 0.80) -> dict:
    need = required_n_per_arm(p_control, mde, alpha, power)
    have = min(n_treated, n_control)
    return {
        "required_n_per_arm": need,
        "smaller_arm_n": int(have),
        "powered": bool(have >= need),
        "mde": mde,
    }
