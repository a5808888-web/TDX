from __future__ import annotations

import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from local_env import load_local_env
from ai_consensus_layer import build_default_dual_ai_layer
from fibonacci_master_system import (
    FibonacciMasterInput,
    fetch_akshare_history,
    run_fibonacci_master_system,
)
from i18n import get_i18n
from market_data_connectors import AKShareMarketConnector, AShareQuery, ConnectorError
from locust_realtime_verification import (
    DataSourceTag,
    PricePayload,
    build_data_sync_status_panel,
    build_verified_stock_data,
    sync_status_to_output,
    verified_stock_to_output,
)
from locust_autonomous_ai_analysis import AutonomousAIAnalysisLayer, ModelView, ai_analysis_to_output
from fibonacci_anchor_intelligence import (
    AnchorIntelligenceInput,
    AnchorMode,
    FibonacciAnchorIntelligenceLayer,
    KLine,
    ManualAnchorInput,
    anchor_intelligence_to_output,
)
from locust_fib_hypothesis_system import (
    FibHypothesisSystemInput,
    PriceBar as HypothesisPriceBar,
    fib_hypothesis_result_to_output,
    run_fib_hypothesis_system,
)
from locust_fib_probability_validation import (
    FibProbabilityValidationInput,
    PriceBar as ProbabilityPriceBar,
    WaveSet,
    fib_probability_result_to_output,
    run_fib_probability_validation,
)
from locust_multitimeframe_fib_intelligence import (
    MultiTimeframeFibInput,
    MultiTimeframeWaveSet,
    multitimeframe_fib_result_to_output,
    run_multitimeframe_fib_intelligence,
)
from locust_full_history_fib_system import (
    FullHistoryFibInput,
    HistoryBar,
    full_history_fib_to_output,
    run_full_history_fib_system,
)
from locust_market_heatmap_system import (
    GlobalHeatmapTile,
    HeatmapTimeframe,
    MarketHeatmapInput,
    SectorHeatmapSource,
    market_heatmap_to_output,
    run_market_heatmap_system,
)
from locust_institutional_flow import (
    InstitutionObservation,
    InstitutionScope,
    institutional_flow_to_output,
    run_institutional_flow_intelligence,
)
from locust_equity_hierarchy import (
    EquityMetrics,
    SectorHierarchyInput,
    build_equity_hierarchy,
    equity_hierarchy_to_output,
)
from locust_top_core_equity_engine import (
    CoreEquityInput,
    CoreEquityType,
    run_top_core_equity_engine,
    top_core_equity_to_output,
)
from fibonacci_wave_system import SwingKind, SwingPoint, TrendDirection, WaveSegment, WaveTier
from locust_price_guard import (
    GuardedPrice,
    KLinePayload,
    MarketData,
    MarketType as GuardMarketType,
    PriceSource,
    market_data_list_to_output,
)
from market_state_engine import determine_a_share_market_state, market_state_to_output
from humanoid_robot_module import humanoid_robot_to_output, load_humanoid_robot_module
from locust_sector_framework import sector_frameworks_to_output


DEFAULT_LOCALE = "zh-CN"
load_local_env()
UI_TEXT = get_i18n(locale=DEFAULT_LOCALE)
LOCKED_MARKET_CACHE_TTL_SECONDS = 180

A_SHARE_COCKPIT_SYMBOLS = (
    "601138.SH",
    "002475.SZ",
    "000977.SZ",
    "603019.SH",
    "000938.SZ",
    "300308.SZ",
    "300502.SZ",
    "300394.SZ",
    "002281.SZ",
    "000034.SZ",
    "002261.SZ",
    "002463.SZ",
    "300476.SZ",
    "002916.SZ",
    "688183.SH",
    "603986.SH",
    "301308.SZ",
    "300223.SZ",
    "002837.SZ",
    "300499.SZ",
    "301018.SZ",
    "002518.SZ",
    "002335.SZ",
    "300693.SZ",
    "600406.SH",
    "000400.SZ",
    "002028.SZ",
    "002050.SZ",
    "601689.SH",
    "688017.SH",
    "603728.SH",
    "300580.SZ",
    "603009.SH",
    "603662.SH",
    "300124.SZ",
    "002472.SZ",
    "300660.SZ",
    "300750.SZ",
    "300274.SZ",
    "300014.SZ",
    "600673.SH",
    "601899.SH",
    "600547.SH",
    "603993.SH",
    "600276.SH",
    "603259.SH",
    "300760.SZ",
    "600519.SH",
    "000858.SZ",
    "603288.SH",
    "000333.SZ",
    "601088.SH",
    "600900.SH",
    "600036.SH",
    "601318.SH",
    "002747.SZ",
    "300024.SZ",
    "300607.SZ",
    "601127.SH",
    "002085.SZ",
    "002371.SZ",
    "000001.SZ",
    "000002.SZ",
    "000003.SZ",
)

ACCOUNT_HOLDING_NAMES = {
    "601689.SH": "拓普集团",
    "000977.SZ": "浪潮信息",
}

STOCK_NAME_OVERRIDES = {
    **ACCOUNT_HOLDING_NAMES,
    "600673.SH": "东阳光",
}

_LOCKED_MARKET_CACHE: dict[str, object] | None = None
_LOCKED_MARKET_CACHE_AT: datetime | None = None
_LOCKED_MARKET_CACHE_LOCK = threading.Lock()


class LocustDashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/api/sync-status":
            self._send_json(sync_status_to_output(_sample_sync_panel()))
            return
        if path == "/api/market-state":
            self._send_json(market_state_to_output(determine_a_share_market_state()))
            return
        if path == "/api/locked-market-data":
            self._send_json(_locked_market_data_output())
            return
        if path == "/api/one-click-trading-package":
            self._send_json(_sample_one_click_trading_package())
            return
        if path == "/api/lucky-zone-system":
            self._send_json(_sample_lucky_zone_system())
            return
        if path == "/api/dynamic-recalculation-sample":
            self._send_json(_sample_dynamic_recalculation_output())
            return
        if path == "/exports/tonghuashun_watchlist.txt":
            payload = _sample_one_click_trading_package()
            self._send_text(str(payload["同花顺导入文件"]["TXT"]), "text/plain; charset=utf-8")
            return
        if path == "/exports/tonghuashun_execution.csv":
            payload = _sample_one_click_trading_package()
            self._send_text("\ufeff" + str(payload["同花顺导入文件"]["CSV"]), "text/csv; charset=utf-8")
            return
        if path == "/api/humanoid-robot-module":
            self._send_json(_sample_humanoid_robot_module_output())
            return
        if path == "/api/sector-framework":
            self._send_json(sector_frameworks_to_output())
            return
        if path == "/api/realtime-sample":
            self._send_json({"stocks": [verified_stock_to_output(item) for item in _sample_realtime_stocks()]})
            return
        if path == "/api/ai-analysis-sample":
            self._send_json(_sample_ai_analysis_output())
            return
        if path == "/api/anchor-intelligence-sample":
            self._send_json(_sample_anchor_intelligence_output())
            return
        if path == "/api/fib-hypothesis-sample":
            self._send_json(_sample_fib_hypothesis_output())
            return
        if path == "/api/fib-probability-sample":
            self._send_json(_sample_fib_probability_output())
            return
        if path == "/api/multitimeframe-fib-sample":
            self._send_json(_sample_multitimeframe_fib_output())
            return
        if path == "/api/full-history-fib-sample":
            self._send_json(_sample_full_history_fib_output())
            return
        if path == "/api/fibonacci-master":
            self._send_json(_fibonacci_master_api_output(query))
            return
        if path == "/api/market-heatmap-sample":
            self._send_json(_sample_market_heatmap_output())
            return
        if path == "/api/institutional-flow-sample":
            self._send_json(_sample_institutional_flow_output())
            return
        if path == "/api/equity-hierarchy-sample":
            self._send_json(_sample_equity_hierarchy_output())
            return
        if path == "/api/top-core-equity-sample":
            self._send_json(_sample_top_core_equity_output())
            return
        if path == "/api/price-guard-sample":
            self._send_json(_sample_price_guard_output())
            return
        super().do_GET()

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _send_json(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, payload: str, content_type: str) -> None:
        body = payload.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), LocustDashboardHandler)
    print(f"蝗虫计划 V7 已启动：http://{host}:{port}/trading_cockpit.html")
    server.serve_forever()


def _locked_market_data_output() -> dict[str, object]:
    global _LOCKED_MARKET_CACHE, _LOCKED_MARKET_CACHE_AT

    now = datetime.now(timezone.utc)
    if _locked_market_cache_is_fresh(now):
        return _LOCKED_MARKET_CACHE

    with _LOCKED_MARKET_CACHE_LOCK:
        now = datetime.now(timezone.utc)
        if _locked_market_cache_is_fresh(now):
            return _LOCKED_MARKET_CACHE
        payload = _build_locked_market_data_payload(now)
        _LOCKED_MARKET_CACHE = payload
        _LOCKED_MARKET_CACHE_AT = now
        return payload


def _locked_market_cache_is_fresh(now: datetime) -> bool:
    return (
        _LOCKED_MARKET_CACHE is not None
        and _LOCKED_MARKET_CACHE_AT is not None
        and now - _LOCKED_MARKET_CACHE_AT < timedelta(seconds=LOCKED_MARKET_CACHE_TTL_SECONDS)
    )


def _build_locked_market_data_payload(now: datetime) -> dict[str, object]:
    state = determine_a_share_market_state()
    timestamp = state.reference_time
    queries = tuple(AShareQuery(symbol=symbol, set_code=0, trend=50.0, volatility=30.0) for symbol in A_SHARE_COCKPIT_SYMBOLS)
    snapshots: dict[str, object] = {}
    errors: dict[str, str] = {}

    try:
        snapshots, errors = AKShareMarketConnector().fetch_snapshot_map(queries)
    except ConnectorError as exc:
        errors = {symbol: str(exc) for symbol in A_SHARE_COCKPIT_SYMBOLS}

    items = {}
    for symbol in A_SHARE_COCKPIT_SYMBOLS:
        snapshot = snapshots.get(symbol)
        if snapshot is None:
            items[symbol] = _locked_market_error_item(symbol, timestamp, errors.get(symbol, "AKShare 未返回可用行情。"))
        else:
            items[symbol] = _locked_market_item(
                symbol=symbol,
                price=snapshot.price,
                volume=snapshot.volume,
                timestamp=timestamp,
                market_state=state.state.value,
            )

    return {
        "source_policy": {
            "A股": "AKShare",
            "全球": "富途开放接口",
            "price_rule": "price.value = ONLY RAW MARKET DATA",
        },
        "market_state": market_state_to_output(state)["Market State"],
        "generated_at": _format_api_time(now),
        "cache_ttl_seconds": LOCKED_MARKET_CACHE_TTL_SECONDS,
        "items": items,
    }


