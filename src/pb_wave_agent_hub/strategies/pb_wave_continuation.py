from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta

from pb_wave_agent_hub.features.pb_wave import pct_change, short_return_pct


@dataclass(frozen=True)
class BreakdownEntrySpec:
    spec_id: str
    min_wait_hours_after_base_exit: float
    max_search_hours_after_base_exit: float
    impulse_lookback_hours: int
    min_impulse_drop_pct: float
    min_distance_from_anchor_peak_pct: float
    pullback_lookback_hours: int
    min_pullback_pct: float
    breakdown_lookback_hours: int
    require_ema8_below_ema21: bool
    require_ema21_below_ema55: bool
    require_rebound_into_ema21_band: bool
    require_rebound_below_ema55: bool
    max_oi_12h_pct: float | None
    min_weakness_score: int
    stop_floor_pct: float
    stop_cap_pct: float
    stop_atr_buffer_mult: float


@dataclass(frozen=True)
class ShelfVariant:
    variant_id: str
    min_rebound_pct: float
    min_anchor_gap_pct: float
    max_anchor_gap_pct: float
    shelf_min_hours: int
    shelf_max_range_pct: float
    require_ema8_flat_or_down: bool
    min_negative_close_count_last3: int
    max_oi_12h_pct: float | None


@dataclass(frozen=True)
class ProfitExitVariant:
    variant_id: str
    min_hold_hours: float
    max_hold_hours: float
    tp1_r: float
    tp1_ratio: float
    tp2_r: float
    resume_ma_period: int
    resume_confirm_bars: int
    profit_mode_trigger_pct: float | None = None
    profit_mode_resume_ma_period: int | None = None
    profit_mode_resume_confirm_bars: int | None = None
    profit_mode_lock_pct: float | None = None


@dataclass(frozen=True)
class PrototypeConfig:
    config_id: str
    use_failed_reclaim: bool
    use_shelf_break: bool
    max_oi_to_vol_ratio: float
    max_stop_pct: float
    min_impulse_or_pullback_pct: float
    require_pre12h_rebuild_nonnegative: bool
    require_pre24h_rebuild_nonnegative: bool


FAILED_RECLAIM_SPEC = BreakdownEntrySpec(
    spec_id="failed_reclaim_ema21",
    min_wait_hours_after_base_exit=6.0,
    max_search_hours_after_base_exit=168.0,
    impulse_lookback_hours=48,
    min_impulse_drop_pct=10.0,
    min_distance_from_anchor_peak_pct=9.0,
    pullback_lookback_hours=24,
    min_pullback_pct=2.5,
    breakdown_lookback_hours=8,
    require_ema8_below_ema21=True,
    require_ema21_below_ema55=True,
    require_rebound_into_ema21_band=True,
    require_rebound_below_ema55=True,
    max_oi_12h_pct=1.5,
    min_weakness_score=6,
    stop_floor_pct=4.0,
    stop_cap_pct=10.0,
    stop_atr_buffer_mult=0.35,
)

SHELF_BREAK_SPEC = ShelfVariant(
    variant_id="shelf_break_loose",
    min_rebound_pct=10.0,
    min_anchor_gap_pct=-8.0,
    max_anchor_gap_pct=6.0,
    shelf_min_hours=4,
    shelf_max_range_pct=4.5,
    require_ema8_flat_or_down=True,
    min_negative_close_count_last3=2,
    max_oi_12h_pct=3.0,
)

CONTINUATION_EXIT_VARIANT = ProfitExitVariant(
    variant_id="profit_mode_4pct_lock20_55ema",
    min_hold_hours=18.0,
    max_hold_hours=120.0,
    tp1_r=1.0,
    tp1_ratio=0.15,
    tp2_r=5.5,
    resume_ma_period=8,
    resume_confirm_bars=2,
    profit_mode_trigger_pct=4.0,
    profit_mode_resume_ma_period=55,
    profit_mode_resume_confirm_bars=2,
    profit_mode_lock_pct=2.0,
)

PROTO_BALANCED = PrototypeConfig(
    config_id="proto_balanced",
    use_failed_reclaim=True,
    use_shelf_break=True,
    max_oi_to_vol_ratio=1.00,
    max_stop_pct=6.0,
    min_impulse_or_pullback_pct=5.0,
    require_pre12h_rebuild_nonnegative=True,
    require_pre24h_rebuild_nonnegative=False,
)


