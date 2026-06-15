from __future__ import annotations

from bisect import bisect_right
from datetime import timedelta
import math

LOOKBACK_BARS_REQUIRED = 168
PEAK_LOOKBACK_HOURS = 16
PRE_BREAKOUT_RANGE_HOURS = 12
ATR_PERIOD = 14


def safe_float(value):
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if math.isfinite(num) else None


def pct_change(first_value, last_value):
    first = safe_float(first_value)
    last = safe_float(last_value)
    if first in (None, 0) or last is None:
        return None
    return ((last - first) / first) * 100.0


def short_return_pct(entry_price, exit_price):
    entry = safe_float(entry_price)
    exit_price = safe_float(exit_price)
    if entry in (None, 0) or exit_price is None:
        return None
    return ((entry - exit_price) / entry) * 100.0


def interval_trend_label(first_close, last_close):
    chg = pct_change(first_close, last_close)
    if chg is None:
        return "Unknown"
    if chg >= 10:
        return "StrongUp"
    if chg >= 2:
        return "Up"
    if chg <= -10:
        return "StrongDown"
    if chg <= -2:
        return "Down"
    return "Range"


def compute_ema_series(candles, period):
    if not candles:
        return []
    alpha = 2.0 / (period + 1.0)
    ema = None
    out = []
    for candle in candles:
        close_price = candle.close_price
        ema = close_price if ema is None else (close_price * alpha + ema * (1.0 - alpha))
        out.append(ema)
    return out


def compute_atr_1h_pct(candles, idx):
    if idx < ATR_PERIOD:
        return None
    window = candles[idx - ATR_PERIOD : idx + 1]
    if len(window) < ATR_PERIOD + 1:
        return None
    true_ranges = []
    prev_close = None
    for candle in window:
        high = candle.high_price
        low = candle.low_price
        if prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)
        prev_close = candle.close_price
    recent = true_ranges[-ATR_PERIOD:]
    entry_price = candles[idx].close_price
    if not recent or entry_price in (None, 0):
        return None
    atr_abs = sum(recent) / len(recent)
    return atr_abs / entry_price * 100.0


def align_oi_values(candles, oi_rows):
    if not candles:
        return []
    if not oi_rows:
        return [None] * len(candles)
    oi_times = [row.ts_utc for row in oi_rows]
    oi_values = [row.sum_open_interest_value for row in oi_rows]
    out = []
    for candle in candles:
        pos = bisect_right(oi_times, candle.close_time_utc) - 1
        out.append(oi_values[pos] if pos >= 0 else None)
    return out


def pct_change_by_steps(values, idx, steps):
    if idx < steps:
        return None
    current = safe_float(values[idx])
    previous = safe_float(values[idx - steps])
    if current is None or previous in (None, 0):
        return None
    return ((current - previous) / previous) * 100.0


def quote_volume_sum(candles):
    values = [safe_float(candle.quote_volume) for candle in candles]
    values = [value for value in values if value is not None]
    return sum(values) if values else None


