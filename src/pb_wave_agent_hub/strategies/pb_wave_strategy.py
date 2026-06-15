from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta

from pb_wave_agent_hub.features.pb_wave import short_return_pct
from pb_wave_agent_hub.strategies.pb_wave_continuation import build_continuation_candidates
from pb_wave_agent_hub.strategies.pb_wave_continuation import run_combined_strategy


MAX_GROSS_PCT = 500.0
ENTRY_COOLDOWN_HOURS = 12.0
CLUSTER_GAP_HOURS = 18.0
MIN_BUFFER_PCT = 0.25


@dataclass(frozen=True)
class EntryProfile:
    min_runup_24h_pct: float
    min_trend_7d_pct: float
    min_peak_age_hours: int
    max_peak_age_hours: int
    min_breakout_margin_pct: float
    min_retrace_from_peak_pct: float
    max_retrace_from_peak_pct: float
    min_lower_high_gap_pct: float
    weakness_score_min: int
    require_below_slow_ma: bool
    require_below_trend_ma: bool


@dataclass(frozen=True)
class StopProfile:
    stop_floor_pct: float
    stop_cap_pct: float
    stop_atr_buffer_mult: float


@dataclass(frozen=True)
class ExitProfile:
    min_hold_hours: float
    max_hold_hours: float
    tp1_r: float
    tp1_ratio: float
    tp2_r: float
    resume_ma_period: int
    resume_confirm_bars: int


ENTRY_PROFILE = EntryProfile(
    min_runup_24h_pct=9.0,
    min_trend_7d_pct=8.0,
    min_peak_age_hours=1,
    max_peak_age_hours=5,
    min_breakout_margin_pct=1.2,
    min_retrace_from_peak_pct=1.0,
    max_retrace_from_peak_pct=7.0,
    min_lower_high_gap_pct=0.5,
    weakness_score_min=4,
    require_below_slow_ma=False,
    require_below_trend_ma=False,
)

STOP_PROFILE = StopProfile(
    stop_floor_pct=4.0,
    stop_cap_pct=10.0,
    stop_atr_buffer_mult=0.35,
)

EXIT_PROFILE = ExitProfile(
    min_hold_hours=12.0,
    max_hold_hours=72.0,
    tp1_r=1.0,
    tp1_ratio=0.35,
    tp2_r=3.0,
    resume_ma_period=8,
    resume_confirm_bars=2,
)

VARIANT_CAPS = {
    "max_runup_24h_pct": 18.0,
    "max_oi_12h_pct": 18.0,
    "max_oi_24h_pct": 24.0,
    "max_oi_to_vol_ratio": 0.90,
}


def snapshot_matches_entry(snapshot, profile):
    return (
        snapshot["trend_7d_label"] in {"Up", "StrongUp"}
        and snapshot["trend_48h_label"] in {"Up", "StrongUp"}
        and snapshot["trend_24h_label"] in {"Range", "Up", "StrongUp"}
        and (snapshot["runup_24h_pct"] or -999.0) >= profile.min_runup_24h_pct
        and (snapshot["trend_7d_pct"] or -999.0) >= profile.min_trend_7d_pct
        and profile.min_peak_age_hours <= snapshot["peak_age_hours"] <= profile.max_peak_age_hours
        and (snapshot["breakout_margin_pct"] or -999.0) >= profile.min_breakout_margin_pct
        and snapshot["retrace_from_peak_pct"] is not None
        and profile.min_retrace_from_peak_pct <= snapshot["retrace_from_peak_pct"] <= profile.max_retrace_from_peak_pct
        and (snapshot["lower_high_gap_pct"] or -999.0) >= profile.min_lower_high_gap_pct
        and snapshot["breakout_failed"]
        and snapshot["lower_high_confirmed"]
        and snapshot["weakness_score"] >= profile.weakness_score_min
        and (snapshot["below_slow_ma"] if profile.require_below_slow_ma else snapshot["below_fast_ma"])
        and ((not profile.require_below_trend_ma) or snapshot["below_trend_ma"])
    )