def ema_value(state, period, idx):
    if period == 8:
        return state["ema8_1h"][idx]
    if period == 21:
        return state["ema21_1h"][idx]
    if period == 55:
        return state["ema55_1h"][idx]
    raise ValueError(f"unsupported ema period: {period}")


def resolve_position_notional(equity_usd, risk_pct, stop_pct, max_gross_pct):
    if stop_pct in (None, 0):
        return None
    risk_usd = equity_usd * (risk_pct / 100.0)
    gross_cap_usd = equity_usd * (max_gross_pct / 100.0)
    return min(risk_usd / (stop_pct / 100.0), gross_cap_usd)


def strength_resume_signal(state, idx, ma_period, confirm_fast_ema=True):
    selected_ema = ema_value(state, ma_period, idx)
    selected_ema_prev = ema_value(state, ma_period, idx - 1)
    candle = state["1h"][idx]
    prev = state["1h"][idx - 1]
    base_cond = (
        candle.close_price > selected_ema
        and selected_ema >= selected_ema_prev
        and candle.close_price > prev.close_price
    )
    if not confirm_fast_ema:
        return base_cond
    return base_cond and state["ema8_1h"][idx] >= state["ema8_1h"][idx - 1]


def negative_close_count(rows):
    return sum(1 for row in rows if row.close_price < row.open_price)


def rebound_touches_ema21(state, start_idx, rel_high_idx, rebound_high):
    ema21 = state["ema21_1h"][start_idx + rel_high_idx]
    if ema21 in (None, 0):
        return False
    return rebound_high >= ema21 * 0.992


def build_base_trade_infos(selected_candidates, base_simulator, strategy, cost_model):
    infos = []
    for item in selected_candidates:
        trade = base_simulator(item["state"], item["index"], item["signal"], 10000.0, strategy, cost_model)
        if not trade or not trade.get("exit_dt"):
            continue
        infos.append(
            {
                "state": item["state"],
                "index": item["index"],
                "signal": item["signal"],
                "trade": trade,
                "anchor_peak_price": item["signal"]["peak_price"],
                "base_entry_dt": item["signal"]["entry_dt"],
                "base_exit_dt": datetime.fromisoformat(trade["exit_dt"]),
            }
        )
    return infos