def compute_state_snapshots(state):
    one_h = state["1h"]
    snapshots = [None] * len(one_h)
    for idx in range(LOOKBACK_BARS_REQUIRED, len(one_h)):
        candle = one_h[idx]
        prev = one_h[idx - 1]

        ema8 = state["ema8_1h"][idx]
        ema8_prev = state["ema8_1h"][idx - 1]
        ema21 = state["ema21_1h"][idx]
        ema21_prev = state["ema21_1h"][idx - 1]
        ema55 = state["ema55_1h"][idx]
        ema55_prev = state["ema55_1h"][idx - 1]
        if None in (ema8, ema8_prev, ema21, ema21_prev, ema55, ema55_prev):
            continue

        window_24h = one_h[idx - 23 : idx + 1]
        peak_start = max(0, idx - PEAK_LOOKBACK_HOURS)
        peak_window = one_h[peak_start:idx]
        if len(peak_window) < 8:
            continue
        peak_pos = max(range(peak_start, idx), key=lambda pos: one_h[pos].high_price)
        peak_bar = one_h[peak_pos]
        peak_age_hours = idx - peak_pos

        range_start = max(0, peak_pos - PRE_BREAKOUT_RANGE_HOURS)
        pre_breakout_window = one_h[range_start:peak_pos]
        if len(pre_breakout_window) < 6:
            continue
        pre_breakout_high = max(bar.high_price for bar in pre_breakout_window)
        breakout_margin_pct = ((peak_bar.high_price / pre_breakout_high) - 1.0) * 100.0 if pre_breakout_high else None

        post_peak_window = one_h[peak_pos + 1 : idx + 1]
        if not post_peak_window:
            continue
        post_peak_high = max(bar.high_price for bar in post_peak_window)
        lower_high_gap_pct = ((peak_bar.high_price - post_peak_high) / peak_bar.high_price) * 100.0 if peak_bar.high_price else None

        low_24h = min(bar.low_price for bar in window_24h)
        runup_24h_pct = ((peak_bar.high_price / low_24h) - 1.0) * 100.0 if low_24h else None
        trend_7d_pct = pct_change(one_h[idx - 168].close_price, candle.close_price)
        trend_7d_label = interval_trend_label(one_h[idx - 168].close_price, candle.close_price)
        trend_48h_label = interval_trend_label(one_h[idx - 48].close_price, candle.close_price)
        trend_24h_label = interval_trend_label(one_h[idx - 24].close_price, candle.close_price)
        price_change_4h_pct = pct_change(one_h[idx - 4].close_price, candle.close_price)
        retrace_from_peak_pct = ((peak_bar.high_price - candle.close_price) / peak_bar.high_price) * 100.0 if peak_bar.high_price else None

        breakout_failed = (
            peak_age_hours >= 1
            and breakout_margin_pct is not None
            and peak_bar.close_price > pre_breakout_high
            and candle.close_price < pre_breakout_high
        )
        lower_high_confirmed = (
            lower_high_gap_pct is not None
            and prev.high_price < peak_bar.high_price
            and candle.high_price < peak_bar.high_price
        )

        below_fast_ma = candle.close_price < ema8
        below_slow_ma = candle.close_price < ema21
        below_trend_ma = candle.close_price < ema55
        fast_rollover = ema8 <= ema8_prev
        slow_rollover = ema21 <= ema21_prev
        trend_rollover = ema55 <= ema55_prev
        close_below_prev_low = candle.close_price < prev.low_price
        lower_close_pair = candle.close_price < prev.close_price and prev.close_price < one_h[idx - 2].close_price
        red_bar = candle.close_price < candle.open_price
        two_bar_negative_pct = pct_change(one_h[idx - 2].close_price, candle.close_price)

        weakness_score = 0
        weakness_score += 2 if breakout_failed else 0
        weakness_score += 1 if lower_high_confirmed else 0
        weakness_score += 1 if below_fast_ma else 0
        weakness_score += 1 if below_slow_ma else 0
        weakness_score += 1 if fast_rollover else 0
        weakness_score += 1 if close_below_prev_low else 0
        weakness_score += 1 if lower_close_pair else 0
        weakness_score += 1 if red_bar else 0
        weakness_score += 1 if (two_bar_negative_pct or 999.0) <= -1.0 else 0

        atr_pct = compute_atr_1h_pct(one_h, idx)
        oi_1h_pct = pct_change_by_steps(state["oi_value_1h_aligned"], idx, 1)
        oi_4h_pct = pct_change_by_steps(state["oi_value_1h_aligned"], idx, 4)
        oi_12h_pct = pct_change_by_steps(state["oi_value_1h_aligned"], idx, 12)
        oi_24h_pct = pct_change_by_steps(state["oi_value_1h_aligned"], idx, 24)
        current_oi_value = safe_float(state["oi_value_1h_aligned"][idx])
        quote_volume_24h = quote_volume_sum(window_24h)
        oi_to_vol_ratio = current_oi_value / quote_volume_24h if current_oi_value and quote_volume_24h else None
        price_oi_divergence_4h = None
        if price_change_4h_pct is not None and oi_4h_pct is not None:
            price_oi_divergence_4h = price_change_4h_pct - oi_4h_pct

        snapshots[idx] = {
            "symbol": state["symbol"],
            "signal_symbol": state["signal_symbol"],
            "entry_dt": candle.close_time_utc,
            "entry_price": candle.close_price,
            "peak_idx": peak_pos,
            "peak_price": peak_bar.high_price,
            "peak_age_hours": peak_age_hours,
            "pre_breakout_high": pre_breakout_high,
            "breakout_margin_pct": breakout_margin_pct,
            "runup_24h_pct": runup_24h_pct,
            "trend_7d_pct": trend_7d_pct,
            "trend_7d_label": trend_7d_label,
            "trend_48h_label": trend_48h_label,
            "trend_24h_label": trend_24h_label,
            "price_change_4h_pct": price_change_4h_pct,
            "retrace_from_peak_pct": retrace_from_peak_pct,
            "lower_high_gap_pct": lower_high_gap_pct,
            "breakout_failed": breakout_failed,
            "lower_high_confirmed": lower_high_confirmed,
            "below_fast_ma": below_fast_ma,
            "below_slow_ma": below_slow_ma,
            "below_trend_ma": below_trend_ma,
            "fast_rollover": fast_rollover,
            "slow_rollover": slow_rollover,
            "trend_rollover": trend_rollover,
            "close_below_prev_low": close_below_prev_low,
            "lower_close_pair": lower_close_pair,
            "red_bar": red_bar,
            "two_bar_negative_pct": two_bar_negative_pct,
            "weakness_score": weakness_score,
            "atr_1h_pct": atr_pct,
            "oi_1h_pct": oi_1h_pct,
            "oi_4h_pct": oi_4h_pct,
            "oi_12h_pct": oi_12h_pct,
            "oi_24h_pct": oi_24h_pct,
            "oi_value_usd": current_oi_value,
            "quote_volume_24h": quote_volume_24h,
            "oi_to_vol_ratio": oi_to_vol_ratio,
            "price_oi_divergence_4h": price_oi_divergence_4h,
        }
    return snapshots


