from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StrategyConfig:
    strategy_id: str
    strategy_code: str
    risk_pct: float


@dataclass(frozen=True)
class CostModelConfig:
    fee_bps_per_side: float
    slippage_bps_per_side: float


@dataclass(frozen=True)
class ReplayConfig:
    snapshot_path: Path
    kline_dir: Path
    oi_dir: Path
    output_dir: Path
    lookback_hours: int
    forward_hours: int
    strategies: list[StrategyConfig]
    cost_model: CostModelConfig


@dataclass(frozen=True)
class BatchReplayConfig:
    snapshot_paths: list[Path]
    kline_dir: Path
    oi_dir: Path
    output_dir: Path
    lookback_hours: int
    forward_hours: int
    strategies: list[StrategyConfig]
    cost_model: CostModelConfig
    carry_equity: bool


def parse_strategies(raw_items: list[dict]) -> list[StrategyConfig]:
    return [
        StrategyConfig(
            strategy_id=item["strategy_id"],
            strategy_code=item["strategy_code"],
            risk_pct=float(item["risk_pct"]),
        )
        for item in raw_items
    ]


def parse_cost_model(raw: dict) -> CostModelConfig:
    return CostModelConfig(
        fee_bps_per_side=float(raw.get("cost_model", {}).get("fee_bps_per_side", 4.0)),
        slippage_bps_per_side=float(raw.get("cost_model", {}).get("slippage_bps_per_side", 5.0)),
    )


def load_replay_config(path: str | Path) -> ReplayConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return ReplayConfig(
        snapshot_path=Path(raw["snapshot_path"]),
        kline_dir=Path(raw["kline_dir"]),
        oi_dir=Path(raw["oi_dir"]),
        output_dir=Path(raw["output_dir"]),
        lookback_hours=int(raw.get("lookback_hours", 240)),
        forward_hours=int(raw.get("forward_hours", 168)),
        strategies=parse_strategies(raw.get("strategies", [])),
        cost_model=parse_cost_model(raw),
    )


def load_batch_replay_config(path: str | Path) -> BatchReplayConfig:
    config_path = Path(path).resolve()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    project_dir = config_path.parent.parent
    snapshot_paths = [Path(item) for item in raw.get("snapshot_paths", [])]
    snapshot_glob = raw.get("snapshot_glob")
    if snapshot_glob:
        snapshot_paths.extend(sorted(project_dir.glob(snapshot_glob)))
    deduped_snapshot_paths = []
    seen = set()
    for item in snapshot_paths:
        resolved = item if item.is_absolute() else (project_dir / item)
        key = str(resolved.resolve())
        if key in seen:
            continue
        seen.add(key)
        deduped_snapshot_paths.append(item)
    return BatchReplayConfig(
        snapshot_paths=deduped_snapshot_paths,
        kline_dir=Path(raw["kline_dir"]),
        oi_dir=Path(raw["oi_dir"]),
        output_dir=Path(raw["output_dir"]),
        lookback_hours=int(raw.get("lookback_hours", 240)),
        forward_hours=int(raw.get("forward_hours", 168)),
        strategies=parse_strategies(raw.get("strategies", [])),
        cost_model=parse_cost_model(raw),
        carry_equity=bool(raw.get("carry_equity", True)),
    )
