from __future__ import annotations

import csv
import json
from datetime import timedelta
from datetime import datetime
from datetime import timezone
from pathlib import Path

from pb_wave_agent_hub.schemas import Candle1H, OI1H, Snapshot, SnapshotRow


def parse_dt(value: str) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        suffix = ""
        base = text
        if "+" in text[10:]:
            base, plus_suffix = text.rsplit("+", 1)
            suffix = f"+{plus_suffix}"
        elif "-" in text[10:]:
            base, minus_suffix = text.rsplit("-", 1)
            suffix = f"-{minus_suffix}"
        parts = base.split("T")
        if len(parts) == 2:
            date_part, time_part = parts
            time_fields = time_part.split(":")
            while len(time_fields) < 3:
                time_fields.append("00")
            time_fields = [field.zfill(2) for field in time_fields]
            repaired = f"{date_part}T{':'.join(time_fields)}{suffix}"
            parsed = datetime.fromisoformat(repaired)
        else:
            raise
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def safe_float(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


class LocalFilesProvider:
    def __init__(self, snapshot_path: Path, kline_dir: Path, oi_dir: Path):
        self.snapshot_path = snapshot_path
        self.kline_dir = kline_dir
        self.oi_dir = oi_dir

    def load_snapshot(self) -> Snapshot:
        raw = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            snapshot_id = raw["snapshot_id"]
            captured_at_utc = parse_dt(raw["captured_at_utc"])
            source_rows = raw.get("rows", [])
        else:
            if not raw:
                raise RuntimeError(f"empty snapshot payload: {self.snapshot_path}")
            snapshot_id = raw[0]["snapshot_id"]
            captured_at_utc = parse_dt(raw[0]["captured_at_utc"])
            source_rows = raw
        return Snapshot(
            snapshot_id=snapshot_id,
            captured_at_utc=captured_at_utc,
            rows=[
                SnapshotRow(
                    symbol=str(item.get("symbol") or "").upper(),
                    signal_symbol=str(item.get("signal_symbol") or item.get("binance_perp_symbol") or "").upper(),
                    change_24h_pct=safe_float(item.get("change_24h_pct")),
                    volume_24h_usd=safe_float(item.get("volume_24h_usd")),
                    top15_position=int(item["top15_position"]) if item.get("top15_position") not in (None, "") else None,
                )
                for item in source_rows
            ],
        )

    def load_klines_1h(self, signal_symbol: str) -> list[Candle1H]:
        path = self.kline_dir / f"{signal_symbol}.csv"
        rows = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                open_time_utc = parse_dt(row["open_time_utc"])
                close_time_raw = row.get("close_time_utc")
                rows.append(
                    Candle1H(
                        symbol=signal_symbol,
                        open_time_utc=open_time_utc,
                        close_time_utc=parse_dt(close_time_raw) if close_time_raw else (open_time_utc + timedelta(hours=1)),
                        open_price=float(row["open"]),
                        high_price=float(row["high"]),
                        low_price=float(row["low"]),
                        close_price=float(row["close"]),
                        volume=safe_float(row.get("volume")),
                        quote_volume=safe_float(row.get("quote_volume")),
                    )
                )
        return rows

    def load_oi_1h(self, signal_symbol: str) -> list[OI1H]:
        path = self.oi_dir / f"{signal_symbol}.csv"
        rows = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                rows.append(
                    OI1H(
                        symbol=signal_symbol,
                        ts_utc=parse_dt(row["ts_utc"]),
                        sum_open_interest=safe_float(row.get("sum_open_interest")),
                        sum_open_interest_value=safe_float(row.get("sum_open_interest_value")),
                    )
                )
        return rows
