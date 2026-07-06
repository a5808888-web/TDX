from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from fibonacci_wave_system import SwingKind, WaveSegment


FIB_HYPOTHESIS_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786, 1.272, 1.618)
CORE_CONFLUENCE_RATIOS: tuple[float, ...] = (0.382, 0.5, 0.618)
TOUCH_TOLERANCE = 0.005
CONFLUENCE_TOLERANCE = 0.005
REACTION_THRESHOLD = 0.003


class HypothesisLayer(str, Enum):
    MAIN = "main_weekly"
    MID = "mid_daily"
    SMALL = "small_60min"


class ZoneType(str, Enum):
    PRIMARY_BUY_ZONE = "PRIMARY_BUY_ZONE"
    SECONDARY_BUY_ZONE = "SECONDARY_BUY_ZONE"
    INVALID_FIB_ZONE = "INVALID_FIB_ZONE"


class ZoneStrength(str, Enum):
    WEAK = "weak"
    STRONG = "strong"
    CORE = "core"


@dataclass(frozen=True)
class PriceBar:
    timestamp: str
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class FibHypothesisLevel:
    ratio: float
    fib_price: float
    touches: int
    successes: int
    accuracy_score: float
    verified: bool


@dataclass(frozen=True)
class HypothesisWave:
    layer: HypothesisLayer
    wave_name: str
    anchor_low: float
    anchor_high: float
    fib_levels: tuple[FibHypothesisLevel, ...]
    validity_score: float
    total_touches: int
    successful_touches: int


@dataclass(frozen=True)
class ConfluenceMember:
    layer: HypothesisLayer
    wave_name: str
    ratio: float
    fib_price: float
    level_accuracy_score: float


@dataclass(frozen=True)
class StatisticalConfluenceZone:
    zone_low: float
    zone_high: float
    included_levels: tuple[ConfluenceMember, ...]
    overlap_count: int
    average_accuracy_score: float
    confidence_score: float
    strength: ZoneStrength


