"""生成可复现的合成月末价格数据（虚构股票，不含任何真实/客户信息）。

输出：tests/fixtures/synthetic_prices.csv
列：date, ticker, close
设计：固定随机种子，每只股票有不同的漂移与波动，使截面动量存在可检验差异。
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

SEED = 42
N_STOCKS = 10
START = "2023-01-31"
END = "2025-12-31"
INIT_PRICE = 100.0


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    dates = pd.date_range(START, END, freq="ME")  # 每月最后一天
    n_months = len(dates)

    # 每只股票的年化漂移（有正有负）与月度波动
    annual_drifts = rng.normal(loc=0.08, scale=0.10, size=N_STOCKS)
    monthly_vol = rng.uniform(0.04, 0.09, size=N_STOCKS)

    rows = []
    for i in range(N_STOCKS):
        ticker = f"SYN{i + 1:02d}"
        # 给部分股票加入一段持续性的趋势，便于产生动量结构
        trend = np.zeros(n_months)
        trend[6:18] += annual_drifts[i] * 0.6
        monthly_ret = (
            annual_drifts[i] / 12.0
            + trend / 12.0
            + monthly_vol[i] * rng.standard_normal(n_months)
        )
        prices = INIT_PRICE * np.cumprod(1.0 + monthly_ret)
        for d, px in zip(dates, prices):
            rows.append({"date": d.strftime("%Y-%m-%d"), "ticker": ticker, "close": round(px, 4)})

    return pd.DataFrame(rows)


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    out_path = os.path.join(root, "tests", "fixtures", "synthetic_prices.csv")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df = generate()
    df.to_csv(out_path, index=False)
    print(f"saved {out_path}: {df['ticker'].nunique()} stocks, {df['date'].nunique()} dates, {len(df)} rows")


if __name__ == "__main__":
    main()
