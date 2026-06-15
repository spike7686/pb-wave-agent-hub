#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

HEADERS = {"user-agent": "pb-wave-clean/1.0", "accept": "application/json"}
WORKDIR = Path(__file__).resolve().parents[1]
DATA_DIR = WORKDIR / "data" / "pb_wave_market"
LATEST_PATH = DATA_DIR / "latest.json"
LATEST_CSV_PATH = DATA_DIR / "latest.csv"
HISTORY_JSONL_PATH = DATA_DIR / "history.jsonl"
HISTORY_CSV_PATH = DATA_DIR / "history.csv"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
KLINES_DIR = DATA_DIR / "klines"
OI_DIR = DATA_DIR / "oi"
META_DIR = DATA_DIR / "meta"

KLINE_LIMIT = 240
OI_LIMIT = 240
BINANCE_PERP_QUOTES = ["USDT", "USDC"]
PERP_OI_PERIOD = "1h"
CN_TZ = timezone(timedelta(hours=8))
MIN_SOURCE_VOLUME_USD = 15_000_000
MIN_SIGNAL_VOLUME_USD = 15_000_000
KNOWN_STABLECOIN_SYMBOLS = {
    "USDT", "USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USDE", "USD1", "PYUSD", "USDD",
    "FRAX", "GHO", "RLUSD", "LUSD", "USDP", "SUSD", "EURC",
}
KNOWN_STABLECOIN_NAMES = {
    "tether", "usd coin", "binance usd", "trueusd", "first digital usd", "dai", "ethena usde",
    "world liberty financial usd", "paypal usd", "usdd", "frax", "gho", "ripple usd", "liquity usd",
    "pax dollar", "susd", "euro coin",
}
KNOWN_NON_TARGET_SYMBOLS = {"PAXG", "XAUT"}
KNOWN_NON_TARGET_NAMES = {"pax gold", "tether gold"}
KNOWN_WRAPPED_OR_STAKED_SYMBOLS = {
    "WBTC", "WETH", "WEETH", "STETH", "RETH", "METH", "CBETH", "CBBTC",
    "TBTC", "BTCB", "SOLVBTC", "EZETH", "RSETH", "OSETH",
}
EXCLUDED_NAME_KEYWORDS = {
    "wrapped bitcoin",
    "wrapped btc",
    "wrapped ether",
    "wrapped ethereum",
    "coinbase wrapped",
    "staked ether",
    "liquid staked",
    "liquid restaked",
    "restaked",
    "synthetic dollar",
    "synthetic usd",
    "gold",
}
VALID_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}$")

for path in [DATA_DIR, SNAPSHOT_DIR, KLINES_DIR, OI_DIR, META_DIR]:
    path.mkdir(parents=True, exist_ok=True)


def get_json(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def now_utc():
    return datetime.now(timezone.utc)


def safe_float(v):
    try:
        if v in (None, ""):
            return None
        return float(v)
    except Exception:
        return None


def safe_int(v):
    try:
        if v in (None, ""):
            return None
        return int(v)
    except Exception:
        return None


def is_excluded_symbol(row: dict) -> bool:
    symbol = str(row.get("symbol") or "").upper().strip()
    name = str(row.get("name") or "").strip().lower()
    if symbol in KNOWN_STABLECOIN_SYMBOLS or name in KNOWN_STABLECOIN_NAMES:
        return True
    if symbol in KNOWN_NON_TARGET_SYMBOLS or name in KNOWN_NON_TARGET_NAMES:
        return True
    if symbol in KNOWN_WRAPPED_OR_STAKED_SYMBOLS:
        return True
    if not VALID_SYMBOL_RE.fullmatch(symbol):
        return True
    for keyword in EXCLUDED_NAME_KEYWORDS:
        if keyword in name:
            return True
    return False


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})


def append_history_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})


def resolve_binance_perp_symbol(symbol: str, futures_by_symbol: dict):
    symbol = str(symbol or "").upper()
    for quote in BINANCE_PERP_QUOTES:
        exact = f"{symbol}{quote}"
        if exact in futures_by_symbol:
            return exact, futures_by_symbol[exact]
    return None, None


def fetch_binance_futures_klines(symbol_pair: str, interval: str, limit: int):
    params = urlencode({"symbol": symbol_pair, "interval": interval, "limit": limit})
    return get_json(f"https://fapi.binance.com/fapi/v1/klines?{params}")


def fetch_binance_futures_open_interest_hist(symbol_pair: str, period: str, limit: int):
    params = urlencode({"symbol": symbol_pair, "period": period, "limit": limit})
    return get_json(f"https://fapi.binance.com/futures/data/openInterestHist?{params}")


def sync_symbol_1h_klines(symbol: str, perp_symbol: str):
    payload = fetch_binance_futures_klines(perp_symbol, "1h", KLINE_LIMIT)
    rows = []
    for item in payload:
        open_dt = datetime.fromtimestamp(int(item[0]) / 1000, tz=timezone.utc)
        rows.append(
            {
                "symbol": symbol.upper(),
                "binance_perp_symbol": perp_symbol,
                "kline_source": "perp",
                "interval": "1h",
                "open_time": open_dt.isoformat(),
                "open": item[1],
                "high": item[2],
                "low": item[3],
                "close": item[4],
                "volume": item[5],
                "quote_volume": item[7],
                "trades": item[8],
            }
        )
    write_csv(
        KLINES_DIR / symbol.upper() / "1h" / "candles.csv",
        [
            "symbol",
            "binance_perp_symbol",
            "kline_source",
            "interval",
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_volume",
            "trades",
        ],
        rows,
    )
    return len(rows)


