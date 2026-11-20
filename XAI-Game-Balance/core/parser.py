"""
core/parser.py
Normalize uploaded JSON or JSONL bytes into (gameplay_instance_dict, events_list).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple


def parse_upload(raw: bytes) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Accept either:
      - JSON:  {"gameplay_instance": {...}, "events": [...]}
      - JSONL: one event per line (gameplay_instance injected as empty)

    Returns (gameplay_instance_dict, events_list).
    Raises ValueError with a human-readable message on failure.
    """
    text = raw.decode("utf-8").strip()

    # --- Try JSON first ---
    if text.startswith("{") or text.startswith("["):
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and "events" in obj:
                gi = obj.get("gameplay_instance", {})
                events = obj["events"]
                if not isinstance(events, list):
                    raise ValueError("'events' must be a JSON array.")
                return gi, events
            if isinstance(obj, list):
                return {}, obj
        except json.JSONDecodeError:
            pass  # fall through to JSONL

    # --- Try JSONL ---
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("Uploaded file is empty.")

    events: List[Dict[str, Any]] = []
    parse_errors: List[str] = []
    for i, line in enumerate(lines, start=1):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            parse_errors.append(f"Line {i}: {exc}")

    if parse_errors:
        sample = parse_errors[:5]
        suffix = f" … and {len(parse_errors)-5} more" if len(parse_errors) > 5 else ""
        raise ValueError("JSONL parse errors:\n" + "\n".join(sample) + suffix)

    if not events:
        raise ValueError("No events found in uploaded file.")

    return {}, events
