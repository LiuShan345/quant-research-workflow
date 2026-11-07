"""回测：信号后交易、等权、按换手扣单边成本，输出净值、交易与指标。"""
from __future__ import annotations

import numpy as np
import pandas as pd


def run_backtest(
    wide: pd.DataFrame, signals: pd.DataFrame, one_way_cost_bps: float
):
    sel = signals[signals["selected"]].copy()
    rebalance_dates = sorted(sel["rebalance_date"].unique())
    prev_weights: dict[str, float] = {}
    period_rows, trade_rows = [], []

    for rd in rebalance_dates:
        block = sel[sel["rebalance_date"] == rd]
        t = pd.Timestamp(rd)
        nxt = pd.Timestamp(block["earliest_execution_time"].iloc[0])
        holdings = list(block["ticker"])
        weights = {s: 1.0 / len(holdings) for s in holdings}

        indiv_ret = wide.loc[nxt] / wide.loc[t] - 1.0
        gross = float(sum(weights[s] * indiv_ret[s] for s in weights))

        all_names = set(weights) | set(prev_weights)
        turnover = float(
            sum(abs(weights.get(s, 0.0) - prev_weights.get(s, 0.0)) for s in all_names)
        )
        cost = turnover * one_way_cost_bps / 10000.0
        net = gross - cost

        period_rows.append(
            {
                "rebalance_date": rd,
                "execution_date": nxt.strftime("%Y-%m-%d"),
                "gross_return": gross,
                "turnover": turnover,
                "cost": cost,
                "net_return": net,
                "holdings": ",".join(holdings),
            }
        )
        for s in all_names:
            delta = weights.get(s, 0.0) - prev_weights.get(s, 0.0)
            if abs(delta) > 1e-12:
                trade_rows.append(
                    {"rebalance_date": rd, "ticker": s, "delta_weight": delta}
                )
        prev_weights = weights

    perf = pd.DataFrame(period_rows)
    trades = pd.DataFrame(trade_rows)
    equity = (1.0 + perf["net_return"]).cumprod()
    n = len(perf)

    metrics = {
        "n_periods": int(n),
        "annualized_return": float(equity.iloc[-1] ** (12.0 / n) - 1.0),
        "sharpe_ratio": float(
            perf["net_return"].mean() / perf["net_return"].std(ddof=1) * np.sqrt(12.0)
        ),
        "max_drawdown": float((equity / equity.cummax() - 1.0).min()),
        "avg_turnover": float(perf["turnover"].mean()),
        "final_equity": float(equity.iloc[-1]),
    }
    return perf, trades, metrics, equity
