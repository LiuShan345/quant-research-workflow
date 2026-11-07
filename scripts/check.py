"""回归检查：独立重跑关键 gate、校验产物哈希，输出可审阅的回归结论。

用法：python scripts/check.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import data as data_mod  # noqa: E402
import gates  # noqa: E402
from common import load_config, path, sha256_file, write_json  # noqa: E402


def main() -> None:
    cfg = load_config()
    with open(path(".state", "state.json"), "r", encoding="utf-8") as f:
        state = json.load(f)

    # 1) 产物哈希校验：当前文件必须与状态中记录的哈希一致
    hash_ok = all(
        sha256_file(path(art["path"])) == art["sha256"]
        for art in state["artifacts"].values()
    )

    # 2) 重新独立执行 PIT 泄露测试
    prices = data_mod.load_prices()
    wide = data_mod.to_wide(prices)
    leak_ok, leak_ev = gates.pit_leakage_test(
        wide, cfg["strategy"]["lookback_months"], cfg["strategy"]["top_k"]
    )

    # 3) 数据质量与限额独立复核
    quality = data_mod.quality_check(prices, cfg["universe"]["n_stocks"])
    data_ok, _ = gates.data_gate(quality)

    result = {
        "artifact_hashes_valid": hash_ok,
        "data_gate_pass": data_ok,
        "pit_leakage_pass": leak_ok,
        "pit_detail": leak_ev,
        "open_issues": len(state["open_issues"]),
        "all_pass": bool(hash_ok and leak_ok and data_ok and len(state["open_issues"]) == 0),
    }
    write_json(path("evidence", "regression_check.json"), result)
    print("回归检查:", "PASS" if result["all_pass"] else "FAIL")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
