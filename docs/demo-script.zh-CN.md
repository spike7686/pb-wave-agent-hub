# 演示讲稿

语言版本：

- [English](./demo-script.md)
- 简体中文

## 目标

这份讲稿是给项目短演示准备的。

推荐时长：

- `3 到 5 分钟`

核心表达：

- `PB Wave Agent Hub` 会把榜单快照转换成结构化、可回测的做空策略规格
- 它不只是一个页面
- 它不只是一个模拟盘
- 它是一条可以复现的 strategy skill 管线

## 演示结构

建议顺序：

1. 先讲问题
2. 再讲管线
3. 再展示仓库
4. 再展示生成结果
5. 最后落到为什么它重要

## 开场

建议讲法：

“PB Wave Agent Hub 从加密市场榜单快照出发，用 Binance 永续合约的 1 小时价格和 open interest 数据补充市场上下文，再把这个市场状态转换成结构化的做空策略规格，这些规格可以被回放、检查和扩展。”

## 问题定义

建议讲法：

“很多加密交易演示只展示买卖信号，但并没有说明候选池是怎么选出来的、默认的执行市场是什么、以及结果是否可复现。这个项目想解决的就是中间这层缺失的问题。”

## 系统在做什么

建议讲法：

“这个系统有两层。实时层会收集经过过滤的、可在永续合约执行的榜单，并运行三个虚拟资金簿：PB5、PB7.5 和 PB10。回放层会冻结历史快照，用 1 小时 K 线和 OI 重建市场上下文，生成结构化信号，然后把这些信号回放成订单和权益曲线。”

## 展示仓库

建议打开：

- `README.md`
- `docs/architecture.md`
- `docs/strategy-skill-schema.md`

建议讲法：

“这里可以看到，这个仓库是按研究和回放框架来组织的。目标是从市场数据生成机器可读的策略规格，并用可复现的回放结果验证它。”

## 展示最小可复现路径

建议打开或提到：

- `configs/month_replay.minimal_example.json`
- `tests/test_minimal_replay.py`

建议讲法：

“为了保证可复现，我在仓库里带了最小样例数据、回放配置和 smoke test。评委可以本地直接运行批量回放、导出 strategy skill JSON，再验证这些输出文件确实能生成。”

建议执行的命令：

```bash
python3 -m pip install -e '.[dev]'
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.run_batch_replay --config configs/month_replay.minimal_example.json
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.export_strategy_skill --config configs/month_replay.minimal_example.json --output data/examples/month_2026_05/skill_example.json
pytest tests/test_minimal_replay.py
```

## 展示生成结果

建议打开：

- `data/examples/month_2026_05/runs_min/batch_summary.csv`
- `data/examples/month_2026_05/skill_example.json`

建议讲法：

“这里是回放汇总结果，这里是导出的 strategy skill JSON。重点在于，这个仓库不是停留在信号想法层面，它能产出结构化结果，而且这些结果可以继续被检查和回放。”

## 解释为什么有些样例快照没有成交

建议讲法：

“自带的最小样例主要是流程验证样例，不是刻意挑选的高收益 PnL 样例。所以有些快照会产出零笔成交，这是正常的。但这仍然有价值，因为它证明了状态重建、过滤、诊断和导出整条管线都能工作。”

## 为什么它重要

建议讲法：

“它的重要性在于，它确实把市场数据转换成了结构化、可回测的策略规格。它有明确的入场、止损、目标位、诊断信息和回放结果，而不是停留在信号想法层面。”

## 如果观众问原创性在哪里

建议回答：

“原创性不在某一个单独指标，而在组合方式。这个项目把榜单驱动的候选发现、永续市场路由、1h 结构弱化识别、OI 上下文以及可复现回放输出组合在了一起。”

## 如果观众问实际应用价值

建议回答：

“研究员或者未来的执行 Agent 都可以把它当作筛选和信号规格层来用。它可以作为交易前 intelligence 模块、回放研究工具，或者未来执行 Agent 的决策引擎。”

## 结束语

建议讲法：

“所以 PB Wave Agent Hub 的核心价值是，它让这个策略变得可检查、可解释、可复现。它不是只说‘这里有个信号’，而是把信号怎么来的、如何编码、如何回放都完整展示出来。”