def build_symbol_state(snapshot_row, klines, oi_rows, snapshot_dt, lookback_hours, forward_hours):
    start_dt = snapshot_dt - timedelta(hours=lookback_hours)
    end_dt = snapshot_dt + timedelta(hours=forward_hours)
    candles = [candle for candle in sorted(klines, key=lambda x: x.close_time_utc) if candle.close_time_utc >= start_dt and candle.close_time_utc <= end_dt]
    oi_window = [row for row in sorted(oi_rows, key=lambda x: x.ts_utc) if row.ts_utc >= start_dt - timedelta(hours=24) and row.ts_utc <= end_dt]

    warnings = []
    if len(candles) < LOOKBACK_BARS_REQUIRED + 1:
        warnings.append(f"{snapshot_row.signal_symbol} 1h_kline_insufficient")
        return None, warnings

    oi_aligned = align_oi_values(candles, oi_window)
    aligned_count = sum(1 for value in oi_aligned if value is not None)
    if aligned_count < LOOKBACK_BARS_REQUIRED + 1:
        warnings.append(f"{snapshot_row.signal_symbol} oi_align_insufficient")
        return None, warnings

    replay_start_idx = next((idx for idx, candle in enumerate(candles) if candle.close_time_utc >= snapshot_dt), None)
    if replay_start_idx is None:
        warnings.append(f"{snapshot_row.signal_symbol} replay_start_missing")
        return None, warnings

    state = {
        "symbol": snapshot_row.symbol,
        "signal_symbol": snapshot_row.signal_symbol,
        "snapshot_rank": snapshot_row.top15_position,
        "snapshot_change_24h_pct": snapshot_row.change_24h_pct,
        "snapshot_volume_24h_usd": snapshot_row.volume_24h_usd,
        "1h": candles,
        "1h_close_times": [candle.close_time_utc for candle in candles],
        "ema8_1h": compute_ema_series(candles, 8),
        "ema21_1h": compute_ema_series(candles, 21),
        "ema55_1h": compute_ema_series(candles, 55),
        "oi_value_1h_aligned": oi_aligned,
        "replay_start_dt": snapshot_dt,
        "replay_end_dt": end_dt,
        "replay_start_idx": replay_start_idx,
    }
    state["snapshots"] = compute_state_snapshots(state)
    return state, warnings


def build_pb_wave_features(snapshot, klines_by_symbol, oi_by_symbol, config):
    warnings = []
    states = []
    for row in snapshot.rows:
        if not row.signal_symbol:
            warnings.append(f"{row.symbol} signal_symbol_missing")
            continue
        klines = klines_by_symbol.get(row.signal_symbol) or []
        oi_rows = oi_by_symbol.get(row.signal_symbol) or []
        state, state_warnings = build_symbol_state(
            snapshot_row=row,
            klines=klines,
            oi_rows=oi_rows,
            snapshot_dt=snapshot.captured_at_utc,
            lookback_hours=config.lookback_hours,
            forward_hours=config.forward_hours,
        )
        warnings.extend(state_warnings)
        if state is not None:
            states.append(state)

    replay_end_dt = snapshot.captured_at_utc + timedelta(hours=config.forward_hours)
    return {
        "snapshot_id": snapshot.snapshot_id,
        "captured_at_utc": snapshot.captured_at_utc.isoformat(),
        "replay_end_utc": replay_end_dt.isoformat(),
        "state_count": len(states),
        "symbol_count": len(snapshot.rows),
        "warnings": warnings,
        "states": states,
        "loaded_symbol_stats": {
            signal_symbol: {
                "kline_rows": len(klines_by_symbol.get(signal_symbol) or []),
                "oi_rows": len(oi_by_symbol.get(signal_symbol) or []),
            }
            for signal_symbol in sorted(set(klines_by_symbol) | set(oi_by_symbol))
        },
    }
