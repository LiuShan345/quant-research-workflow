"""状态机：定义合法状态与允许的状态转换，由控制器在转换前核验。"""
from __future__ import annotations

STATES = [
    "INIT",
    "DATA_READY",
    "SIGNAL_READY",
    "BACKTEST_DONE",
    "ROBUST_DONE",
    "AWAITING_APPROVAL",
    "ACCEPTED",
    "REVISION",
    "BLOCKED",
    "STOPPED",
    "MONITORING",
]

# 合法的前向、修复、终止与监测转换
TRANSITIONS = {
    "INIT": ["DATA_READY", "BLOCKED", "STOPPED"],
    "DATA_READY": ["SIGNAL_READY", "REVISION", "BLOCKED", "STOPPED"],
    "SIGNAL_READY": ["BACKTEST_DONE", "REVISION", "BLOCKED", "STOPPED"],
    "BACKTEST_DONE": ["ROBUST_DONE", "REVISION", "BLOCKED", "STOPPED"],
    "ROBUST_DONE": ["AWAITING_APPROVAL", "REVISION", "BLOCKED", "STOPPED"],
    "AWAITING_APPROVAL": ["ACCEPTED", "REVISION", "STOPPED"],
    "REVISION": ["DATA_READY", "SIGNAL_READY", "BACKTEST_DONE", "ROBUST_DONE"],
    "ACCEPTED": ["MONITORING"],
    "MONITORING": ["INIT"],
    "BLOCKED": [],
    "STOPPED": [],
}


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, [])
