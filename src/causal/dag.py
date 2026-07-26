"""Declarative causal graph (backdoor set) shared by DoWhy and reporting."""
from __future__ import annotations
from src.data.generate_synthetic_ehr import CONFOUNDERS, TREATMENT, OUTCOME


def gml_graph(confounders=CONFOUNDERS, treatment=TREATMENT, outcome=OUTCOME) -> str:
    """Return a GML string: confounders -> T, confounders -> Y, T -> Y."""
    nodes, edges = [], []
    all_nodes = list(confounders) + [treatment, outcome]
    for nm in all_nodes:
        nodes.append(f'node [ id "{nm}" label "{nm}" ]')
    for c in confounders:
        edges.append(f'edge [ source "{c}" target "{treatment}" ]')
        edges.append(f'edge [ source "{c}" target "{outcome}" ]')
    edges.append(f'edge [ source "{treatment}" target "{outcome}" ]')
    return "graph [ directed 1 " + " ".join(nodes + edges) + " ]"
