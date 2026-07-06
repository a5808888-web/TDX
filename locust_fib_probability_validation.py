from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from fibonacci_wave_system import SwingKind, WaveSegment


PROBABILITY_FIB_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786)
TOUCH_TOLERANCE = 0.005
REACTION_THRESHOLD = 0.003
CONFLUENCE_TOLERANCE = 0.005


class ProbabilityWaveLayer(str, Enum):
    PRIMARY = "primary_wave"
    SECONDARY = "secondary_wave"
    MICRO = "micro_wave"


class FibReaction(str, Enum):
    BOUNCE = "bounce"
    REJECTION = "rejection"
    BREAK = "break"
    CONSOLIDATION = "consolidation"


class ProbabilityDecision(str, Enum):
    BUY = "BUY"
    WATCH = "WATCH"
    AVOID = "AVOID"


@dataclass(frozen=True)
class PriceBar:
    timestamp: str
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class FibTouchEvent:
    timestamp: str
    ratio: float
    fib_price: float
    reaction: FibReaction
    success: bool


@dataclass(frozen=True)
class ProbabilityFibLevel:
    ratio: float
    fib_price: float
    touch_events: tuple[FibTouchEvent, ...]
    total_touches: int
    successful_reactions: int
    accuracy: float
    verified: bool


@dataclass(frozen=True)
class ProbabilityWave:
    layer: ProbabilityWaveLayer
    wave_name: str
    anchor_low: float
    anchor_high: float
    fib_levels: tuple[ProbabilityFibLevel, ...]
    accuracy_by_ratio: dict[float, float]


@dataclass(frozen=True)
class WaveSet:
    primary_wave: WaveSegment
    secondary_wave: WaveSegment
    micro_wave: WaveSegment


@dataclass(frozen=True)
class ProbabilityConfluenceMember:
    layer: ProbabilityWaveLayer
    wave_name: str
    ratio: float
    fib_price: float
    accuracy: float


@dataclass(frozen=True)
class ProbabilityConfluenceZone:
    zone_low: float
    zone_high: float
    supporting_waves: tuple[ProbabilityWaveLayer, ...]
    included_levels: tuple[ProbabilityConfluenceMember, ...]
    historical_success_rate: float
    confluence_score: float
    probability_score: float


@dataclass(frozen=True)
class HighestProbabilityZone:
    price_range: tuple[float, float]
    probability_score: float
    supporting_waves: tuple[ProbabilityWaveLayer, ...]
    confidence: str
    included_levels: tuple[ProbabilityConfluenceMember, ...]


@dataclass(frozen=True)
class FibProbabilityValidationInput:
    wave_set: WaveSet
    historical_prices: tuple[PriceBar, ...]
    risk_score: float
    trend_alignment: bool


@dataclass(frozen=True)
class FibProbabilityValidationResult:
    waves: tuple[ProbabilityWave, ...]
    confluence_zones: tuple[ProbabilityConfluenceZone, ...]
    highest_probability_zone: HighestProbabilityZone | None
    decision: ProbabilityDecision
    reasons: tuple[str, ...]


def run_fib_probability_validation(data: FibProbabilityValidationInput) -> FibProbabilityValidationResult:
    if len(data.historical_prices) < 3:
        raise ValueError("Fib probability validation requires at least 3 historical bars.")
    _validate_bars(data.historical_prices)

    waves = (
        build_probability_wave(ProbabilityWaveLayer.PRIMARY, data.wave_set.primary_wave, data.historical_prices),
        build_probability_wave(ProbabilityWaveLayer.SECONDARY, data.wave_set.secondary_wave, data.historical_prices),
        build_probability_wave(ProbabilityWaveLayer.MICRO, data.wave_set.micro_wave, data.historical_prices),
    )
    zones = detect_probability_confluence_zones(waves)
    highest_zone = zones[0] if zones else None
    buy_zone = _highest_zone_to_buy_zone(highest_zone)
    decision, reasons = evaluate_probability_decision(buy_zone, data.risk_score, data.trend_alignment)

    return FibProbabilityValidationResult(
        waves=waves,
        confluence_zones=zones,
        highest_probability_zone=buy_zone,
        decision=decision,
        reasons=reasons,
    )


