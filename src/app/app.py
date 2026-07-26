"""
Streamlit CATE explorer -- the 'application' layer for clinicians / execs.

Run:  streamlit run src/app/app.py

Lets a user set a patient's SOFA and lactate and see the model's predicted
individualized mortality benefit of early vasopressors, plus a cohort-level
targeting curve. Import-guarded so the repo installs without streamlit.
"""
from __future__ import annotations
import numpy as np

try:
    import streamlit as st
    import matplotlib.pyplot as plt
except Exception as e:  # pragma: no cover
    raise SystemExit("Install extras:  pip install streamlit matplotlib") from e

from src.data.generate_synthetic_ehr import generate
from src.causal.estimators import ate_and_cate_dml


@st.cache_resource
def _fit():
    df = generate(n=8000)
    res = ate_and_cate_dml(df, effect_modifiers=("sofa_score", "lactate"))
    return df, res


def main():
    st.title("Individualized Treatment Effect Explorer")
    st.caption("Early vasopressor initiation → 28-day mortality (synthetic cohort)")

    df, res = _fit()
    st.metric("Population ATE (risk difference)", f"{res.ate:+.3f}",
              help="Negative = mortality reduction")

    c1, c2 = st.columns(2)
    sofa = c1.slider("SOFA score", 0, 24, 8)
    lact = c2.slider("Lactate (mmol/L)", 0.5, 20.0, 4.0)

    from econml.dml import CausalForestDML  # noqa
    cate = res  # already fit; query effect for this patient
    # Re-query effect at the chosen point:
    est_point = np.array([[sofa, lact]])
    # res doesn't hold the estimator; refit-free approximation via nearest cohort:
    mask = (np.abs(df["sofa_score"] - sofa) <= 1) & (np.abs(df["lactate"] - lact) <= 1)
    local = res.cate[mask.values]
    pred = float(local.mean()) if local.size else float(res.ate)
    st.metric("Predicted benefit for this patient", f"{pred:+.3f}")
    if pred < -0.03:
        st.success("Model recommends EARLY vasopressors (meets -3pp threshold).")
    else:
        st.info("Benefit below decision threshold; use clinical judgment.")

    fig, ax = plt.subplots()
    order = np.argsort(res.cate)
    ax.plot(np.arange(len(order)), np.sort(res.cate))
    ax.axhline(-0.03, ls="--", color="red", label="decision threshold")
    ax.set_xlabel("patients (ranked by predicted benefit)")
    ax.set_ylabel("predicted risk difference")
    ax.legend()
    st.pyplot(fig)


if __name__ == "__main__":
    main()
