from __future__ import annotations

import argparse
import json
from pathlib import Path

from pb_wave_agent_hub.config import ReplayConfig
from pb_wave_agent_hub.config import load_batch_replay_config
from pb_wave_agent_hub.config import load_replay_config
from pb_wave_agent_hub.features.pb_wave import build_pb_wave_features
from pb_wave_agent_hub.providers.local_files import LocalFilesProvider
from pb_wave_agent_hub.strategies.pb_wave_strategy import build_candidate_lists
from pb_wave_agent_hub.strategies.pb_wave_strategy import build_signal
from pb_wave_agent_hub.strategies.pb_wave_strategy import ENTRY_PROFILE
from pb_wave_agent_hub.strategies.pb_wave_strategy import STOP_PROFILE
from pb_wave_agent_hub.strategies.pb_wave_strategy import EXIT_PROFILE


def resolve_config_and_provider(config_path: str | Path) -> tuple[ReplayConfig, LocalFilesProvider]:
    raw = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if "snapshot_path" in raw:
        config = load_replay_config(config_path)
        provider = LocalFilesProvider(
            snapshot_path=config.snapshot_path,
            kline_dir=config.kline_dir,
            oi_dir=config.oi_dir,
        )
        return config, provider

    batch_config = load_batch_replay_config(config_path)
    if not batch_config.snapshot_paths:
        raise RuntimeError("batch replay config contains no snapshot paths")
    snapshot_path = batch_config.snapshot_paths[0]
    config = ReplayConfig(
        snapshot_path=snapshot_path,
        kline_dir=batch_config.kline_dir,
        oi_dir=batch_config.oi_dir,
        output_dir=batch_config.output_dir,
        lookback_hours=batch_config.lookback_hours,
        forward_hours=batch_config.forward_hours,
        strategies=batch_config.strategies,
        cost_model=batch_config.cost_model,
    )
    provider = LocalFilesProvider(
        snapshot_path=snapshot_path,
        kline_dir=config.kline_dir,
        oi_dir=config.oi_dir,
    )
    return config, provider


def main():
    parser = argparse.ArgumentParser(description="Export a Track-2-style strategy skill payload from one snapshot.")
    parser.add_argument("--config", required=True, help="Replay config JSON path.")
    parser.add_argument("--output", required=True, help="Skill JSON output path.")
    args = parser.parse_args()

    config, provider = resolve_config_and_provider(args.config)
    snapshot = provider.load_snapshot()
    klines_by_symbol = {}
    oi_by_symbol = {}
    for row in snapshot.rows:
        if not row.signal_symbol:
            continue
        try:
            klines_by_symbol[row.signal_symbol] = provider.load_klines_1h(row.signal_symbol)
        except FileNotFoundError:
            klines_by_symbol[row.signal_symbol] = []
        try:
            oi_by_symbol[row.signal_symbol] = provider.load_oi_1h(row.signal_symbol)
        except FileNotFoundError:
            oi_by_symbol[row.signal_symbol] = []

    features = build_pb_wave_features(snapshot, klines_by_symbol, oi_by_symbol, config)
    raw_candidates, clusters, selected_candidates, diagnostics = build_candidate_lists(features["states"])

    candidates = []
    for item in selected_candidates:
        signal = build_signal(item["signal"], STOP_PROFILE) if "stop_price" not in item["signal"] else item["signal"]
        if signal is None:
            continue
        candidates.append(
            {
                "symbol": signal["symbol"],
                "signal_symbol": signal["signal_symbol"],
                "rank": signal.get("snapshot_rank"),
                "strategy_family": "pb_wave_short",
                "signal_type": "base",
                "entry_time_utc": signal["entry_dt"].isoformat(),
                "entry_price": signal["entry_price"],
                "stop_price": signal["stop_price"],
                "stop_pct": signal["stop_pct"],
                "tp1_price": signal["entry_price"] - (signal["stop_price"] - signal["entry_price"]) * EXIT_PROFILE.tp1_r,
                "tp2_price": signal["entry_price"] - (signal["stop_price"] - signal["entry_price"]) * EXIT_PROFILE.tp2_r,
                "tp1_ratio": EXIT_PROFILE.tp1_ratio,
                "target_r_multiple": EXIT_PROFILE.tp2_r,
                "features": {
                    "runup_24h_pct": signal.get("runup_24h_pct"),
                    "trend_7d_pct": signal.get("trend_7d_pct"),
                    "trend_7d_label": signal.get("trend_7d_label"),
                    "trend_48h_label": signal.get("trend_48h_label"),
                    "trend_24h_label": signal.get("trend_24h_label"),
                    "retrace_from_peak_pct": signal.get("retrace_from_peak_pct"),
                    "peak_age_hours": signal.get("peak_age_hours"),
                    "breakout_margin_pct": signal.get("breakout_margin_pct"),
                    "lower_high_gap_pct": signal.get("lower_high_gap_pct"),
                    "weakness_score": signal.get("weakness_score"),
                    "oi_1h_pct": signal.get("oi_1h_pct"),
                    "oi_4h_pct": signal.get("oi_4h_pct"),
                    "oi_12h_pct": signal.get("oi_12h_pct"),
                    "oi_24h_pct": signal.get("oi_24h_pct"),
                    "oi_to_vol_ratio": signal.get("oi_to_vol_ratio"),
                    "price_oi_divergence_4h": signal.get("price_oi_divergence_4h"),
                },
                "rationale": {
                    "entry_profile": "entry_core",
                    "stop_profile": "stop_balanced",
                    "exit_profile": "exit_12h_tail",
                    "summary": "pb_wave_base_signal",
                },
                "blockers": [],
            }
        )

    payload = {
        "skill_name": "pb_wave_short_skill",
        "skill_version": "0.1.0",
        "snapshot_id": snapshot.snapshot_id,
        "captured_at_utc": snapshot.captured_at_utc.isoformat(),
        "market": "binance_perp",
        "universe_size": len(snapshot.rows),
        "state_count": len(features["states"]),
        "warning_count": len(features["warnings"]),
        "raw_candidate_count": len(raw_candidates),
        "base_cluster_count": len(clusters),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "warnings": features["warnings"][:50],
        "diagnostics_preview": diagnostics[:50],
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
