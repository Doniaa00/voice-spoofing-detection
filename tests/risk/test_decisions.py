"""Layering of the shared core (SDD Fig. 1): the band rule lives in src/risk, not in research code.

The API container has the Risk & Confidence service but not the Evaluation service, so src/risk
must never import src.evaluation; the harness re-exports the band rule instead of defining it.
"""
from __future__ import annotations

import ast
from pathlib import Path

import src.evaluation.metrics as metrics
import src.risk.decisions as decisions

RISK_DIR = Path(__file__).resolve().parents[2] / "src" / "risk"


def test_metrics_reexports_the_core_band_rule():
    # Same objects, not copies: evaluation and deployment cannot drift apart.
    assert metrics.three_way_decisions is decisions.three_way_decisions
    assert (metrics.AUTHENTIC, metrics.SYNTHETIC, metrics.UNCERTAIN) == (
        decisions.AUTHENTIC,
        decisions.SYNTHETIC,
        decisions.UNCERTAIN,
    )
    assert metrics.DECISIONS is decisions.DECISIONS


def _imported_modules(path: Path) -> list[str]:
    """Absolute module names imported by a source file (relative imports resolved inside src.risk)."""
    names = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # from .x / ..x: resolve against the src.risk package
                base = ["src", "risk"][: max(0, 2 - (node.level - 1))]
                names.append(".".join(base + ([node.module] if node.module else [])))
            else:
                names.append(node.module or "")
    return names


def test_risk_does_not_import_evaluation():
    files = sorted(RISK_DIR.glob("*.py"))
    assert files, f"no source files found in {RISK_DIR}"
    offending = {
        f.name: name
        for f in files
        for name in _imported_modules(f)
        if name == "src.evaluation" or name.startswith("src.evaluation.") or name.startswith("evaluation")
    }
    assert offending == {}
