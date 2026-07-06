from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Literal

from fibonacci_wave_system import SwingKind, WaveSegment


FIB_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786, 1.272, 1.618)
CONFLUENCE_TOLERANCE = 0.003


class WavePattern(str, Enum):
    TREND = "trend"
    RANGE = "range"
    IMPULSE = "impulse"


class LevelKind(str, Enum):
    FIB = "fib"
    MOVING_AVERAGE = "moving_average"
    PRIOR_HIGH = "prior_high"
    PRIOR_LOW = "prior_low"


class ZoneRole(str, Enum):
    SUPPORT = "support"
    RESISTANCE = "resistance"
    CORE = "core"


class ConfluenceStrength(str, Enum):
    WEAK = "weak"
    STRONG = "strong"
    CORE = "core"


class FinalDecision(str, Enum):
    BUY = "BUY"
    WATCH = "WATCH"
    AVOID = "AVOID"
    SELL = "SELL"


FibPosition = Literal[
    "above_anchor_high",
    "shallow_pullback",
    "golden_retracement",
    "deep_pullback",
    "below_anchor_low",
]


@dataclass(frozen=True)
class ConfirmedWaveSegment:
    source: WaveSegment
    wave_name: str
    pattern: WavePattern
    anchor_low: float
    anchor_high: float
    confirmed: bool


@dataclass(frozen=True)
class FibPriceLevel:
    wave_name: str
    ratio: float
    fib_price: float
    distance_to_current_price: float


@dataclass(frozen=True)
class FibMatrix:
    wave_name: str
    anchor_low: float
    anchor_high: float
    range: float
    current_price: float
    current_position: FibPosition
    levels: tuple[FibPriceLevel, ...]


@dataclass(frozen=True)
class PriceReference:
    kind: LevelKind
    name: str
    price: float


@dataclass(frozen=True)
class HeatmapLevel:
    kind: LevelKind
    source_name: str
    price: float
    ratio: float | None = None


@dataclass(frozen=True)
class ConfluenceZone:
    zone_low: float
    zone_high: float
    overlap_count: int
    included_levels: tuple[HeatmapLevel, ...]
    strength: ConfluenceStrength
    role: ZoneRole


@dataclass(frozen=True)
class TradeSignal:
    decision: FinalDecision
    final_score: float
    fib_position_score: float
    confluence_strength_score: float
    locust_score: float
    risk_score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class LocustWaveFibHeatmapInput:
    waves: tuple[WaveSegment, ...]
    current_price: float
    locust_score: float
    risk_score: float
    moving_averages: tuple[PriceReference, ...] = ()
    prior_levels: tuple[PriceReference, ...] = ()


@dataclass(frozen=True)
class LocustWaveFibHeatmapResult:
    wave_segments: tuple[ConfirmedWaveSegment, ...]
    fib_matrices: tuple[FibMatrix, ...]
    confluence_zones: tuple[ConfluenceZone, ...]
    trade_signal: TradeSignal


def run_wave_fib_confluence_heatmap(data: LocustWaveFibHeatmapInput) -> LocustWaveFibHeatmapResult:
    _validate_score(data.locust_score, "locust_score")
    _validate_score(data.risk_score, "risk_score")
    if data.current_price <= 0:
        raise ValueError("current_price must be positive.")

    wave_segments = tuple(identify_confirmed_wave(wave) for wave in data.waves)
    fib_matrices = tuple(build_heatmap_fib_matrix(wave, data.current_price) for wave in wave_segments)
    confluence_zones = build_confluence_heatmap(
        fib_matrices=fib_matrices,
        moving_averages=data.moving_averages,
        prior_levels=data.prior_levels,
        current_price=data.current_price,
    )
    trade_signal = build_trade_signal(
        wave_segments=wave_segments,
        fib_matrices=fib_matrices,
        confluence_zones=confluence_zones,
        current_price=data.current_price,
        locust_score=data.locust_score,
        risk_score=data.risk_score,
    )

    return LocustWaveFibHeatmapResult(
        wave_segments=wave_segments,
        fib_matrices=fib_matrices,
        confluence_zones=confluence_zones,
        trade_signal=trade_signal,
    )


