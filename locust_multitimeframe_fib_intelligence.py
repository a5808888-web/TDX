from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from fibonacci_wave_system import SwingKind, WaveSegment


MULTI_TIMEFRAME_FIB_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786, 1.272, 1.618)
RETRACEMENT_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786)
EXTENSION_RATIOS: tuple[float, ...] = (1.272, 1.618)
CONFLUENCE_TOLERANCE = 0.005


class MultiTimeframeLayer(str, Enum):
    LONG = "LONG WAVE"
    MID = "MID WAVE"
    SHORT = "SHORT WAVE"
    MICRO = "MICRO WAVE"


class MultiTimeframeDecision(str, Enum):
    BUY = "BUY"
    WAIT = "WAIT"
    AVOID = "AVOID"


LAYER_WEIGHTS: dict[MultiTimeframeLayer, float] = {
    MultiTimeframeLayer.LONG: 0.4,
    MultiTimeframeLayer.MID: 0.3,
    MultiTimeframeLayer.SHORT: 0.2,
    MultiTimeframeLayer.MICRO: 0.1,
}


EXPECTED_TIMEFRAMES: dict[MultiTimeframeLayer, set[str]] = {
    MultiTimeframeLayer.LONG: {"1w", "1m", "week", "weekly", "month", "monthly", "周线", "月线"},
    MultiTimeframeLayer.MID: {"1w", "1d", "week", "weekly", "day", "daily", "周线", "日线"},
    MultiTimeframeLayer.SHORT: {"1d", "60min", "60m", "1h", "day", "daily", "日线", "小时"},
    MultiTimeframeLayer.MICRO: {"15min", "15m", "30min", "30m", "15分钟", "30分钟"},
}


@dataclass(frozen=True)
class MultiTimeframeWaveSet:
    long_wave: WaveSegment
    mid_wave: WaveSegment
    short_wave: WaveSegment
    micro_wave: WaveSegment


@dataclass(frozen=True)
class MultiTimeframeFibLevel:
    ratio: float
    fib_price: float
    level_type: str
    distance_to_current_price: float


@dataclass(frozen=True)
class MultiTimeframeFibWave:
    layer: MultiTimeframeLayer
    wave: WaveSegment
    wave_type: str
    timeframe: str
    status: str
    fib_levels: tuple[MultiTimeframeFibLevel, ...]


@dataclass(frozen=True)
class MultiFibMember:
    layer: MultiTimeframeLayer
    wave_name: str
    ratio: float
    fib_price: float


@dataclass(frozen=True)
class MultiFibConfluenceZone:
    zone_low: float
    zone_high: float
    overlap_count: int
    included_levels: tuple[MultiFibMember, ...]
    supporting_waves: tuple[MultiTimeframeLayer, ...]
    weighted_support: float
    zone_type: str


@dataclass(frozen=True)
class ProbabilityZones:
    probability_zone: tuple[MultiFibConfluenceZone, ...]
    high_confidence_zone: tuple[MultiFibConfluenceZone, ...]
    low_confidence_zone: tuple[MultiFibConfluenceZone, ...]


@dataclass(frozen=True)
class MultiTimeframeBuyZone:
    price_low: float
    price_high: float
    probability_score: float
    supporting_waves: tuple[MultiTimeframeLayer, ...]


@dataclass(frozen=True)
class MultiTimeframeSellZone:
    long_wave_break: float
    mid_wave_break: float
    short_wave_stop: float
    micro_noise_note: str
    rules: tuple[str, ...]


@dataclass(frozen=True)
class MultiTimeframeFibInput:
    symbol: str
    current_price: float
    wave_set: MultiTimeframeWaveSet
    micro_structure_confirmed: bool
    trend_alignment: bool


@dataclass(frozen=True)
class MultiTimeframeFibResult:
    symbol: str
    current_price: float
    waves: tuple[MultiTimeframeFibWave, ...]
    confluence_zones: tuple[MultiFibConfluenceZone, ...]
    probability_zones: ProbabilityZones
    probability_score: float
    layer_consistency: dict[MultiTimeframeLayer, float]
    buy_zone: MultiTimeframeBuyZone | None
    sell_zone: MultiTimeframeSellZone
    decision: MultiTimeframeDecision
    reasons: tuple[str, ...]