def generate_breakdown_candidates(base_trade_infos, entry_spec, min_buffer_pct):
    infos_by_symbol = {}
    for info in base_trade_infos:
        infos_by_symbol.setdefault(info["state"]["symbol"], []).append(info)
    for rows in infos_by_symbol.values():
        rows.sort(key=lambda item: item["base_entry_dt"])

    candidates = []
    for rows in infos_by_symbol.values():
        state = rows[0]["state"]
        one_h = state["1h"]
        close_times = state["1h_close_times"]
        for pos, anchor in enumerate(rows):
            search_start_dt = anchor["base_exit_dt"] + timedelta(hours=entry_spec.min_wait_hours_after_base_exit)
            search_end_dt = anchor["base_exit_dt"] + timedelta(hours=entry_spec.max_search_hours_after_base_exit)
            if pos + 1 < len(rows):
                next_base_dt = rows[pos + 1]["base_entry_dt"]
                search_end_dt = min(search_end_dt, next_base_dt - timedelta(hours=1))
            start_idx = bisect_left(close_times, search_start_dt)
            end_idx = bisect_left(close_times, search_end_dt)
            anchor_peak_price = anchor["anchor_peak_price"]
            anchor_idx_floor = anchor["index"] + 1

            for j in range(max(start_idx, anchor_idx_floor + 4), min(end_idx + 1, len(one_h))):
                snap = state["snapshots"][j]
                if snap is None:
                    continue
                bar = one_h[j]
                if entry_spec.require_ema8_below_ema21 and not (state["ema8_1h"][j] < state["ema21_1h"][j]):
                    continue
                if entry_spec.require_ema21_below_ema55 and not (state["ema21_1h"][j] < state["ema55_1h"][j]):
                    continue
                if snap.get("weakness_score") is None or snap["weakness_score"] < entry_spec.min_weakness_score:
                    continue

                distance_from_anchor_peak_pct = ((anchor_peak_price - bar.close_price) / anchor_peak_price) * 100.0 if anchor_peak_price else None
                if distance_from_anchor_peak_pct is None or distance_from_anchor_peak_pct < entry_spec.min_distance_from_anchor_peak_pct:
                    continue

                impulse_start = max(anchor_idx_floor, j - entry_spec.impulse_lookback_hours)
                impulse_window = one_h[impulse_start:j]
                if len(impulse_window) < 8:
                    continue
                impulse_high = max(row.high_price for row in impulse_window)
                impulse_low = min(row.low_price for row in impulse_window)
                impulse_drop_pct = ((impulse_high - impulse_low) / impulse_high) * 100.0 if impulse_high else None
                if impulse_drop_pct is None or impulse_drop_pct < entry_spec.min_impulse_drop_pct:
                    continue

                pullback_start = max(impulse_start + 2, j - entry_spec.pullback_lookback_hours)
                pullback_window = one_h[pullback_start:j]
                if len(pullback_window) < 5:
                    continue
                rel_high_idx = max(range(len(pullback_window)), key=lambda k: pullback_window[k].high_price)
                if rel_high_idx < 1 or rel_high_idx >= len(pullback_window) - 1:
                    continue
                rebound_high = pullback_window[rel_high_idx].high_price
                recent_low_before_rebound = min(row.low_price for row in pullback_window[: rel_high_idx + 1])
                if recent_low_before_rebound in (None, 0):
                    continue
                pullback_pct = ((rebound_high / recent_low_before_rebound) - 1.0) * 100.0
                if pullback_pct < entry_spec.min_pullback_pct:
                    continue

                if entry_spec.require_rebound_into_ema21_band and not rebound_touches_ema21(state, pullback_start, rel_high_idx, rebound_high):
                    continue
                if entry_spec.require_rebound_below_ema55:
                    ema55_rebound = state["ema55_1h"][pullback_start + rel_high_idx]
                    if ema55_rebound is None or rebound_high >= ema55_rebound * 1.003:
                        continue

                floor_start = max(pullback_start, j - entry_spec.breakdown_lookback_hours)
                prior_floor = min(row.low_price for row in one_h[floor_start:j])
                if bar.close_price >= prior_floor or not snap.get("close_below_prev_low"):
                    continue

                oi_12h = snap.get("oi_12h_pct")
                if entry_spec.max_oi_12h_pct is not None and (oi_12h is None or oi_12h > entry_spec.max_oi_12h_pct):
                    continue

                atr_pct = snap.get("atr_1h_pct")
                stop_buffer_pct = max(min_buffer_pct, (atr_pct or 0.0) * entry_spec.stop_atr_buffer_mult)
                raw_stop_price = rebound_high * (1.0 + stop_buffer_pct / 100.0)
                raw_stop_pct = ((raw_stop_price / bar.close_price) - 1.0) * 100.0 if bar.close_price else None
                if raw_stop_pct is None:
                    continue
                effective_stop_pct = max(entry_spec.stop_floor_pct, raw_stop_pct)
                if effective_stop_pct > entry_spec.stop_cap_pct:
                    continue
                stop_price = raw_stop_price if raw_stop_pct >= entry_spec.stop_floor_pct else bar.close_price * (1.0 + effective_stop_pct / 100.0)

                candidates.append(
                    {
                        "kind": "continuation",
                        "family_id": "breakdown_failed_reclaim",
                        "state": state,
                        "index": j,
                        "signal": {
                            **snap,
                            "entry_dt": snap["entry_dt"],
                            "entry_price": snap["entry_price"],
                            "stop_pct": effective_stop_pct,
                            "stop_price": stop_price,
                            "distance_from_anchor_peak_pct": distance_from_anchor_peak_pct,
                            "impulse_drop_pct": impulse_drop_pct,
                            "pullback_pct": pullback_pct,
                            "prior_floor": prior_floor,
                            "rebound_high": rebound_high,
                            "base_anchor_entry_dt": anchor["base_entry_dt"].isoformat(),
                            "base_anchor_exit_dt": anchor["base_exit_dt"].isoformat(),
                        },
                    }
                )
                break
    candidates.sort(key=lambda item: item["signal"]["entry_dt"])
    return candidates