def entry_blockers(snapshot, profile):
    blockers = []
    if snapshot["trend_7d_label"] not in {"Up", "StrongUp"}:
        blockers.append("trend_7d")
    if snapshot["trend_48h_label"] not in {"Up", "StrongUp"}:
        blockers.append("trend_48h")
    if snapshot["trend_24h_label"] not in {"Range", "Up", "StrongUp"}:
        blockers.append("trend_24h")
    if (snapshot["runup_24h_pct"] or -999.0) < profile.min_runup_24h_pct:
        blockers.append("runup_24h")
    if (snapshot["trend_7d_pct"] or -999.0) < profile.min_trend_7d_pct:
        blockers.append("trend_7d_pct")
    if not (profile.min_peak_age_hours <= snapshot["peak_age_hours"] <= profile.max_peak_age_hours):
        blockers.append("peak_age")
    if (snapshot["breakout_margin_pct"] or -999.0) < profile.min_breakout_margin_pct:
        blockers.append("breakout_margin")
    retrace = snapshot["retrace_from_peak_pct"]
    if retrace is None or not (profile.min_retrace_from_peak_pct <= retrace <= profile.max_retrace_from_peak_pct):
        blockers.append("retrace")
    if (snapshot["lower_high_gap_pct"] or -999.0) < profile.min_lower_high_gap_pct:
        blockers.append("lower_high_gap")
    if not snapshot["breakout_failed"]:
        blockers.append("breakout_failed")
    if not snapshot["lower_high_confirmed"]:
        blockers.append("lower_high")
    if snapshot["weakness_score"] < profile.weakness_score_min:
        blockers.append("weakness_score")
    if profile.require_below_slow_ma:
        if not snapshot["below_slow_ma"]:
            blockers.append("below_slow_ma")
    elif not snapshot["below_fast_ma"]:
        blockers.append("below_fast_ma")
    if profile.require_below_trend_ma and not snapshot["below_trend_ma"]:
        blockers.append("below_trend_ma")
    return blockers


def candidate_passes_caps(signal):
    checks = [
        ("max_runup_24h_pct", signal.get("runup_24h_pct")),
        ("max_oi_12h_pct", signal.get("oi_12h_pct")),
        ("max_oi_24h_pct", signal.get("oi_24h_pct")),
        ("max_oi_to_vol_ratio", signal.get("oi_to_vol_ratio")),
    ]
    for key, value in checks:
        cap = VARIANT_CAPS[key]
        if cap is not None and value is not None and value > cap:
            return False
    return True


def cap_blockers(signal):
    blockers = []
    checks = [
        ("max_runup_24h_pct", "runup_cap", signal.get("runup_24h_pct")),
        ("max_oi_12h_pct", "oi_12h_cap", signal.get("oi_12h_pct")),
        ("max_oi_24h_pct", "oi_24h_cap", signal.get("oi_24h_pct")),
        ("max_oi_to_vol_ratio", "oi_to_vol_cap", signal.get("oi_to_vol_ratio")),
    ]
    for key, label, value in checks:
        cap = VARIANT_CAPS[key]
        if cap is not None and value is not None and value > cap:
            blockers.append(label)
    return blockers


def build_signal(snapshot, stop_profile):
    stop_buffer_pct = max(MIN_BUFFER_PCT, (snapshot["atr_1h_pct"] or 0.0) * stop_profile.stop_atr_buffer_mult)
    raw_stop_price = snapshot["peak_price"] * (1.0 + stop_buffer_pct / 100.0)
    raw_stop_pct = ((raw_stop_price / snapshot["entry_price"]) - 1.0) * 100.0 if snapshot["entry_price"] else None
    if raw_stop_pct is None:
        return None
    effective_stop_pct = max(stop_profile.stop_floor_pct, raw_stop_pct)
    if effective_stop_pct > stop_profile.stop_cap_pct:
        return None
    stop_price = (
        raw_stop_price
        if raw_stop_pct >= stop_profile.stop_floor_pct
        else snapshot["entry_price"] * (1.0 + effective_stop_pct / 100.0)
    )
    return {
        **snapshot,
        "raw_stop_pct": raw_stop_pct,
        "stop_pct": effective_stop_pct,
        "stop_price": stop_price,
    }


