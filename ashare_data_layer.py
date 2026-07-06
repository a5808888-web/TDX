from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Iterable


PRICE_DEVIATION_WARNING = 0.003
DELAYED_AFTER_SECONDS = 60


class AStockSource(str, Enum):
    AKSHARE = "AKShare"
    EASTMONEY = "Eastmoney"
    TUSHARE = "TuShare"


class AStockValidationStatus(str, Enum):
    REALTIME = "REALTIME"
    DATA_WARNING = "DATA_WARNING"
    DELAYED = "DELAYED"
    DATA_ERROR = "DATA_ERROR"


@dataclass(frozen=True)
class AStockPrice:
    value: float | None
    source: AStockSource
    timestamp: datetime


@dataclass(frozen=True)
class AStockKLine:
    source: AStockSource
    rows: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class EastmoneyFlow:
    sector_flow: float
    capital_flow: float
    reference_price: float | None
    timestamp: datetime
    source: AStockSource = AStockSource.EASTMONEY


@dataclass(frozen=True)
class AStockValidation:
    status: AStockValidationStatus
    price_deviation: float | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AStockData:
    symbol: str
    price: AStockPrice
    volume: float
    kline: AStockKLine
    sector_flow: float
    capital_flow: float
    validation: AStockValidation


def build_astock_data(
    symbol: str,
    price: AStockPrice,
    volume: float,
    kline: AStockKLine,
    flow: EastmoneyFlow,
    now: datetime | None = None,
) -> AStockData:
    validation = validate_astock_data_contract(symbol, price, volume, kline, flow, now=now)
    return AStockData(
        symbol=symbol,
        price=price,
        volume=volume,
        kline=kline,
        sector_flow=flow.sector_flow,
        capital_flow=flow.capital_flow,
        validation=validation,
    )


def validate_astock_data_contract(
    symbol: str,
    price: AStockPrice,
    volume: float,
    kline: AStockKLine,
    flow: EastmoneyFlow,
    now: datetime | None = None,
) -> AStockValidation:
    if not symbol.strip():
        raise ValueError("AStockData.symbol is required.")
    if price.source is not AStockSource.AKSHARE:
        raise ValueError("A股实时价格唯一来源必须是 AKShare。")
    if kline.source is not AStockSource.AKSHARE:
        raise ValueError("A股K线唯一来源必须是 AKShare。")
    if flow.source is not AStockSource.EASTMONEY:
        raise ValueError("A股资金流/板块流来源必须是 Eastmoney。")
    if price.timestamp.tzinfo is None or flow.timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware.")
    if volume < 0:
        raise ValueError("volume cannot be negative.")

    now = now or _utc_now()
    reasons: list[str] = []
    deviation = _price_deviation(price.value, flow.reference_price)
    status = AStockValidationStatus.REALTIME

    if price.value is None or price.value <= 0:
        status = AStockValidationStatus.DATA_ERROR
        reasons.append("AKShare price is missing or invalid.")
    elif now - price.timestamp > timedelta(seconds=DELAYED_AFTER_SECONDS):
        status = AStockValidationStatus.DELAYED
        reasons.append("AKShare price timestamp is delayed over 60 seconds.")
    elif deviation is not None and deviation > PRICE_DEVIATION_WARNING:
        status = AStockValidationStatus.DATA_WARNING
        reasons.append("AKShare and Eastmoney price deviation is over 0.3%.")

    if not reasons:
        reasons.append("AKShare price passed Eastmoney cross-check.")

    return AStockValidation(status=status, price_deviation=deviation, reasons=tuple(reasons))


def astock_data_to_output(item: AStockData) -> dict[str, object]:
    return {
        "AStockData": {
            "symbol": item.symbol,
            "price": {
                "value": item.price.value,
                "source": item.price.source.value,
                "timestamp": _format_time(item.price.timestamp),
            },
            "volume": item.volume,
            "kline": {
                "source": item.kline.source.value,
                "rows": item.kline.rows,
            },
            "sector_flow": {
                "value": item.sector_flow,
                "source": AStockSource.EASTMONEY.value,
            },
            "capital_flow": {
                "value": item.capital_flow,
                "source": AStockSource.EASTMONEY.value,
            },
            "validation": {
                "status": item.validation.status.value,
                "price_deviation": item.validation.price_deviation,
                "reasons": item.validation.reasons,
            },
        }
    }


def astock_list_to_output(items: Iterable[AStockData]) -> dict[str, object]:
    return {"items": tuple(astock_data_to_output(item)["AStockData"] for item in items)}


def _price_deviation(akshare_price: float | None, eastmoney_price: float | None) -> float | None:
    if akshare_price is None or akshare_price <= 0 or eastmoney_price is None or eastmoney_price <= 0:
        return None
    return abs(akshare_price - eastmoney_price) / akshare_price


def _format_time(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
