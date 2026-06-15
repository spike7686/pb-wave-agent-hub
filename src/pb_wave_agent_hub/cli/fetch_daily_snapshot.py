from __future__ import annotations

import argparse
import json
from pathlib import Path

from pb_wave_agent_hub.providers.cmc_historical import CoinMarketCapHistoricalProvider, SnapshotRequest


def main():
    parser = argparse.ArgumentParser(description="Fetch one daily 24h leaderboard snapshot.")
    parser.add_argument("--date", required=True, help="UTC date, for example 2026-06-01")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--min-volume-usd", type=float, default=15_000_000.0)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    provider = CoinMarketCapHistoricalProvider()
    payload = provider.fetch_snapshot_rows(
        SnapshotRequest(
            date=args.date,
            limit=args.limit,
            min_volume_usd=args.min_volume_usd,
        )
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

