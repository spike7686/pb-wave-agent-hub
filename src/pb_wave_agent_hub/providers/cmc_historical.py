from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from pb_wave_agent_hub.http import request_json


CMC_HISTORICAL_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/historical"
BINANCE_FUTURES_24H_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"
BINANCE_PERP_QUOTES = ("USDT", "USDC")


def safe_float(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def safe_int(value):
    try:
        if value in (None, ""):
            return None
        return int(value)
    except Exception:
        return None


def utc_iso_date(value: str) -> str:
    if "T" in value:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    return value


@dataclass(frozen=True)
class SnapshotRequest:
    date: str
    limit: int = 15
    min_volume_usd: float = 15_000_000.0
    sort: str = "percent_change_24h"
    sort_dir: str = "desc"
    convert: str = "USD"


def resolve_binance_perp_symbol(symbol: str, futures_by_symbol: dict[str, dict]) -> tuple[str | None, dict | None]:
    base = str(symbol or "").upper().strip()
    for quote in BINANCE_PERP_QUOTES:
        candidate = f"{base}{quote}"
        if candidate in futures_by_symbol:
            return candidate, futures_by_symbol[candidate]
    return None, None


class CoinMarketCapHistoricalProvider:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("CMC_PRO_API_KEY")
        if not self.api_key:
            raise RuntimeError("CMC_PRO_API_KEY is required for CoinMarketCap historical snapshots")

    def fetch_snapshot_rows(self, request: SnapshotRequest) -> dict:
        raw = request_json(
            CMC_HISTORICAL_URL,
            headers={
                "Accept": "application/json",
                "X-CMC_PRO_API_KEY": self.api_key,
                "User-Agent": "pb-wave-agent-hub/0.1.0",
            },
            params={
                "date": utc_iso_date(request.date),
                "start": 1,
                "limit": 5000,
                "convert": request.convert,
                "sort": request.sort,
                "sort_dir": request.sort_dir,
            },
        )
        futures = request_json(
            BINANCE_FUTURES_24H_URL,
            headers={"Accept": "application/json", "User-Agent": "pb-wave-agent-hub/0.1.0"},
        )
        futures_by_symbol = {(item.get("symbol") or "").upper(): item for item in futures}

        rows = []
        for item in raw.get("data", []) or []:
            quote = ((item.get("quote") or {}).get(request.convert) or {})
            symbol = str(item.get("symbol") or "").upper()
            change_24h = safe_float(quote.get("percent_change_24h"))
            volume_24h = safe_float(quote.get("volume_24h"))
            price_usd = safe_float(quote.get("price"))
            market_cap_usd = safe_float(quote.get("market_cap"))
            if change_24h is None or volume_24h is None or price_usd is None:
                continue
            if volume_24h < request.min_volume_usd:
                continue
            signal_symbol, futures_row = resolve_binance_perp_symbol(symbol, futures_by_symbol)
            if not signal_symbol or not futures_row:
                continue
            rows.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "symbol": symbol,
                    "signal_market": "perp",
                    "signal_symbol": signal_symbol,
                    "binance_perp_symbol": signal_symbol,
                    "binance_perp_status": "matched",
                    "change_24h_pct": change_24h,
                    "volume_24h_usd": volume_24h,
                    "price_usd": price_usd,
                    "market_cap_usd": market_cap_usd,
                    "signal_quote_volume_usd": safe_float(futures_row.get("quoteVolume")),
                    "signal_trade_count_24h": safe_int(futures_row.get("count")),
                    "perp_quote_volume_24h": safe_float(futures_row.get("quoteVolume")),
                    "perp_trade_count_24h": safe_int(futures_row.get("count")),
                }
            )
            if len(rows) >= request.limit:
                break

        captured_at_utc = f"{utc_iso_date(request.date)}T23:59:59+00:00"
        snapshot_id = datetime.fromisoformat(captured_at_utc).strftime("%Y%m%dT%H%M%SZ")
        for idx, row in enumerate(rows, start=1):
            row["top15_position"] = idx
            row["snapshot_id"] = snapshot_id
            row["captured_at_utc"] = captured_at_utc

        return {
            "snapshot_id": snapshot_id,
            "captured_at_utc": captured_at_utc,
            "source": {
                "provider": "coinmarketcap_historical",
                "date": utc_iso_date(request.date),
                "sort": request.sort,
                "sort_dir": request.sort_dir,
                "min_volume_usd": request.min_volume_usd,
                "captured_at_inference": "Historical daily listings are end-of-day UTC snapshots per CMC docs.",
            },
            "rows": rows,
        }

