"""
core/registry.py
Family plugin registry — v2.5
Registered families: pathfinding, puzzle_interaction, strategy_combat, game_jam_generic

Generic gameplay variable feature columns are appended to every family's
FEATURE_COLS at registration time so the ML pipeline picks them up automatically.
"""
from __future__ import annotations

from typing import Any, Callable, Dict

from shared.generic_fields import GENERIC_FEATURE_COLS

_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_family(
    name: str,
    required_fields: list,
    optional_defaults: dict,
    feature_cols: list,
    extract_fn: Callable,
    rules_fn: Callable,
) -> None:
    # Append generic feature cols — avoid duplicates in case of re-registration
    merged_feature_cols = list(feature_cols) + [
        c for c in GENERIC_FEATURE_COLS if c not in feature_cols
    ]
    _REGISTRY[name] = {
        "required_fields": required_fields,
        "optional_defaults": optional_defaults,
        "feature_cols": merged_feature_cols,
        "extract": extract_fn,
        "rules": rules_fn,
    }


def get_family(name: str) -> Dict[str, Any]:
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown telemetry family '{name}'. "
            f"Available: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[name]


def list_families() -> list:
    return list(_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Auto-register all families at import time
# ---------------------------------------------------------------------------
from families.pathfinding.config import REQUIRED_FIELDS as PF_REQ, OPTIONAL_DEFAULTS as PF_OPT, FEATURE_COLS as PF_FEAT  # noqa: E402
from families.pathfinding.extractor import aggregate_sessions as pf_extract  # noqa: E402
from families.pathfinding.rules import generate_recommendations as pf_rules  # noqa: E402

from families.puzzle_interaction.config import REQUIRED_FIELDS as PI_REQ, OPTIONAL_DEFAULTS as PI_OPT, FEATURE_COLS as PI_FEAT  # noqa: E402
from families.puzzle_interaction.extractor import aggregate_sessions as pi_extract  # noqa: E402
from families.puzzle_interaction.rules import generate_recommendations as pi_rules  # noqa: E402

from families.strategy_combat.config import REQUIRED_FIELDS as SC_REQ, OPTIONAL_DEFAULTS as SC_OPT, FEATURE_COLS as SC_FEAT  # noqa: E402
from families.strategy_combat.extractor import aggregate_sessions as sc_extract  # noqa: E402
from families.strategy_combat.rules import generate_recommendations as sc_rules  # noqa: E402

from families.game_jam_generic.config import REQUIRED_FIELDS as GJ_REQ, OPTIONAL_DEFAULTS as GJ_OPT, FEATURE_COLS as GJ_FEAT  # noqa: E402
from families.game_jam_generic.extractor import aggregate_sessions as gj_extract  # noqa: E402
from families.game_jam_generic.rules import generate_recommendations as gj_rules  # noqa: E402

from families.accessibility_precision.config import REQUIRED_FIELDS as AP_REQ, OPTIONAL_DEFAULTS as AP_OPT, FEATURE_COLS as AP_FEAT  # noqa: E402
from families.accessibility_precision.extractor import aggregate_sessions as ap_extract  # noqa: E402
from families.accessibility_precision.rules import generate_recommendations as ap_rules  # noqa: E402

register_family(
    name="pathfinding",
    required_fields=PF_REQ,
    optional_defaults=PF_OPT,
    feature_cols=PF_FEAT,
    extract_fn=pf_extract,
    rules_fn=pf_rules,
)

# Alias for backwards compatibility
register_family(
    name="pathfinding_basic",
    required_fields=PF_REQ,
    optional_defaults=PF_OPT,
    feature_cols=PF_FEAT,
    extract_fn=pf_extract,
    rules_fn=pf_rules,
)

register_family(
    name="puzzle_interaction",
    required_fields=PI_REQ,
    optional_defaults=PI_OPT,
    feature_cols=PI_FEAT,
    extract_fn=pi_extract,
    rules_fn=pi_rules,
)

register_family(
    name="strategy_combat",
    required_fields=SC_REQ,
    optional_defaults=SC_OPT,
    feature_cols=SC_FEAT,
    extract_fn=sc_extract,
    rules_fn=sc_rules,
)

register_family(
    name="game_jam_generic",
    required_fields=GJ_REQ,
    optional_defaults=GJ_OPT,
    feature_cols=GJ_FEAT,
    extract_fn=gj_extract,
    rules_fn=gj_rules,
)

register_family(
    name="accessibility_precision",
    required_fields=AP_REQ,
    optional_defaults=AP_OPT,
    feature_cols=AP_FEAT,
    extract_fn=ap_extract,
    rules_fn=ap_rules,
)
