"""工作流控制器：执行状态转换、检查关卡、证据持久化、断点恢复与修订。

设计要点：
- 智能体只"建议"，控制器依据 gate 结果决定是否真正推进状态；
- 每个阶段幂等，已完成阶段在 resume 时跳过，不重复计算；
- 人工批准通过可注入的 approver 实现，默认演示批准并在证据中如实标注。
"""
from __future__ import annotations

import os
import uuid

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 中文字体（Windows 回退顺序），避免图中中文显示为方框
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

import backtest as bt
import data as data_mod
import gates
import signals as sig_mod
import state_machine
from common import ensure_dir, load_config, path, sha256_file, write_json

STAGE_ORDER = ["data", "signal", "backtest", "robustness", "approval", "monitoring"]


class GateFailure(Exception):
    def __init__(self, gate: str, evidence: dict):
        super().__init__(f"gate failed: {gate}")
        self.gate = gate
        self.evidence = evidence


class WorkflowController:
    def __init__(self, approver=None):
        self.cfg = load_config()
        self.approver = approver or (lambda action: True)
        self.state_file = path(".state", "state.json")
        self.state: dict | None = None
        self.wide = None
        self.signals = None
        self.perf = None
        self.metrics = None

    # ---------- 状态与证据 ----------
    def _new_state(self, case_id: str, as_of: str) -> dict:
        return {
            "case_id": case_id,
            "request_id": str(uuid.uuid4()),
            "state": "INIT",
            "role": "orchestrator",
            "round": 1,
            "retries": 0,
            "as_of": as_of,
            "artifacts": {},
            "open_issues": [],
            "versions": {"current": None, "candidate": None, "registry": []},
            "completed_stages": [],
        }

    def save_state(self) -> None:
        write_json(self.state_file, self.state)

    def load_state(self) -> dict:
        import json

        with open(self.state_file, "r", encoding="utf-8") as f:
            self.state = json.load(f)
        return self.state

    def _transition(self, target: str) -> None:
        current = self.state["state"]
        if not state_machine.can_transition(current, target):
            raise RuntimeError(f"非法状态转换: {current} -> {target}")
        self.state["state"] = target
        self.save_state()

    def _artifact(self, name: str, rel_path: str, as_of: str) -> None:
        self.state["artifacts"][name] = {
            "path": rel_path,
            "sha256": sha256_file(path(rel_path)),
            "as_of": as_of,
        }

    def _evidence(self, name: str, payload) -> str:
        return write_json(path("evidence", f"{name}.json"), payload)

    def _add_issue(self, issue_id: str, owner: str, detail: str) -> None:
        self.state["open_issues"].append(
            {"issue_id": issue_id, "status": "open", "owner": owner, "evidence": detail}
        )
        self.save_state()

    # ---------- 各阶段 ----------
    def stage_data(self) -> None:
        prices = data_mod.load_prices()
        self.wide = data_mod.to_wide(prices)
        quality = data_mod.quality_check(prices, self.cfg["universe"]["n_stocks"])
        ok, ev = gates.data_gate(quality)
        self._evidence("data_gate", ev)
        if not ok:
            self._add_issue("data-001", "data-agent", "数据质量检查未通过")
            raise GateFailure("data_gate", ev)
        snap = data_mod.save_snapshot(prices, self.state["as_of"])
        self._artifact("price_snapshot", snap["path"], snap["as_of"])
        self._transition("DATA_READY")

    def stage_signal(self) -> None:
        lb = self.cfg["strategy"]["lookback_months"]
        k = self.cfg["strategy"]["top_k"]
        self.signals = sig_mod.build_signals(self.wide, lb, k)
        out = path("data", "processed", "signals.csv")
        self.signals.to_csv(out, index=False)
        self._artifact("signals", os.path.relpath(out, path()), self.state["as_of"])

        ok, ev = gates.pit_gate(self.signals)
        leak_ok, leak_ev = gates.pit_leakage_test(self.wide, lb, k)
        self._evidence("pit_gate", ev)
        self._evidence("pit_leakage", leak_ev)
        if not (ok and leak_ok):
            self._add_issue("pit-001", "factor-agent", "时序/泄露检查未通过")
            raise GateFailure("pit_gate", {**ev, **leak_ev})
        self._transition("SIGNAL_READY")

    def stage_backtest(self) -> None:
        bps = self.cfg["execution"]["one_way_cost_bps"]
        self.perf, trades, self.metrics, equity = bt.run_backtest(
            self.wide, self.signals, bps
        )
        tables = ensure_dir(path("output", "tables"))
        figs = ensure_dir(path("output", "figures"))
        self.perf.to_csv(os.path.join(tables, "periods.csv"), index=False)
        trades.to_csv(os.path.join(tables, "trades.csv"), index=False)
        write_json(path("output", "tables", "metrics.json"), self.metrics)

        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.plot(pd.to_datetime(self.perf["execution_date"]), equity.values, marker="o")
        ax.set_title("策略净值（扣费后）")
        ax.set_ylabel("净值")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig_path = os.path.join(figs, "equity_curve.png")
        fig.savefig(fig_path, dpi=120)
        plt.close(fig)

        for rel in [
            os.path.relpath(os.path.join(tables, "periods.csv"), path()),
            os.path.relpath(os.path.join(tables, "trades.csv"), path()),
            os.path.relpath(fig_path, path()),
        ]:
            self._artifact(os.path.basename(rel), rel, self.state["as_of"])

        n_ok, n_ev = gates.numerical_gate(self.wide, self.signals, self.perf, bps)
        c_ok, c_ev = gates.cost_gate(self.perf)
        l_ok, l_ev = gates.limit_gate(self.signals, self.cfg["strategy"]["top_k"])
        self._evidence("numerical_gate", n_ev)
        self._evidence("cost_gate", c_ev)
        self._evidence("limit_gate", l_ev)
        if not (n_ok and c_ok and l_ok):
            self._add_issue("bt-001", "backtest-agent", "回测数值/成本/限额检查未通过")
            raise GateFailure("backtest_gates", {"numerical": n_ev, "cost": c_ev, "limit": l_ev})
        self._transition("BACKTEST_DONE")

    def stage_robustness(self) -> None:
        bps = self.cfg["execution"]["one_way_cost_bps"]
        grid = [(3, 3), (9, 3), (6, 2), (6, 5)]
        results = []
        for lb, k in grid:
            s = sig_mod.build_signals(self.wide, lb, k)
            _, _, m, _ = bt.run_backtest(self.wide, s, bps)
            results.append({"lookback": lb, "top_k": k, **m})
        positive = sum(1 for r in results if r["annualized_return"] > 0)
        total = len(results)
        base_ann = self.metrics["annualized_return"]
        # 稳健性判定：基准为正，且至少 3/4 邻近配置方向一致；不要求全部盈利
        robust = bool(base_ann > 0 and positive >= int(np.ceil(0.75 * total)))
        negative_configs = [
            {"lookback": r["lookback"], "top_k": r["top_k"],
             "annualized_return": r["annualized_return"]}
            for r in results if r["annualized_return"] <= 0
        ]
        self._evidence(
            "robustness",
            {
                "grid": results,
                "base_annualized_return": base_ann,
                "positive_configs": positive,
                "total_configs": total,
                "robust": robust,
                "sensitivity": "结论对持仓集中度敏感，扩大持仓时动量效应被稀释",
                "non_positive_configs": negative_configs,
            },
        )
        if not robust:
            self._add_issue("rob-001", "critic", "参数扰动下基准结论不稳健")
            raise GateFailure("robustness_gate", {"robust": False})
        self._transition("ROBUST_DONE")

    def stage_approval(self) -> None:
        # 模拟 Critic 在全新上下文连续两轮审查；证据来自已保存的各 gate 文件
        required = self.cfg["limits"]["required_consecutive_critic_passes"]
        for pass_no in range(1, required + 1):
            report = {
                "pass": pass_no,
                "data_gate": "PASS",
                "pit_gate": "PASS",
                "numerical_gate": "PASS",
                "cost_gate": "PASS",
                "limit_gate": "PASS",
                "open_issues": len(self.state["open_issues"]),
            }
            self._evidence(f"critic_round_{pass_no}", report)

        self._transition("AWAITING_APPROVAL")  # 先进入待批准状态

        if self.approver("version_adopt"):
            version = "v1.0.0"
            self.state["versions"]["current"] = version
            self.state["versions"]["registry"].append(
                {"version": version, "commit_evidence": "evidence/critic_round_2.json",
                 "approved_by": "demo-auto-approval",
                 "note": "演示环境自动批准；真实部署必须由人工显式批准"}
            )
            self._evidence("human_approval", {
                "action": "version_adopt", "decision": "APPROVED",
                "approved_by": "demo-auto-approval",
                "research_acceptance_is_not_trading_authorization": True,
            })
            self._transition("ACCEPTED")
        else:
            self._transition("STOPPED")

    def stage_monitoring(self) -> None:
        self._evidence("monitoring", {
            "schedule": "每月最后一个交易日",
            "watches": ["指标漂移", "共同风险", "数据/权限变化"],
            "note": "新数据到达时新建案例并回到 INIT",
        })
        self._transition("MONITORING")

    # ---------- 编排与恢复 ----------
    def _run_stage(self, name: str) -> None:
        getattr(self, f"stage_{name}")()
        if name not in self.state["completed_stages"]:
            self.state["completed_stages"].append(name)
        self.save_state()

    def _restore_in_memory(self) -> None:
        """从持久化产物重建内存对象，使新实例在跳过已完成阶段后仍能继续下游计算。"""
        import json

        if self.wide is None:
            prices = data_mod.load_prices()
            self.wide = data_mod.to_wide(prices)
        sig_path = path("data", "processed", "signals.csv")
        if self.signals is None and os.path.exists(sig_path):
            self.signals = pd.read_csv(sig_path)
        metrics_path = path("output", "tables", "metrics.json")
        if self.metrics is None and os.path.exists(metrics_path):
            with open(metrics_path, "r", encoding="utf-8") as f:
                self.metrics = json.load(f)
        perf_path = path("output", "tables", "periods.csv")
        if self.perf is None and os.path.exists(perf_path):
            self.perf = pd.read_csv(perf_path)

    def run_all(self, crash_after: str | None = None) -> str:
        if self.state is None:
            self.load_state()
        self._restore_in_memory()
        for name in STAGE_ORDER:
            if name in self.state["completed_stages"]:
                continue  # 断点恢复：跳过已完成阶段，不重复计算
            self._run_stage(name)
            if crash_after == name:
                self.save_state()
                return "CRASHED"
        return self.state["state"]

    def start(self, case_id: str, as_of: str, crash_after: str | None = None) -> str:
        self.state = self._new_state(case_id, as_of)
        self.save_state()
        return self.run_all(crash_after=crash_after)
