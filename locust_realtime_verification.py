from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Iterable

from market_state_engine import MarketStateSnapshot, determine_a_share_market_state, market_state_to_output


SYNC_INTERVAL_SECONDS = 180


class DataSourceTag(str, Enum):
    AKSHARE = "AKShare"
    FUTU = "Futu"
    MIXED = "Mixed"
    STALE = "Stale"


class RefreshStatus(str, Enum):
    REALTIME = "REALTIME"
    DELAYED = "DELAYED"
    STALE = "STALE"


class ConnectionState(str, Enum):
    YES = "YES"
    NO = "NO"


class OpenApiState(str, Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"


@dataclass(frozen=True)
class PricePayload:
    value: float
    source: DataSourceTag
    timestamp: datetime


@dataclass(frozen=True)
class VerifiedStockData:
    stock_name: str
    symbol: str
    price: PricePayload
    last_sync_time: datetime
    refresh_status: RefreshStatus
    data_source_tag: DataSourceTag
    fib_zone: str
    confluence_layers: int
    buy_point_1: float
    buy_point_2: float
    stop_loss: float
    take_profit: float
    locust_score: float
    risk_score: float


@dataclass(frozen=True)
class SourceSyncStatus:
    name: str
    connected: ConnectionState
    last_sync_time: datetime | None
    realtime_update: ConnectionState
    openapi_status: OpenApiState | None = None


@dataclass(frozen=True)
class AIStrategyStatus:
    codex_status: str
    deepseek_status: str


@dataclass(frozen=True)
class DataSyncStatusPanel:
    a_share: SourceSyncStatus
    global_market: SourceSyncStatus
    ai_strategy: AIStrategyStatus
    market_state: MarketStateSnapshot
    sync_interval: int
    sync_active: bool
    fib_engine_running: bool
    signal_engine_active: bool


def verify_price_refresh(
    price: PricePayload,
    last_sync_time: datetime,
    now: datetime | None = None,
    delayed_after_seconds: int = SYNC_INTERVAL_SECONDS,
) -> RefreshStatus:
    if price.value <= 0:
        raise ValueError("price.value must be positive.")
    now = now or _utc_now()
    if price.timestamp > last_sync_time:
        return RefreshStatus.REALTIME
    if now - price.timestamp <= timedelta(seconds=delayed_after_seconds):
        return RefreshStatus.DELAYED
    return RefreshStatus.STALE


def build_verified_stock_data(
    stock_name: str,
    symbol: str,
    price: PricePayload,
    last_sync_time: datetime,
    fib_zone: str,
    confluence_layers: int,
    buy_point_1: float,
    buy_point_2: float,
    stop_loss: float,
    take_profit: float,
    locust_score: float,
    risk_score: float,
    now: datetime | None = None,
) -> VerifiedStockData:
    _validate_required_stock_fields(stock_name, symbol, price)
    status = verify_price_refresh(price, last_sync_time, now=now)
    source = DataSourceTag.STALE if status is RefreshStatus.STALE else price.source
    return VerifiedStockData(
        stock_name=stock_name,
        symbol=symbol,
        price=price,
        last_sync_time=last_sync_time,
        refresh_status=status,
        data_source_tag=source,
        fib_zone=fib_zone,
        confluence_layers=confluence_layers,
        buy_point_1=round(buy_point_1, 2),
        buy_point_2=round(buy_point_2, 2),
        stop_loss=round(stop_loss, 2),
        take_profit=round(take_profit, 2),
        locust_score=locust_score,
        risk_score=risk_score,
    )


def build_data_sync_status_panel(
    a_share_prices: Iterable[PricePayload],
    global_prices: Iterable[PricePayload],
    ai_deepseek_ok: bool,
    now: datetime | None = None,
) -> DataSyncStatusPanel:
    now = now or _utc_now()
    market_state = determine_a_share_market_state(now)
    a_share_tuple = tuple(a_share_prices)
    global_tuple = tuple(global_prices)
    a_last = max((item.timestamp for item in a_share_tuple), default=None)
    g_last = max((item.timestamp for item in global_tuple), default=None)

    return DataSyncStatusPanel(
        a_share=SourceSyncStatus(
            name="A股数据状态（AKShare）",
            connected=_yes_no(bool(a_share_tuple)),
            last_sync_time=a_last,
            realtime_update=_yes_no(market_state.allow_price_update and _is_live(a_last, now)),
        ),
        global_market=SourceSyncStatus(
            name="全球数据状态（Futu）",
            connected=_yes_no(bool(global_tuple)),
            last_sync_time=g_last,
            realtime_update=_yes_no(_is_live(g_last, now)),
            openapi_status=OpenApiState.RUNNING if global_tuple else OpenApiState.STOPPED,
        ),
        ai_strategy=AIStrategyStatus(
            codex_status="RUNNING",
            deepseek_status="OK" if ai_deepseek_ok else "NO",
        ),
        market_state=market_state,
        sync_interval=SYNC_INTERVAL_SECONDS,
        sync_active=market_state.allow_price_update,
        fib_engine_running=market_state.allow_fib_calculation,
        signal_engine_active=True,
    )


class RealTimeSyncEngine:
    def __init__(self, sync_fn: Callable[[], tuple[VerifiedStockData, ...]], interval_seconds: int = SYNC_INTERVAL_SECONDS) -> None:
        self.sync_fn = sync_fn
        self.interval_seconds = interval_seconds
        self.last_sync_time: datetime | None = None
        self.items: tuple[VerifiedStockData, ...] = ()

    def sync_once(self, now: datetime | None = None) -> tuple[VerifiedStockData, ...]:
        self.items = self.sync_fn()
        self.last_sync_time = now or _utc_now()
        return self.items

    def should_sync(self, now: datetime | None = None) -> bool:
        if self.last_sync_time is None:
            return True
        return (now or _utc_now()) - self.last_sync_time >= timedelta(seconds=self.interval_seconds)


def verified_stock_to_output(item: VerifiedStockData) -> dict[str, object]:
    return {
        "股票": item.stock_name,
        "symbol": item.symbol,
        "价格（实时）": {
            "value": item.price.value,
            "source": item.price.source.value,
            "timestamp": _format_time(item.price.timestamp),
        },
        "更新时间": _format_time(item.price.timestamp),
        "数据来源": item.data_source_tag.value,
        "是否刷新": item.refresh_status.value,
        "Fib区间": item.fib_zone,
        "共振强度": item.confluence_layers,
        "买点1": item.buy_point_1,
        "买点2": item.buy_point_2,
        "止损": item.stop_loss,
        "止盈": item.take_profit,
        "LocustScore": item.locust_score,
        "RiskScore": item.risk_score,
    }


def sync_status_to_output(panel: DataSyncStatusPanel) -> dict[str, object]:
    return {
        "DATA SYNC STATUS PANEL": {
            "A股数据状态（AKShare）": _source_status_to_output(panel.a_share),
            "全球数据状态（Futu）": _source_status_to_output(panel.global_market),
            "AI策略状态": {
                "Codex运行状态": panel.ai_strategy.codex_status,
                "DeepSeek调用状态": panel.ai_strategy.deepseek_status,
            },
            "市场状态": market_state_to_output(panel.market_state)["Market State"],
            "sync_interval": panel.sync_interval,
            "System": {
                "3-minute sync active": panel.sync_active,
                "Fib engine running": panel.fib_engine_running,
                "Signal engine active": panel.signal_engine_active,
            },
        }
    }


def _source_status_to_output(status: SourceSyncStatus) -> dict[str, object]:
    output: dict[str, object] = {
        "是否连接": status.connected.value,
        "最后同步时间": _format_time(status.last_sync_time) if status.last_sync_time else None,
        "是否实时更新": status.realtime_update.value,
    }
    if status.openapi_status is not None:
        output["OpenAPI状态"] = status.openapi_status.value
    return output


def _validate_required_stock_fields(stock_name: str, symbol: str, price: PricePayload) -> None:
    if not stock_name.strip():
        raise ValueError("股票名不能为空。")
    if not symbol.strip():
        raise ValueError("symbol不能为空。")
    if price.timestamp.tzinfo is None:
        raise ValueError("price.timestamp must be timezone-aware.")
    if price.source is DataSourceTag.STALE:
        raise ValueError("price.source must identify the original data source, not Stale.")


def _is_live(timestamp: datetime | None, now: datetime) -> bool:
    if timestamp is None:
        return False
    return now - timestamp <= timedelta(seconds=SYNC_INTERVAL_SECONDS)


def _yes_no(value: bool) -> ConnectionState:
    return ConnectionState.YES if value else ConnectionState.NO


def _format_time(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
