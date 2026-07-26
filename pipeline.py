"""
End-to-end causal pipeline. Runs the pre-registered analysis in order:

  1. Load config (the frozen pre-registration).
  2. Generate/ingest cohort.
  3. Power / MDE gate  -> NO-GO if underpowered.
  4. Positivity (common support) check.
  5. ATE two ways: IPW (transparent) + CausalForestDML (orthogonal).
  6. DoWhy identification + refutation gate (placebo / RCC / subset).
  7. Overlap/balance diagnostics + E-value sensitivity to unmeasured confounding.
  8. Primary KPI gate + guardrails.
  9. CATE + targeting policy value.
 10. Emit a decision report (dict + JSON) and a MODEL_CARD.md.

Run:  python pipeline.py
"""
from __future__ import annotations
import json
import yaml
import numpy as np

from src.data.generate_synthetic_ehr import generate, TREATMENT, OUTCOME
from src.evaluation.power import power_check
from src.evaluation.metrics import primary_kpi_gate, guardrail_check, policy_value
from src.evaluation.diagnostics import (
    propensity_diagnostics, standardized_mean_differences,
)
from src.evaluation.sensitivity import (
    evalue_risk_difference, dowhy_unobserved_confounder,
)
from src.reporting.model_card import generate_model_card
from src.reporting.evaluation_report import generate_evaluation_report
from src.reporting.pdf_report import markdown_to_pdf
from src.causal.estimators import (
    ate_ipw, ate_and_cate_dml, dowhy_identified_ate, estimate_propensity,
    positivity_report,
)