def generate_shelf_candidates(base_trade_infos, variant, min_buffer_pct):
    infos_by_symbol = {}
    for info in base_trade_infos:
        infos_by_symbol.setdefault(info["state"]["symbol"], []).append(info)
    for rows in infos_by_symbol.values():
        rows.sort(key=lambda item: item["base_entry_dt"])

    candidates = []
    for rows in infos_by_symbol.values():
        state = rows[0]["state"]
        one_h = state["1h"]
        close_times = state["1h_close_times"]
        for pos, anchor in enumerate(rows):
            search_start_dt = anchor["base_exit_dt"] + timedelta(hours=12)
            search_end_dt = anchor["base_exit_dt"] + timedelta(hours=14 * 24)
            if pos + 1 < len(rows):
                next_base_dt = rows[pos + 1]["base_entry_dt"]
                search_end_dt = min(search_end_dt, next_base_dt - timedelta(hours=1))
            start_idx = bisect_left(close_times, search_start_dt)
            end_idx = bisect_left(close_times, search_end_dt)
            anchor_peak = anchor["anchor_peak_price"]
            anchor_floor_idx = anchor["index"] + 1

            for j in range(max(start_idx, anchor_floor_idx + 10), min(end_idx + 1, len(one_h))):
                snap = state["snapshots"][j]
                if snap is None or snap.get("weakness_score") is None or snap["weakness_score"] < 7 or not snap.get("close_below_prev_low"):
                    continue
                if variant.max_oi_12h_pct is not None:
                    oi12 = snap.get("oi_12h_pct")
                    if oi12 is None or oi12 > variant.max_oi_12h_pct:
                        continue

                win_start = max(anchor_floor_idx, j - 96)
                win = one_h[win_start:j]
                if len(win) < 12:
                    continue
                rel_high_idx = max(range(len(win)), key=lambda k: win[k].high_price)
                rebound_high_bar = win[rel_high_idx]
                rebound_abs_idx = win_start + rel_high_idx
                low_before = min(r.low_price for r in one_h[win_start:rebound_abs_idx + 1])
                if low_before in (None, 0):
                    continue
                rebound_pct = ((rebound_high_bar.high_price / low_before) - 1.0) * 100.0
                anchor_gap_pct = ((anchor_peak - rebound_high_bar.high_price) / anchor_peak) * 100.0 if anchor_peak else None
                if rebound_pct < variant.min_rebound_pct:
                    continue
                if anchor_gap_pct is None or not (variant.min_anchor_gap_pct <= anchor_gap_pct <= variant.max_anchor_gap_pct):
                    continue

                shelf_start = max(rebound_abs_idx + 1, j - variant.shelf_min_hours)
                shelf = one_h[shelf_start:j]
                if len(shelf) < variant.shelf_min_hours:
                    continue
                shelf_high = max(r.high_price for r in shelf)
                shelf_low = min(r.low_price for r in shelf)
                shelf_range_pct = ((shelf_high - shelf_low) / shelf_high) * 100.0 if shelf_high else None
                if shelf_range_pct is None or shelf_range_pct > variant.shelf_max_range_pct:
                    continue
                if one_h[j].close_price >= shelf_low:
                    continue
                if negative_close_count(one_h[max(j - 3, 0):j]) < variant.min_negative_close_count_last3:
                    continue
                if variant.require_ema8_flat_or_down and state["ema8_1h"][j] > state["ema8_1h"][j - 1]:
                    continue

                atr_pct = snap.get("atr_1h_pct")
                stop_buffer_pct = max(min_buffer_pct, (atr_pct or 0.0) * 0.45)
                raw_stop_price = shelf_high * (1.0 + stop_buffer_pct / 100.0)
                raw_stop_pct = ((raw_stop_price / one_h[j].close_price) - 1.0) * 100.0 if one_h[j].close_price else None
                if raw_stop_pct is None:
                    continue
                stop_pct = max(4.5, raw_stop_pct)
                if stop_pct > 12.0:
                    continue
                stop_price = raw_stop_price if raw_stop_pct >= 4.5 else one_h[j].close_price * (1.0 + stop_pct / 100.0)

                candidates.append(
                    {
                        "kind": "continuation",
                        "family_id": "rebuild_shelf_break",
                        "state": state,
                        "index": j,
                        "signal": {
                            **snap,
                            "entry_dt": snap["entry_dt"],
                            "entry_price": snap["entry_price"],
                            "stop_pct": stop_pct,
                            "stop_price": stop_price,
                            "rebound_pct": rebound_pct,
                            "anchor_gap_pct": anchor_gap_pct,
                            "shelf_high": shelf_high,
                            "shelf_low": shelf_low,
                            "shelf_range_pct": shelf_range_pct,
                            "base_anchor_entry_dt": anchor["base_entry_dt"].isoformat(),
                            "base_anchor_exit_dt": anchor["base_exit_dt"].isoformat(),
                        },
                    }
                )
                break
    candidates.sort(key=lambda item: item["signal"]["entry_dt"])
    return candidates