def _locked_market_item(
    symbol: str,
    price: float,
    volume: float,
    timestamp: datetime,
    market_state: str,
) -> dict[str, object]:
    value = round(float(price), 2)
    return {
        "symbol": symbol,
        "market_type": "A股",
        "price": {
            "value": value,
            "source": "AKShare",
            "timestamp": _format_api_time(timestamp),
            "STATUS": market_state,
            "raw_price": value,
            "api_price": value,
            "ui_price": value,
            "diff": 0,
        },
        "volume": float(volume),
        "kline": {
            "timeframe": "1D",
            "rows": ({"time": _format_api_time(timestamp), "high": value, "low": value, "close": value},),
        },
        "price_lock": "LOCKED",
    }


def _locked_market_error_item(symbol: str, timestamp: datetime, error: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "market_type": "A股",
        "price": {
            "value": None,
            "source": "AKShare",
            "timestamp": _format_api_time(timestamp),
            "STATUS": "DATA ERROR",
            "raw_price": None,
            "api_price": None,
            "ui_price": None,
            "diff": None,
            "error": error,
        },
        "volume": 0,
        "kline": {"timeframe": "1D", "rows": ()},
        "price_lock": "ERROR",
    }


def _format_api_time(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _fibonacci_master_api_output(query: dict[str, list[str]]) -> dict[str, object]:
    requested = query.get("symbols", [""])[0]
    symbols = tuple(
        item.strip().upper()
        for item in requested.split(",")
        if item.strip()
    ) or tuple(ACCOUNT_HOLDING_NAMES)
    symbols = tuple(symbol for symbol in symbols if symbol in A_SHARE_COCKPIT_SYMBOLS or symbol in ACCOUNT_HOLDING_NAMES)[:3]
    if not symbols:
        return {"system": "Fibonacci Master System", "analyses": (), "errors": {"symbols": "No supported A-share symbols requested."}}

    try:
        ai_layer = build_default_dual_ai_layer()
    except Exception:
        ai_layer = None

    locked = _locked_market_data_output()
    items = locked.get("items", {}) if isinstance(locked, dict) else {}
    analyses: list[dict[str, object]] = []
    errors: dict[str, str] = {}
    for symbol in symbols:
        try:
            price_payload = _locked_price_for_symbol(symbol, items)
            history = fetch_akshare_history(symbol)
            analyses.append(
                run_fibonacci_master_system(
                    FibonacciMasterInput(
                        stock_name=_stock_name_for_symbol(symbol),
                        symbol=symbol,
                        current_price=price_payload["value"],
                        data_source=str(price_payload.get("source") or "AKShare"),
                        updated_at=str(price_payload.get("timestamp") or _format_api_time(datetime.now(timezone.utc))),
                        history=history,
                        sector=_sector_for_symbol(symbol),
                        stock_identity=_stock_identity_for_symbol(symbol),
                        is_holding=symbol in ACCOUNT_HOLDING_NAMES,
                        holding_cost=None,
                        holding_quantity=None,
                        t1_locked=False,
                        is_core_or_lucky=_is_core_or_lucky_symbol(symbol),
                        is_trade_pool=True,
                        data_status=_fib_data_status(price_payload),
                        day_high=history[-1].high if history else None,
                        sector_heat=_sector_heat_for_symbol(symbol),
                    ),
                    ai_layer=ai_layer,
                )
            )
        except Exception as exc:
            errors[symbol] = f"{type(exc).__name__}: {exc}"

    return {
        "system": "Fibonacci Master System",
        "source_policy": "current_price and history must come from AKShare or real market connectors; AI cannot generate prices",
        "generated_at": _format_api_time(datetime.now(timezone.utc)),
        "analyses": analyses,
        "errors": errors,
    }


def _locked_price_for_symbol(symbol: str, items: object) -> dict[str, object]:
    if isinstance(items, dict):
        item = items.get(symbol)
        if isinstance(item, dict):
            price = item.get("price")
            if isinstance(price, dict) and price.get("value"):
                return price
    snapshot = AKShareMarketConnector().fetch_snapshot(AShareQuery(symbol=symbol, set_code=0, trend=50.0, volatility=30.0))
    return {
        "value": snapshot.price,
        "source": snapshot.source.value,
        "timestamp": _format_api_time(datetime.now(timezone.utc)),
    }


def _stock_name_for_symbol(symbol: str) -> str:
    return STOCK_NAME_OVERRIDES.get(symbol, symbol)


def _sector_for_symbol(symbol: str) -> str:
    if symbol == "601689.SH":
        return "人形机器人 / 具身智能"
    if symbol == "000977.SZ":
        return "AI服务器 / 算力 / AI硬件"
    if symbol == "600673.SH":
        return "电子元件 / 电容材料 / 新材料"
    return "A股交易池"


def _stock_identity_for_symbol(symbol: str) -> str:
    if symbol == "601689.SH":
        return "核心股/趋势"
    if symbol == "000977.SZ":
        return "交易池/趋势"
    if symbol == "600673.SH":
        return "朋友测算/观察"
    return "交易池"


def _is_core_or_lucky_symbol(symbol: str) -> bool:
    return symbol in {"601689.SH"}


def _sector_heat_for_symbol(symbol: str) -> float | None:
    if symbol == "601689.SH":
        return 82.0
    if symbol == "000977.SZ":
        return 86.0
    if symbol == "600673.SH":
        return 62.0
    return None


def _fib_data_status(price_payload: dict[str, object]) -> str:
    status = str(price_payload.get("STATUS") or "").upper()
    if status == "LIVE":
        return "实时"
    if status == "FROZEN":
        return "收盘冻结"
    if status == "DATA ERROR":
        return "数据失效"
    return "静态历史"


def _sample_realtime_stocks():
    now = datetime.now(timezone.utc)
    last_sync = now - timedelta(seconds=1)
    return (
        build_verified_stock_data(
            stock_name="工业富联",
            symbol="601138.SH",
            price=PricePayload(51.88, DataSourceTag.AKSHARE, now),
            last_sync_time=last_sync,
            fib_zone="BUY_ZONE",
            confluence_layers=3,
            buy_point_1=49.2,
            buy_point_2=52.6,
            stop_loss=47.9,
            take_profit=57.8,
            locust_score=84,
            risk_score=28,
            now=now,
        ),
        build_verified_stock_data(
            stock_name="NVDA",
            symbol="US.NVDA",
            price=PricePayload(194.83, DataSourceTag.FUTU, now),
            last_sync_time=last_sync,
            fib_zone="NEUTRAL_ZONE",
            confluence_layers=2,
            buy_point_1=188.4,
            buy_point_2=198.2,
            stop_loss=182.5,
            take_profit=211.5,
            locust_score=78,
            risk_score=32,
            now=now,
        ),
    )


def _sample_sync_panel():
    stocks = _sample_realtime_stocks()
    ashare_prices = tuple(item.price for item in stocks if item.price.source is DataSourceTag.AKSHARE)
    futu_prices = tuple(item.price for item in stocks if item.price.source is DataSourceTag.FUTU)
    return build_data_sync_status_panel(ashare_prices, futu_prices, ai_deepseek_ok=True)


class _SampleAIClient:
    def analyze_deepseek(self, stock, triggers):
        return ModelView("DeepSeek", "结构判断：Wave有效，Fib回撤合理，存在共振区；交易建议：等待买点确认；风险判断：未见假突破。", 82)

    def analyze_doubao(self, stock, triggers):
        return ModelView("Doubao", "情绪评分偏强，板块热点延续，资金流入，市场共识方向偏多。", 76)


def _sample_ai_analysis_output():
    layer = AutonomousAIAnalysisLayer(_SampleAIClient())
    analyses = layer.analyze_after_sync(_sample_realtime_stocks())
    return {"stocks": {symbol: ai_analysis_to_output(analysis)["AI_ANALYSIS"] for symbol, analysis in analyses.items()}}


def _sample_anchor_klines():
    return (
        KLine("2026-06-24", 42.8, 44.1, 41.9, 43.2, 930000),
        KLine("2026-06-25", 43.2, 44.0, 40.8, 42.7, 860000),
        KLine("2026-06-26", 42.7, 46.6, 42.2, 45.8, 1180000),
        KLine("2026-06-29", 45.8, 51.3, 45.1, 50.6, 1460000),
        KLine("2026-06-30", 50.6, 56.8, 49.9, 55.2, 1760000),
        KLine("2026-07-01", 55.2, 59.4, 54.3, 58.1, 1680000),
        KLine("2026-07-02", 58.1, 58.4, 54.8, 55.6, 1390000),
        KLine("2026-07-03", 55.6, 56.2, 53.6, 54.4, 1250000),
    )


def _sample_anchor_intelligence_output():
    layer = FibonacciAnchorIntelligenceLayer()
    result = layer.evaluate(
        AnchorIntelligenceInput(
            symbol="601138.SH",
            current_price=51.88,
            klines=_sample_anchor_klines(),
            mode=AnchorMode.HYBRID,
            manual_anchor=ManualAnchorInput(manual_anchor_low=40.9, manual_anchor_high=59.2),
        )
    )
    return anchor_intelligence_to_output(result)


def _sample_wave(low: float, high: float, name: str, tier: WaveTier, timeframe: str) -> WaveSegment:
    return WaveSegment(
        low=SwingPoint(low, SwingKind.LOW, "2026-06-01", timeframe, tier, True),
        high=SwingPoint(high, SwingKind.HIGH, "2026-07-01", timeframe, tier, True),
        tier=tier,
        direction=TrendDirection.UP,
        name=name,
    )


def _sample_fib_hypothesis_prices():
    return (
        HypothesisPriceBar("2026-06-20", 151.0, 149.6, 150.1),
        HypothesisPriceBar("2026-06-21", 156.0, 151.2, 155.0),
        HypothesisPriceBar("2026-06-22", 150.4, 149.5, 149.8),
        HypothesisPriceBar("2026-06-23", 149.0, 145.2, 146.0),
        HypothesisPriceBar("2026-06-24", 139.0, 137.6, 138.4),
        HypothesisPriceBar("2026-06-25", 143.0, 139.0, 142.5),
        HypothesisPriceBar("2026-06-26", 167.0, 166.1, 166.5),
        HypothesisPriceBar("2026-06-27", 164.0, 160.0, 161.0),
    )


def _sample_fib_hypothesis_output():
    result = run_fib_hypothesis_system(
        FibHypothesisSystemInput(
            main_wave=_sample_wave(100.0, 200.0, "主波段", WaveTier.PRIMARY, "1W"),
            mid_wave=_sample_wave(80.0, 220.0, "中波段", WaveTier.OPERATING, "1D"),
            small_wave=_sample_wave(120.0, 180.0, "小波段", WaveTier.EXECUTION, "60min"),
            historical_prices=_sample_fib_hypothesis_prices(),
        )
    )
    return fib_hypothesis_result_to_output(result)


def _sample_fib_probability_prices():
    return (
        ProbabilityPriceBar("2026-06-20", 150.3, 149.7, 149.9),
        ProbabilityPriceBar("2026-06-21", 156.0, 153.0, 154.0),
        ProbabilityPriceBar("2026-06-22", 150.2, 149.6, 149.8),
        ProbabilityPriceBar("2026-06-23", 155.0, 152.0, 154.2),
        ProbabilityPriceBar("2026-06-24", 150.1, 149.5, 149.7),
        ProbabilityPriceBar("2026-06-25", 149.0, 145.5, 146.0),
    )


def _sample_fib_probability_output():
    result = run_fib_probability_validation(
        FibProbabilityValidationInput(
            wave_set=WaveSet(
                primary_wave=_sample_wave(100.0, 200.0, "主波段", WaveTier.PRIMARY, "1W"),
                secondary_wave=_sample_wave(80.0, 220.0, "中波段", WaveTier.OPERATING, "1D"),
                micro_wave=_sample_wave(120.0, 180.0, "小波段", WaveTier.EXECUTION, "60min"),
            ),
            historical_prices=_sample_fib_probability_prices(),
            risk_score=28,
            trend_alignment=True,
        )
    )
    return fib_probability_result_to_output(result)


def _sample_multitimeframe_fib_output():
    result = run_multitimeframe_fib_intelligence(
        MultiTimeframeFibInput(
            symbol="601138.SH",
            current_price=150.0,
            wave_set=MultiTimeframeWaveSet(
                long_wave=_sample_wave(100.0, 200.0, "长期战略", WaveTier.PRIMARY, "1W"),
                mid_wave=_sample_wave(80.0, 220.0, "中期趋势", WaveTier.OPERATING, "1D"),
                short_wave=_sample_wave(120.0, 180.0, "短期交易", WaveTier.EXECUTION, "60min"),
                micro_wave=_sample_wave(140.0, 160.0, "执行确认", WaveTier.MICRO, "15min"),
            ),
            micro_structure_confirmed=True,
            trend_alignment=True,
        )
    )
    return multitimeframe_fib_result_to_output(result)


def _sample_full_history_fib_output():
    result = run_full_history_fib_system(
        FullHistoryFibInput(
            symbol="601138.SH",
            current_price=150.0,
            history=(
                HistoryBar("IPO-01", 80.0, 50.0, 70.0, 100.0),
                HistoryBar("IPO-02", 100.0, 60.0, 90.0, 120.0),
                HistoryBar("GROWTH-01", 200.0, 100.0, 150.0, 150.0),
                HistoryBar("GROWTH-02", 180.0, 120.0, 150.0, 180.0),
                HistoryBar("IMPULSE-01", 220.0, 80.0, 150.0, 230.0),
                HistoryBar("IMPULSE-02", 210.0, 90.0, 150.0, 260.0),
                HistoryBar("CORRECTION-01", 180.0, 120.0, 150.0, 210.0),
                HistoryBar("CORRECTION-02", 170.0, 130.0, 150.0, 190.0),
                HistoryBar("RESTART-01", 250.0, 130.0, 150.0, 260.0),
                HistoryBar("RESTART-02", 200.0, 140.0, 170.0, 310.0),
            ),
            mid_wave=_sample_wave(80.0, 220.0, "中期趋势", WaveTier.OPERATING, "1D"),
            short_wave=_sample_wave(120.0, 180.0, "短期交易", WaveTier.EXECUTION, "60min"),
            micro_wave=_sample_wave(140.0, 160.0, "微结构", WaveTier.MICRO, "15min"),
            short_stop_fall_confirmed=True,
            volume_supported=True,
        )
    )
    return full_history_fib_to_output(result)


def _sample_market_heatmap_output():
    result = run_market_heatmap_system(
        MarketHeatmapInput(
            timeframe=HeatmapTimeframe.DAYS_7,
            sectors=(
                SectorHeatmapSource("AI服务器", 3.2, 72, 0.85, 58, 92, "工业富联", ("工业富联", "浪潮信息", "中科曙光"), 65),
                SectorHeatmapSource("光通信", 2.6, 66, 0.78, 45, 90, "中际旭创", ("中际旭创", "新易盛", "天孚通信"), 74),
                SectorHeatmapSource("算力网络", 2.1, 58, 0.66, 36, 86, "中科曙光", ("中科曙光", "紫光股份", "拓维信息"), 68),
                SectorHeatmapSource("机器人", 1.5, 38, 0.52, 28, 82, "三花智控", ("三花智控", "拓普集团", "绿的谐波"), 61),
                SectorHeatmapSource("电力", 1.1, 32, 0.42, 18, 78, "国电南瑞", ("国电南瑞", "许继电气", "思源电气"), 60),
                SectorHeatmapSource("存储", 0.8, 12, 0.25, 9, 68, "兆易创新", ("兆易创新", "江波龙", "北京君正"), 56),
                SectorHeatmapSource("银行", 0.3, 15, 0.12, 8, 64, "招商银行", ("招商银行", "工商银行", "建设银行"), 53),
                SectorHeatmapSource("消费", -0.2, 4, 0.08, -3, 58, "贵州茅台", ("贵州茅台", "五粮液", "美的集团"), 51),
                SectorHeatmapSource("医药", -0.8, -8, 0.1, -8, 55, "恒瑞医药", ("恒瑞医药", "药明康德", "迈瑞医疗"), 49),
                SectorHeatmapSource("地产", -3.5, -48, 0.03, -35, 25, "低成交样本", ("地产A", "地产B"), 48),
            ),
            global_tiles=(
                GlobalHeatmapTile("半导体（美股）", 2.1, 82, "A股半导体提振", "流入"),
                GlobalHeatmapTile("AI芯片", 2.7, 88, "A股AI权重提升", "流入"),
                GlobalHeatmapTile("黄金", 1.3, 76, "有色黄金权重提升", "流入"),
                GlobalHeatmapTile("原油", -0.4, 48, "通胀扰动", "流出"),
                GlobalHeatmapTile("VIX", 0.8, 56, "风险中性", "流入"),
                GlobalHeatmapTile("美债", -0.5, 42, "估值承压", "流出"),
                GlobalHeatmapTile("纳斯达克", 1.8, 80, "成长风格修复", "流入"),
            ),
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        )
    )
    return market_heatmap_to_output(result)


def _sample_institutional_flow_output():
    result = run_institutional_flow_intelligence(
        (
            InstitutionObservation("ARK Invest", InstitutionScope.GLOBAL, 12.0, ("NVDA", "TSLA", "ROBOT ETF"), ("Cash",), "现金", "AI", 86, 92, 68, 82, "富途机构追踪"),
            InstitutionObservation("Berkshire Hathaway", InstitutionScope.GLOBAL, 5.0, ("Consumer Staples", "Healthcare"), ("High Beta Tech",), "科技", "消费", 42, 74, 86, 55, "富途机构追踪"),
            InstitutionObservation("Bridgewater", InstitutionScope.GLOBAL, -10.0, ("Gold", "Treasury"), ("Risk Assets",), "风险资产", "黄金", -66, 80, 78, 70, "富途机构追踪"),
            InstitutionObservation("北向资金", InstitutionScope.CHINA, 8.0, ("工业富联", "中际旭创"), ("地产链",), "地产", "AI硬件", 72, 84, 64, 76, "北向资金"),
            InstitutionObservation("公募基金", InstitutionScope.CHINA, 6.0, ("三花智控", "拓普集团"), ("低成交板块",), "红利", "机器人", 58, 78, 62, 68, "公募基金"),
        )
    )
    return institutional_flow_to_output(result)


def _sample_equity_hierarchy_output():
    hierarchy = build_equity_hierarchy(
        SectorHierarchyInput(
            sector_name="AI服务器 / 算力 / AI硬件",
            heat_score=86,
            locust_score=82,
            risk_score=28,
            equities=(
                EquityMetrics("工业富联", "601138.SH", "中军", 92, 88, 4, 82, 26, 1.05, 34, 92, 0.62),
                EquityMetrics("浪潮信息", "000977.SZ", "中军", 86, 78, 3, 72, 34, 0.92, 38, 76, 0.58),
                EquityMetrics("中科曙光", "603019.SH", "趋势票", 84, 80, 3, 64, 36, 1.28, 56, 70, 0.68),
                EquityMetrics("拓维信息", "002261.SZ", "补涨票", 62, 58, 2, 42, 48, 0.96, 52, 48, 0.46),
                EquityMetrics("退潮样本A", "000001.SZ", "禁买票", 24, 0, 0, 18, 92, 1.6, 86, 12, 0.2, fib_valid=False, blocked=True),
            ),
        )
    )
    return equity_hierarchy_to_output(hierarchy)


def _sample_top_core_equity_output():
    result = run_top_core_equity_engine(
        (
            CoreEquityInput("工业富联", "601138.SH", "AI服务器 / 算力 / AI硬件", CoreEquityType.LEADER, 88, 86, True, "0.382–0.618", 84, "BUY", 88, 100, funding_status="北向/公募持续流入", ai_summary="DeepSeek结构有效，豆包情绪支持"),
            CoreEquityInput("中际旭创", "300308.SZ", "光通信 / CPO / 光模块", CoreEquityType.LEADER, 91, 82, True, "buy", 82, "WAIT", 80, 98, funding_status="机构增持映射光模块", ai_summary="智能结论一致，等待回踩确认"),
            CoreEquityInput("三花智控", "002050.SZ", "人形机器人 / 具身智能", CoreEquityType.CORE_INSTITUTION, 84, 78, True, "0.382–0.618", 76, "WAIT", 78, 88, funding_status="机器人链公募调仓流入", ai_summary="产业链地位清晰，等待量产兑现"),
            CoreEquityInput("紫金矿业", "601899.SH", "有色金属 / 黄金 / 铜", CoreEquityType.CORE_INSTITUTION, 83, 76, True, "0.382–0.618", 78, "WAIT", 76, 86, funding_status="避险资金稳定流入", ai_summary="黄金强势但不追高"),
            CoreEquityInput("补涨样本", "000002.SZ", "动态新增池", CoreEquityType.LAGGING, 90, 84, True, "buy", 80, "BUY", 82, 55),
            CoreEquityInput("无Fib样本", "000003.SZ", "AI服务器 / 算力 / AI硬件", CoreEquityType.LEADER, 88, 84, True, "neutral", 42, "BUY", 81, 95),
            CoreEquityInput("情绪样本", "000004.SZ", "热门题材", CoreEquityType.LEADER, 86, 80, True, "buy", 78, "BUY", 77, 82, emotion_stock=True),
        )
    )
    return top_core_equity_to_output(result)


def _sample_one_click_trading_package() -> dict[str, object]:
    generated_at = _format_api_time(datetime.now(timezone.utc))
    leader_pool = (
        _execution_pool_row("光通信 / CPO / 光模块", "中际旭创", "300308", 1116.00, 92, 86, "核心推荐"),
        _execution_pool_row("人工智能服务器 / 算力 / 人工智能硬件", "工业富联", "601138", 64.72, 88, 84, "核心推荐"),
        _execution_pool_row("光通信 / CPO / 光模块", "新易盛", "300502", 376.20, 87, 82, "观察"),
    )
    core_pool = (
        _execution_pool_row("人形机器人 / 具身智能", "三花智控", "002050", 31.64, 82, 78, "观察"),
        _execution_pool_row("有色金属 / 黄金 / 铜", "紫金矿业", "601899", 28.60, 84, 76, "观察"),
        _execution_pool_row("电力 / 电网 / 电力设备 / 电算协同", "国电南瑞", "600406", 24.18, 80, 74, "观察"),
    )
    trend_pool = (
        _execution_pool_row("光通信 / CPO / 光模块", "天孚通信", "300394", 154.30, 82, 79, "观察"),
        _execution_pool_row("人工智能服务器 / 算力 / 人工智能硬件", "浪潮信息", "000977", 58.15, 81, 77, "观察"),
        _execution_pool_row("人形机器人 / 具身智能", "拓普集团", "601689", 73.10, 80, 75, "观察"),
    )
    buy_table = (
        _buy_point_row("中际旭创", "300308", 1116.00, 1051.48, 1073.51, "1051.48 - 1095.54", 930.20, "1218.40 / 1326.80", 86, 96, 28, "WAIT"),
        _buy_point_row("工业富联", "601138", 64.72, 60.97, 62.25, "60.97 - 63.53", 56.80, "70.65 / 76.12", 84, 92, 26, "WAIT"),
        _buy_point_row("新易盛", "300502", 376.20, 351.30, 360.40, "351.30 - 369.50", 330.20, "410.60 / 448.90", 82, 94, 32, "WAIT"),
    )
    export_rows = leader_pool + core_pool + trend_pool
    txt = "\n".join(str(item["代码"]) for item in export_rows)
    csv = _tonghuashun_csv(export_rows)
    return {
        "系统": "One-Click Trading Execution System（一键交易执行系统）",
        "生成时间": generated_at,
        "输入数据来源": ("AKShare / 东方财富", "富途开放接口", "Locust Heatmap", "机构资金流", "DeepSeek + 豆包", "Fibonacci结构系统"),
        "今日交易决策": {
            "龙头": len(leader_pool),
            "中军": len(core_pool),
            "趋势": len(trend_pool),
            "可交易": sum(1 for item in buy_table if item["是否可交易"] == "YES"),
            "风险等级": "中",
        },
        "龙头股池": leader_pool,
        "中军股池": core_pool,
        "趋势股池": trend_pool,
        "今日买点表": buy_table,
        "过滤规则": {
            "HeatScore < 80": "禁止进入龙头池和导出清单",
            "无Fib结构": "禁止输出买点",
            "无实时价格": "禁止进入导出",
            "AI未确认结构": "禁止推荐",
        },
        "同花顺导入文件": {
            "TXT": txt,
            "CSV": csv,
            "TXT路径": "/exports/tonghuashun_watchlist.txt",
            "CSV路径": "/exports/tonghuashun_execution.csv",
        },
    }


def _sample_lucky_zone_system() -> dict[str, object]:
    generated_at = _format_api_time(datetime.now(timezone.utc))
    assets = (
        _lucky_zone_row(
            "中际旭创",
            "300308",
            "光通信 / CPO / 光模块",
            "龙头",
            "爆发",
            "机构持续 / 北向流入",
            "长期0.618支撑 / 0.5中枢 / 回撤区",
            "强趋势",
            "中",
            "YES",
        ),
        _lucky_zone_row(
            "工业富联",
            "601138",
            "人工智能服务器 / 算力 / 人工智能硬件",
            "龙头",
            "加速",
            "机构持续 / 主力控盘",
            "长期0.618支撑 / 0.5中枢 / 回撤区",
            "健康趋势",
            "低",
            "YES",
        ),
        _lucky_zone_row(
            "新易盛",
            "300502",
            "光通信 / CPO / 光模块",
            "关键卡位",
            "爆发",
            "机构持续 / 北向流入",
            "长期0.618支撑 / 0.5中枢 / 回撤区",
            "强趋势",
            "中",
            "YES",
        ),
        _lucky_zone_row(
            "立讯精密",
            "002475",
            "人工智能服务器 / 算力 / 人工智能硬件",
            "核心供应链",
            "稳定",
            "资金待确认",
            "长期支撑观察 / 未到加仓区",
            "健康趋势",
            "中",
            "NO",
        ),
    )
    return {
        "系统": "Lucky Zone System（幸运区核心资产系统）",
        "生成时间": generated_at,
        "定义": "高增长 + 高确定性 + 长期复利型核心资产结构识别",
        "优先级": "Lucky Zone > 龙头 > 中军 > 趋势",
        "进入条件": (
            "行业属于人工智能 / 光通信 / 半导体核心",
            "机构持续3个月以上净流入",
            "长周期斐波那契不破0.618支撑",
            "趋势稳定上行",
            "无剧烈波动",
        ),
        "交易规则": "不频繁交易 / 只做回撤买点 / 长期持有为主 / 斐波那契作为加仓点",
        "禁止规则": ("禁止短线交易", "禁止情绪操作", "禁止高频进出"),
        "幸运区核心资产": assets,
        "结论": "只把同时满足产业地位、长期资金、斐波那契稳定和趋势连续性的股票标为YES。",
    }


def _sample_dynamic_recalculation_output() -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {
        "系统": "Dynamic Recalculation & Real-Time Refresh System（全系统动态同步更新机制）",
        "生成时间": _format_api_time(now),
        "同步频率": "交易时间每180秒；用户点击同步时立即全量重算；非交易时间使用最近收盘冻结数据继续分析",
        "市场状态": {
            "LIVE": "实时交易中：价格、热力图、买卖点、智能分析动态变化",
            "FROZEN": "收盘冻结：价格锁定为收盘价，允许继续计算斐波那契、共振和智能分析",
            "STATIC": "非交易日静态历史：引用最近交易日收盘数据，不显示为今日实时行情",
        },
        "重算流水线": (
            "A股行情数据",
            "全球行情数据",
            "A股板块热力图",
            "全球板块热力图",
            "板块HeatScore",
            "板块LocustScore",
            "板块RiskScore",
            "选股池",
            "股票分级",
            "重点候选池",
            "机构资金流向",
            "Fibonacci波段/回撤/扩展/共振区",
            "买点1/买点2/止损/止盈",
            "AI分析",
            "幸运区",
            "首页核心推荐",
            "账户执行区",
        ),
        "变化日志": (
            _change_log_row(now, "板块热力图", "光通信 / CPO", "轮动", "主线", "热度评分上升并且资金流入增强", "AKShare / 东方财富"),
            _change_log_row(now, "股票分级体系", "中际旭创", "中军股", "龙头股", "板块资金集中度提升", "AKShare / 东方财富 / 机构资金流"),
            _change_log_row(now, "斐波那契买点1", "工业富联", "60.97", "61.35", "锚点和收盘价同步后重新计算0.786回撤", "AKShare"),
            _change_log_row(now, "智能分析", "新易盛", "WAIT", "BUY", "DeepSeek结构判断与豆包情绪共振改善", "DeepSeek / 豆包"),
            _change_log_row(now, "幸运区", "立讯精密", "NO", "NO", "资金结构仍待确认，继续观察", "AKShare / 东方财富 / DeepSeek / 豆包"),
        ),
        "禁止事项": {
            "静态股票池": True,
            "静态推荐": True,
            "静态热力图": True,
            "静态Fib买点": True,
            "静态AI分析": True,
            "静态幸运区": True,
            "无更新时间": True,
            "用旧数据当新数据": True,
        },
    }


def _change_log_row(
    timestamp: datetime,
    module: str,
    target: str,
    old_status: str,
    new_status: str,
    reason: str,
    source: str,
) -> dict[str, object]:
    return {
        "时间": _format_api_time(timestamp),
        "模块": module,
        "对象": target,
        "旧状态": old_status,
        "新状态": new_status,
        "变化原因": reason,
        "数据来源": source,
    }


def _lucky_zone_row(
    stock_name: str,
    code: str,
    sector: str,
    industry_position: str,
    growth_structure: str,
    capital_structure: str,
    fib_structure: str,
    trend_structure: str,
    risk_level: str,
    entered: str,
) -> dict[str, object]:
    return {
        "股票": stock_name,
        "代码": code,
        "所属板块": sector,
        "产业地位": industry_position,
        "增长结构": growth_structure,
        "资金结构": capital_structure,
        "Fib结构": fib_structure,
        "趋势结构": trend_structure,
        "风险等级": risk_level,
        "是否进入幸运区": entered,
    }


def _execution_pool_row(
    sector: str,
    stock_name: str,
    code: str,
    price: float,
    heat_score: int,
    fib_score: int,
    status: str,
) -> dict[str, object]:
    return {
        "板块": sector,
        "股票": stock_name,
        "代码": code,
        "价格": price,
        "HeatScore": heat_score,
        "FibScore": fib_score,
        "状态": status,
    }


def _buy_point_row(
    stock_name: str,
    code: str,
    current_price: float,
    buy_point_1: float,
    buy_point_2: float,
    best_zone: str,
    stop_loss: float,
    take_profit: str,
    fib_score: int,
    locust_score: int,
    risk_score: int,
    trade_status: str,
) -> dict[str, object]:
    return {
        "股票": stock_name,
        "代码": code,
        "当前价格": current_price,
        "买点1": f"回撤0.786｜{buy_point_1:.2f}",
        "买点2": f"上升0.236｜{buy_point_2:.2f}",
        "最佳买点区间": best_zone,
        "止损": f"anchor_low 下方｜{stop_loss:.2f}",
        "止盈": take_profit,
        "FibScore": fib_score,
        "LocustScore": locust_score,
        "RiskScore": risk_score,
        "是否可交易": trade_status,
    }


def _tonghuashun_csv(rows: tuple[dict[str, object], ...]) -> str:
    header = "板块,分类,代码,名称,角色,HeatScore,FibScore"
    lines = [header]
    for item in rows:
        sector = str(item["板块"])
        category = "龙头" if int(item["HeatScore"]) > 85 else "中军" if int(item["HeatScore"]) >= 82 else "趋势"
        lines.append(f'{sector},{category},{item["代码"]},{item["股票"]},{category},{item["HeatScore"]},{item["FibScore"]}')
    return "\n".join(lines)


def _sample_price_guard_output():
    now = datetime.now(timezone.utc)
    items = (
        MarketData(
            symbol="601138.SH",
            market_type=GuardMarketType.A_SHARE,
            price=GuardedPrice(51.88, PriceSource.AKSHARE, now),
            volume=1000000,
            kline=KLinePayload("1D", ({"close": 51.88},)),
        ),
        MarketData(
            symbol="US.NVDA",
            market_type=GuardMarketType.GLOBAL,
            price=GuardedPrice(194.83, PriceSource.FUTU, now),
            volume=2000000,
            kline=KLinePayload("1D", ({"close": 194.83},)),
        ),
    )
    return market_data_list_to_output(items, now)


def _sample_humanoid_robot_module_output():
    state = determine_a_share_market_state()
    result = load_humanoid_robot_module(
        updated_at=state.reference_time.strftime("%Y-%m-%d %H:%M:%S"),
        market_state=state.ui_label,
    )
    return humanoid_robot_to_output(result)


if __name__ == "__main__":
    run(
        host=os.environ.get("LOCUST_BACKEND_HOST", "127.0.0.1"),
        port=int(os.environ.get("LOCUST_BACKEND_PORT", "8000")),
    )
