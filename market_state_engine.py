from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
from zoneinfo import ZoneInfo


CN_MARKET_TZ = ZoneInfo("Asia/Shanghai")
A_SHARE_OPEN = time(9, 30)
A_SHARE_LUNCH_START = time(11, 30)
A_SHARE_LUNCH_END = time(13, 0)
A_SHARE_CLOSE = time(15, 0)


class MarketState(str, Enum):
    LIVE = "LIVE"
    FROZEN = "FROZEN"
    STATIC = "STATIC"


@dataclass(frozen=True)
class MarketStateSnapshot:
    market: str
    state: MarketState
    trading_day: bool
    market_open: bool
    market_closed: bool
    reference_time: datetime
    data_source: str
    price_behavior: str
    fib_behavior: str
    heatmap_behavior: str
    allow_price_update: bool
    allow_new_kline: bool
    allow_ai_analysis: bool
    allow_fib_calculation: bool
    ui_label: str
    ui_note: str


def determine_a_share_market_state(
    now: datetime | None = None,
    trading_days: set[date] | None = None,
) -> MarketStateSnapshot:
    current = _to_cn_time(now or datetime.now(CN_MARKET_TZ))
    trading_day = _is_trading_day(current.date(), trading_days)
    market_open = trading_day and _is_a_share_open_time(current.time())
    market_closed = trading_day and not market_open

    if not trading_day:
        reference_time = _last_trading_day_close(current.date(), trading_days)
        return MarketStateSnapshot(
            market="A股",
            state=MarketState.STATIC,
            trading_day=False,
            market_open=False,
            market_closed=False,
            reference_time=reference_time,
            data_source="last_trading_day_close",
            price_behavior="frozen_price",
            fib_behavior="frozen_wave",
            heatmap_behavior="frozen_state",
            allow_price_update=False,
            allow_new_kline=False,
            allow_ai_analysis=True,
            allow_fib_calculation=True,
            ui_label="STATIC（非交易日）",
            ui_note="引用历史收盘数据",
        )

    if market_open:
        return MarketStateSnapshot(
            market="A股",
            state=MarketState.LIVE,
            trading_day=True,
            market_open=True,
            market_closed=False,
            reference_time=current,
            data_source="AKShare real-time",
            price_behavior="real_time_update",
            fib_behavior="real_time_recalculate",
            heatmap_behavior="real_time_update",
            allow_price_update=True,
            allow_new_kline=True,
            allow_ai_analysis=True,
            allow_fib_calculation=True,
            ui_label="LIVE（实时）",
            ui_note="交易中，价格/Fib/热力图实时更新",
        )

    reference_time = _trading_day_freeze_time(current)
    return MarketStateSnapshot(
        market="A股",
        state=MarketState.FROZEN,
        trading_day=True,
        market_open=False,
        market_closed=True,
        reference_time=reference_time,
        data_source="close_price" if current.time() >= A_SHARE_CLOSE else "latest_session_snapshot",
        price_behavior="locked_close_price",
        fib_behavior="calculation_allowed_no_price_update",
        heatmap_behavior="locked_state",
        allow_price_update=False,
        allow_new_kline=False,
        allow_ai_analysis=True,
        allow_fib_calculation=True,
        ui_label="FROZEN（收盘）" if current.time() >= A_SHARE_CLOSE else "FROZEN（盘中冻结）",
        ui_note="数据锁定，允许复盘计算但不更新价格",
    )


def market_state_to_output(snapshot: MarketStateSnapshot) -> dict[str, object]:
    return {
        "Market State": {
            "market": snapshot.market,
            "state": snapshot.state.value,
            "trading_day": snapshot.trading_day,
            "market_open": snapshot.market_open,
            "market_closed": snapshot.market_closed,
            "reference_time": _format_time(snapshot.reference_time),
            "data_source": snapshot.data_source,
            "price_behavior": snapshot.price_behavior,
            "fib_behavior": snapshot.fib_behavior,
            "heatmap_behavior": snapshot.heatmap_behavior,
            "allow_price_update": snapshot.allow_price_update,
            "allow_new_kline": snapshot.allow_new_kline,
            "allow_ai_analysis": snapshot.allow_ai_analysis,
            "allow_fib_calculation": snapshot.allow_fib_calculation,
            "ui_label": snapshot.ui_label,
            "ui_note": snapshot.ui_note,
        }
    }


def _is_a_share_open_time(value: time) -> bool:
    return A_SHARE_OPEN <= value < A_SHARE_LUNCH_START or A_SHARE_LUNCH_END <= value < A_SHARE_CLOSE


def _trading_day_freeze_time(current: datetime) -> datetime:
    if current.time() >= A_SHARE_CLOSE:
        return current.replace(hour=15, minute=0, second=0, microsecond=0)
    return current


def _last_trading_day_close(current_date: date, trading_days: set[date] | None) -> datetime:
    candidate = current_date - timedelta(days=1)
    while not _is_trading_day(candidate, trading_days):
        candidate -= timedelta(days=1)
    return datetime.combine(candidate, A_SHARE_CLOSE, tzinfo=CN_MARKET_TZ)


def _is_trading_day(value: date, trading_days: set[date] | None) -> bool:
    if trading_days is not None:
        return value in trading_days
    return value.weekday() < 5


def _to_cn_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=CN_MARKET_TZ)
    return value.astimezone(CN_MARKET_TZ)


def _format_time(value: datetime) -> str:
    return value.astimezone(CN_MARKET_TZ).strftime("%Y-%m-%d %H:%M:%S")
