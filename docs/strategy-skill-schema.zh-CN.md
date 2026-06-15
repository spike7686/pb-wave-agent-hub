# Strategy Skill 数据结构

语言版本：

- [English](./strategy-skill-schema.md)
- 简体中文

## 目的

Strategy Skill 这一层的目标，是把一个固定时点的市场快照，转换成结构化、可回放的交易规格。

这个仓库采用的概念性输出结构如下。

## 顶层对象

```json
{
  "skill_name": "pb_wave_short_skill",
  "skill_version": "0.1.0",
  "snapshot_id": "20260531T231504Z",
  "captured_at_utc": "2026-05-31T23:15:04+00:00",
  "market": "binance_perp",
  "universe_size": 15,
  "candidate_count": 3,
  "candidates": []
}
```

## Candidate 对象

```json
{
  "symbol": "WLD",
  "signal_symbol": "WLDUSDT",
  "rank": 1,
  "strategy_family": "pb_wave_short",
  "signal_type": "base",
  "entry_time_utc": "2026-05-31T23:00:00+00:00",
  "entry_price": 1.2345,
  "stop_price": 1.2850,
  "stop_pct": 4.09,
  "tp1_price": 1.1840,
  "tp2_price": 1.0830,
  "tp1_ratio": 0.35,
  "target_r_multiple": 3.0,
  "features": {},
  "rationale": {},
  "blockers": []
}
```

## Feature 字段

建议包含：

- `runup_24h_pct`
- `trend_7d_pct`
- `trend_7d_label`
- `trend_48h_label`
- `trend_24h_label`
- `retrace_from_peak_pct`
- `peak_age_hours`
- `breakout_margin_pct`
- `lower_high_gap_pct`
- `weakness_score`
- `oi_1h_pct`
- `oi_4h_pct`
- `oi_12h_pct`
- `oi_24h_pct`
- `oi_to_vol_ratio`
- `price_oi_divergence_4h`

## Rationale 字段

建议包含：

- `entry_profile`
- `stop_profile`
- `exit_profile`
- `selection_variant`
- `summary`

## 为什么这个结构重要

这个结构的重要性在于，它提供了：

- 机器可读的策略输出
- 从原始市场数据到最终订单规格之间的清晰桥梁
- 一个可回放、可检查、可扩展的输出格式
