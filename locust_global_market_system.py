from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from fibonacci_wave_system import SwingKind, WaveSegment
from locust_wave_fib_heatmap import (
    ConfluenceZone,
    FibMatrix,
    LevelKind,
    LocustWaveFibHeatmapInput,
    PriceReference,
    build_heatmap_fib_matrix,
    identify_confirmed_wave,
    run_wave_fib_confluence_heatmap,
)


class MarketType(str, Enum):
    A_SHARE = "A股"
    US = "US"
    HK = "HK"
    GLOBAL_ETF = "GLOBAL_ETF"


class DataSource(str, Enum):
    AKSHARE = "akshare"
    EASTMONEY = "eastmoney"
    FUTU_OPENAPI = "futu_openapi"
    MCP_FUTU = "mcp_futu"


class Decision(str, Enum):
    BUY = "BUY"
    WAIT = "WAIT"
    AVOID = "AVOID"


class LocustRegime(str, Enum):
    MAIN_UPTREND = "主升"
    TREND = "趋势"
    RANGE = "震荡"
    EBB = "退潮"


class RiskRegime(str, Enum):
    SAFE = "安全"
    NORMAL = "正常"
    RISK = "风险"
    FORBIDDEN = "禁止交易"


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    market_type: MarketType
    source: DataSource
    price: float
    volume: float
    trend: float
    volatility: float
    locust_score: float | None = None
    risk_score: float | None = None


@dataclass(frozen=True)
class MarketObject:
    symbol: str
    market_type: MarketType
    price: float
    volume: float
    trend: float
    fib_structure: FibMatrix
    confluence_score: float
    locust_score: float
    risk_score: float
    data_source: DataSource


@dataclass(frozen=True)
class GlobalRiskContext:
    vix: float
    soxx_trend: float
    qqq_trend: float
    gold_trend: float
    sector_ebb_score: float


@dataclass(frozen=True)
class TradeDecision:
    symbol: str
    market_type: MarketType
    decision: Decision
    final_score: float
    risk_score: float
    fib_zone: str
    confluence: str
    buy_points: tuple[float, ...]
    stop_loss: float
    take_profit: float
    tradable: bool
    price: float
    anchor_low: float
    anchor_high: float
    data_source: DataSource
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class UnifiedMarketResult:
    a_share_top: tuple[TradeDecision, ...]
    us_top: tuple[TradeDecision, ...]
    hk_top: tuple[TradeDecision, ...]
    unified_rank: tuple[TradeDecision, ...]
    risk_regime: RiskRegime


class AShareAKShareAdapter:
    source = DataSource.AKSHARE

    def normalize_snapshot(self, snapshot: MarketSnapshot) -> MarketSnapshot:
        validate_data_source(snapshot.market_type, snapshot.source)
        return snapshot


class FutuOpenApiAdapter:
    source = DataSource.FUTU_OPENAPI

    def normalize_snapshot(self, snapshot: MarketSnapshot) -> MarketSnapshot:
        validate_data_source(snapshot.market_type, snapshot.source)
        return snapshot


class FutuMcpAdapter:
    source = DataSource.MCP_FUTU

    def normalize_snapshot(self, snapshot: MarketSnapshot) -> MarketSnapshot:
        validate_data_source(snapshot.market_type, snapshot.source)
        return snapshot


def validate_data_source(market_type: MarketType, source: DataSource) -> None:
    if market_type is MarketType.A_SHARE and source is not DataSource.AKSHARE:
        raise ValueError("A股行情数据源只能使用 AKShare，禁止其他来源覆盖。")
    if market_type in {MarketType.US, MarketType.HK, MarketType.GLOBAL_ETF} and source not in {
        DataSource.FUTU_OPENAPI,
        DataSource.MCP_FUTU,
    }:
        raise ValueError("全球市场数据源只能使用 Futu OpenAPI 或 Futu MCP 桥接层。")