def sync_symbol_1h_oi(symbol: str, perp_symbol: str):
    payload = fetch_binance_futures_open_interest_hist(perp_symbol, PERP_OI_PERIOD, OI_LIMIT)
    rows = []
    for item in payload:
        ts = datetime.fromtimestamp(int(item["timestamp"]) / 1000, tz=timezone.utc)
        rows.append(
            {
                "symbol": symbol.upper(),
                "binance_perp_symbol": perp_symbol,
                "interval": "1h",
                "ts": ts.isoformat(),
                "sum_open_interest": item.get("sumOpenInterest"),
                "sum_open_interest_value": item.get("sumOpenInterestValue"),
            }
        )
    write_csv(
        OI_DIR / symbol.upper() / "1h" / "oi.csv",
        ["symbol", "binance_perp_symbol", "interval", "ts", "sum_open_interest", "sum_open_interest_value"],
        rows,
    )
    return len(rows)


def main():
    run_dt = now_utc()
    snapshot_id = run_dt.strftime("%Y%m%dT%H%M%SZ")
    cp = get_json("https://api.coinpaprika.com/v1/tickers")
    bn_futures = get_json("https://fapi.binance.com/fapi/v1/ticker/24hr")
    bn_futures_by_symbol = {(r.get("symbol") or "").upper(): r for r in bn_futures}

    filtered = []
    for r in cp:
        q = (r.get("quotes") or {}).get("USD") or {}
        vol = safe_float(q.get("volume_24h"))
        chg = safe_float(q.get("percent_change_24h"))
        price = safe_float(q.get("price"))
        mc = safe_float(q.get("market_cap"))
        if vol is None or chg is None or price is None:
            continue
        if vol <= MIN_SOURCE_VOLUME_USD:
            continue
        row = {
            "snapshot_id": snapshot_id,
            "captured_at_utc": run_dt.isoformat(),
            "captured_at_cst": run_dt.astimezone(CN_TZ).isoformat(),
            "id": r.get("id"),
            "name": r.get("name"),
            "symbol": (r.get("symbol") or "").upper(),
            "price_usd": price,
            "change_24h_pct": chg,
            "volume_24h_usd": vol,
            "market_cap_usd": mc,
        }
        if is_excluded_symbol(row):
            continue
        filtered.append(row)
    filtered.sort(key=lambda x: x["change_24h_pct"], reverse=True)

    final_rows = []
    for row in filtered:
        symbol = row["symbol"]
        perp_symbol, perp_match = resolve_binance_perp_symbol(symbol, bn_futures_by_symbol)
        if not perp_symbol or not perp_match:
            continue
        signal_quote_volume_usd = safe_float(perp_match.get("quoteVolume"))
        signal_trade_count_24h = safe_int(perp_match.get("count"))
        if signal_quote_volume_usd is None or signal_quote_volume_usd < MIN_SIGNAL_VOLUME_USD:
            continue
        final_rows.append(
            {
                **row,
                "status": "active",
                "top15_position": len(final_rows) + 1,
                "signal_market": "perp",
                "signal_symbol": perp_symbol,
                "binance_perp_symbol": perp_symbol,
                "binance_perp_status": "matched",
                "binance_pair": None,
                "binance_status": "optional",
                "binance_quote_volume_usd": None,
                "binance_trade_count_24h": None,
                "signal_quote_volume_usd": signal_quote_volume_usd,
                "signal_trade_count_24h": signal_trade_count_24h,
                "perp_quote_volume_24h": signal_quote_volume_usd,
                "perp_trade_count_24h": signal_trade_count_24h,
            }
        )
        if len(final_rows) >= 15:
            break

    sync_summary = []
    for row in final_rows:
        kline_rows = sync_symbol_1h_klines(row["symbol"], row["binance_perp_symbol"])
        oi_rows = sync_symbol_1h_oi(row["symbol"], row["binance_perp_symbol"])
        sync_summary.append(
            {
                "symbol": row["symbol"],
                "signal_symbol": row["signal_symbol"],
                "binance_perp_symbol": row["binance_perp_symbol"],
                "kline_source": "perp",
                "kline_rows": kline_rows,
                "oi_rows": oi_rows,
            }
        )

    fieldnames = list(final_rows[0].keys()) if final_rows else [
        "snapshot_id", "captured_at_utc", "captured_at_cst", "top15_position", "id", "name", "symbol",
        "price_usd", "change_24h_pct", "volume_24h_usd", "market_cap_usd", "status",
        "signal_market", "signal_symbol", "signal_quote_volume_usd", "signal_trade_count_24h",
        "binance_pair", "binance_status", "binance_perp_symbol", "binance_perp_status",
        "binance_quote_volume_usd", "binance_trade_count_24h", "perp_quote_volume_24h", "perp_trade_count_24h",
    ]
    write_csv(LATEST_CSV_PATH, fieldnames, final_rows)
    append_history_csv(HISTORY_CSV_PATH, fieldnames, final_rows)
    with HISTORY_JSONL_PATH.open("a", encoding="utf-8") as handle:
        for row in final_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    LATEST_PATH.write_text(json.dumps(final_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (SNAPSHOT_DIR / f"{snapshot_id}.json").write_text(json.dumps(final_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (META_DIR / "manifest.json").write_text(
        json.dumps(
            {
                "snapshot_id": snapshot_id,
                "captured_at_utc": run_dt.isoformat(),
                "top15_count": len(final_rows),
                "sync_summary": sync_summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "top15_count": len(final_rows), "sync_summary": sync_summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
