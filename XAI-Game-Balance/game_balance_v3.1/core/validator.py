"""
core/validator.py
Validates a list of raw event dicts against a family's required fields.

Generic optional fields (from shared/generic_fields.py) are merged into
optional_defaults automatically so every family accepts them without any
change to family configs.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from shared.generic_fields import GENERIC_OPTIONAL_DEFAULTS


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
    - Generic fields are merged silently — family configs need no changes.
    """
    # Merge generic defaults with family-specific defaults.
    # Family-specific values take precedence if there is a key collision.
    merged_defaults = {**GENERIC_OPTIONAL_DEFAULTS, **optional_defaults}

    clean: List[Dict[str, Any]] = []
    errors: List[str] = []

    for i, event in enumerate(events):
        # Required fields must be present
        missing = set(required_fields) - set(event.keys())
        if missing:
            errors.append(f"Event {i}: missing required fields {sorted(missing)}")
            continue

        # Required fields must be non-null
        null_required = [f for f in required_fields if event[f] is None]
        if null_required:
            errors.append(
                f"Event {i}: required fields must not be null: {sorted(null_required)}"
            )
            continue

        clean.append(event)

    return clean, errors