def identify_confirmed_wave(wave: WaveSegment) -> ConfirmedWaveSegment:
    _validate_wave_anchors(wave)
    price_range_pct = wave.price_range / wave.low.price
    if price_range_pct <= 0.05:
        pattern = WavePattern.RANGE
    elif price_range_pct >= 0.2:
        pattern = WavePattern.IMPULSE
    else:
        pattern = WavePattern.TREND

    return ConfirmedWaveSegment(
        source=wave,
        wave_name=wave.name or wave.tier.value,
        pattern=pattern,
        anchor_low=wave.low.price,
        anchor_high=wave.high.price,
        confirmed=True,
    )


def build_heatmap_fib_matrix(wave: ConfirmedWaveSegment, current_price: float) -> FibMatrix:
    price_range = wave.anchor_high - wave.anchor_low
    levels = tuple(
        FibPriceLevel(
            wave_name=wave.wave_name,
            ratio=ratio,
            fib_price=wave.anchor_high - ratio * price_range,
            distance_to_current_price=wave.anchor_high - ratio * price_range - current_price,
        )
        for ratio in FIB_RATIOS
    )

    return FibMatrix(
        wave_name=wave.wave_name,
        anchor_low=wave.anchor_low,
        anchor_high=wave.anchor_high,
        range=price_range,
        current_price=current_price,
        current_position=_classify_fib_position(wave.anchor_low, wave.anchor_high, levels, current_price),
        levels=levels,
    )


def build_confluence_heatmap(
    fib_matrices: Iterable[FibMatrix],
    moving_averages: Iterable[PriceReference],
    prior_levels: Iterable[PriceReference],
    current_price: float,
    tolerance: float = CONFLUENCE_TOLERANCE,
) -> tuple[ConfluenceZone, ...]:
    levels = tuple(_collect_heatmap_levels(fib_matrices, moving_averages, prior_levels))
    zones: list[ConfluenceZone] = []
    seen: set[tuple[tuple[str, str, float | None], ...]] = set()

    for base in levels:
        cluster = tuple(level for level in levels if _prices_overlap(base.price, level.price, tolerance))
        if len(cluster) < 2:
            continue
        if sum(1 for level in cluster if level.kind is LevelKind.FIB) < 1:
            continue

        key = tuple(sorted((level.kind.value, level.source_name, level.ratio) for level in cluster))
        if key in seen:
            continue
        seen.add(key)

        zone_low = min(level.price for level in cluster)
        zone_high = max(level.price for level in cluster)
        strength = _classify_zone_strength(cluster)
        zones.append(
            ConfluenceZone(
                zone_low=zone_low,
                zone_high=zone_high,
                overlap_count=len(cluster),
                included_levels=cluster,
                strength=strength,
                role=_classify_zone_role(cluster, strength, zone_low, zone_high, current_price),
            )
        )

    return tuple(sorted(zones, key=lambda zone: (-zone.overlap_count, zone.zone_low)))


def build_trade_signal(
    wave_segments: tuple[ConfirmedWaveSegment, ...],
    fib_matrices: tuple[FibMatrix, ...],
    confluence_zones: tuple[ConfluenceZone, ...],
    current_price: float,
    locust_score: float,
    risk_score: float,
) -> TradeSignal:
    fib_position_score = _score_fib_position(fib_matrices)
    confluence_strength_score = _score_confluence_strength(confluence_zones, current_price)
    final_score = fib_position_score + confluence_strength_score + locust_score - risk_score
    reasons: list[str] = []

    active_zones = _active_zones(confluence_zones, current_price)
    trend_supported = any(wave.pattern in {WavePattern.TREND, WavePattern.IMPULSE} for wave in wave_segments)

    if _structure_broken(fib_matrices, current_price):
        return TradeSignal(
            decision=FinalDecision.SELL,
            final_score=final_score,
            fib_position_score=fib_position_score,
            confluence_strength_score=confluence_strength_score,
            locust_score=locust_score,
            risk_score=risk_score,
            reasons=("结构破坏：当前价格跌破波段 anchor_low",),
        )
    if risk_score >= 75:
        return TradeSignal(
            decision=FinalDecision.AVOID,
            final_score=final_score,
            fib_position_score=fib_position_score,
            confluence_strength_score=confluence_strength_score,
            locust_score=locust_score,
            risk_score=risk_score,
            reasons=("风险过高，禁止开仓",),
        )
    if not confluence_zones:
        return TradeSignal(
            decision=FinalDecision.AVOID,
            final_score=final_score,
            fib_position_score=fib_position_score,
            confluence_strength_score=confluence_strength_score,
            locust_score=locust_score,
            risk_score=risk_score,
            reasons=("无有效共振区，禁止直接买入",),
        )

    if fib_position_score <= 0:
        reasons.append("当前价格不在有效 Fib 位置")
    if not active_zones:
        reasons.append("结构存在，但价格尚未进入共振区")
    if not trend_supported:
        reasons.append("波段不是 trend/impulse 结构")
    if locust_score < 60:
        reasons.append("LocustScore 资金支持不足")

    if not reasons and final_score >= 60:
        return TradeSignal(
            decision=FinalDecision.BUY,
            final_score=final_score,
            fib_position_score=fib_position_score,
            confluence_strength_score=confluence_strength_score,
            locust_score=locust_score,
            risk_score=risk_score,
            reasons=("共振、趋势、资金均确认",),
        )

    return TradeSignal(
        decision=FinalDecision.WATCH,
        final_score=final_score,
        fib_position_score=fib_position_score,
        confluence_strength_score=confluence_strength_score,
        locust_score=locust_score,
        risk_score=risk_score,
        reasons=tuple(reasons) or ("结构存在但评分未达到 BUY 阈值",),
    )