def load_config(path: str = "config/experiment.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# =========================================================================== #
# Phases as a dependency graph. Each phase is a function that reads/writes a
# shared `ctx`; a phase declares which other phases must run first. The CLI and
# the full run() both resolve this graph, so there is ONE source of truth and no
# duplicated logic.
# =========================================================================== #
def _ctx_new(cfg: dict) -> dict:
    return {"cfg": cfg, "report": {"study_id": cfg["meta"]["study_id"]},
            "_done": set()}


def _p_data(ctx):
    cfg = ctx["cfg"]
    df = generate(n=cfg["repro"]["n_patients"], seed=cfg["repro"]["seed"])
    ctx["df"] = df
    ctx["report"]["naive_association"] = float(
        df.loc[df[TREATMENT] == 1, OUTCOME].mean()
        - df.loc[df[TREATMENT] == 0, OUTCOME].mean())
    ctx["report"]["oracle_ate"] = float(df["_true_ite"].mean())


def _p_power(ctx):
    cfg, df = ctx["cfg"], ctx["df"]
    n_t = int((df[TREATMENT] == 1).sum())
    n_c = int((df[TREATMENT] == 0).sum())
    ctx["report"]["power"] = power_check(
        n_t, n_c, cfg["power"]["baseline_event_rate"],
        cfg["power"]["minimum_detectable_effect"],
        cfg["power"]["alpha"], cfg["power"]["power"])


def _p_propensity(ctx):
    ctx["ps"] = estimate_propensity(ctx["df"])
    ctx["report"]["positivity"] = positivity_report(ctx["ps"])


def _p_estimate(ctx):
    cfg, df = ctx["cfg"], ctx["df"]
    ctx["ipw"] = ate_ipw(df)
    ctx["dml"] = ate_and_cate_dml(df, effect_modifiers=cfg["estimand"]["effect_modifiers"])
    ctx["report"]["ate_ipw"] = {"ate": ctx["ipw"].ate,
                                "ci": [ctx["ipw"].ci_low, ctx["ipw"].ci_high]}
    ctx["report"]["ate_dml"] = {"ate": ctx["dml"].ate,
                                "ci": [ctx["dml"].ci_low, ctx["dml"].ci_high]}


def _p_refute(ctx):
    from src.causal.refutation import run_refutations
    ctx["dowhy"] = dowhy_identified_ate(ctx["df"])
    ctx["report"]["refutation"] = run_refutations(*ctx["dowhy"])


def _p_diagnostics(ctx):
    ctx["report"]["propensity_diagnostics"] = propensity_diagnostics(ctx["df"], ctx["ps"])
    ctx["report"]["balance"] = standardized_mean_differences(ctx["df"], ctx["ps"])


def _p_sensitivity(ctx):
    cfg, dml = ctx["cfg"], ctx["dml"]
    model, estimand, estimate = ctx["dowhy"]
    ctx["report"]["sensitivity"] = {
        "evalue": evalue_risk_difference(
            dml.ate, dml.ci_high, cfg["power"]["baseline_event_rate"]),
        **dowhy_unobserved_confounder(model, estimand, estimate),
    }


def _p_kpi(ctx):
    dml = ctx["dml"]
    ctx["report"]["primary_kpi"] = primary_kpi_gate(
        dml.ate, dml.ci_high, ctx["cfg"]["primary_kpi"]["success_threshold"])


def _p_guardrails(ctx):
    df = ctx["df"]
    gr = [guardrail_check(df, "acute_kidney_injury", 0.02),
          guardrail_check(df, "limb_ischemia", 0.01)]
    ctx["report"]["guardrails"] = gr
    ctx["report"]["guardrails_pass"] = all(x["pass"] for x in gr)


def _p_policy(ctx):
    ctx["report"]["policy"] = policy_value(ctx["dml"].cate, ctx["df"])


def _p_decision(ctx):
    r = ctx["report"]
    refut_ok = r.get("refutation", {}).get("all_passed", True)
    r["DECISION_GO"] = bool(
        r["primary_kpi"]["GO"] and r["guardrails_pass"]
        and r["power"]["powered"] and r["positivity"]["positivity_ok"]
        and r["balance"]["all_balanced"] and refut_ok)


def _p_modelcard(ctx):
    ctx["report"]["model_card_path"] = generate_model_card(ctx["report"], ctx["cfg"])


def _p_report(ctx):
    ctx["report"]["evaluation_report_path"] = generate_evaluation_report(
        ctx["report"], ctx["cfg"])


def _p_pdf(ctx):
    md = ctx["report"].get("evaluation_report_path", "CLINICAL_CAUSAL_EVALUATION_REPORT.md")
    ctx["report"]["evaluation_report_pdf"] = markdown_to_pdf(md)


# name -> (function, [prerequisite phases])
PHASES: dict = {
    "data":         (_p_data,         []),
    "power":        (_p_power,        ["data"]),
    "propensity":   (_p_propensity,   ["data"]),
    "estimate":     (_p_estimate,     ["data"]),
    "refute":       (_p_refute,       ["data"]),
    "diagnostics":  (_p_diagnostics,  ["propensity"]),
    "sensitivity":  (_p_sensitivity,  ["estimate", "refute"]),
    "kpi":          (_p_kpi,          ["estimate"]),
    "guardrails":   (_p_guardrails,   ["data"]),
    "policy":       (_p_policy,       ["estimate"]),
    "decision":     (_p_decision,     ["kpi", "guardrails", "power",
                                       "propensity", "diagnostics", "refute"]),
    "modelcard":    (_p_modelcard,    ["decision", "sensitivity"]),
    "report":       (_p_report,       ["decision", "sensitivity", "policy"]),
    "pdf":          (_p_pdf,          ["report"]),
}

# report keys each phase owns (for printing just that phase's slice)
PHASE_OUTPUT_KEYS: dict = {
    "data": ["naive_association", "oracle_ate"],
    "power": ["power"],
    "propensity": ["positivity"],
    "estimate": ["ate_ipw", "ate_dml"],
    "refute": ["refutation"],
    "diagnostics": ["propensity_diagnostics", "balance"],
    "sensitivity": ["sensitivity"],
    "kpi": ["primary_kpi"],
    "guardrails": ["guardrails", "guardrails_pass"],
    "policy": ["policy"],
    "decision": ["DECISION_GO"],
    "modelcard": ["model_card_path"],
    "report": ["evaluation_report_path"],
    "pdf": ["evaluation_report_pdf"],
}


def _ensure(name: str, ctx: dict):
    """Run `name` and its prerequisites once each (memoized)."""
    if name in ctx["_done"]:
        return
    func, deps = PHASES[name]
    for d in deps:
        _ensure(d, ctx)
    func(ctx)
    ctx["_done"].add(name)


def run(config_path: str = "config/experiment.yaml") -> dict:
    """Run every phase (resolves the full graph: model card + evaluation report)."""
    ctx = _ctx_new(load_config(config_path))
    _ensure("modelcard", ctx)
    _ensure("pdf", ctx)          # pulls in `report`, then renders the PDF
    return ctx["report"]


def run_phase(name: str, config_path: str = "config/experiment.yaml") -> dict:
    """Run a single phase (plus only the prerequisites it needs) and return that
    phase's outputs. `name='all'` runs the full pipeline."""
    if name == "all":
        return run(config_path)
    if name not in PHASES:
        raise SystemExit(
            f"unknown phase '{name}'. choose from: {', '.join(PHASES)}, all")
    ctx = _ctx_new(load_config(config_path))
    _ensure(name, ctx)
    return {k: ctx["report"][k] for k in PHASE_OUTPUT_KEYS[name]
            if k in ctx["report"]}


def _print_full_summary(rep: dict):
    print(json.dumps(rep, indent=2, default=float))
    print("\n" + "=" * 60)
    print("DECISION:", "GO" if rep["DECISION_GO"] else "NO-GO")
    print("Oracle ATE : {:+.4f}".format(rep["oracle_ate"]))
    print("Naive assoc: {:+.4f}  (biased by confounding)".format(rep["naive_association"]))
    print("IPW  ATE   : {:+.4f}".format(rep["ate_ipw"]["ate"]))
    print("DML  ATE   : {:+.4f}".format(rep["ate_dml"]["ate"]))


def main(argv=None):
    """Console entry point (installed as the `causal-ehr` command)."""
    import argparse

    ap = argparse.ArgumentParser(
        prog="causal-ehr",
        description="Causal-EHR pipeline (Phases 0-4). Run all phases or one.")
    ap.add_argument("--phase", default="all",
                    help="phase to run: " + ", ".join(list(PHASES) + ["all"]))
    ap.add_argument("--config", default="config/experiment.yaml",
                    help="path to the frozen pre-registration YAML")
    ap.add_argument("--list", action="store_true",
                    help="list phases and their dependencies, then exit")
    args = ap.parse_args(argv)

    if args.list:
        print("Phase           depends on")
        print("-" * 45)
        for n, (_f, deps) in PHASES.items():
            print(f"  {n:13s} {', '.join(deps) or '(none)'}")
        return 0

    if args.phase == "all":
        _print_full_summary(run(args.config))
    else:
        out = run_phase(args.phase, args.config)
        print(f"# phase: {args.phase}")
        print(json.dumps(out, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
