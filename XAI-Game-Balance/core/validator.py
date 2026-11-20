"""
core/validator.py
Validates a list of raw event dicts against a family's required fields,
and checks values for type, range and consistency.

Generic optional fields (from shared/generic_fields.py) are merged into
optional_defaults automatically so every family accepts them without any
change to family configs.

Value checks:
- numeric fields must be numbers (text such as "abc" is rejected)
- flags (success_flag, timeout_flag, was_backtracked) must be 0 or 1
- counts and times must not be negative; 0-1 scores must stay within 0-1
- contradictions are rejected (success together with a timeout or a fail event)
- dataset_warnings(): dataset-level warnings that do not skip events
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from shared.generic_fields import GENERIC_OPTIONAL_DEFAULTS

# Fields that must hold numbers when present and non-null (all families).
NUMERIC_FIELDS = {
    "decision_time_ms", "completion_time_ms", "success_flag",
    "was_backtracked", "moves", "timeout_flag", "nodes_expanded",
    "interaction_count", "wrong_interaction_count", "hint_count",
    "damage_taken", "deaths", "resource_loss", "healing_usage",
    "error_count", "assistance_used", "idle_time_ms",
    "input_precision_score", "undo_count",
    "objective_progress", "system_state_score", "positive_action_count",
    "negative_action_count", "influence_score", "custom_game_score",
}
# Must be exactly 0 or 1.
FLAG_FIELDS = {"success_flag", "timeout_flag", "was_backtracked"}
# Must not be negative.
NON_NEGATIVE_FIELDS = {
    "decision_time_ms", "completion_time_ms", "moves", "nodes_expanded",
    "interaction_count", "wrong_interaction_count", "hint_count",
    "damage_taken", "deaths", "resource_loss", "healing_usage",
    "error_count", "idle_time_ms", "undo_count",
    "positive_action_count", "negative_action_count",
}
# Must be within 0..1 (as documented in shared/generic_fields.py).
UNIT_INTERVAL_FIELDS = {"objective_progress", "system_state_score", "influence_score"}
# Measurement fields that are suspicious if 0 in every single event.
CONSTANT_ZERO_CHECK_FIELDS = {
    "decision_time_ms", "completion_time_ms", "nodes_expanded", "moves",
    "idle_time_ms", "interaction_count",
}
FAIL_EVENT_TYPES = {"level_fail", "fail", "failure"}


def _is_number(v: Any) -> bool:
    # bool is accepted on purpose: JSON true/false are valid flags
    return isinstance(v, (int, float)) and v == v  # v == v excludes NaN


def _value_problems(event: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    for field, value in event.items():
        if field not in NUMERIC_FIELDS or value is None:
            continue
        if not _is_number(value):
            problems.append(f"'{field}' must be a number (got {value!r})")
            continue
        if field in FLAG_FIELDS and value not in (0, 1):
            problems.append(f"'{field}' must be 0 or 1 (got {value!r})")
        if field in NON_NEGATIVE_FIELDS and value < 0:
            problems.append(f"'{field}' must not be negative (got {value!r})")
        if field in UNIT_INTERVAL_FIELDS and not 0 <= value <= 1:
            problems.append(f"'{field}' must be between 0 and 1 (got {value!r})")
    if problems:
        return problems
    success = event.get("success_flag")
    if success == 1 and event.get("timeout_flag") == 1:
        problems.append("success_flag=1 and timeout_flag=1 in the same event (contradiction)")
    if success == 1 and str(event.get("event_type", "")).lower() in FAIL_EVENT_TYPES:
        problems.append(f"success_flag=1 on a '{event.get('event_type')}' event (contradiction)")
    return problems


def validate_events(
    events: List[Dict[str, Any]],
    required_fields: list,
    optional_defaults: dict,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Returns (clean_events, error_messages).
    Invalid rows are skipped; errors are collected and returned.

    Rules:
    - Required fields must be present and non-null.
    - Optional fields (family-specific + generic) may be absent or null —
      both are preserved as-is and treated as NaN by extractors.
    - Present values must have the right type, range and be consistent.
    - Generic fields are merged silently — family configs need no changes.
    """
    merged_defaults = {**GENERIC_OPTIONAL_DEFAULTS, **optional_defaults}  # noqa: F841 (kept for compatibility)

    clean: List[Dict[str, Any]] = []
    errors: List[str] = []

    for i, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"Event {i}: must be a JSON object")
            continue

        missing = set(required_fields) - set(event.keys())
        if missing:
            errors.append(f"Event {i}: missing required fields {sorted(missing)}")
            continue

        null_required = [f for f in required_fields if event[f] is None]
        if null_required:
            errors.append(
                f"Event {i}: required fields must not be null: {sorted(null_required)}"
            )
            continue

        problems = _value_problems(event)
        if problems:
            errors.append(f"Event {i}: " + "; ".join(problems))
            continue

        clean.append(event)

    return clean, errors


def dataset_warnings(gameplay_instance: Any, events: List[Dict[str, Any]]) -> List[str]:
    """
    Dataset-level checks that do not skip events. Returns warning strings in the
    'CODE|message' format used by the API.
    """
    warnings: List[str] = []

    if not isinstance(gameplay_instance, dict) or not gameplay_instance:
        warnings.append(
            "MISSING_GAMEPLAY_INSTANCE|The upload has no 'gameplay_instance' block, so the "
            "gameplay type could not be read from the file and the default type was used. "
            "Add a gameplay_instance block with 'telemetry_family' to analyse with the right rules."
        )
    elif not gameplay_instance.get("telemetry_family"):
        warnings.append(
            "MISSING_GAMEPLAY_INSTANCE|'gameplay_instance' has no 'telemetry_family'; "
            "the default gameplay type was used."
        )

    end_types = {"level_end", "level_fail", "level_complete", "fail", "failure"}
    for field in sorted(CONSTANT_ZERO_CHECK_FIELDS):
        pool = events
        if field == "completion_time_ms":
            # completion time is only meaningful on end/fail events
            pool = [e for e in events if str(e.get("event_type", "")).lower() in end_types]
        values = [e.get(field) for e in pool if e.get(field) is not None]
        if values and all(v == 0 for v in values):
            warnings.append(
                f"CONSTANT_ZERO_FIELD|'{field}' is 0 in every event. If this value was not "
                f"recorded, send null (or omit the field) instead of 0; 0 is treated as a real "
                f"measurement and can lead to misleading recommendations."
            )

    players_per_session: Dict[Any, set] = {}
    for e in events:
        players_per_session.setdefault(e.get("session_id"), set()).add(e.get("player_id"))
    dup = sorted(str(s) for s, p in players_per_session.items() if len(p) > 1)
    if dup:
        warnings.append(
            f"DUPLICATE_SESSION_ID|These session_id values are used by more than one player: "
            f"{dup[:5]}. Each play session should have its own session_id; results for these "
            f"sessions may be merged incorrectly."
        )

    return warnings