def cluster_candidates(signals):
    if not signals:
        return []
    sorted_signals = sorted(signals, key=lambda item: item["signal"]["entry_dt"])
    clusters = [[sorted_signals[0]]]
    gap = timedelta(hours=CLUSTER_GAP_HOURS)
    for item in sorted_signals[1:]:
        prev_dt = clusters[-1][-1]["signal"]["entry_dt"]
        curr_dt = item["signal"]["entry_dt"]
        if curr_dt - prev_dt <= gap:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    return clusters


def build_candidate_lists(states):
    cooldown = timedelta(hours=ENTRY_COOLDOWN_HOURS)
    raw_signals = []
    diagnostics = []
    for state in states:
        active = False
        last_entry_dt = None
        for idx, snapshot in enumerate(state["snapshots"]):
            if idx < state["replay_start_idx"] or snapshot is None:
                continue
            if snapshot["entry_dt"] > state["replay_end_dt"]:
                break
            blockers = entry_blockers(snapshot, ENTRY_PROFILE)
            if blockers:
                diagnostics.append(
                    {
                        "symbol": snapshot["symbol"],
                        "signal_symbol": snapshot["signal_symbol"],
                        "entry_dt": snapshot["entry_dt"].isoformat(),
                        "decision": "blocked_entry",
                        "blockers": blockers,
                    }
                )
                active = False
                continue
            signal = build_signal(snapshot, STOP_PROFILE)
            if not signal:
                diagnostics.append(
                    {
                        "symbol": snapshot["symbol"],
                        "signal_symbol": snapshot["signal_symbol"],
                        "entry_dt": snapshot["entry_dt"].isoformat(),
                        "decision": "blocked_stop",
                        "blockers": ["stop_invalid"],
                    }
                )
                active = False
                continue
            caps = cap_blockers(signal)
            if caps:
                diagnostics.append(
                    {
                        "symbol": snapshot["symbol"],
                        "signal_symbol": snapshot["signal_symbol"],
                        "entry_dt": snapshot["entry_dt"].isoformat(),
                        "decision": "blocked_caps",
                        "blockers": caps,
                        "stop_pct": signal["stop_pct"],
                    }
                )
                active = False
                continue
            if not active and (last_entry_dt is None or (signal["entry_dt"] - last_entry_dt) >= cooldown):
                raw_signals.append({"state": state, "index": idx, "signal": signal})
                diagnostics.append(
                    {
                        "symbol": signal["symbol"],
                        "signal_symbol": signal["signal_symbol"],
                        "entry_dt": signal["entry_dt"].isoformat(),
                        "decision": "selected_raw",
                        "blockers": [],
                        "stop_pct": signal["stop_pct"],
                    }
                )
                last_entry_dt = signal["entry_dt"]
                active = True
    clusters = cluster_candidates(raw_signals)
    picked = [min(cluster, key=lambda item: item["signal"]["entry_dt"]) for cluster in clusters]
    picked.sort(key=lambda item: item["signal"]["entry_dt"])
    return raw_signals, clusters, picked, diagnostics


def ema_value(state, period, idx):
    if period == 8:
        return state["ema8_1h"][idx]
    if period == 21:
        return state["ema21_1h"][idx]
    if period == 55:
        return state["ema55_1h"][idx]
    raise ValueError(f"unsupported ema period: {period}")


