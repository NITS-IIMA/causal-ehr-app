"""
MIMIC-IV loader stub.

MIMIC-IV is credentialed (PhysioNet DUA + CITI training required); it cannot be
bundled. Swap this in once you have BigQuery / Postgres access. The pipeline is
schema-agnostic: it only needs the columns declared in config/experiment.yaml
(confounders + treatment + outcome), so the synthetic generator and this loader
are interchangeable.

Reference cohort logic (sketch):
  - Base cohort: `mimiciv_derived.sepsis3` (Sepsis-3) intersected with an ICU stay.
  - Treatment: first vasopressor time from `mimiciv_derived.vasoactive_agent`;
    early = within 6h of shock onset (persistent hypotension / lactate>=2).
  - Outcome: 28-day mortality from `admissions.deathtime` / `patients.dod`.
  - Confounders: first-24h SOFA (`sepsis3`/`sofa`), first lactate, min MAP,
    Charlson comorbidity, baseline creatinine, age at admission.
"""
from __future__ import annotations
import pandas as pd

REQUIRED_COLUMNS = [
    "age", "sofa_score", "lactate", "mean_arterial_pressure",
    "comorbidity_index", "baseline_creatinine",
    "early_vasopressor", "mortality_28d",
    "acute_kidney_injury", "limb_ischemia",
]


def load(source: str | None = None) -> pd.DataFrame:
    raise NotImplementedError(
        "Provide a MIMIC-IV connection. Return a DataFrame with columns: "
        + ", ".join(REQUIRED_COLUMNS)
        + ". Until then, use src.data.generate_synthetic_ehr.generate()."
    )
