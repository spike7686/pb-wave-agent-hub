# PB Wave Agent Hub

语言版本：

- [English](./README.md)
- 简体中文

`PB Wave Agent Hub` 是一个面向 Binance 永续合约市场的 PB Wave 做空策略研究与虚拟交易框架。

这个项目围绕一条结构化信号管线展开：

- 输入榜单快照
- 用 Binance 永续合约的 1h K 线和 1h OI 数据补充上下文
- 产出结构化做空候选信号，包含入场 / 止损 / 目标位
- 将这些候选信号前向回放，生成订单、PnL 和权益曲线

## 项目做什么

这个仓库包含两套互相关联的工作流。

### 1. 实时工作流

实时工作流运行的是当前线上策略栈：

- 收集合约可交易候选榜单
- 同步 1h 永续 K 线和 1h OI
- 运行三个风险档位的虚拟盘：
  - `PB5`
  - `PB7.5`
  - `PB10`
- 提供一个极简只读监控页面

主要文件：

- `scripts/pb_wave_collector.py`
- `scripts/pb_wave_paper_trader.py`
- `services/server.py`

### 2. 回放工作流

回放工作流用于做“基于榜单快照条件”的历史回测：

1. 读取历史榜单快照
2. 读取对应的 1h 永续 K 线和 1h OI 数据
3. 从每个快照时点开始向前回放 PB Wave 做空策略
4. 生成订单、汇总结果和权益曲线

核心包：

- `src/pb_wave_agent_hub/`

### 3. Strategy Skill 工作流

这一层的核心输出不是实时执行，而是：

- 市场快照输入
- 结构化策略候选输出
- 可回放的订单规格输出

因此这个仓库支持从历史快照导出一个 `strategy-skill-style` 的 JSON 结果，并用回放引擎验证它。

## 为什么这个项目值得看

这不是一个只看价格的普通回测器。

它把这些东西组合在一起：

- 基于榜单的候选池发现
- 面向永续合约执行的市场上下文
- 基于 1h 结构的做空时机判断
- 基于 OI 的弱化信号识别
- continuation 延续信号逻辑
- 显式计入手续费和滑点的虚拟执行

所以它实际上处在几个方向的交叉点上：

- 市场筛选
- 执行感知型虚拟交易
- 可复现的历史回放研究

## 项目结构

```text
pb-wave-agent-hub/
  app/
  configs/
  data/
    snapshots/
    klines_1h/
    oi_1h/
    runs/
  docs/
  runtime/
  scripts/
  services/
  src/pb_wave_agent_hub/
```

## 快速开始

### 环境

推荐：

- Python `3.10+`

可编辑安装：

```bash
cd /path/to/pb-wave-agent-hub
python3 -m pip install -e .
```

安装测试依赖：

```bash
python3 -m pip install -e '.[dev]'
```

## 最快演示路径

如果你想最快验证这个仓库是可运行的，执行下面三条命令即可：

```bash
cd /path/to/pb-wave-agent-hub
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.run_batch_replay --config configs/month_replay.minimal_example.json
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.export_strategy_skill --config configs/month_replay.minimal_example.json --output data/examples/month_2026_05/skill_example.json
pytest tests/test_minimal_replay.py
```

预期产物：

- `data/examples/month_2026_05/runs_min/batch_summary.csv`
- `data/examples/month_2026_05/runs_min/batch_summary.json`
- `data/examples/month_2026_05/skill_example.json`

## 实时模拟盘

运行一次 collector：

```bash
cd /path/to/pb-wave-agent-hub
python3 scripts/pb_wave_collector.py
```

运行入场流程：

```bash
python3 scripts/pb_wave_paper_trader.py --mode entry_5m
```

运行持仓管理流程：

```bash
python3 scripts/pb_wave_paper_trader.py --mode manage_1m
```

启动只读页面：

```bash
python3 services/server.py
```

然后打开：

- `http://127.0.0.1:8080`

## 一个月回放工作流

这个仓库支持一套可复现的单月回放流程。

### 第 1 步：把旧快照转换成回放格式

如果你已经有旧格式原始快照：

```bash
cd /path/to/pb-wave-agent-hub
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.import_legacy_snapshots \
  --input-dir /absolute/path/to/legacy/top15_tracker/snapshots/raw \
  --output-dir data/snapshots/month_2026_05 \
  --start-date 2026-05-01 \
  --end-date 2026-05-31
```

