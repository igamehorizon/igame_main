"""
shared/rule_utils.py
Helpers shared by the family rule files.
"""
from __future__ import annotations

from typing import List

_ORDER = ["low", "medium", "high"]


def shap_bump(priority: str, feature: str, top_names: List[str]) -> str:
    """Raise priority by one level when the metric behind a problem is also one of the
    two features that most influence success (SHAP). A problem is only reported when its
    metric has crossed its threshold; the explanation never creates a problem on its own."""
    if feature in top_names[:2] and priority in _ORDER:
        return _ORDER[min(_ORDER.index(priority) + 1, len(_ORDER) - 1)]
    return priority


def finalize(recs, per_archetype, limit: int = 4):
    """Keep the `limit` most important recommendations (by priority, ties keep rule
    order) and attach the archetype note to the first one."""
    from shared.archetype_notes import append_archetype_note
    order = {"high": 0, "medium": 1, "low": 2}
    recs = sorted(recs, key=lambda r: order.get(r.get("priority", "low"), 2))[:limit]
    return append_archetype_note(recs, per_archetype)
