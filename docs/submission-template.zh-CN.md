# 提交说明模板

语言版本：

- [English](./submission-template.md)
- 简体中文

## 项目名称

PB Wave Agent Hub

## 一句话总结

PB Wave Agent Hub 是一个面向 Track 2 的策略技能引擎，它把加密市场榜单快照转换成可回测的做空策略规格，并使用 Binance 永续 K 线和 OI 数据作为上下文。

## 赛道

Track 2: Strategy Skills

## 它解决了什么问题

很多加密策略演示只展示“有信号”，却没有展示：

- 候选筛选是否有纪律
- 执行上下文是否真实
- 历史回放是否可复现
- 成本假设是否透明

这个项目试图补上这些空白，它把下面几部分组合起来：

- 过滤后的榜单构建
- 面向永续合约的候选路由
- 1h 结构弱化识别
- 基于 OI 的信号修正
- 带手续费和滑点的虚拟执行

## 核心功能

- `PB5`、`PB7.5`、`PB10` 三个风险档位的实时虚拟盘
- 只读监控页面
- 历史快照导入
- 月度快照清单生成
- Binance 永续历史同步计划生成
- 批量回放，输出订单和权益曲线
- 从历史快照导出 strategy-skill 风格的 JSON

## 可复现性

公开仓库中包含：

- 源代码
- 使用说明
- 回放配置
- 样例快照
- 最小 smoke test
- 样例回放输出

可复现流程：

1. 导入或抓取快照
2. 生成 manifest / sync plan
3. 同步 Binance 永续 1h K 线和 OI
4. 运行批量回放
5. 检查订单和汇总结果
6. 导出 strategy-skill JSON

## 演示命令

```bash
python3 -m pip install -e '.[dev]'
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.run_batch_replay --config configs/month_replay.minimal_example.json
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.export_strategy_skill --config configs/month_replay.minimal_example.json --output data/examples/month_2026_05/skill_example.json
pytest tests/test_minimal_replay.py
```

## 演示输出

- `batch_summary.csv`：按快照汇总的策略结果
- `batch_summary.json`：回放汇总 JSON
- `trades.json`：生成的回放订单
- `equity_curve.json`：回放权益轨迹
- `skill_example.json`：Track 2 风格的策略技能 JSON

## 为什么它适合 Track 2

- 它把市场数据转换成结构化、可回放的策略规格
- 它不依赖实时执行层
- 它清楚展示了从原始快照到订单规格的路径
- 它天然支持回测与检查

## 备注

- 不发币
- 不募资
- 不做流动性事件
- 仅用于研究和虚拟交易
