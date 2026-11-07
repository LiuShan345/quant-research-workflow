"""端到端入口：运行一个完整研究案例。

用法：python run.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

from controller import WorkflowController  # noqa: E402


def main() -> None:
    controller = WorkflowController()
    final = controller.start(case_id="case-001", as_of="2025-12-31")
    print("最终状态:", final)
    print("回测指标:", controller.metrics)


if __name__ == "__main__":
    main()
