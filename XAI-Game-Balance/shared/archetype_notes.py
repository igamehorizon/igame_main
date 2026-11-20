"""
shared/archetype_notes.py
Shared helper for annotating rule-based recommendations with archetype-level
concentration signals, derived from the descriptive `per_archetype` breakdown
already computed in analysis/analyze.py (see run_pipeline -> per_level[...]["per_archetype"]).

Design intent
-------------
This module does NOT change any rule threshold or priority. Archetype
membership is unsupervised (K-Means, K=3, unstable across reruns and
unlabeled) and is deliberately kept out of the conditions that decide
*whether* a rule fires or *how severe* it is graded. What it CAN safely do
is annotate an already-fired recommendation's technical_reason with a
descriptive caveat when the underlying success/failure pattern is
concentrated within one behavioral cluster rather than spread evenly across
all of them. The decision logic stays auditable and threshold-based; the
archetype layer only enriches the explanation attached to that decision.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

MIN_SESSIONS_PER_ARCHETYPE = 2   # ignore clusters too small to be meaningful
CONCENTRATION_GAP = 0.3          # 30-point success-rate spread between best/worst cluster


def describe_archetype_concentration(
    per_archetype: Optional[List[Dict[str, Any]]],
) -> Optional[str]:
    """
    Returns a one-sentence caveat if success rate varies sharply across
    behavioral archetypes for this level, or None if there isn't enough
    evidence (too few archetypes represented, too few sessions per
    archetype, or a roughly even spread).
    """
    if not per_archetype:
        return None

    usable = [a for a in per_archetype if a.get("n_sessions", 0) >= MIN_SESSIONS_PER_ARCHETYPE]
    if len(usable) < 2:
        return None

    ranked = sorted(usable, key=lambda a: a["success_rate"])
    lowest, highest = ranked[0], ranked[-1]
    gap = highest["success_rate"] - lowest["success_rate"]

    if gap < CONCENTRATION_GAP:
        return None

    return (
        f"This pattern is not evenly distributed across player types: the behavioral "
        f"cluster with the lowest success rate (cluster {lowest['archetype_id']}, "
        f"{lowest['success_rate']:.0%} success, n={lowest['n_sessions']}) diverges "
        f"sharply from the cluster with the highest ({highest['success_rate']:.0%} success, "
        f"n={highest['n_sessions']}), suggesting the issue may affect a specific "
        f"behavioral profile more than others rather than all players uniformly."
    )


def append_archetype_note(
    recs: List[Dict[str, str]],
    per_archetype: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, str]]:
    """
    Appends the concentration caveat (if any) to the technical_reason of the
    first (highest-priority) fired recommendation. No-op if recs is empty or
    no concentration signal is found. Mutates and returns recs for convenience.
    """
    if not recs:
        return recs
    note = describe_archetype_concentration(per_archetype)
    if note:
        recs[0]["technical_reason"] = recs[0]["technical_reason"].rstrip() + " " + note
    return recs