def heatmap_result_to_output(result: LocustWaveFibHeatmapResult) -> dict[str, object]:
    return {
        "WaveSegment": tuple(_wave_to_output(wave) for wave in result.wave_segments),
        "FibMatrix": tuple(_matrix_to_output(matrix) for matrix in result.fib_matrices),
        "ConfluenceZone": tuple(_zone_to_output(zone) for zone in result.confluence_zones),
        "TradeSignal": {
            "decision": result.trade_signal.decision.value,
            "final_score": result.trade_signal.final_score,
            "fib_position_score": result.trade_signal.fib_position_score,
            "confluence_strength_score": result.trade_signal.confluence_strength_score,
            "locust_score": result.trade_signal.locust_score,
            "risk_score": result.trade_signal.risk_score,
            "reasons": result.trade_signal.reasons,
        },
    }


def _validate_wave_anchors(wave: WaveSegment) -> None:
    if wave.low.kind is not SwingKind.LOW or wave.high.kind is not SwingKind.HIGH:
        raise ValueError("Wave requires confirmed pivot low and pivot high anchors.")
    if not wave.confirmed:
        raise ValueError("Unconfirmed waves cannot be used.")
    if _is_forbidden_anchor(wave.low) or _is_forbidden_anchor(wave.high):
        raise ValueError("Intraday extreme or current price cannot be used as a wave anchor.")
    if wave.low.price <= 0 or wave.high.price <= 0:
        raise ValueError("Wave anchor prices must be positive.")
    if wave.high.price <= wave.low.price:
        raise ValueError("anchor_high must be greater than anchor_low.")


def _is_forbidden_anchor(anchor) -> bool:
    normalized = anchor.timeframe.strip().lower()
    forbidden = {"tick", "1min", "5min", "15min", "30min", "intraday", "day_high", "day_low", "current_price", "分时", "日内高点", "日内低点"}
    return normalized in forbidden


def _validate_score(value: float, field_name: str) -> None:
    if value < 0 or value > 100:
        raise ValueError(f"{field_name} must be between 0 and 100.")


def _classify_fib_position(
    anchor_low: float,
    anchor_high: float,
    levels: Iterable[FibPriceLevel],
    current_price: float,
) -> FibPosition:
    if current_price > anchor_high:
        return "above_anchor_high"
    if current_price < anchor_low:
        return "below_anchor_low"
    level_236 = _fib_level_price(levels, 0.236)
    level_382 = _fib_level_price(levels, 0.382)
    level_618 = _fib_level_price(levels, 0.618)
    level_786 = _fib_level_price(levels, 0.786)
    if level_382 <= current_price <= level_236:
        return "shallow_pullback"
    if level_618 <= current_price <= level_382:
        return "golden_retracement"
    if level_786 <= current_price <= level_618:
        return "deep_pullback"
    return "below_anchor_low"


def _fib_level_price(levels: Iterable[FibPriceLevel], ratio: float) -> float:
    for level in levels:
        if level.ratio == ratio:
            return level.fib_price
    raise ValueError(f"Missing Fib ratio: {ratio}")


