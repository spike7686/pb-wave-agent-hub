from __future__ import annotations

from datetime import datetime, timezone

from pb_wave_agent_hub.http import request_json


BINANCE_FAPI_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
BINANCE_FAPI_OI_URL = "https://fapi.binance.com/futures/data/openInterestHist"


def to_ms(value: str) -> int:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def ms_to_iso(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


class BinancePerpHistoryProvider:
    def fetch_1h_klines(self, signal_symbol: str, start_iso: str, end_iso: str) -> list[dict]:
        start_ms = to_ms(start_iso)
        end_ms = to_ms(end_iso)
        rows = []
        cursor = start_ms
        while cursor < end_ms:
            payload = request_json(
                BINANCE_FAPI_KLINES_URL,
                headers={"Accept": "application/json", "User-Agent": "pb-wave-agent-hub/0.1.0"},
                params={
                    "symbol": signal_symbol,
                    "interval": "1h",
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": 1500,
                },
            )
            if not payload:
                break
            for item in payload:
                open_ms = int(item[0])
                rows.append(
                    {
                        "symbol": signal_symbol,
                        "open_time_ms": open_ms,
                        "open_time_utc": ms_to_iso(open_ms),
                        "open": item[1],
                        "high": item[2],
                        "low": item[3],
                        "close": item[4],
                        "volume": item[5],
                        "close_time_ms": int(item[6]),
                        "close_time_utc": ms_to_iso(int(item[6])),
                        "quote_volume": item[7],
                        "trades": item[8],
                        "taker_buy_base_volume": item[9],
                        "taker_buy_quote_volume": item[10],
                    }
                )
            last_open_ms = int(payload[-1][0])
            next_cursor = last_open_ms + 60 * 60 * 1000
            if next_cursor <= cursor:
                break
            cursor = next_cursor
        deduped = {row["open_time_ms"]: row for row in rows}
        return [deduped[k] for k in sorted(deduped)]

    def fetch_1h_oi(self, signal_symbol: str, start_iso: str, end_iso: str) -> list[dict]:
        start_ms = to_ms(start_iso)
        end_ms = to_ms(end_iso)
        rows = []
        cursor = start_ms
        while cursor < end_ms:
            payload = request_json(
                BINANCE_FAPI_OI_URL,
                headers={"Accept": "application/json", "User-Agent": "pb-wave-agent-hub/0.1.0"},
                params={
                    "symbol": signal_symbol,
                    "period": "1h",
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": 500,
                },
            )
            if not payload:
                break
            for item in payload:
                ts_ms = int(item["timestamp"])
                rows.append(
                    {
                        "symbol": signal_symbol,
                        "ts_ms": ts_ms,
                        "ts_utc": ms_to_iso(ts_ms),
                        "sum_open_interest": item.get("sumOpenInterest"),
                        "sum_open_interest_value": item.get("sumOpenInterestValue"),
                    }
                )
            last_ts_ms = int(payload[-1]["timestamp"])
            next_cursor = last_ts_ms + 60 * 60 * 1000
            if next_cursor <= cursor:
                break
            cursor = next_cursor
        deduped = {row["ts_ms"]: row for row in rows}
        return [deduped[k] for k in sorted(deduped)]