def build_market_object(
    snapshot: MarketSnapshot,
    waves: tuple[WaveSegment, ...],
    moving_averages: tuple[PriceReference, ...] = (),
    prior_levels: tuple[PriceReference, ...] = (),
    global_risk_context: GlobalRiskContext | None = None,
) -> MarketObject:
    validate_data_source(snapshot.market_type, snapshot.source)
    if snapshot.price <= 0:
        raise ValueError("price is required and must be positive.")
    if not waves:
        raise ValueError("At least one confirmed wave is required.")

    locust_score = snapshot.locust_score
    if locust_score is None:
        locust_score = calculate_locust_score(snapshot)
    risk_score = snapshot.risk_score
    if risk_score is None:
        risk_score = calculate_risk_score(snapshot, global_risk_context)

    heatmap = run_wave_fib_confluence_heatmap(
        LocustWaveFibHeatmapInput(
            waves=waves,
            current_price=snapshot.price,
            locust_score=locust_score,
            risk_score=risk_score,
            moving_averages=moving_averages,
            prior_levels=prior_levels,
        )
    )
    fib_structure = heatmap.fib_matrices[0]
    confluence_score = score_confluence(heatmap.confluence_zones, snapshot.price)

    return MarketObject(
        symbol=snapshot.symbol,
        market_type=snapshot.market_type,
        price=snapshot.price,
        volume=snapshot.volume,
        trend=snapshot.trend,
        fib_structure=fib_structure,
        confluence_score=confluence_score,
        locust_score=locust_score,
        risk_score=risk_score,
        data_source=snapshot.source,
    )


def calculate_locust_score(snapshot: MarketSnapshot) -> float:
    if snapshot.market_type is MarketType.A_SHARE:
        if snapshot.locust_score is None:
            raise ValueError("A股 LocustScore 必须来自 Eastmoney 资金流。")
        return snapshot.locust_score
    volume_score = min(snapshot.volume / 1_000_000, 100)
    trend_score = snapshot.trend
    volatility_score = max(0, 100 - snapshot.volatility)
    return _clamp(volume_score * 0.35 + trend_score * 0.45 + volatility_score * 0.2)


def classify_locust_score(score: float) -> LocustRegime:
    if score > 80:
        return LocustRegime.MAIN_UPTREND
    if score >= 60:
        return LocustRegime.TREND
    if score >= 40:
        return LocustRegime.RANGE
    return LocustRegime.EBB


def calculate_risk_score(snapshot: MarketSnapshot, context: GlobalRiskContext | None = None) -> float:
    base = snapshot.risk_score if snapshot.risk_score is not None else snapshot.volatility
    if context is None:
        return _clamp(base)
    vix_score = min(context.vix * 2.2, 100)
    tech_pressure = max(0, 100 - ((context.soxx_trend + context.qqq_trend) / 2))
    gold_pressure = max(0, context.gold_trend - 50)
    return _clamp(base * 0.25 + vix_score * 0.3 + tech_pressure * 0.25 + gold_pressure * 0.1 + context.sector_ebb_score * 0.1)


def classify_risk_score(score: float) -> RiskRegime:
    if score < 30:
        return RiskRegime.SAFE
    if score < 60:
        return RiskRegime.NORMAL
    if score <= 80:
        return RiskRegime.RISK
    return RiskRegime.FORBIDDEN


def score_fib_structure(matrix: FibMatrix) -> float:
    if matrix.current_position == "golden_retracement":
        return 100.0
    if matrix.current_position in {"shallow_pullback", "deep_pullback"}:
        return 70.0
    if matrix.current_position == "above_anchor_high":
        return 55.0
    return 20.0


def score_confluence(zones: Iterable[ConfluenceZone], current_price: float) -> float:
    best = 0.0
    for zone in zones:
        midpoint = (zone.zone_low + zone.zone_high) / 2
        padding = midpoint * 0.003
        if not (zone.zone_low - padding <= current_price <= zone.zone_high + padding):
            continue
        if zone.overlap_count >= 4:
            best = max(best, 100.0)
        elif zone.overlap_count == 3:
            best = max(best, 80.0)
        elif zone.overlap_count == 2:
            best = max(best, 55.0)
    return best


def final_score(obj: MarketObject) -> float:
    return (
        0.4 * score_fib_structure(obj.fib_structure)
        + 0.3 * obj.locust_score
        + 0.2 * obj.trend
        - 0.1 * obj.risk_score
    )


