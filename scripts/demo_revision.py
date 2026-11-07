"""有界修订循环演示：注入问题项 -> 进入 REVISION -> 修复并重跑 -> Critic 核验后关闭。

用法：python scripts/demo_revision.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from controller import WorkflowController  # noqa: E402
from common import path, write_json  # noqa: E402


def main() -> None:
    demo_state = path(".state", "demos", "revision_state.json")
    os.makedirs(os.path.dirname(demo_state), exist_ok=True)
    if os.path.exists(demo_state):
        os.remove(demo_state)

    c = WorkflowController()
    c.state_file = demo_state
    c.start("case-revision", "2025-12-31", crash_after="data")  # 停在 DATA_READY
    c.load_state()

    # 注入一个问题项并退回修订
    c._add_issue("demo-issue-001", "factor-agent", "演示：信号时序证据缺失")
    c._transition("REVISION")  # DATA_READY -> REVISION

    # 修复：重新生成信号与完整 PIT 证据（REVISION -> SIGNAL_READY）
    c.stage_signal()

    # 模拟独立 Critic 核验通过后关闭问题项
    for issue in c.state["open_issues"]:
        if issue["issue_id"] == "demo-issue-001":
            issue["status"] = "resolved"
            issue["evidence"] = "evidence/pit_leakage.json"
    if "signal" not in c.state["completed_stages"]:
        c.state["completed_stages"].append("signal")
    c.save_state()

    ledger = c.state["open_issues"]
    write_json(
        path("evidence", "revision_demo.json"),
        {
            "问题项台账": ledger,
            "修复边": "REVISION -> SIGNAL_READY",
            "问题项由独立核验关闭": all(i["status"] == "resolved" for i in ledger),
        },
    )
    print("修订演示完成，问题项已关闭")


if __name__ == "__main__":
    main()