def candidate_features(candidate):
    state = candidate["state"]
    j = candidate["index"]
    sig = candidate["signal"]
    rows = state["1h"]
    prev12 = rows[max(0, j - 12):j]
    prev24 = rows[max(0, j - 24):j]
    pre12_close_change = pct_change(prev12[0].close_price, prev12[-1].close_price) if len(prev12) >= 2 else None
    pre24_close_change = pct_change(prev24[0].close_price, prev24[-1].close_price) if len(prev24) >= 2 else None
    impulse_or_pullback = None
    for key in ["pullback_pct", "impulse_drop_pct", "rebound_pct"]:
        if sig.get(key) is not None:
            impulse_or_pullback = max(impulse_or_pullback or -999999.0, sig.get(key))
    return {
        "oi_to_vol_ratio": sig.get("oi_to_vol_ratio"),
        "stop_pct": sig.get("stop_pct"),
        "pre12h_close_change_pct": pre12_close_change,
        "pre24h_close_change_pct": pre24_close_change,
        "impulse_or_pullback_pct": impulse_or_pullback,
    }


def build_candidate_universe(base_trade_infos, min_buffer_pct):
    raw = []
    raw.extend(generate_breakdown_candidates(base_trade_infos, FAILED_RECLAIM_SPEC, min_buffer_pct))
    raw.extend(generate_shelf_candidates(base_trade_infos, SHELF_BREAK_SPEC, min_buffer_pct))
    deduped = {}
    priority = {"breakdown_failed_reclaim": 1, "rebuild_shelf_break": 2}
    for item in sorted(raw, key=lambda x: (x["signal"]["entry_dt"], priority[x["family_id"]])):
        key = (item["state"]["symbol"], item["signal"]["entry_dt"].isoformat())
        cur = deduped.get(key)
        if cur is None or priority[item["family_id"]] < priority[cur["family_id"]]:
            deduped[key] = item
    return list(sorted(deduped.values(), key=lambda x: x["signal"]["entry_dt"]))


def filter_candidates(candidates, config):
    filtered = []
    diagnostics = []
    for item in candidates:
        family = item["family_id"]
        if family == "breakdown_failed_reclaim" and not config.use_failed_reclaim:
            continue
        if family == "rebuild_shelf_break" and not config.use_shelf_break:
            continue

        feat = candidate_features(item)
        blockers = []
        if feat["oi_to_vol_ratio"] is None or feat["oi_to_vol_ratio"] > config.max_oi_to_vol_ratio:
            blockers.append("oi_to_vol_ratio")
        if feat["stop_pct"] is None or feat["stop_pct"] > config.max_stop_pct:
            blockers.append("stop_pct")
        if feat["impulse_or_pullback_pct"] is None or feat["impulse_or_pullback_pct"] < config.min_impulse_or_pullback_pct:
            blockers.append("impulse_or_pullback")
        if config.require_pre12h_rebuild_nonnegative and (feat["pre12h_close_change_pct"] is None or feat["pre12h_close_change_pct"] < 0):
            blockers.append("pre12h_rebuild")
        if config.require_pre24h_rebuild_nonnegative and (feat["pre24h_close_change_pct"] is None or feat["pre24h_close_change_pct"] < 0):
            blockers.append("pre24h_rebuild")
        if blockers:
            diagnostics.append(
                {
                    "symbol": item["state"]["symbol"],
                    "signal_symbol": item["state"]["signal_symbol"],
                    "family_id": family,
                    "entry_dt": item["signal"]["entry_dt"].isoformat(),
                    "decision": "blocked_continuation_filter",
                    "blockers": blockers,
                }
            )
            continue
        diagnostics.append(
            {
                "symbol": item["state"]["symbol"],
                "signal_symbol": item["state"]["signal_symbol"],
                "family_id": family,
                "entry_dt": item["signal"]["entry_dt"].isoformat(),
                "decision": "selected_continuation",
                "blockers": [],
            }
        )
        filtered.append(item)
    return filtered, diagnostics