def run_multitimeframe_fib_intelligence(data: MultiTimeframeFibInput) -> MultiTimeframeFibResult:
    if data.current_price <= 0:
        raise ValueError("Multi-timeframe Fibonacci requires a positive current price.")

    waves = (
        build_multitimeframe_fib_wave(MultiTimeframeLayer.LONG, data.wave_set.long_wave, data.current_price),
        build_multitimeframe_fib_wave(MultiTimeframeLayer.MID, data.wave_set.mid_wave, data.current_price),
        build_multitimeframe_fib_wave(MultiTimeframeLayer.SHORT, data.wave_set.short_wave, data.current_price),
        build_multitimeframe_fib_wave(MultiTimeframeLayer.MICRO, data.wave_set.micro_wave, data.current_price),
    )
    zones = detect_multi_fib_confluence_zones(waves)
    probability_zones = _build_probability_zones(zones)
    layer_consistency = _calculate_layer_consistency(waves, zones, data.current_price, data.micro_structure_confirmed)
    probability_score = round(
        sum(layer_consistency[layer] * LAYER_WEIGHTS[layer] for layer in MultiTimeframeLayer),
        2,
    )
    buy_zone = _select_buy_zone(zones, probability_score, data.current_price)
    sell_zone = _build_sell_zone(waves)
    decision, reasons = _evaluate_multitimeframe_decision(
        waves=waves,
        zones=zones,
        buy_zone=buy_zone,
        current_price=data.current_price,
        probability_score=probability_score,
        layer_consistency=layer_consistency,
        micro_structure_confirmed=data.micro_structure_confirmed,
        trend_alignment=data.trend_alignment,
    )

    return MultiTimeframeFibResult(
        symbol=data.symbol,
        current_price=data.current_price,
        waves=waves,
        confluence_zones=zones,
        probability_zones=probability_zones,
        probability_score=probability_score,
        layer_consistency=layer_consistency,
        buy_zone=buy_zone,
        sell_zone=sell_zone,
        decision=decision,
        reasons=reasons,
    )


def build_multitimeframe_fib_wave(
    layer: MultiTimeframeLayer,
    wave: WaveSegment,
    current_price: float,
) -> MultiTimeframeFibWave:
    _validate_multitimeframe_wave(layer, wave)
    price_range = wave.high.price - wave.low.price
    levels = tuple(
        MultiTimeframeFibLevel(
            ratio=ratio,
            fib_price=round(_fib_price(wave, ratio), 3),
            level_type="retracement" if ratio in RETRACEMENT_RATIOS else "extension",
            distance_to_current_price=round(_fib_price(wave, ratio) - current_price, 3),
        )
        for ratio in MULTI_TIMEFRAME_FIB_RATIOS
    )
    return MultiTimeframeFibWave(
        layer=layer,
        wave=wave,
        wave_type=_wave_type(wave),
        timeframe=f"{wave.low.timeframe}/{wave.high.timeframe}",
        status="confirmed",
        fib_levels=levels,
    )


def detect_multi_fib_confluence_zones(
    waves: Iterable[MultiTimeframeFibWave],
    tolerance: float = CONFLUENCE_TOLERANCE,
) -> tuple[MultiFibConfluenceZone, ...]:
    levels = tuple(
        MultiFibMember(
            layer=wave.layer,
            wave_name=wave.wave.name or wave.layer.value,
            ratio=level.ratio,
            fib_price=level.fib_price,
        )
        for wave in waves
        for level in wave.fib_levels
    )
    zones: list[MultiFibConfluenceZone] = []
    seen: set[tuple[tuple[str, float, float], ...]] = set()

    for base in levels:
        cluster = tuple(item for item in levels if _same_price_band(base.fib_price, item.fib_price, tolerance))
        supporting_waves = tuple(sorted({item.layer for item in cluster}, key=lambda layer: -LAYER_WEIGHTS[layer]))
        if len(supporting_waves) < 2:
            continue
        key = tuple(sorted((item.layer.value, item.ratio, item.fib_price) for item in cluster))
        if key in seen:
            continue
        seen.add(key)
        weighted_support = round(sum(LAYER_WEIGHTS[layer] for layer in supporting_waves) * 100, 2)
        zones.append(
            MultiFibConfluenceZone(
                zone_low=round(min(item.fib_price for item in cluster), 3),
                zone_high=round(max(item.fib_price for item in cluster), 3),
                overlap_count=len(cluster),
                included_levels=cluster,
                supporting_waves=supporting_waves,
                weighted_support=weighted_support,
                zone_type=_zone_type(weighted_support, len(supporting_waves)),
            )
        )

    return tuple(sorted(zones, key=lambda zone: (-zone.weighted_support, -zone.overlap_count, zone.zone_low)))