def _collect_heatmap_levels(
    fib_matrices: Iterable[FibMatrix],
    moving_averages: Iterable[PriceReference],
    prior_levels: Iterable[PriceReference],
) -> Iterable[HeatmapLevel]:
    for matrix in fib_matrices:
        for level in matrix.levels:
            yield HeatmapLevel(kind=LevelKind.FIB, source_name=f"{matrix.wave_name}:{level.ratio:g}", price=level.fib_price, ratio=level.ratio)
    for reference in moving_averages:
        yield HeatmapLevel(kind=LevelKind.MOVING_AVERAGE, source_name=reference.name, price=reference.price)
    for reference in prior_levels:
        if reference.kind not in {LevelKind.PRIOR_HIGH, LevelKind.PRIOR_LOW}:
            raise ValueError("prior_levels must use PRIOR_HIGH or PRIOR_LOW.")
        yield HeatmapLevel(kind=reference.kind, source_name=reference.name, price=reference.price)


def _prices_overlap(price_a: float, price_b: float, tolerance: float) -> bool:
    reference_price = (price_a + price_b) / 2
    if reference_price <= 0:
        return False
    return abs(price_a - price_b) / reference_price < tolerance


def _classify_zone_strength(levels: tuple[HeatmapLevel, ...]) -> ConfluenceStrength:
    if len(levels) >= 4:
        return ConfluenceStrength.CORE
    if len(levels) == 3:
        return ConfluenceStrength.STRONG
    return ConfluenceStrength.WEAK


def _classify_zone_role(
    levels: tuple[HeatmapLevel, ...],
    strength: ConfluenceStrength,
    zone_low: float,
    zone_high: float,
    current_price: float,
) -> ZoneRole:
    kinds = {level.kind for level in levels}
    if strength is ConfluenceStrength.CORE or {LevelKind.FIB, LevelKind.MOVING_AVERAGE, LevelKind.PRIOR_HIGH}.issubset(kinds):
        return ZoneRole.CORE
    if zone_high < current_price:
        return ZoneRole.SUPPORT
    return ZoneRole.RESISTANCE


def _score_fib_position(fib_matrices: tuple[FibMatrix, ...]) -> float:
    if any(matrix.current_position == "golden_retracement" for matrix in fib_matrices):
        return 25.0
    if any(matrix.current_position in {"shallow_pullback", "deep_pullback"} for matrix in fib_matrices):
        return 10.0
    return 0.0


def _score_confluence_strength(confluence_zones: tuple[ConfluenceZone, ...], current_price: float) -> float:
    active = _active_zones(confluence_zones, current_price)
    if any(zone.strength is ConfluenceStrength.CORE for zone in active):
        return 35.0
    if any(zone.strength is ConfluenceStrength.STRONG for zone in active):
        return 25.0
    if active:
        return 15.0
    return 0.0


def _active_zones(confluence_zones: tuple[ConfluenceZone, ...], current_price: float) -> tuple[ConfluenceZone, ...]:
    active: list[ConfluenceZone] = []
    for zone in confluence_zones:
        zone_mid = (zone.zone_low + zone.zone_high) / 2
        padding = zone_mid * CONFLUENCE_TOLERANCE
        if zone.zone_low - padding <= current_price <= zone.zone_high + padding:
            active.append(zone)
    return tuple(active)


def _structure_broken(fib_matrices: tuple[FibMatrix, ...], current_price: float) -> bool:
    if not fib_matrices:
        return True
    actionable_low = max(matrix.anchor_low for matrix in fib_matrices)
    return current_price < actionable_low


def _wave_to_output(wave: ConfirmedWaveSegment) -> dict[str, object]:
    return {
        "wave_name": wave.wave_name,
        "pattern": wave.pattern.value,
        "confirmed": wave.confirmed,
        "anchor_low": wave.anchor_low,
        "anchor_high": wave.anchor_high,
    }


def _matrix_to_output(matrix: FibMatrix) -> dict[str, object]:
    return {
        "wave_name": matrix.wave_name,
        "anchor_low": matrix.anchor_low,
        "anchor_high": matrix.anchor_high,
        "range": matrix.range,
        "current_price": matrix.current_price,
        "current_position": matrix.current_position,
        "levels": {
            f"{level.ratio:g}": {
                "fib_price": level.fib_price,
                "distance_to_current_price": level.distance_to_current_price,
            }
            for level in matrix.levels
        },
    }


def _zone_to_output(zone: ConfluenceZone) -> dict[str, object]:
    return {
        "zone_low": zone.zone_low,
        "zone_high": zone.zone_high,
        "overlap_count": zone.overlap_count,
        "included_levels": tuple(
            {
                "kind": level.kind.value,
                "source_name": level.source_name,
                "ratio": level.ratio,
                "price": level.price,
            }
            for level in zone.included_levels
        ),
        "strength": zone.strength.value,
        "role": zone.role.value,
    }
