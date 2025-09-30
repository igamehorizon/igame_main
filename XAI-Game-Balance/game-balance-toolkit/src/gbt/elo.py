from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Tuple

def compute_elo(df_sessions: pd.DataFrame, k: float = 16.0, iters: int = 1) -> Tuple[pd.Series, pd.Series]:
    players = df_sessions["player_id"].astype(str).unique()
    levels = df_sessions["level_id"].astype(str).unique()
    p_rating = {p: 1500.0 for p in players}
    l_rating = {l: 1500.0 for l in levels}

    def expected(r_a, r_b):
        return 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400))

    rng = np.random.default_rng(0)
    idx = np.arange(len(df_sessions))
    for _ in range(iters):
        rng.shuffle(idx)
        for i in idx:
            row = df_sessions.iloc[int(i)]
            p = str(row["player_id"])
            l = str(row["level_id"])
            y = float(row.get("success_flag", np.nan))
            if not np.isfinite(y):
                continue
            pe = expected(p_rating[p], l_rating[l])
            le = 1.0 - pe
            p_rating[p] += k * (y - pe)
            l_rating[l] += k * ((1.0 - y) - le)

    return pd.Series(p_rating), pd.Series(l_rating)
