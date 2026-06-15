from __future__ import annotations

import json
from pathlib import Path
import csv

from pb_wave_agent_hub.config import ReplayConfig
from pb_wave_agent_hub.features.pb_wave import build_pb_wave_features
from pb_wave_agent_hub.strategies.pb_wave_strategy import run_pb_wave_strategy
from pb_wave_agent_hub.providers.local_files import LocalFilesProvider


def run_snapshot_replay(config, provider, starting_equity_by_strategy=None):
    snapshot = provider.load_snapshot()
    klines_by_symbol = {}
    oi_by_symbol = {}
    load_warnings = []
    for row in snapshot.rows:
        if not row.signal_symbol:
            continue
        try:
            klines_by_symbol[row.signal_symbol] = provider.load_klines_1h(row.signal_symbol)
        except FileNotFoundError:
            load_warnings.append(f"{row.signal_symbol} kline_file_missing")
            klines_by_symbol[row.signal_symbol] = []
        try:
            oi_by_symbol[row.signal_symbol] = provider.load_oi_1h(row.signal_symbol)
        except FileNotFoundError:
            load_warnings.append(f"{row.signal_symbol} oi_file_missing")
            oi_by_symbol[row.signal_symbol] = []
    features = build_pb_wave_features(snapshot, klines_by_symbol, oi_by_symbol, config)
    features["warnings"] = load_warnings + features["warnings"]
    result = run_pb_wave_strategy(snapshot, features, config, starting_equity_by_strategy=starting_equity_by_strategy)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    summary_out = config.output_dir / "summary.json"
    trades_out = config.output_dir / "trades.json"
    curve_out = config.output_dir / "equity_curve.json"
    summary_out.write_text(json.dumps(result["summary"], ensure_ascii=False, indent=2), encoding="utf-8")
    trades_out.write_text(json.dumps(result["trades"], ensure_ascii=False, indent=2), encoding="utf-8")
    curve_out.write_text(json.dumps(result["equity_curve"], ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "summary_path": summary_out,
        "trades_path": trades_out,
        "equity_curve_path": curve_out,
        "result": result,
    }


def write_batch_summary_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "snapshot_id",
        "captured_at_utc",
        "strategy_id",
        "strategy_code",
        "starting_equity_usd",
        "state_count",
        "warning_count",
        "raw_base_signal_count",
        "base_cluster_count",
        "base_selected_count",
        "closed_count",
        "win_count",
        "loss_count",
        "win_rate",
        "realized_pnl_usd",
        "gross_realized_pnl_usd",
        "cost_total_usd",
        "equity_usd",
        "max_drawdown_pct",
        "total_realized_r",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def write_batch_equity_curve_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "strategy_id",
        "strategy_code",
        "snapshot_id",
        "captured_at_utc",
        "starting_equity_usd",
        "ending_equity_usd",
        "realized_pnl_usd",
        "cost_total_usd",
        "closed_count",
        "win_rate",
        "max_drawdown_pct",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def run_batch_snapshot_replay(config):
    config.output_dir.mkdir(parents=True, exist_ok=True)
    batch_rows = []
    batch_json = []
    batch_equity_rows = []
    rolling_equity_by_strategy = {strategy.strategy_id: 10000.0 for strategy in config.strategies}
    for snapshot_path in config.snapshot_paths:
        snapshot_name = snapshot_path.stem
        run_output_dir = config.output_dir / snapshot_name
        single_config = ReplayConfig(
            snapshot_path=snapshot_path,
            kline_dir=config.kline_dir,
            oi_dir=config.oi_dir,
            output_dir=run_output_dir,
            lookback_hours=config.lookback_hours,
            forward_hours=config.forward_hours,
            strategies=config.strategies,
            cost_model=config.cost_model,
        )
        provider = LocalFilesProvider(
            snapshot_path=snapshot_path,
            kline_dir=config.kline_dir,
            oi_dir=config.oi_dir,
        )
        run_payload = run_snapshot_replay(
            single_config,
            provider,
            starting_equity_by_strategy=rolling_equity_by_strategy if config.carry_equity else None,
        )
        summary = run_payload["result"]["summary"]
        batch_json.append(summary)
        for strategy_id, strategy_summary in (summary.get("strategies") or {}).items():
            batch_rows.append(
                {
                    "snapshot_id": summary.get("snapshot_id"),
                    "captured_at_utc": summary.get("captured_at_utc"),
                    "strategy_id": strategy_id,
                    "strategy_code": strategy_summary.get("strategy_code"),
                    "starting_equity_usd": strategy_summary.get("starting_equity_usd"),
                    "state_count": summary.get("state_count"),
                    "warning_count": len(summary.get("warnings") or []),
                    "raw_base_signal_count": (summary.get("candidate_summary") or {}).get("raw_base_signal_count"),
                    "base_cluster_count": (summary.get("candidate_summary") or {}).get("base_cluster_count"),
                    "base_selected_count": (summary.get("candidate_summary") or {}).get("base_selected_count"),
                    "closed_count": strategy_summary.get("closed_count"),
                    "win_count": strategy_summary.get("win_count"),
                    "loss_count": strategy_summary.get("loss_count"),
                    "win_rate": strategy_summary.get("win_rate"),
                    "realized_pnl_usd": strategy_summary.get("realized_pnl_usd"),
                    "gross_realized_pnl_usd": strategy_summary.get("gross_realized_pnl_usd"),
                    "cost_total_usd": strategy_summary.get("cost_total_usd"),
                    "equity_usd": strategy_summary.get("equity_usd"),
                    "max_drawdown_pct": strategy_summary.get("max_drawdown_pct"),
                    "total_realized_r": strategy_summary.get("total_realized_r"),
                }
            )
            batch_equity_rows.append(
                {
                    "strategy_id": strategy_id,
                    "strategy_code": strategy_summary.get("strategy_code"),
                    "snapshot_id": summary.get("snapshot_id"),
                    "captured_at_utc": summary.get("captured_at_utc"),
                    "starting_equity_usd": strategy_summary.get("starting_equity_usd"),
                    "ending_equity_usd": strategy_summary.get("equity_usd"),
                    "realized_pnl_usd": strategy_summary.get("realized_pnl_usd"),
                    "cost_total_usd": strategy_summary.get("cost_total_usd"),
                    "closed_count": strategy_summary.get("closed_count"),
                    "win_rate": strategy_summary.get("win_rate"),
                    "max_drawdown_pct": strategy_summary.get("max_drawdown_pct"),
                }
            )
            if config.carry_equity:
                rolling_equity_by_strategy[strategy_id] = float(strategy_summary.get("equity_usd") or rolling_equity_by_strategy[strategy_id])

    summary_csv = config.output_dir / "batch_summary.csv"
    summary_json = config.output_dir / "batch_summary.json"
    curve_csv = config.output_dir / "batch_equity_curve.csv"
    curve_json = config.output_dir / "batch_equity_curve.json"
    write_batch_summary_csv(summary_csv, batch_rows)
    summary_json.write_text(json.dumps(batch_json, ensure_ascii=False, indent=2), encoding="utf-8")
    write_batch_equity_curve_csv(curve_csv, batch_equity_rows)
    curve_json.write_text(json.dumps(batch_equity_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary_csv
