"""PIT 动量信号构建：只用截至调仓日的数据，并记录信号可用与最早执行时间。"""
from __future__ import annotations

import pandas as pd


def build_signals(wide: pd.DataFrame, lookback: int, top_k: int) -> pd.DataFrame:
    """返回每个调仓日全部股票的动量排名，以及是否入选。

    时序约定：信号在 t 日收盘后形成（signal_time=t），
    最早在下一个月末执行（earliest_execution_time=t+1），天然满足 T+1。
    """
    dates = list(wide.index)
    rows = []
    # 需要足够回看历史，且后面要有一个可执行的持有期
    for idx in range(lookback, len(dates) - 1):
        t = dates[idx]
        past = dates[idx - lookback]
        momentum = wide.loc[t] / wide.loc[past] - 1.0
        ranked = momentum.sort_values(ascending=False)
        selected = set(ranked.head(top_k).index)
        exec_time = dates[idx + 1]
        for rank, (ticker, value) in enumerate(ranked.items(), start=1):
            rows.append(
                {
                    "rebalance_date": t.strftime("%Y-%m-%d"),
                    "ticker": ticker,
                    "momentum": round(float(value), 6),
                    "rank": int(rank),
                    "selected": bool(ticker in selected),
                    "signal_time": t.strftime("%Y-%m-%d"),
                    "earliest_execution_time": exec_time.strftime("%Y-%m-%d"),
                }
            )
    return pd.DataFrame(rows)


def selected_table(signals: pd.DataFrame) -> pd.DataFrame:
    return signals[signals["selected"]].reset_index(drop=True)