### 第 2 步：生成快照清单

```bash
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.build_snapshot_manifest \
  --snapshot-glob 'data/snapshots/month_2026_05/*.json' \
  --output data/snapshots/month_2026_05_manifest.json
```

### 第 3 步：生成统一的历史数据同步计划

```bash
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.build_history_sync_plan \
  --snapshot-glob 'data/snapshots/month_2026_05/*.json' \
  --lookback-hours 240 \
  --forward-hours 168 \
  --output data/plans/month_2026_05_sync_plan.json
```

### 第 4 步：下载所需的 Binance 永续 1h K 线和 OI 数据

```bash
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.sync_binance_history_plan \
  --plan data/plans/month_2026_05_sync_plan.json \
  --kline-dir data/klines_1h \
  --oi-dir data/oi_1h
```

### 第 5 步：运行批量回放

```bash
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.run_batch_replay \
  --config configs/month_replay.example.json
```

### 第 6 步：读取结果

输出文件：

- `data/runs/month_2026_05/batch_summary.csv`
- `data/runs/month_2026_05/batch_summary.json`
- `data/runs/month_2026_05/batch_equity_curve.csv`
- `data/runs/month_2026_05/batch_equity_curve.json`

每个快照目录下还会有：

- `summary.json`
- `trades.json`
- `equity_curve.json`

## Skill 导出

可以从单个快照导出一个 `strategy-skill-style` JSON。

这个命令支持两种配置输入：

- 单快照 replay 配置
- 批量 replay 配置

如果传入的是批量配置，则会自动使用该配置中的第一个快照做导出。

示例命令：

```bash
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.export_strategy_skill \
  --config configs/month_replay.minimal_example.json \
  --output data/examples/month_2026_05/skill_example.json
```

这个导出结果会包含：

- 过滤后的候选信号
- 入场 / 止损 / 目标位字段
- 特征上下文
- 适合回放和检查的信号元数据

## 内置样例资源

仓库里自带一个轻量级样例目录：

- `data/examples/month_2026_05/snapshots/`
- `data/examples/month_2026_05/snapshots_min/`
- `data/examples/month_2026_05/klines_1h_min/`
- `data/examples/month_2026_05/oi_1h_min/`

用途：

- 展示目录结构应该长什么样
- 提供便于检查的小样本
- 让评委更容易快速做 smoke test

需要注意：

- 这些样例资源 **不是** 完整的一月可复现数据包
- 它们主要是一个“流程验证样例”
- 其中有些样例快照本来就会产出 `0 trades`，这是正常的，因为这里的目标是证明“回放和诊断管线是通的”，不是刻意挑选一个收益最好看的样例
- 完整回放还是应该按正式流程执行：
  - 导入或生成快照
  - 生成历史同步计划
  - 同步 Binance 永续 K 线和 OI
  - 运行批量回放

## 测试入口

仓库自带一个最小 smoke test：

```bash
pytest tests/test_minimal_replay.py
```

这个测试会验证：

- 自带最小批量回放能成功运行
- 汇总产物能被生成
- strategy-skill JSON 能被成功导出

## 内置策略资金簿

仓库使用三个风险档位：

- `PB5`
- `PB7.5`
- `PB10`

这三个档位和当前线上虚拟盘保持一致。

## 成本模型

无论是回放还是模拟盘，都显式使用一个简单透明的执行成本模型：

- 手续费：`4 bps per side`
- 滑点：`5 bps per side`

这个模型不是为了极致精确，而是为了可解释、可复现。

## 数据打包建议

建议仓库中保留：

- 源代码
- 示例配置
- 小规模样例快照
- 样例回放输入
- 样例回放输出
- 使用说明

建议通过 release 附件或外部 bundle 提供：

- 一个月完整快照
- 对应的 1h K 线历史
- 对应的 1h OI 历史
- 完整回放输出

这样仓库本身会更干净，但仍然保留可复现性。

## 扩展方向

如果后续想更贴近 BSC 生态，可以在这个仓库之上增加：

- BSC 链上策略状态锚定
- BSC Agent 任务调度
- 基于 `BNB AI Agent SDK` 的榜单扫描和交易决策封装

这些更适合当作扩展能力，而不是当前仓库的前置条件。

## 许可与免责声明

这是一个研究和虚拟交易仓库。

- 不发币
- 不募资
- 不做流动性引导
- 不承诺真实收益

请自行评估使用风险。