def simulate_trade_profit_mode(state, entry_idx, signal, equity_usd, strategy, cost_model, variant, max_gross_pct):
    candles = state["1h"]
    entry_price = signal["entry_price"]
    stop_price = signal["stop_price"]
    stop_pct = signal["stop_pct"]
    entry_dt = signal["entry_dt"]
    notional_usd = resolve_position_notional(equity_usd, strategy.risk_pct, stop_pct, max_gross_pct)
    if notional_usd in (None, 0):
        return None

    qty = notional_usd / entry_price if entry_price else None
    risk_abs = stop_price - entry_price
    tp1_price = entry_price - risk_abs * variant.tp1_r
    tp2_price = entry_price - risk_abs * variant.tp2_r
    min_hold_dt = entry_dt + timedelta(hours=variant.min_hold_hours)
    end_dt = entry_dt + timedelta(hours=variant.max_hold_hours)

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
    profit_mode_active = False
    profit_mode_activated_at = None

    for j in range(entry_idx + 1, len(candles)):
        bar = candles[j]
        if bar.close_time_utc > end_dt:
            break

        best_bar_return = short_return_pct(entry_price, bar.low_price)
        close_return = short_return_pct(entry_price, bar.close_price)
        worst_bar_return = short_return_pct(entry_price, bar.high_price)
        if best_bar_return is not None:
            best_path_return_pct = best_bar_return if best_path_return_pct is None else max(best_path_return_pct, best_bar_return)
        if worst_bar_return is not None:
            worst_path_return_pct = worst_bar_return if worst_path_return_pct is None else min(worst_path_return_pct, worst_bar_return)

        if (
            variant.profit_mode_trigger_pct is not None
            and not profit_mode_active
            and best_path_return_pct is not None
            and best_path_return_pct >= variant.profit_mode_trigger_pct
        ):
            profit_mode_active = True
            profit_mode_activated_at = bar.close_time_utc.isoformat()
            if variant.profit_mode_lock_pct is not None:
                lock_price = entry_price * (1.0 - variant.profit_mode_lock_pct / 100.0)
                stop_price_live = min(stop_price_live, lock_price)

        if bar.high_price >= stop_price_live:
            stop_return = short_return_pct(entry_price, stop_price_live)
            gross_return_pct += remaining_weight * (stop_return or 0.0)
            remaining_weight = 0.0
            exit_code = "stop_after_tp1" if tp1_taken else "stop_loss"
            if profit_mode_active and (stop_return or 0.0) > 0:
                exit_code = "profit_lock_after_tp1" if tp1_taken else "profit_lock"
            exit_dt = bar.close_time_utc
            exit_price = stop_price_live
            break

        if not tp1_taken and bar.low_price <= tp1_price and remaining_weight > 0:
            ratio = min(variant.tp1_ratio, remaining_weight)
            gross_return_pct += ratio * (stop_pct * variant.tp1_r)
            remaining_weight -= ratio
            tp1_taken = True
            stop_price_live = min(stop_price_live, entry_price)

        if tp1_taken and not tp2_taken and bar.low_price <= tp2_price and remaining_weight > 0:
            gross_return_pct += remaining_weight * (stop_pct * variant.tp2_r)
            remaining_weight = 0.0
            tp2_taken = True
            exit_code = "take_profit_tail"
            exit_dt = bar.close_time_utc
            exit_price = tp2_price
            break

        if bar.close_time_utc >= min_hold_dt:
            if profit_mode_active:
                ma_period = variant.profit_mode_resume_ma_period or variant.resume_ma_period
                confirm_bars = variant.profit_mode_resume_confirm_bars or variant.resume_confirm_bars
            else:
                ma_period = variant.resume_ma_period
                confirm_bars = variant.resume_confirm_bars
            resumed_now = strength_resume_signal(state, j, ma_period)
            resume_hits = resume_hits + 1 if resumed_now else 0
            if resume_hits >= confirm_bars:
                gross_return_pct += remaining_weight * (close_return or 0.0)
                remaining_weight = 0.0
                exit_code = "profit_mode_resume_after_tp1" if (profit_mode_active and tp1_taken) else (
                    "profit_mode_resume" if profit_mode_active else ("strength_resume_after_tp1" if tp1_taken else "strength_resume")
                )
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
    profit_capture_ratio = None
    if best_path_return_pct not in (None, 0):
        profit_capture_ratio = gross_return_pct / best_path_return_pct
    return {
        "strategy_id": strategy.strategy_id,
        "strategy_code": strategy.strategy_code,
        "entry_kind": "continuation",
        "family_id": signal.get("family_id"),
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
        "profit_capture_ratio": profit_capture_ratio,
        "hold_hours": (exit_dt - entry_dt).total_seconds() / 3600.0 if exit_dt else None,
        "exit_code": exit_code,
        "tp1_taken": tp1_taken,
        "tp2_taken": tp2_taken,
        "profit_mode_active": profit_mode_active,
        "profit_mode_activated_at": profit_mode_activated_at,
        "signal": {
            "runup_24h_pct": signal.get("runup_24h_pct"),
            "trend_7d_pct": signal.get("trend_7d_pct"),
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
            "base_anchor_entry_dt": signal.get("base_anchor_entry_dt"),
            "base_anchor_exit_dt": signal.get("base_anchor_exit_dt"),
            "distance_from_anchor_peak_pct": signal.get("distance_from_anchor_peak_pct"),
            "impulse_drop_pct": signal.get("impulse_drop_pct"),
            "pullback_pct": signal.get("pullback_pct"),
            "rebound_pct": signal.get("rebound_pct"),
            "anchor_gap_pct": signal.get("anchor_gap_pct"),
        },
    }


