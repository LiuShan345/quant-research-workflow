"""数据加载、带日期快照与质量检查。"""
from __future__ import annotations

import os

import pandas as pd

from common import ensure_dir, path, sha256_file


def load_prices() -> pd.DataFrame:
    df = pd.read_csv(path("tests", "fixtures", "synthetic_prices.csv"))
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)


def to_wide(prices: pd.DataFrame) -> pd.DataFrame:
    wide = prices.pivot(index="date", columns="ticker", values="close").sort_index()
    wide.index.name = "date"
    return wide


def quality_check(prices: pd.DataFrame, expected_n_stocks: int) -> dict:
    """确定性数据质量检查，返回各项布尔结果。"""
    dup = prices.duplicated(subset=["date", "ticker"]).sum()
    checks = {
        "no_duplicate_rows": int(dup) == 0,
        "all_prices_positive": bool((prices["close"] > 0).all()),
        "no_missing_values": bool(prices.notna().all().all()),
        "n_stocks_matches": prices["ticker"].nunique() == expected_n_stocks,
        "balanced_panel": bool(
            prices.groupby("ticker")["date"].nunique().nunique() == 1
        ),
    }
    checks["all_pass"] = all(checks.values())
    return checks


def save_snapshot(prices: pd.DataFrame, as_of: str) -> dict:
    """固化截至 as_of 的数据快照并计算哈希。"""
    cutoff = pd.Timestamp(as_of)
    snap = prices[prices["date"] <= cutoff].copy()
    out_dir = ensure_dir(path("data", "raw"))
    out_path = os.path.join(out_dir, f"snapshot_{as_of}.csv")
    snap.to_csv(out_path, index=False)
    return {
        "path": os.path.relpath(out_path, path()),
        "sha256": sha256_file(out_path),
        "as_of": as_of,
        "rows": len(snap),
    }
