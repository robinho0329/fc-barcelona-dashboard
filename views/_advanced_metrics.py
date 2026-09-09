"""Pure aggregation helpers for the advanced player view."""

import numpy as np
import pandas as pd


def rate_label(metric: str) -> str:
    """Label rate metrics without misrepresenting percentages as per-game."""
    return metric if metric.endswith("성공률") else f"경기당 {metric}"


def per_appearance(
    df: pd.DataFrame, metrics: dict[str, str], min_appearances: int
) -> pd.DataFrame:
    """Return player event totals normalized by matches with recorded events."""
    g = df.groupby("player").agg(
        경기=("match_id", "nunique"),
        시즌=("season", "nunique"),
        **{label: (column, "sum") for label, column in metrics.items()},
        패스성공=("passes_completed", "sum"),
    )
    g = g[g["경기"] >= min_appearances]
    out = g[["경기", "시즌"]].copy()
    for label in metrics:
        out[label] = (g[label] / g["경기"]).round(2)
    out["패스 성공률"] = (
        g["패스성공"] / g["패스"].replace(0, np.nan) * 100
    ).round(1)
    return out.sort_values("경기", ascending=False)
