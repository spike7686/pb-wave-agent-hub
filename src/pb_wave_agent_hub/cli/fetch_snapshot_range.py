from __future__ import annotations

import argparse
import json
from datetime import date
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from pb_wave_agent_hub.providers.cmc_historical import CoinMarketCapHistoricalProvider
from pb_wave_agent_hub.providers.cmc_historical import SnapshotRequest


def iter_dates(start_day: date, end_day: date):
    cursor = start_day
    while cursor <= end_day:
        yield cursor
        cursor += timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description="Fetch a range of daily leaderboard snapshots.")
    parser.add_argument("--start-date", required=True, help="UTC date, for example 2025-06-01")
    parser.add_argument("--end-date", required=True, help="UTC date, for example 2026-05-31")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--min-volume-usd", type=float, default=15_000_000.0)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    start_day = date.fromisoformat(args.start_date)
    end_day = date.fromisoformat(args.end_date)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    provider = CoinMarketCapHistoricalProvider()

    manifest_rows = []
    for day in iter_dates(start_day, end_day):
        payload = provider.fetch_snapshot_rows(
            SnapshotRequest(
                date=day.isoformat(),
                limit=args.limit,
                min_volume_usd=args.min_volume_usd,
            )
        )
        snapshot_id = payload["snapshot_id"]
        out = output_dir / f"{snapshot_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest_rows.append(
            {
                "date": day.isoformat(),
                "snapshot_id": snapshot_id,
                "captured_at_utc": payload.get("captured_at_utc"),
                "row_count": len(payload.get("rows") or []),
                "path": str(out),
            }
        )
        print(json.dumps(manifest_rows[-1], ensure_ascii=False))

    manifest = {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "start_date": args.start_date,
        "end_date": args.end_date,
        "limit": args.limit,
        "min_volume_usd": args.min_volume_usd,
        "snapshot_count": len(manifest_rows),
        "rows": manifest_rows,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(manifest_path)


if __name__ == "__main__":
    main()