def strength_resume_signal(state, idx, exit_profile):
    selected_ema = ema_value(state, exit_profile.resume_ma_period, idx)
    selected_ema_prev = ema_value(state, exit_profile.resume_ma_period, idx - 1)
    candle = state["1h"][idx]
    prev = state["1h"][idx - 1]
    return (
        candle.close_price > selected_ema
        and selected_ema >= selected_ema_prev
        and candle.close_price > prev.close_price
        and state["ema8_1h"][idx] >= state["ema8_1h"][idx - 1]
    )


def resolve_position_notional(equity_usd, risk_pct, stop_pct):
    if stop_pct in (None, 0):
        return None
    risk_usd = equity_usd * (risk_pct / 100.0)
    gross_cap_usd = equity_usd * (MAX_GROSS_PCT / 100.0)
    return min(risk_usd / (stop_pct / 100.0), gross_cap_usd)


def simulate_trade(state, entry_idx, signal, equity_usd, strategy, cost_model):
    candles = state["1h"]
    entry_price = signal["entry_price"]
    stop_price = signal["stop_price"]
    stop_pct = signal["stop_pct"]
    entry_dt = signal["entry_dt"]
    notional_usd = resolve_position_notional(equity_usd, strategy.risk_pct, stop_pct)
    if notional_usd in (None, 0):
        return None

    qty = notional_usd / entry_price if entry_price else None
    risk_abs = stop_price - entry_price
    tp1_price = entry_price - risk_abs * EXIT_PROFILE.tp1_r
    tp2_price = entry_price - risk_abs * EXIT_PROFILE.tp2_r
    min_hold_dt = entry_dt + timedelta(hours=EXIT_PROFILE.min_hold_hours)
    end_dt = entry_dt + timedelta(hours=EXIT_PROFILE.max_hold_hours)

    remaining_weight = 1.0
    gross_return_pct = 0.0
    best_path_return_pct = None
    worst_path_return_pct = None
    exit_code = "timeout"
    exit_dt = None
    exit_price = None
    tp1_taken = False
    tp2_taken = False
    stop_price_live = stop_price
    resume_hits = 0

    for j in range(entry_idx + 1, len(candles)):
        bar = candles[j]
        if bar.close_time_utc > end_dt:
            break

        if bar.high_price >= stop_price_live:
            stop_return = short_return_pct(entry_price, stop_price_live)
            gross_return_pct += remaining_weight * (stop_return or 0.0)
            remaining_weight = 0.0
            exit_code = "stop_after_tp1" if tp1_taken else "stop_loss"
            exit_dt = bar.close_time_utc
            exit_price = stop_price_live
            break

        best_bar_return = short_return_pct(entry_price, bar.low_price)
        close_return = short_return_pct(entry_price, bar.close_price)
        worst_bar_return = short_return_pct(entry_price, bar.high_price)
        if best_bar_return is not None:
            best_path_return_pct = best_bar_return if best_path_return_pct is None else max(best_path_return_pct, best_bar_return)
        if worst_bar_return is not None:
            worst_path_return_pct = worst_bar_return if worst_path_return_pct is None else min(worst_path_return_pct, worst_bar_return)

        if not tp1_taken and bar.low_price <= tp1_price and remaining_weight > 0:
            ratio = min(EXIT_PROFILE.tp1_ratio, remaining_weight)
            gross_return_pct += ratio * (stop_pct * EXIT_PROFILE.tp1_r)
            remaining_weight -= ratio
            tp1_taken = True
            stop_price_live = min(stop_price_live, entry_price)

        if tp1_taken and not tp2_taken and bar.low_price <= tp2_price and remaining_weight > 0:
            gross_return_pct += remaining_weight * (stop_pct * EXIT_PROFILE.tp2_r)
            remaining_weight = 0.0
            tp2_taken = True
            exit_code = "take_profit_tail"
            exit_dt = bar.close_time_utc
            exit_price = tp2_price
            break

        if bar.close_time_utc >= min_hold_dt:
            resumed_now = strength_resume_signal(state, j, EXIT_PROFILE)
            resume_hits = resume_hits + 1 if resumed_now else 0
            if resume_hits >= EXIT_PROFILE.resume_confirm_bars:
                gross_return_pct += remaining_weight * (close_return or 0.0)
                remaining_weight = 0.0
                exit_code = "strength_resume_after_tp1" if tp1_taken else "strength_resume"
                exit_dt = bar.close_time_utc
                exit_price = bar.close_price
                break

    if remaining_weight > 0:
        timeout_bar = None
        for j in range(entry_idx + 1, len(candles)):
            bar = candles[j]
            if bar.close_time_utc > end_dt:
                break
            timeout_bar = bar
        if timeout_bar is None:
            return None
        timeout_return = short_return_pct(entry_price, timeout_bar.close_price)
        gross_return_pct += remaining_weight * (timeout_return or 0.0)
        exit_code = "timeout_after_tp1" if tp1_taken else "timeout"
        exit_dt = timeout_bar.close_time_utc
        exit_price = timeout_bar.close_price

    gross_pnl_usd = notional_usd * (gross_return_pct / 100.0)
    fee_usd = notional_usd * ((cost_model.fee_bps_per_side * 2.0) / 10000.0)
    slippage_usd = notional_usd * ((cost_model.slippage_bps_per_side * 2.0) / 10000.0)
    total_cost_usd = fee_usd + slippage_usd
    net_pnl_usd = gross_pnl_usd - total_cost_usd
    risk_usd = equity_usd * (strategy.risk_pct / 100.0)
    realized_r = (net_pnl_usd / risk_usd) if risk_usd else None
    hold_hours = (exit_dt - entry_dt).total_seconds() / 3600.0 if exit_dt else None
    return {
        "strategy_id": strategy.strategy_id,
        "strategy_code": strategy.strategy_code,
        "symbol": state["symbol"],
        "signal_symbol": state["signal_symbol"],
        "entry_dt": entry_dt.isoformat(),
        "exit_dt": exit_dt.isoformat() if exit_dt else None,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "stop_price": stop_price,
        "stop_pct": stop_pct,
        "tp1_price": tp1_price,
        "tp2_price": tp2_price,
        "position_notional_usd": notional_usd,
        "qty": qty,
        "gross_realized_return_pct": gross_return_pct,
        "gross_realized_pnl_usd": gross_pnl_usd,
        "cost_fee_usd": fee_usd,
        "cost_slippage_usd": slippage_usd,
        "cost_total_usd": total_cost_usd,
        "realized_pnl_usd": net_pnl_usd,
        "realized_r": realized_r,
        "best_path_return_pct": best_path_return_pct,
        "worst_path_return_pct": worst_path_return_pct,
        "hold_hours": hold_hours,
        "exit_code": exit_code,
        "tp1_taken": tp1_taken,
        "tp2_taken": tp2_taken,
        "signal": {
            "runup_24h_pct": signal["runup_24h_pct"],
            "trend_7d_pct": signal["trend_7d_pct"],
            "retrace_from_peak_pct": signal["retrace_from_peak_pct"],
            "peak_age_hours": signal["peak_age_hours"],
            "breakout_margin_pct": signal["breakout_margin_pct"],
            "lower_high_gap_pct": signal["lower_high_gap_pct"],
            "weakness_score": signal["weakness_score"],
            "oi_1h_pct": signal["oi_1h_pct"],
            "oi_4h_pct": signal["oi_4h_pct"],
            "oi_12h_pct": signal["oi_12h_pct"],
            "oi_24h_pct": signal["oi_24h_pct"],
            "oi_to_vol_ratio": signal["oi_to_vol_ratio"],
            "price_oi_divergence_4h": signal["price_oi_divergence_4h"],
        },
    }


