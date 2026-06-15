from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SnapshotRow:
    symbol: str
    signal_symbol: str
    change_24h_pct: float | None
    volume_24h_usd: float | None
    top15_position: int | None


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    captured_at_utc: datetime
    rows: list[SnapshotRow]


@dataclass(frozen=True)
class Candle1H:
    symbol: str
    open_time_utc: datetime
    close_time_utc: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float | None
    quote_volume: float | None


@dataclass(frozen=True)
class OI1H:
    symbol: str
    ts_utc: datetime
    sum_open_interest: float | None
    sum_open_interest_value: float | None