@dataclass(frozen=True)
class OptimalEntryZone:
    zone_type: ZoneType
    zone_low: float
    zone_high: float
    confidence_score: float
    included_levels: tuple[ConfluenceMember, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class FibHypothesisSystemInput:
    main_wave: WaveSegment
    mid_wave: WaveSegment
    small_wave: WaveSegment
    historical_prices: tuple[PriceBar, ...]


@dataclass(frozen=True)
class FibHypothesisSystemResult:
    hypothesis_waves: tuple[HypothesisWave, ...]
    confluence_zones: tuple[StatisticalConfluenceZone, ...]
    primary_buy_zones: tuple[OptimalEntryZone, ...]
    secondary_buy_zones: tuple[OptimalEntryZone, ...]
    invalid_fib_zones: tuple[OptimalEntryZone, ...]


def run_fib_hypothesis_system(data: FibHypothesisSystemInput) -> FibHypothesisSystemResult:
    if len(data.historical_prices) < 3:
        raise ValueError("Statistical validation requires at least 3 historical price bars.")
    _validate_price_bars(data.historical_prices)

    hypotheses = (
        build_hypothesis_wave(HypothesisLayer.MAIN, data.main_wave, data.historical_prices),
        build_hypothesis_wave(HypothesisLayer.MID, data.mid_wave, data.historical_prices),
        build_hypothesis_wave(HypothesisLayer.SMALL, data.small_wave, data.historical_prices),
    )
    confluence_zones = detect_statistical_confluence_zones(hypotheses)
    primary, secondary, invalid = extract_optimal_entry_zones(hypotheses, confluence_zones)

    return FibHypothesisSystemResult(
        hypothesis_waves=hypotheses,
        confluence_zones=confluence_zones,
        primary_buy_zones=primary,
        secondary_buy_zones=secondary,
        invalid_fib_zones=invalid,
    )


def build_hypothesis_wave(
    layer: HypothesisLayer,
    wave: WaveSegment,
    historical_prices: tuple[PriceBar, ...],
) -> HypothesisWave:
    _validate_hypothesis_wave(layer, wave)
    price_range = wave.high.price - wave.low.price
    levels = tuple(
        _validate_fib_level(ratio, wave.high.price - price_range * ratio, historical_prices)
        if ratio < 1
        else _validate_fib_level(ratio, wave.low.price + price_range * ratio, historical_prices)
        for ratio in FIB_HYPOTHESIS_RATIOS
    )
    total_touches = sum(level.touches for level in levels)
    successful_touches = sum(level.successes for level in levels)
    validity_score = _accuracy(successful_touches, total_touches)

    return HypothesisWave(
        layer=layer,
        wave_name=wave.name or layer.value,
        anchor_low=wave.low.price,
        anchor_high=wave.high.price,
        fib_levels=levels,
        validity_score=validity_score,
        total_touches=total_touches,
        successful_touches=successful_touches,
    )


def detect_statistical_confluence_zones(
    hypotheses: Iterable[HypothesisWave],
    tolerance: float = CONFLUENCE_TOLERANCE,
) -> tuple[StatisticalConfluenceZone, ...]:
    levels = tuple(
        ConfluenceMember(
            layer=hypothesis.layer,
            wave_name=hypothesis.wave_name,
            ratio=level.ratio,
            fib_price=level.fib_price,
            level_accuracy_score=level.accuracy_score,
        )
        for hypothesis in hypotheses
        for level in hypothesis.fib_levels
        if level.ratio in CORE_CONFLUENCE_RATIOS and level.verified
    )
    zones: list[StatisticalConfluenceZone] = []
    seen: set[tuple[tuple[str, str, float], ...]] = set()

    for base in levels:
        cluster = tuple(level for level in levels if _same_price_band(base.fib_price, level.fib_price, tolerance))
        if len({level.layer for level in cluster}) < 2:
            continue
        key = tuple(sorted((level.layer.value, level.wave_name, level.ratio) for level in cluster))
        if key in seen:
            continue
        seen.add(key)

        zone_low = min(level.fib_price for level in cluster)
        zone_high = max(level.fib_price for level in cluster)
        average_accuracy = sum(level.level_accuracy_score for level in cluster) / len(cluster)
        overlap_score = min(100.0, len(cluster) / 4 * 100)
        confidence = round(average_accuracy * 0.65 + overlap_score * 0.35, 2)
        zones.append(
            StatisticalConfluenceZone(
                zone_low=zone_low,
                zone_high=zone_high,
                included_levels=cluster,
                overlap_count=len(cluster),
                average_accuracy_score=round(average_accuracy, 2),
                confidence_score=confidence,
                strength=_classify_zone_strength(len(cluster)),
            )
        )

    return tuple(sorted(zones, key=lambda zone: (-zone.confidence_score, -zone.overlap_count, zone.zone_low)))


def extract_optimal_entry_zones(
    hypotheses: tuple[HypothesisWave, ...],
    confluence_zones: tuple[StatisticalConfluenceZone, ...],
) -> tuple[tuple[OptimalEntryZone, ...], tuple[OptimalEntryZone, ...], tuple[OptimalEntryZone, ...]]:
    primary: list[OptimalEntryZone] = []
    secondary: list[OptimalEntryZone] = []
    invalid: list[OptimalEntryZone] = []

    for zone in confluence_zones:
        reasons = (
            f"{zone.overlap_count}个已验证斐波层级共振",
            f"平均命中率{zone.average_accuracy_score:.2f}",
            "价格差小于0.5%",
        )
        entry_zone = OptimalEntryZone(
            zone_type=ZoneType.PRIMARY_BUY_ZONE if zone.confidence_score >= 70 else ZoneType.SECONDARY_BUY_ZONE,
            zone_low=round(zone.zone_low, 3),
            zone_high=round(zone.zone_high, 3),
            confidence_score=zone.confidence_score,
            included_levels=zone.included_levels,
            reasons=reasons,
        )
        if entry_zone.zone_type is ZoneType.PRIMARY_BUY_ZONE:
            primary.append(entry_zone)
        else:
            secondary.append(entry_zone)

    verified_keys = {
        (member.layer, member.wave_name, member.ratio, member.fib_price)
        for zone in confluence_zones
        for member in zone.included_levels
    }
    for hypothesis in hypotheses:
        for level in hypothesis.fib_levels:
            key = (hypothesis.layer, hypothesis.wave_name, level.ratio, level.fib_price)
            if key in verified_keys:
                continue
            if not level.verified or level.accuracy_score < 50:
                invalid.append(
                    OptimalEntryZone(
                        zone_type=ZoneType.INVALID_FIB_ZONE,
                        zone_low=round(level.fib_price * (1 - TOUCH_TOLERANCE), 3),
                        zone_high=round(level.fib_price * (1 + TOUCH_TOLERANCE), 3),
                        confidence_score=level.accuracy_score,
                        included_levels=(
                            ConfluenceMember(
                                layer=hypothesis.layer,
                                wave_name=hypothesis.wave_name,
                                ratio=level.ratio,
                                fib_price=level.fib_price,
                                level_accuracy_score=level.accuracy_score,
                            ),
                        ),
                        reasons=("未通过历史触达反应验证", "禁止作为单一斐波买点"),
                    )
                )

    return tuple(primary), tuple(secondary), tuple(invalid)


def fib_hypothesis_result_to_output(result: FibHypothesisSystemResult) -> dict[str, object]:
    return {
        "Locust Plan V6": "Fibonacci Hypothesis System + Statistical Validation + Confluence Detection + Optimal Zone Extraction",
        "HypothesisWave": tuple(_hypothesis_to_output(hypothesis) for hypothesis in result.hypothesis_waves),
        "FibAccuracyScore": {
            hypothesis.layer.value: hypothesis.validity_score for hypothesis in result.hypothesis_waves
        },
        "ConfluenceZone": tuple(_confluence_to_output(zone) for zone in result.confluence_zones),
        "OptimalEntryZone": {
            "高概率买点区": tuple(_entry_zone_to_output(zone) for zone in result.primary_buy_zones),
            "次级买点区": tuple(_entry_zone_to_output(zone) for zone in result.secondary_buy_zones),
            "无效Fib区": tuple(_entry_zone_to_output(zone) for zone in result.invalid_fib_zones),
        },
        "Rules": {
            "禁止单Fib决策": True,
            "禁止未验证Fib": True,
            "禁止用当前价格强行画锚点": True,
            "共振误差": "<0.5%",
        },
    }


def _validate_fib_level(ratio: float, fib_price: float, prices: tuple[PriceBar, ...]) -> FibHypothesisLevel:
    touches = 0
    successes = 0
    for index, bar in enumerate(prices[:-1]):
        if not _touches_level(bar, fib_price):
            continue
        touches += 1
        if _reacts_after_touch(fib_price, prices[index + 1]):
            successes += 1

    return FibHypothesisLevel(
        ratio=ratio,
        fib_price=round(fib_price, 3),
        touches=touches,
        successes=successes,
        accuracy_score=_accuracy(successes, touches),
        verified=touches > 0 and successes > 0,
    )


def _validate_hypothesis_wave(layer: HypothesisLayer, wave: WaveSegment) -> None:
    if not wave.confirmed:
        raise ValueError("Hypothesis Wave requires confirmed anchors.")
    if wave.low.kind is not SwingKind.LOW or wave.high.kind is not SwingKind.HIGH:
        raise ValueError("Hypothesis Wave requires one swing low and one swing high.")
    if wave.low.price <= 0 or wave.high.price <= 0 or wave.high.price <= wave.low.price:
        raise ValueError("Hypothesis Wave anchors must be positive and ordered.")
    if _forbidden_anchor_timeframe(wave.low.timeframe) or _forbidden_anchor_timeframe(wave.high.timeframe):
        raise ValueError("Current price or intraday extreme cannot be used as a Fib hypothesis anchor.")
    expected_timeframes = {
        HypothesisLayer.MAIN: {"1w", "week", "weekly", "周线"},
        HypothesisLayer.MID: {"1d", "day", "daily", "日线"},
        HypothesisLayer.SMALL: {"60min", "60m", "1h", "hour", "小时"},
    }
    if wave.low.timeframe.strip().lower() not in expected_timeframes[layer] or wave.high.timeframe.strip().lower() not in expected_timeframes[layer]:
        raise ValueError(f"{layer.value} requires its matching timeframe anchors.")


def _validate_price_bars(prices: tuple[PriceBar, ...]) -> None:
    for bar in prices:
        if min(bar.high, bar.low, bar.close) <= 0:
            raise ValueError("Historical prices must be positive.")
        if bar.high < max(bar.low, bar.close):
            raise ValueError("Historical price bar high is inconsistent.")
        if bar.low > min(bar.high, bar.close):
            raise ValueError("Historical price bar low is inconsistent.")


def _touches_level(bar: PriceBar, level_price: float, tolerance: float = TOUCH_TOLERANCE) -> bool:
    lower = level_price * (1 - tolerance)
    upper = level_price * (1 + tolerance)
    return bar.low <= upper and bar.high >= lower


def _reacts_after_touch(level_price: float, next_bar: PriceBar, reaction_threshold: float = REACTION_THRESHOLD) -> bool:
    return next_bar.close >= level_price * (1 + reaction_threshold) or next_bar.close <= level_price * (1 - reaction_threshold)


def _same_price_band(price_a: float, price_b: float, tolerance: float) -> bool:
    reference = (price_a + price_b) / 2
    if reference <= 0:
        return False
    return abs(price_a - price_b) / reference < tolerance


def _accuracy(successes: int, touches: int) -> float:
    if touches == 0:
        return 0.0
    return round(successes / touches * 100, 2)


def _classify_zone_strength(overlap_count: int) -> ZoneStrength:
    if overlap_count >= 4:
        return ZoneStrength.CORE
    if overlap_count >= 3:
        return ZoneStrength.STRONG
    return ZoneStrength.WEAK


def _forbidden_anchor_timeframe(timeframe: str) -> bool:
    normalized = timeframe.strip().lower()
    return normalized in {"tick", "1min", "5min", "15min", "30min", "intraday", "day_high", "current_price", "分时", "日内高点"}


def _hypothesis_to_output(hypothesis: HypothesisWave) -> dict[str, object]:
    return {
        "layer": hypothesis.layer.value,
        "wave_name": hypothesis.wave_name,
        "anchor_low": hypothesis.anchor_low,
        "anchor_high": hypothesis.anchor_high,
        "validity_score": hypothesis.validity_score,
        "successful_touches": hypothesis.successful_touches,
        "total_touches": hypothesis.total_touches,
        "fib_levels": {
            f"{level.ratio:g}": {
                "fib_price": level.fib_price,
                "touches": level.touches,
                "successes": level.successes,
                "accuracy_score": level.accuracy_score,
                "verified": level.verified,
            }
            for level in hypothesis.fib_levels
        },
    }


def _confluence_to_output(zone: StatisticalConfluenceZone) -> dict[str, object]:
    return {
        "zone_low": zone.zone_low,
        "zone_high": zone.zone_high,
        "overlap_count": zone.overlap_count,
        "average_accuracy_score": zone.average_accuracy_score,
        "confidence_score": zone.confidence_score,
        "strength": zone.strength.value,
        "included_levels": tuple(_member_to_output(member) for member in zone.included_levels),
    }


def _entry_zone_to_output(zone: OptimalEntryZone) -> dict[str, object]:
    return {
        "zone_type": zone.zone_type.value,
        "BUY ZONE": {"下沿": zone.zone_low, "上沿": zone.zone_high},
        "Confidence Score": zone.confidence_score,
        "included_levels": tuple(_member_to_output(member) for member in zone.included_levels),
        "reasons": zone.reasons,
    }


def _member_to_output(member: ConfluenceMember) -> dict[str, object]:
    return {
        "layer": member.layer.value,
        "wave_name": member.wave_name,
        "ratio": member.ratio,
        "fib_price": member.fib_price,
        "level_accuracy_score": member.level_accuracy_score,
    }
