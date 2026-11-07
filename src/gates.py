"""可执行检查关卡：由控制器运行，不依赖模型自述。每个关卡返回 (是否通过, 证据)。"""
from __future__ import annotations

import numpy as np
import pandas as pd


def data_gate(quality: dict):
    evidence = {k: bool(v) for k, v in quality.items()}
    return bool(quality.get("all_pass")), evidence


def pit_gate(signals: pd.DataFrame):
    """执行时间必须严格晚于信号时间。"""
    ok = bool(
        (
            pd.to_datetime(signals["earliest_execution_time"])
            > pd.to_datetime(signals["signal_time"])
        ).all()
    )
    return ok, {"execution_after_signal": ok, "rows_checked": int(len(signals))}


def pit_leakage_test(wide: pd.DataFrame, lookback: int, top_k: int, seed: int = 7):
    """扰动 t 之后的价格，t 时点选出的股票必须不变，证明无未来信息泄露。"""
    rng = np.random.default_rng(seed)
    dates = list(wide.index)
    idx = lookback + 2  # 选一个有完整回看的调仓日
    t, past = dates[idx], dates[idx - lookback]

    def top_names(frame: pd.DataFrame):
        mom = frame.loc[t] / frame.loc[past] - 1.0
        return list(mom.sort_values(ascending=False).head(top_k).index)

    base_picks = top_names(wide)
    disturbed = wide.copy()
    later = disturbed.index > t
    factor = 1.0 + rng.normal(0.0, 0.2, size=(int(later.sum()), wide.shape[1]))
    disturbed.loc[later] = disturbed.loc[later].values * factor
    disturbed_picks = top_names(disturbed)

    unchanged = base_picks == disturbed_picks
    return bool(unchanged), {
        "rebalance_date": t.strftime("%Y-%m-%d"),
        "base_picks": base_picks,
        "disturbed_picks": disturbed_picks,
        "signal_unchanged_after_future_shock": unchanged,
    }


def numerical_gate(wide: pd.DataFrame, signals: pd.DataFrame, perf: pd.DataFrame, cost_bps: float):
    """独立复算第一个调仓期的净收益，与回测表比对。"""
    sel = signals[signals["selected"]]
    first_date = sorted(sel["rebalance_date"].unique())[0]
    block = sel[sel["rebalance_date"] == first_date]
    t = pd.Timestamp(first_date)
    nxt = pd.Timestamp(block["earliest_execution_time"].iloc[0])
    holdings = list(block["ticker"])
    gross = float((wide.loc[nxt] / wide.loc[t] - 1.0)[holdings].mean())
    turnover = 1.0  # 首期从空仓建仓
    expected_net = gross - turnover * cost_bps / 10000.0
    actual_net = float(perf.iloc[0]["net_return"])
    ok = abs(expected_net - actual_net) < 1e-12
    return ok, {
        "recomputed_net": expected_net,
        "reported_net": actual_net,
        "abs_diff": abs(expected_net - actual_net),
    }


def cost_gate(perf: pd.DataFrame):
    """有换手就应有成本，且 net = gross - cost。"""
    cost_positive = bool((perf.loc[perf["turnover"] > 0, "cost"] > 0).all())
    identity = bool(
        np.allclose(perf["net_return"], perf["gross_return"] - perf["cost"], atol=1e-12)
    )
    return cost_positive and identity, {
        "cost_charged_on_turnover": cost_positive,
        "net_equals_gross_minus_cost": identity,
    }


def limit_gate(signals: pd.DataFrame, top_k: int):
    """每个调仓日入选数量必须等于 top_k。"""
    counts = signals[signals["selected"]].groupby("rebalance_date").size()
    ok = bool((counts == top_k).all())
    return ok, {"min": int(counts.min()), "max": int(counts.max()), "expected": top_k}