def summarize_strategy(strategy, trades, equity_curve, starting_equity_usd):
    final_equity = equity_curve[-1]["equity_usd"] if equity_curve else starting_equity_usd
    realized_pnl_usd = final_equity - starting_equity_usd
    gross_realized_pnl_usd = sum(trade["gross_realized_pnl_usd"] for trade in trades)
    cost_fee_usd = sum(trade["cost_fee_usd"] for trade in trades)
    cost_slippage_usd = sum(trade["cost_slippage_usd"] for trade in trades)
    cost_total_usd = sum(trade["cost_total_usd"] for trade in trades)
    wins = sum(1 for trade in trades if trade["realized_pnl_usd"] > 0)
    losses = sum(1 for trade in trades if trade["realized_pnl_usd"] < 0)
    equity_peak = starting_equity_usd
    max_dd_usd = 0.0
    max_dd_pct = 0.0
    for point in equity_curve:
        equity_peak = max(equity_peak, point["equity_usd"])
        dd_usd = equity_peak - point["equity_usd"]
        dd_pct = (dd_usd / equity_peak * 100.0) if equity_peak else 0.0
        max_dd_usd = max(max_dd_usd, dd_usd)
        max_dd_pct = max(max_dd_pct, dd_pct)
    return {
        "strategy_id": strategy.strategy_id,
        "strategy_code": strategy.strategy_code,
        "starting_equity_usd": starting_equity_usd,
        "equity_usd": final_equity,
        "realized_pnl_usd": realized_pnl_usd,
        "gross_realized_pnl_usd": gross_realized_pnl_usd,
        "cost_fee_usd": cost_fee_usd,
        "cost_slippage_usd": cost_slippage_usd,
        "cost_total_usd": cost_total_usd,
        "open_count": 0,
        "closed_count": len(trades),
        "win_count": wins,
        "loss_count": losses,
        "win_rate": (wins / len(trades)) if trades else None,
        "total_realized_r": sum(trade["realized_r"] for trade in trades if trade["realized_r"] is not None),
        "gross_cap_usd": starting_equity_usd * (MAX_GROSS_PCT / 100.0),
        "equity_peak_usd": equity_peak,
        "max_drawdown_usd": max_dd_usd,
        "max_drawdown_pct": max_dd_pct,
    }


