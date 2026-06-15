from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from pb_wave_agent_hub.providers.binance_history import BinancePerpHistoryProvider


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})


def main():
    parser = argparse.ArgumentParser(description="Sync Binance perp 1h kline and OI history for one snapshot universe.")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--start", required=True, help="ISO timestamp")
    parser.add_argument("--end", required=True, help="ISO timestamp")
    parser.add_argument("--kline-dir", default="data/klines_1h")
    parser.add_argument("--oi-dir", default="data/oi_1h")
    args = parser.parse_args()

    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    rows = snapshot.get("rows", []) if isinstance(snapshot, dict) else snapshot
    provider = BinancePerpHistoryProvider()
    kline_dir = Path(args.kline_dir)
    oi_dir = Path(args.oi_dir)

    for row in rows:
        signal_symbol = str(row.get("signal_symbol") or row.get("binance_perp_symbol") or "").upper().strip()
        if not signal_symbol:
            continue
        klines = provider.fetch_1h_klines(signal_symbol, args.start, args.end)
        oi_rows = provider.fetch_1h_oi(signal_symbol, args.start, args.end)

        write_csv(
            kline_dir / f"{signal_symbol}.csv",
            [
                "symbol",
                "open_time_ms",
                "open_time_utc",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time_ms",
                "close_time_utc",
                "quote_volume",
                "trades",
                "taker_buy_base_volume",
                "taker_buy_quote_volume",
            ],
            klines,
        )
        write_csv(
            oi_dir / f"{signal_symbol}.csv",
            [
                "symbol",
                "ts_ms",
                "ts_utc",
                "sum_open_interest",
                "sum_open_interest_value",
            ],
            oi_rows,
        )
        print(
            json.dumps(
                {
                    "signal_symbol": signal_symbol,
                    "kline_rows": len(klines),
                    "oi_rows": len(oi_rows),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()