def build_probability_wave(
    layer: ProbabilityWaveLayer,
    wave: WaveSegment,
    historical_prices: tuple[PriceBar, ...],
) -> ProbabilityWave:
    _validate_wave(layer, wave)
    price_range = wave.high.price - wave.low.price
    levels = tuple(
        _build_probability_level(ratio, wave.high.price - ratio * price_range, historical_prices)
        for ratio in PROBABILITY_FIB_RATIOS
    )
    return ProbabilityWave(
        layer=layer,
        wave_name=wave.name or layer.value,
        anchor_low=wave.low.price,
        anchor_high=wave.high.price,
        fib_levels=levels,
        accuracy_by_ratio={level.ratio: level.accuracy for level in levels},
    )


def detect_probability_confluence_zones(
    waves: Iterable[ProbabilityWave],
    tolerance: float = CONFLUENCE_TOLERANCE,
) -> tuple[ProbabilityConfluenceZone, ...]:
    levels = tuple(
        ProbabilityConfluenceMember(
            layer=wave.layer,
            wave_name=wave.wave_name,
            ratio=level.ratio,
            fib_price=level.fib_price,
            accuracy=level.accuracy,
        )
        for wave in waves
        for level in wave.fib_levels
        if level.verified
    )
    zones: list[ProbabilityConfluenceZone] = []
    seen: set[tuple[tuple[str, float, float], ...]] = set()

    for base in levels:
        cluster = tuple(item for item in levels if _same_price_band(base.fib_price, item.fib_price, tolerance))
        supporting_layers = tuple(sorted({item.layer for item in cluster}, key=lambda item: item.value))
        if len(supporting_layers) < 2:
            continue
        key = tuple(sorted((item.layer.value, item.ratio, item.fib_price) for item in cluster))
        if key in seen:
            continue
        seen.add(key)

        historical_success_rate = round(sum(item.accuracy for item in cluster) / len(cluster), 2)
        confluence_score = round(len(supporting_layers) * historical_success_rate, 2)
        zones.append(
            ProbabilityConfluenceZone(
                zone_low=round(min(item.fib_price for item in cluster), 3),
                zone_high=round(max(item.fib_price for item in cluster), 3),
                supporting_waves=supporting_layers,
                included_levels=cluster,
                historical_success_rate=historical_success_rate,
                confluence_score=confluence_score,
                probability_score=historical_success_rate,
            )
        )

    return tuple(sorted(zones, key=lambda zone: (-zone.probability_score, -len(zone.supporting_waves), zone.zone_low)))


def evaluate_probability_decision(
    buy_zone: HighestProbabilityZone | None,
    risk_score: float,
    trend_alignment: bool,
) -> tuple[ProbabilityDecision, tuple[str, ...]]:
    reasons: list[str] = []
    if buy_zone is None:
        return ProbabilityDecision.AVOID, ("没有通过历史验证的多波段共振区。",)
    if buy_zone.probability_score <= 70:
        reasons.append("概率未超过70%。")
    if len(buy_zone.supporting_waves) < 2:
        reasons.append("共振不足2个波段。")
    if risk_score >= 40:
        reasons.append("风险分不低于40。")
    if not trend_alignment:
        reasons.append("趋势未对齐。")

    if not reasons:
        return ProbabilityDecision.BUY, ("最高概率区通过概率、共振、风险、趋势四项过滤。",)
    if risk_score >= 60:
        return ProbabilityDecision.AVOID, tuple(reasons)
    return ProbabilityDecision.WATCH, tuple(reasons)