def run_pb_wave_strategy(snapshot, features, config, starting_equity_by_strategy=None):
    raw_candidates, clusters, selected_candidates, diagnostics = build_candidate_lists(features["states"])
    strategy_results = {}
    all_trades = []
    all_equity_points = []
    starting_equity_by_strategy = starting_equity_by_strategy or {}

    for strategy in config.strategies:
        starting_equity_usd = float(starting_equity_by_strategy.get(strategy.strategy_id, 10000.0))
        continuation_bundle = build_continuation_candidates(
            base_selected_candidates=selected_candidates,
            base_simulator=simulate_trade,
            strategy=strategy,
            cost_model=config.cost_model,
            min_buffer_pct=MIN_BUFFER_PCT,
        )
        combined = run_combined_strategy(
            base_selected_candidates=selected_candidates,
            continuation_candidates=continuation_bundle["selected_candidates"],
            base_simulator=simulate_trade,
            strategy=strategy,
            cost_model=config.cost_model,
            starting_equity_usd=starting_equity_usd,
            max_gross_pct=MAX_GROSS_PCT,
        )
        trades = combined["trades"]
        equity_curve = combined["equity_curve"]

        summary = summarize_strategy(strategy, trades, equity_curve, starting_equity_usd)
        summary["base_trade_count"] = combined["base_trade_count"]
        summary["continuation_trade_count"] = combined["continuation_trade_count"]
        summary["continuation_candidate_count"] = len(continuation_bundle["candidate_universe"])
        summary["continuation_selected_count"] = len(continuation_bundle["selected_candidates"])
        strategy_results[strategy.strategy_id] = {
            "config": {
                "strategy_id": strategy.strategy_id,
                "strategy_code": strategy.strategy_code,
                "risk_pct": strategy.risk_pct,
            },
            "summary": summary,
            "trades": trades,
            "equity_curve": equity_curve,
            "continuation": {
                "prototype_config_id": continuation_bundle["prototype_config_id"],
                "exit_variant_id": continuation_bundle["exit_variant_id"],
                "candidate_universe_count": len(continuation_bundle["candidate_universe"]),
                "selected_count": len(continuation_bundle["selected_candidates"]),
                "diagnostic_count": len(continuation_bundle["diagnostics"]),
                "diagnostics_preview": continuation_bundle["diagnostics"][:100],
                "candidate_preview": [
                    {
                        "symbol": row["state"]["symbol"],
                        "signal_symbol": row["state"]["signal_symbol"],
                        "family_id": row["family_id"],
                        "entry_dt": row["signal"]["entry_dt"].isoformat(),
                        "stop_pct": row["signal"]["stop_pct"],
                        "oi_to_vol_ratio": row["signal"].get("oi_to_vol_ratio"),
                    }
                    for row in continuation_bundle["selected_candidates"][:20]
                ],
            },
        }
        all_trades.extend(trades)
        all_equity_points.extend(equity_curve)

    return {
        "summary": {
            "snapshot_id": snapshot.snapshot_id,
            "captured_at_utc": snapshot.captured_at_utc.isoformat(),
            "replay_end_utc": features["replay_end_utc"],
            "symbol_count": features["symbol_count"],
            "state_count": features["state_count"],
            "warnings": features["warnings"],
            "candidate_summary": {
                "raw_base_signal_count": len(raw_candidates),
                "base_cluster_count": len(clusters),
                "base_selected_count": len(selected_candidates),
                "base_diagnostic_count": len(diagnostics),
                "continuation_candidate_count": sum(
                    payload["continuation"]["candidate_universe_count"] for payload in strategy_results.values()
                ),
                "continuation_selected_count": sum(
                    payload["continuation"]["selected_count"] for payload in strategy_results.values()
                ),
                "continuation_diagnostic_count": sum(
                    payload["continuation"]["diagnostic_count"] for payload in strategy_results.values()
                ),
            },
            "variant": {
                "entry_profile": "entry_core",
                "stop_profile": "stop_balanced",
                "exit_profile": "exit_12h_tail",
                "selection_variant": "core_cap_runup_oi_first",
                "continuation_prototype": "proto_balanced",
                "continuation_exit_variant": "profit_mode_4pct_lock20_55ema",
            },
            "diagnostics_preview": {
                "base": diagnostics[:200],
                "continuation": {
                    sid: payload["continuation"]["diagnostics_preview"]
                    for sid, payload in strategy_results.items()
                },
            },
            "strategies": {sid: payload["summary"] for sid, payload in strategy_results.items()},
        },
        "trades": {
            "snapshot_id": snapshot.snapshot_id,
            "candidate_preview": {
                "base": [
                    {
                        "symbol": item["signal"]["symbol"],
                        "signal_symbol": item["signal"]["signal_symbol"],
                        "entry_dt": item["signal"]["entry_dt"].isoformat(),
                        "stop_pct": item["signal"]["stop_pct"],
                        "runup_24h_pct": item["signal"]["runup_24h_pct"],
                        "oi_12h_pct": item["signal"]["oi_12h_pct"],
                    }
                    for item in selected_candidates[:20]
                ],
                "continuation": {
                    sid: payload["continuation"]["candidate_preview"]
                    for sid in strategy_results.keys()
                    for payload in [strategy_results[sid]]
                },
            },
            "by_strategy": {sid: payload["trades"] for sid, payload in strategy_results.items()},
            "all": all_trades,
        },
        "equity_curve": {
            "snapshot_id": snapshot.snapshot_id,
            "by_strategy": {sid: payload["equity_curve"] for sid, payload in strategy_results.items()},
            "all": sorted(all_equity_points, key=lambda row: (row["strategy_id"], row["ts"] or "")),
        },
    }
