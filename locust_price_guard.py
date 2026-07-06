from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Iterable


SYNC_INTERVAL_SECONDS = 180


class MarketType(str, Enum):
    A_SHARE = "A股"
    GLOBAL = "全球"


class PriceSource(str, Enum):
    AKSHARE = "AKShare"
    FUTU = "Futu"


class PriceStatus(str, Enum):
    REALTIME = "REALTIME"
    DELAYED = "DELAYED"
    DATA_ERROR = "DATA ERROR"


@dataclass(frozen=True)
class GuardedPrice:
    value: float | None
    source: PriceSource
    timestamp: datetime


@dataclass(frozen=True)
class KLinePayload:
    timeframe: str
    rows: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class MarketData:
    symbol: str
    market_type: MarketType
    price: GuardedPrice
    volume: float
    kline: KLinePayload


class PriceGuardError(ValueError):
    pass


class PriceGuardLayer:
    def __init__(self, sync_fn: Callable[[], tuple[MarketData, ...]], interval_seconds: int = SYNC_INTERVAL_SECONDS) -> None:
        self.sync_fn = sync_fn
        self.interval_seconds = interval_seconds
        self.items: tuple[MarketData, ...] = ()
        self.last_sync_time: datetime | None = None

    def sync_once(self, now: datetime | None = None) -> tuple[MarketData, ...]:
        items = self.sync_fn()
        for item in items:
            validate_market_data(item)
        self.items = items
        self.last_sync_time = now or _utc_now()
        return self.items

    def should_sync(self, now: datetime | None = None) -> bool:
        if self.last_sync_time is None:
            return True
        return (now or _utc_now()) - self.last_sync_time >= timedelta(seconds=self.interval_seconds)


def validate_market_data(item: MarketData) -> None:
    if not item.symbol.strip():
        raise PriceGuardError("MarketData.symbol is required.")
    if item.market_type is MarketType.A_SHARE and item.price.source is not PriceSource.AKSHARE:
        raise PriceGuardError("A股价格唯一数据源必须是 AKShare。")
    if item.market_type is MarketType.GLOBAL and item.price.source is not PriceSource.FUTU:
        raise PriceGuardError("全球价格唯一数据源必须是富途 OpenAPI。")
    if item.price.timestamp.tzinfo is None:
        raise PriceGuardError("price.timestamp must be timezone-aware.")
    if item.price.value is None or item.price.value <= 0:
        raise PriceGuardError("price.value must be a positive real-time source value.")
    if item.volume < 0:
        raise PriceGuardError("volume cannot be negative.")


def price_status(price: GuardedPrice, now: datetime | None = None) -> PriceStatus:
    now = now or _utc_now()
    if price.value is None or price.value <= 0:
        return PriceStatus.DATA_ERROR
    if now - price.timestamp > timedelta(seconds=SYNC_INTERVAL_SECONDS):
        return PriceStatus.DELAYED
    return PriceStatus.REALTIME


def guarded_price_to_output(price: GuardedPrice, now: datetime | None = None) -> dict[str, object]:
    return {
        "value": price.value,
        "source": price.source.value,
        "timestamp": _format_time(price.timestamp),
        "STATUS": price_status(price, now).value,
    }


def market_data_to_output(item: MarketData, now: datetime | None = None) -> dict[str, object]:
    return {
        "MarketData": {
            "symbol": item.symbol,
            "market_type": item.market_type.value,
            "price": guarded_price_to_output(item.price, now),
            "volume": item.volume,
            "kline": {
                "timeframe": item.kline.timeframe,
                "rows": item.kline.rows,
            },
        }
    }


def market_data_list_to_output(items: Iterable[MarketData], now: datetime | None = None) -> dict[str, object]:
    return {"items": tuple(market_data_to_output(item, now)["MarketData"] for item in items)}


def _format_time(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