def decide_market_object(obj: MarketObject) -> TradeDecision:
    score = final_score(obj)
    fib_zone = fib_zone_label(obj.fib_structure)
    buy_points = calculate_buy_points(obj.fib_structure)
    stop_loss = round(obj.fib_structure.anchor_low * 0.985, 3)
    take_profit = round(obj.fib_structure.anchor_high + obj.fib_structure.range * 0.272, 3)
    tradable = obj.risk_score <= 80 and obj.confluence_score >= 55
    reasons: list[str] = []

    if obj.risk_score > 80:
        decision = Decision.AVOID
        reasons.append("RiskScore > 80，禁止交易")
        tradable = False
    elif obj.confluence_score < 55:
        decision = Decision.AVOID
        reasons.append("无有效共振，禁止无共振直接买入")
        tradable = False
    elif score >= 70 and obj.locust_score >= 60:
        decision = Decision.BUY
        reasons.append("Fib结构、资金与趋势共振")
    elif score >= 45:
        decision = Decision.WAIT
        reasons.append("结构存在，等待更优买点")
    else:
        decision = Decision.AVOID
        reasons.append("综合评分不足")
        tradable = False

    return TradeDecision(
        symbol=obj.symbol,
        market_type=obj.market_type,
        decision=decision,
        final_score=round(score, 3),
        risk_score=obj.risk_score,
        fib_zone=fib_zone,
        confluence=confluence_label(obj.confluence_score),
        buy_points=buy_points,
        stop_loss=stop_loss,
        take_profit=take_profit,
        tradable=tradable,
        price=obj.price,
        anchor_low=obj.fib_structure.anchor_low,
        anchor_high=obj.fib_structure.anchor_high,
        data_source=obj.data_source,
        reasons=tuple(reasons),
    )


def build_unified_market_result(objects: Iterable[MarketObject]) -> UnifiedMarketResult:
    object_tuple = tuple(objects)
    decisions = tuple(sorted((decide_market_object(obj) for obj in object_tuple), key=lambda item: item.final_score, reverse=True))
    risk_regime = classify_risk_score(max((obj.risk_score for obj in object_tuple), default=0))

    return UnifiedMarketResult(
        a_share_top=_top_by_market(decisions, MarketType.A_SHARE),
        us_top=_top_by_market(decisions, MarketType.US),
        hk_top=_top_by_market(decisions, MarketType.HK),
        unified_rank=decisions,
        risk_regime=risk_regime,
    )


def build_decision_from_snapshot(
    snapshot: MarketSnapshot,
    waves: tuple[WaveSegment, ...],
    moving_averages: tuple[PriceReference, ...] = (),
    prior_levels: tuple[PriceReference, ...] = (),
    global_risk_context: GlobalRiskContext | None = None,
) -> TradeDecision:
    obj = build_market_object(
        snapshot=snapshot,
        waves=waves,
        moving_averages=moving_averages,
        prior_levels=prior_levels,
        global_risk_context=global_risk_context,
    )
    return decide_market_object(obj)


def output_trade_decision(decision: TradeDecision) -> dict[str, object]:
    return {
        "symbol": decision.symbol,
        "market_type": decision.market_type.value,
        "decision": decision.decision.value,
        "final_score": decision.final_score,
        "risk_score": decision.risk_score,
        "price": decision.price,
        "fib_zone": decision.fib_zone,
        "confluence": decision.confluence,
        "buy_points": decision.buy_points,
        "stop_loss": decision.stop_loss,
        "take_profit": decision.take_profit,
        "tradable": decision.tradable,
        "anchor_low": decision.anchor_low,
        "anchor_high": decision.anchor_high,
        "data_source": decision.data_source.value,
        "reasons": decision.reasons,
    }


def fib_zone_label(matrix: FibMatrix) -> str:
    if matrix.current_position == "golden_retracement":
        return "BUY_ZONE"
    if matrix.current_position in {"shallow_pullback", "deep_pullback"}:
        return "NEUTRAL_ZONE"
    return "RESISTANCE_ZONE"


def confluence_label(score: float) -> str:
    if score >= 100:
        return "4层以上（核心交易区）"
    if score >= 80:
        return "3层（强）"
    if score >= 55:
        return "2层（弱）"
    return "无有效共振"


def calculate_buy_points(matrix: FibMatrix) -> tuple[float, ...]:
    level_map = {level.ratio: level.fib_price for level in matrix.levels}
    buy_points = (level_map[0.5], level_map[0.618])
    return tuple(round(price, 3) for price in buy_points)


def _top_by_market(decisions: tuple[TradeDecision, ...], market_type: MarketType) -> tuple[TradeDecision, ...]:
    items = tuple(item for item in decisions if item.market_type is market_type)
    return items[:10]

def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))
