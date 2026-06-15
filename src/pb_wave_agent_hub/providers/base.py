from __future__ import annotations

from typing import Protocol

from pb_wave_agent_hub.schemas import Candle1H, OI1H, Snapshot


class ReplayDataProvider(Protocol):
    def load_snapshot(self) -> Snapshot:
        ...

    def load_klines_1h(self, signal_symbol: str) -> list[Candle1H]:
        ...

    def load_oi_1h(self, signal_symbol: str) -> list[OI1H]:
        ...