def build_continuation_candidates(base_selected_candidates, base_simulator, strategy, cost_model, min_buffer_pct):
    base_trade_infos = build_base_trade_infos(
        selected_candidates=base_selected_candidates,
        base_simulator=base_simulator,
        strategy=strategy,
        cost_model=cost_model,
    )
    candidate_universe = build_candidate_universe(base_trade_infos, min_buffer_pct=min_buffer_pct)
    filtered_candidates, diagnostics = filter_candidates(candidate_universe, PROTO_BALANCED)
    return {
        "base_trade_infos": base_trade_infos,
        "candidate_universe": candidate_universe,
        "selected_candidates": filtered_candidates,
        "diagnostics": diagnostics,
        "prototype_config_id": PROTO_BALANCED.config_id,
        "exit_variant_id": CONTINUATION_EXIT_VARIANT.variant_id,
    }


def run_combined_strategy(
    base_selected_candidates,
    continuation_candidates,
    base_simulator,
    strategy,
    cost_model,
    starting_equity_usd,
    max_gross_pct,
):
    events = []
    for item in base_selected_candidates:
        events.append(
            {
                "kind": "base",
                "state": item["state"],
                "index": item["index"],
                "signal": item["signal"],
            }
        )
    for item in continuation_candidates:
        enriched_signal = dict(item["signal"])
        enriched_signal["family_id"] = item["family_id"]
        events.append(
            {
                "kind": "continuation",
                "family_id": item["family_id"],
                "state": item["state"],
                "index": item["index"],
                "signal": enriched_signal,
            }
        )
    events.sort(key=lambda row: row["signal"]["entry_dt"])

    equity_usd = starting_equity_usd
    open_until = None
    trades = []
    equity_curve = []

    for event in events:
        sig_dt = event["signal"]["entry_dt"]
        if open_until and sig_dt < open_until:
            continue
        if event["kind"] == "base":
            trade = base_simulator(
                event["state"],
                event["index"],
                event["signal"],
                equity_usd,
                strategy,
                cost_model,
            )
            if not trade:
                continue
            trade["entry_kind"] = "base"
            trade["family_id"] = "base_failure_swing"
        else:
            trade = simulate_trade_profit_mode(
                event["state"],
                event["index"],
                event["signal"],
                equity_usd,
                strategy,
                cost_model,
                CONTINUATION_EXIT_VARIANT,
                max_gross_pct,
            )
            if not trade:
                continue
        trades.append(trade)
        equity_usd += trade["realized_pnl_usd"]
        open_until = datetime.fromisoformat(trade["exit_dt"]) if trade.get("exit_dt") else sig_dt
        equity_curve.append(
            {
                "strategy_id": strategy.strategy_id,
                "strategy_code": strategy.strategy_code,
                "ts": trade.get("exit_dt"),
                "equity_usd": equity_usd,
                "starting_equity_usd": starting_equity_usd,
                "symbol": trade["symbol"],
                "pnl_usd": trade["realized_pnl_usd"],
                "entry_kind": trade.get("entry_kind"),
                "family_id": trade.get("family_id"),
            }
        )

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "ending_equity_usd": equity_usd,
        "base_trade_count": sum(1 for trade in trades if trade.get("entry_kind") == "base"),
        "continuation_trade_count": sum(1 for trade in trades if trade.get("entry_kind") == "continuation"),
    }
