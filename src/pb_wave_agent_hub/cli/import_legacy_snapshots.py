from __future__ import annotations

import argparse
import json
from pathlib import Path


def normalize_row(snapshot_id: str, captured_at_utc: str, row: dict, position: int) -> dict:
    symbol = str(row.get("symbol") or "").upper().strip()
    signal_symbol = str(
        row.get("signal_symbol")
        or row.get("binance_perp_symbol")
        or row.get("pre_matched_binance_pair")
        or ""
    ).upper().strip()
    return {
        "symbol": symbol,
        "signal_symbol": signal_symbol,
        "change_24h_pct": row.get("change_24h_pct"),
        "volume_24h_usd": row.get("volume_24h_usd"),
        "top15_position": row.get("top15_position") or position,
        "snapshot_id": snapshot_id,
        "captured_at_utc": captured_at_utc,
        "source_symbol": row.get("symbol"),
        "source_name": row.get("name"),
    }


def main():
    parser = argparse.ArgumentParser(description="Convert legacy top15 raw snapshots into replay-ready snapshot payloads.")
    parser.add_argument("--input-dir", required=True, help="Legacy raw snapshot directory.")
    parser.add_argument("--output-dir", required=True, help="Replay snapshot output directory.")
    parser.add_argument("--start-date", help="Optional UTC date filter, for example 2026-05-01")
    parser.add_argument("--end-date", help="Optional UTC date filter, for example 2026-05-31")
    parser.add_argument("--limit", type=int, default=0, help="Optional max snapshot count after filtering.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot_paths = sorted(input_dir.glob("*.json"))
    selected = []
    for path in snapshot_paths:
        day = path.stem[:8]
        if args.start_date and day < args.start_date.replace("-", ""):
            continue
        if args.end_date and day > args.end_date.replace("-", ""):
            continue
        selected.append(path)
        if args.limit and len(selected) >= args.limit:
            break

    manifest_rows = []
    for path in selected:
        raw = json.loads(path.read_text(encoding="utf-8"))
        snapshot_id = raw["snapshot_id"]
        captured_at_utc = raw["captured_at_utc"]
        source_rows = raw.get("top15") or raw.get("rows") or []
        rows = [
            normalize_row(snapshot_id, captured_at_utc, row, pos)
            for pos, row in enumerate(source_rows, start=1)
            if str(row.get("symbol") or "").strip()
        ]
        payload = {
            "snapshot_id": snapshot_id,
            "captured_at_utc": captured_at_utc,
            "rows": rows,
        }
        out = output_dir / f"{snapshot_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest_rows.append(
            {
                "snapshot_id": snapshot_id,
                "captured_at_utc": captured_at_utc,
                "row_count": len(rows),
                "path": str(out),
            }
        )
        print(json.dumps(manifest_rows[-1], ensure_ascii=False))

    manifest = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "snapshot_count": len(manifest_rows),
        "rows": manifest_rows,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(manifest_path)


if __name__ == "__main__":
    main()

