from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List
import numpy as np
import pandas as pd

def load_json_logs(input_path: str) -> pd.DataFrame:
    p = Path(input_path)
    rows: List[Dict] = []
    files: List[Path] = []
    if p.is_dir():
        files = [f for f in p.glob("**/*.jsonl")] + [f for f in p.glob("**/*.json")]
    else:
        files = [p]

    for f in files:
        with f.open("r", encoding="utf-8") as fh:
            content = fh.read()
            # First, try parsing as JSONL (one JSON object per line)
            lines = content.strip().split('\n')
            jsonl_success = True
            for line in lines:
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                    rows.append(obj)
                except json.JSONDecodeError:
                    jsonl_success = False
                    break

            # If JSONL parsing failed, try parsing as single JSON array/object
            if not jsonl_success:
                try:
                    obj = json.loads(content)
                    if isinstance(obj, list):
                        rows.extend(obj)
                    elif isinstance(obj, dict):
                        rows.append(obj)
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not parse {f} as JSON: {e}")
                except Exception as e:
                    print(f"Warning: Error processing {f}: {e}")
    if not rows:
        raise ValueError("No JSON rows loaded. Provide .jsonl/.json files.")

    df = pd.DataFrame(rows)
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def ensure_columns(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    return df

def generate_synthetic_logs(n_players: int = 40, n_levels: int = 10, n_sessions: int = 1500, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    player_skill = {f"P{i}": rng.normal(0, 1) for i in range(n_players)}
    level_diff   = {f"L{j}": rng.normal(0, 1) for j in range(n_levels)}
    rows = []
    for s in range(n_sessions):
        pid = f"P{int(rng.integers(0, n_players))}"
        lid = f"L{int(rng.integers(0, n_levels))}"
        sid = f"S{s}"
        base_dt = max(50, int(rng.normal(300, 80)))
        mismatch = level_diff[lid] - player_skill[pid]
        actions = int(max(1, rng.poisson(20 + 6 * max(0, mismatch))))

        backtrack_prob = 1 / (1 + np.exp(-(mismatch)))
        backtracks = int(rng.binomial(actions, min(0.8, 0.05 + 0.25 * backtrack_prob)))
        mean_dt = base_dt * (1 + 0.25 * max(0, mismatch))
        p_succ = 1 / (1 + np.exp(-(player_skill[pid] - level_diff[lid])))
        success = int(rng.random() < p_succ)
        completion_ms = int((actions * mean_dt) * (1.0 + 0.5 * (1 - success)))

        t0 = pd.Timestamp('2025-01-01') + pd.Timedelta(int(s*3), 's')
        rows.append({
            "timestamp": t0.isoformat(), "session_id": sid, "player_id": pid, "level_id": lid,
            "event_type": "level_start"
        })
        for a in range(actions):
            rows.append({
                "timestamp": (t0 + pd.Timedelta(int((a+1)*mean_dt), 'ms')).isoformat(),
                "session_id": sid, "player_id": pid, "level_id": lid, "event_type": "action",
                "decision_time_ms": int(rng.normal(mean_dt, 30)),
                "was_backtracked": int(a < backtracks)
            })
        rows.append({
            "timestamp": (t0 + pd.Timedelta(completion_ms, 'ms')).isoformat(),
            "session_id": sid, "player_id": pid, "level_id": lid, "event_type": "level_end",
            "success_flag": success, "completion_time_ms": completion_ms
        })
    return pd.DataFrame(rows)
