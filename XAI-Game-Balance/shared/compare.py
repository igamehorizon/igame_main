"""
shared/compare.py
Compares the recommendations of a baseline and a follow-up analysis.

A problem is matched by level and problem type (the problem text without its
measured value), so a problem whose value changed is "persisting" with a
before/after value, not "resolved" plus "new".
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


def problem_type(problem: str) -> str:
    """'High backtrack rate (52.3%)' -> 'High backtrack rate'."""
    return re.split(r"\s*\(", problem or "", maxsplit=1)[0].strip()


def problem_value(problem: str) -> str:
    """'High backtrack rate (52.3%)' -> '52.3%'; '' when the text has no value."""
    m = re.search(r"\(([^)]*)\)", problem or "")
    return m.group(1) if m else ""


def _key(rec: Dict[str, Any]) -> Tuple[str, str]:
    return rec.get("level_id", ""), problem_type(rec.get("problem", ""))


def compare_recommendations(baseline: List[Dict[str, Any]],
                            followup: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    base = {_key(r): r for r in baseline}
    fu = {_key(r): r for r in followup}
    persisting = [
        {"level_id": k[0], "problem_type": k[1],
         "before": problem_value(base[k].get("problem", "")),
         "after": problem_value(fu[k].get("problem", "")),
         "priority_before": base[k].get("priority"), "priority_after": fu[k].get("priority"),
         "baseline": base[k], "followup": fu[k]}
        for k in base if k in fu
    ]
    return {
        "resolved": [r for k, r in base.items() if k not in fu],
        "persisting": persisting,
        "new": [r for k, r in fu.items() if k not in base],
    }