def multitimeframe_fib_result_to_output(result: MultiTimeframeFibResult) -> dict[str, object]:
    wave_by_layer = {wave.layer: wave for wave in result.waves}
    return {
        "Locust Plan V6": "Multi-Timeframe Fibonacci Intelligence System",
        "LONG WAVE Fib": _wave_to_output(wave_by_layer[MultiTimeframeLayer.LONG]),
        "MID WAVE Fib": _wave_to_output(wave_by_layer[MultiTimeframeLayer.MID]),
        "SHORT WAVE Fib": _wave_to_output(wave_by_layer[MultiTimeframeLayer.SHORT]),
        "MICRO WAVE Fib": _wave_to_output(wave_by_layer[MultiTimeframeLayer.MICRO]),
        "Multi-Fib Confluence Zone": tuple(_zone_to_output(zone) for zone in result.confluence_zones),
        "Probability Score": {
            "score": result.probability_score,
            "weights": {
                "LONG WAVE": 40,
                "MID WAVE": 30,
                "SHORT WAVE": 20,
                "MICRO WAVE": 10,
            },
            "layer_consistency": {layer.value: score for layer, score in result.layer_consistency.items()},
            "Probability Zone": tuple(_zone_to_output(zone) for zone in result.probability_zones.probability_zone),
            "High Confidence Zone": tuple(_zone_to_output(zone) for zone in result.probability_zones.high_confidence_zone),
            "Low Confidence Zone": tuple(_zone_to_output(zone) for zone in result.probability_zones.low_confidence_zone),
        },
        "BUY_ZONE": _buy_zone_to_output(result.buy_zone),
        "SELL_ZONE": _sell_zone_to_output(result.sell_zone),
        "Final Advice": {
            "decision": result.decision.value,
            "reasons": result.reasons,
        },
        "Forbidden": {
            "禁止只用单周期Fib": True,
            "禁止短周期覆盖长期趋势": True,
            "禁止日内波段破坏长期结构": True,
            "禁止无共振交易": True,
            "禁止单Fib点决策": True,
        },
    }


def _validate_multitimeframe_wave(layer: MultiTimeframeLayer, wave: WaveSegment) -> None:
    if not wave.confirmed:
        raise ValueError(f"{layer.value} requires confirmed anchors.")
    if wave.low.kind is not SwingKind.LOW or wave.high.kind is not SwingKind.HIGH:
        raise ValueError(f"{layer.value} requires anchor_low and anchor_high.")
    if wave.low.price <= 0 or wave.high.price <= 0 or wave.high.price <= wave.low.price:
        raise ValueError(f"{layer.value} anchors must be positive and ordered.")
    if _forbidden_anchor_timeframe(wave.low.timeframe) or _forbidden_anchor_timeframe(wave.high.timeframe):
        raise ValueError("Current price cannot be used as a Fibonacci anchor.")
    allowed = EXPECTED_TIMEFRAMES[layer]
    if _normalize_timeframe(wave.low.timeframe) not in allowed or _normalize_timeframe(wave.high.timeframe) not in allowed:
        raise ValueError(f"{layer.value} requires its fixed timeframe.")


def _fib_price(wave: WaveSegment, ratio: float) -> float:
    price_range = wave.high.price - wave.low.price
    if ratio in RETRACEMENT_RATIOS:
        return wave.high.price - ratio * price_range
    return wave.high.price + (ratio - 1) * price_range


def _calculate_layer_consistency(
    waves: tuple[MultiTimeframeFibWave, ...],
    zones: tuple[MultiFibConfluenceZone, ...],
    current_price: float,
    micro_structure_confirmed: bool,
) -> dict[MultiTimeframeLayer, float]:
    return {
        wave.layer: _layer_consistency(wave, zones, current_price, micro_structure_confirmed)
        for wave in waves
    }


