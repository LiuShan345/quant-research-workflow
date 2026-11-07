# 期末项目：A 股月度截面动量策略的长程智能体工作流

- **课程**：金融人工智能编程（2026 年秋季，复旦大学国际金融学院）
- **姓名**：Liushan
- **学号**：25260660012
- **项目类型**：个人独立完成

## 一、项目概述

本项目为一项**内容充实、会重复执行的买方量化研究任务**——A 股月度截面动量策略的研究与持续监测——设计并实现了一个端到端的长程智能体工作流。

工作流串联 6 个阶段（数据 → 信号 → 回测 → 稳健性 → 批准 → 监测），**保留持久化状态与检查点、支持重复评估、并能从中断中恢复**。它不是单次提示词或一次性脚本：每个阶段都有可执行检查关卡，生成方与核验方分离，重大操作需人工批准，所有改动按版本管理并可回滚。

- 任务背景与验收标准：`docs/plans/task.md`
- 架构设计与带注释工作流图：`docs/design/architecture.md`

> 说明：本仓库为**本地 Git 仓库，含完整提交历史**，未强制推送远程。如需远程托管，可在 GitHub 新建私有仓库后 `git remote add origin <url>` 并 `git push -u origin main`。

## 二、目录与文件说明

```
quant-research-workflow/
├── README.md                  # 本文件
├── AGENTS.md                  # 给智能体的项目总规则（指令文件）
├── requirements.txt           # Python 依赖
├── run.py                     # 端到端入口
├── config/                    # 限额、状态 schema、全局配置
├── prompts/                   # Orchestrator/Generator/Critic 三角色提示词
├── skills/                    # research-loop、pit-data 两个可复用技能
├── src/                       # 实现代码
│   ├── common.py              # 路径/配置/哈希工具
│   ├── generate_fixture.py    # 合成数据生成器
│   ├── data.py                # 数据加载、快照、质量检查
│   ├── signals.py             # PIT 动量信号
│   ├── backtest.py            # 含成本回测与指标
│   ├── gates.py               # 检查关卡（含 PIT 扰动测试）
│   ├── state_machine.py       # 状态机与合法转换
│   └── controller.py          # 控制器：编排、证据、恢复、修订
├── scripts/                   # 回归检查与恢复/修订演示脚本
├── tests/fixtures/            # 合成示例数据（10 只虚构股票）
├── data/raw, data/processed   # 数据快照与信号
├── output/figures, output/tables  # 净值图、回测表、指标
├── evidence/                  # 核验、批准、修订、恢复证据
└── .state/                    # 持久化状态、检查点与演示状态
```

## 三、环境配置与运行说明

### 1. 环境要求

- Python 3.10 及以上（开发环境为 Anaconda Python 3.13）。
- 安装依赖：

```powershell
pip install -r requirements.txt
```

### 2. 运行命令（在项目根目录执行）

```powershell
# （可选）重新生成可复现的合成数据
python src/generate_fixture.py

# 端到端运行一个完整研究案例
python run.py

# 独立回归检查：重跑关键 gate、校验产物哈希
python scripts/check.py

# 中断恢复演示：崩溃后从断点恢复，不重复已完成阶段
python scripts/demo_recovery.py

# 有界修订循环演示：注入问题项 → 修复 → 核验关闭
python scripts/demo_revision.py
```

### 3. 示例输入与输出

- 输入：`tests/fixtures/synthetic_prices.csv`（10 只虚构股票、36 个月末、固定随机种子，可公开分享，无真实客户信息）。
- 输出：
  - 净值图：`output/figures/equity_curve.png`
  - 分期回测与交易：`output/tables/periods.csv`、`output/tables/trades.csv`
  - 指标：`output/tables/metrics.json`
- 基准结果（29 个持有期）：年化收益约 5.75%、夏普比率约 0.45、最大回撤约 −14.56%、期末净值约 1.145。

## 四、核验与恢复证据

`evidence/` 目录保存了可审阅的证据：

- 五个检查关卡：`data_gate`、`pit_gate`、`numerical_gate`、`cost_gate`、`limit_gate`；
- 防未来信息泄露扰动测试：`pit_leakage.json`（扰动 t 之后价格，t 时点信号不变）；
- 稳健性：`robustness.json`（含敏感性说明，如实记录不盈利的参数组合）；
- 独立 Critic 两轮审查与人工批准：`critic_round_1/2.json`、`human_approval.json`；
- 中断恢复与有界修订：`recovery_demo.json`、`revision_demo.json`；
- 回归检查：`regression_check.json`（结论为 PASS）。

## 五、本人贡献

本项目由本人独立完成，具体包括：确定研究任务与验收标准；设计角色分工、状态机、检查关卡与 PIT 规范；编写并迭代各角色提示词、技能与配置；在智能体协助下完成全部 Python 代码的设计、调试与核验；运行完整案例并保存核验、修订与恢复证据；维护全部 Git 提交历史。代码由智能体辅助生成，但所有需求定义、结果核验与最终决策均由本人完成。

## 六、合规与敏感信息声明

- 示例数据全部为**虚构合成数据**，不含任何真实证券、客户或个人隐私信息。
- 仓库不含密码、密钥、凭据等敏感文件（由 `.gitignore` 强制排除）。
- 研究验收通过不代表策略盈利，也不构成任何交易或资金授权；资金使用需单独的人工批准。