def fib_probability_result_to_output(result: FibProbabilityValidationResult) -> dict[str, object]:
    return {
        "Locust Plan V6": "Fib Probability Model + Multi-Wave Validation + Confluence Detection + Statistical Trading Zone",
        "Wave Set": tuple(_wave_to_output(wave) for wave in result.waves),
        "Fib Probability Score": {
            wave.layer.value: {
                f"{ratio:g} accuracy": accuracy
                for ratio, accuracy in wave.accuracy_by_ratio.items()
            }
            for wave in result.waves
        },
        "Confluence Zone": tuple(_confluence_to_output(zone) for zone in result.confluence_zones),
        "BUY_ZONE": _buy_zone_to_output(result.highest_probability_zone),
        "Trade Rule": {
            "BUY only if": (
                "probability > 70%",
                "confluence >= 2 waves",
                "risk_score < 40",
                "trend_alignment = true",
            ),
            "decision": result.decision.value,
            "reasons": result.reasons,
        },
        "Forbidden": {
            "禁止单Fib作为买点": True,
            "禁止固定0.786逻辑": True,
            "禁止无历史验证Fib": True,
            "禁止单波段决策": True,
        },
    }


def _build_probability_level(ratio: float, fib_price: float, bars: tuple[PriceBar, ...]) -> ProbabilityFibLevel:
    events: list[FibTouchEvent] = []
    for index, bar in enumerate(bars[:-1]):
        if not _touches_level(bar, fib_price):
            continue
        reaction = _classify_reaction(fib_price, bar, bars[index + 1])
        events.append(
            FibTouchEvent(
                timestamp=bar.timestamp,
                ratio=ratio,
                fib_price=round(fib_price, 3),
                reaction=reaction,
                success=reaction in {FibReaction.BOUNCE, FibReaction.REJECTION},
            )
        )
    successes = sum(1 for event in events if event.success)
    return ProbabilityFibLevel(
        ratio=ratio,
        fib_price=round(fib_price, 3),
        touch_events=tuple(events),
        total_touches=len(events),
        successful_reactions=successes,
        accuracy=_accuracy(successes, len(events)),
        verified=bool(events),
    )


def _classify_reaction(level_price: float, touch_bar: PriceBar, next_bar: PriceBar) -> FibReaction:
    if abs(next_bar.close - level_price) / level_price <= REACTION_THRESHOLD:
        return FibReaction.CONSOLIDATION
    if next_bar.close >= level_price * (1 + REACTION_THRESHOLD):
        return FibReaction.BOUNCE
    if touch_bar.close >= level_price and next_bar.close <= level_price * (1 - REACTION_THRESHOLD):
        return FibReaction.BREAK
    if next_bar.close <= level_price * (1 - REACTION_THRESHOLD):
        return FibReaction.REJECTION
    return FibReaction.CONSOLIDATION


def _highest_zone_to_buy_zone(zone: ProbabilityConfluenceZone | None) -> HighestProbabilityZone | None:
    if zone is None:
        return None
    return HighestProbabilityZone(
        price_range=(zone.zone_low, zone.zone_high),
        probability_score=zone.probability_score,
        supporting_waves=zone.supporting_waves,
        confidence=_confidence(zone.probability_score, len(zone.supporting_waves)),
        included_levels=zone.included_levels,
    )


def _validate_wave(layer: ProbabilityWaveLayer, wave: WaveSegment) -> None:
    if not wave.confirmed:
        raise ValueError("Fib probability model requires confirmed anchors.")
    if wave.low.kind is not SwingKind.LOW or wave.high.kind is not SwingKind.HIGH:
        raise ValueError("Fib probability model requires anchor_low and anchor_high.")
    if wave.low.price <= 0 or wave.high.price <= 0 or wave.high.price <= wave.low.price:
        raise ValueError("Fib probability anchors must be positive and ordered.")
    if _forbidden_anchor_timeframe(wave.low.timeframe) or _forbidden_anchor_timeframe(wave.high.timeframe):
        raise ValueError("Fib probability model forbids current price or intraday anchor.")
    expected = {
        ProbabilityWaveLayer.PRIMARY: {"1w", "week", "weekly", "周线"},
        ProbabilityWaveLayer.SECONDARY: {"1d", "day", "daily", "日线"},
        ProbabilityWaveLayer.MICRO: {"60min", "60m", "1h", "hour", "小时"},
    }
    if wave.low.timeframe.strip().lower() not in expected[layer] or wave.high.timeframe.strip().lower() not in expected[layer]:
        raise ValueError(f"{layer.value} requires matching timeframe anchors.")