def _layer_consistency(
    wave: MultiTimeframeFibWave,
    zones: tuple[MultiFibConfluenceZone, ...],
    current_price: float,
    micro_structure_confirmed: bool,
) -> float:
    if wave.layer is MultiTimeframeLayer.MICRO:
        return 100.0 if micro_structure_confirmed else 0.0
    if wave.layer is MultiTimeframeLayer.LONG:
        if _current_in_retracement_band(wave, current_price, 0.382, 0.786):
            return 100.0
        return 65.0 if _layer_has_confluence(wave.layer, zones, current_price) else 0.0
    if wave.layer is MultiTimeframeLayer.MID:
        if _current_in_retracement_band(wave, current_price, 0.382, 0.618):
            return 100.0
        return 55.0 if _layer_has_confluence(wave.layer, zones, current_price) else 0.0
    if _layer_has_confluence(wave.layer, zones, current_price):
        return 100.0
    if _current_in_retracement_band(wave, current_price, 0.382, 0.786):
        return 60.0
    return 0.0


def _evaluate_multitimeframe_decision(
    waves: tuple[MultiTimeframeFibWave, ...],
    zones: tuple[MultiFibConfluenceZone, ...],
    buy_zone: MultiTimeframeBuyZone | None,
    current_price: float,
    probability_score: float,
    layer_consistency: dict[MultiTimeframeLayer, float],
    micro_structure_confirmed: bool,
    trend_alignment: bool,
) -> tuple[MultiTimeframeDecision, tuple[str, ...]]:
    wave_by_layer = {wave.layer: wave for wave in waves}
    reasons: list[str] = []
    long_support = _current_in_retracement_band(wave_by_layer[MultiTimeframeLayer.LONG], current_price, 0.382, 0.786)
    mid_retracement = _current_in_retracement_band(wave_by_layer[MultiTimeframeLayer.MID], current_price, 0.382, 0.618)
    short_confluence = any(
        zone.zone_low <= current_price <= zone.zone_high and MultiTimeframeLayer.SHORT in zone.supporting_waves
        for zone in zones
    )

    if current_price < wave_by_layer[MultiTimeframeLayer.LONG].wave.low.price:
        return MultiTimeframeDecision.AVOID, ("LONG WAVE 已破位，清仓级风险。",)
    if not long_support:
        reasons.append("未处于 LONG WAVE 支撑区。")
    if not mid_retracement:
        reasons.append("未处于 MID WAVE 回撤区。")
    if not short_confluence:
        reasons.append("SHORT WAVE 附近没有多周期共振。")
    if not micro_structure_confirmed:
        reasons.append("MICRO WAVE 没有执行级确认。")
    if not trend_alignment:
        reasons.append("多周期趋势未一致。")
    if buy_zone is None:
        reasons.append("没有可交易的多周期 BUY_ZONE。")
    if probability_score < 70:
        reasons.append("概率融合分低于70。")
    if layer_consistency[MultiTimeframeLayer.LONG] < layer_consistency[MultiTimeframeLayer.SHORT]:
        reasons.append("短周期强于长期结构，禁止短周期覆盖长期趋势。")

    if not reasons:
        return MultiTimeframeDecision.BUY, ("多周期共振区、Fib重叠、长期趋势和执行确认同时满足。",)
    if not trend_alignment:
        return MultiTimeframeDecision.AVOID, tuple(reasons)
    return MultiTimeframeDecision.WAIT, tuple(reasons)


def _select_buy_zone(
    zones: tuple[MultiFibConfluenceZone, ...],
    probability_score: float,
    current_price: float,
) -> MultiTimeframeBuyZone | None:
    candidates = tuple(
        zone for zone in zones
        if zone.zone_low <= current_price <= zone.zone_high
        and MultiTimeframeLayer.LONG in zone.supporting_waves
        and MultiTimeframeLayer.MID in zone.supporting_waves
        and MultiTimeframeLayer.SHORT in zone.supporting_waves
    )
    if not candidates:
        return None
    zone = sorted(candidates, key=lambda item: (-item.weighted_support, -item.overlap_count, item.zone_low))[0]
    return MultiTimeframeBuyZone(
        price_low=zone.zone_low,
        price_high=zone.zone_high,
        probability_score=probability_score,
        supporting_waves=zone.supporting_waves,
    )


def _build_probability_zones(zones: tuple[MultiFibConfluenceZone, ...]) -> ProbabilityZones:
    high = tuple(zone for zone in zones if zone.weighted_support >= 70)
    low = tuple(zone for zone in zones if zone.weighted_support < 70)
    return ProbabilityZones(probability_zone=zones, high_confidence_zone=high, low_confidence_zone=low)


