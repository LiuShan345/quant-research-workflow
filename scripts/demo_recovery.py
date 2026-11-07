"""中断恢复演示：先在 signal 阶段后模拟崩溃，再用新实例从断点恢复，证明不重复已完成阶段。

用法：python scripts/demo_recovery.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from controller import WorkflowController  # noqa: E402
from common import path, write_json  # noqa: E402


def main() -> None:
    demo_state = path(".state", "demos", "recovery_state.json")
    os.makedirs(os.path.dirname(demo_state), exist_ok=True)
    if os.path.exists(demo_state):
        os.remove(demo_state)

    # 第一次运行：在 signal 后模拟崩溃
    first = WorkflowController()
    first.state_file = demo_state
    first.start("case-recovery", "2025-12-31", crash_after="signal")
    crashed = first.load_state()
    after_crash = list(crashed["completed_stages"])

    # 模拟重启：全新控制器实例，仅读取存档后继续
    second = WorkflowController()
    second.state_file = demo_state
    final = second.run_all()
    resumed = second.load_state()

    evidence = {
        "崩溃后已完成阶段": after_crash,
        "恢复后全部阶段": resumed["completed_stages"],
        "最终状态": final,
        "已完成阶段未被重复执行": len(resumed["completed_stages"])
        == len(set(resumed["completed_stages"])),
    }
    write_json(path("evidence", "recovery_demo.json"), evidence)
    print("恢复演示完成:", final)


if __name__ == "__main__":
    main()