def _validate_bars(bars: tuple[PriceBar, ...]) -> None:
    for bar in bars:
        if min(bar.high, bar.low, bar.close) <= 0:
            raise ValueError("Historical prices must be positive.")
        if bar.high < max(bar.low, bar.close):
            raise ValueError("Historical price high is inconsistent.")
        if bar.low > min(bar.high, bar.close):
            raise ValueError("Historical price low is inconsistent.")


def _touches_level(bar: PriceBar, fib_price: float) -> bool:
    return bar.low <= fib_price * (1 + TOUCH_TOLERANCE) and bar.high >= fib_price * (1 - TOUCH_TOLERANCE)


def _same_price_band(price_a: float, price_b: float, tolerance: float) -> bool:
    reference = (price_a + price_b) / 2
    return reference > 0 and abs(price_a - price_b) / reference < tolerance


def _accuracy(successes: int, touches: int) -> float:
    if touches == 0:
        return 0.0
    return round(successes / touches * 100, 2)


def _confidence(probability: float, wave_count: int) -> str:
    if probability >= 85 and wave_count >= 3:
        return "HIGH"
    if probability > 70 and wave_count >= 2:
        return "MEDIUM"
    return "LOW"


def _forbidden_anchor_timeframe(timeframe: str) -> bool:
    return timeframe.strip().lower() in {"tick", "1min", "5min", "15min", "30min", "intraday", "current_price", "day_high", "日内高点", "分时"}


def _wave_to_output(wave: ProbabilityWave) -> dict[str, object]:
    return {
        "layer": wave.layer.value,
        "wave_name": wave.wave_name,
        "anchor_low": wave.anchor_low,
        "anchor_high": wave.anchor_high,
        "fib_levels": {
            f"{level.ratio:g}": {
                "fib_price": level.fib_price,
                "total_touches": level.total_touches,
                "successful_reactions": level.successful_reactions,
                "accuracy": level.accuracy,
                "events": tuple(_event_to_output(event) for event in level.touch_events),
            }
            for level in wave.fib_levels
        },
    }


def _event_to_output(event: FibTouchEvent) -> dict[str, object]:
    return {
        "timestamp": event.timestamp,
        "ratio": event.ratio,
        "fib_price": event.fib_price,
        "reaction": event.reaction.value,
        "success": event.success,
    }


def _confluence_to_output(zone: ProbabilityConfluenceZone) -> dict[str, object]:
    return {
        "zone_low": zone.zone_low,
        "zone_high": zone.zone_high,
        "supporting_waves": tuple(layer.value for layer in zone.supporting_waves),
        "included_levels": tuple(_member_to_output(member) for member in zone.included_levels),
        "historical_success_rate": zone.historical_success_rate,
        "ConfluenceScore": zone.confluence_score,
        "probability_score": zone.probability_score,
    }


def _buy_zone_to_output(zone: HighestProbabilityZone | None) -> dict[str, object] | None:
    if zone is None:
        return None
    return {
        "price_range": zone.price_range,
        "probability_score": zone.probability_score,
        "supporting_waves": tuple(layer.value for layer in zone.supporting_waves),
        "confidence": zone.confidence,
        "included_levels": tuple(_member_to_output(member) for member in zone.included_levels),
    }


def _member_to_output(member: ProbabilityConfluenceMember) -> dict[str, object]:
    return {
        "layer": member.layer.value,
        "wave_name": member.wave_name,
        "ratio": member.ratio,
        "fib_price": member.fib_price,
        "accuracy": member.accuracy,
    }