def _build_sell_zone(waves: tuple[MultiTimeframeFibWave, ...]) -> MultiTimeframeSellZone:
    wave_by_layer = {wave.layer: wave for wave in waves}
    mid_786 = _level_price(wave_by_layer[MultiTimeframeLayer.MID], 0.786)
    short_786 = _level_price(wave_by_layer[MultiTimeframeLayer.SHORT], 0.786)
    return MultiTimeframeSellZone(
        long_wave_break=round(wave_by_layer[MultiTimeframeLayer.LONG].wave.low.price, 3),
        mid_wave_break=round(mid_786, 3),
        short_wave_stop=round(short_786, 3),
        micro_noise_note="MICRO 波动只用于执行确认，不影响长期仓位。",
        rules=(
            "LONG WAVE 破位 -> 清仓",
            "MID WAVE 破位 -> 减仓",
            "SHORT WAVE 失效 -> 止损",
            "MICRO 波动 -> 不影响长期仓位",
        ),
    )


def _wave_to_output(wave: MultiTimeframeFibWave) -> dict[str, object]:
    return {
        "anchor_low": wave.wave.low.price,
        "anchor_high": wave.wave.high.price,
        "wave_type": wave.wave_type,
        "timeframe": wave.timeframe,
        "status": wave.status,
        "fib_levels": {
            f"{level.ratio:g}": {
                "fib_price": level.fib_price,
                "type": level.level_type,
                "distance_to_current_price": level.distance_to_current_price,
            }
            for level in wave.fib_levels
        },
    }


def _zone_to_output(zone: MultiFibConfluenceZone) -> dict[str, object]:
    return {
        "zone_low": zone.zone_low,
        "zone_high": zone.zone_high,
        "overlap_count": zone.overlap_count,
        "supporting_waves": tuple(layer.value for layer in zone.supporting_waves),
        "weighted_support": zone.weighted_support,
        "zone_type": zone.zone_type,
        "included_levels": tuple(
            {
                "wave": item.layer.value,
                "wave_name": item.wave_name,
                "ratio": item.ratio,
                "fib_price": item.fib_price,
            }
            for item in zone.included_levels
        ),
    }


def _buy_zone_to_output(zone: MultiTimeframeBuyZone | None) -> dict[str, object] | None:
    if zone is None:
        return None
    return {
        "price_low": zone.price_low,
        "price_high": zone.price_high,
        "probability_score": zone.probability_score,
        "supporting_waves": tuple(layer.value for layer in zone.supporting_waves),
    }


def _sell_zone_to_output(zone: MultiTimeframeSellZone) -> dict[str, object]:
    return {
        "LONG WAVE 破位": zone.long_wave_break,
        "MID WAVE 破位": zone.mid_wave_break,
        "SHORT WAVE 失效": zone.short_wave_stop,
        "MICRO 波动": zone.micro_noise_note,
        "rules": zone.rules,
    }


def _current_in_retracement_band(
    wave: MultiTimeframeFibWave,
    current_price: float,
    high_ratio: float,
    low_ratio: float,
) -> bool:
    upper = _level_price(wave, high_ratio)
    lower = _level_price(wave, low_ratio)
    return min(lower, upper) <= current_price <= max(lower, upper)


def _layer_has_confluence(
    layer: MultiTimeframeLayer,
    zones: tuple[MultiFibConfluenceZone, ...],
    current_price: float,
) -> bool:
    return any(zone.zone_low <= current_price <= zone.zone_high and layer in zone.supporting_waves for zone in zones)


def _level_price(wave: MultiTimeframeFibWave, ratio: float) -> float:
    for level in wave.fib_levels:
        if level.ratio == ratio:
            return level.fib_price
    raise ValueError(f"Missing multi-timeframe Fibonacci level: {ratio}")


def _same_price_band(price_a: float, price_b: float, tolerance: float) -> bool:
    reference = (price_a + price_b) / 2
    return reference > 0 and abs(price_a - price_b) / reference < tolerance


def _zone_type(weighted_support: float, supporting_wave_count: int) -> str:
    if weighted_support >= 70 and supporting_wave_count >= 3:
        return "High Confidence Zone"
    return "Low Confidence Zone"


def _wave_type(wave: WaveSegment) -> str:
    ratio = wave.price_range / wave.low.price
    if ratio >= 0.25:
        return "impulse"
    if ratio >= 0.08:
        return "trend"
    return "range"


def _normalize_timeframe(timeframe: str) -> str:
    return timeframe.strip().lower()


def _forbidden_anchor_timeframe(timeframe: str) -> bool:
    normalized = _normalize_timeframe(timeframe)
    return normalized in {"current", "current_price", "now", "intraday_high", "日内高点", "当前价"}
