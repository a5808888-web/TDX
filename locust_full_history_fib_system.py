from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from fibonacci_wave_system import SwingKind, WaveSegment


FULL_HISTORY_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786, 1.272, 1.618)
RETRACEMENT_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786)
CONFLUENCE_TOLERANCE = 0.005


class LifecycleStage(str, Enum):
    IPO = "IPO阶段"
    GROWTH = "成长期"
    IMPULSE = "主升浪阶段"
    CORRECTION = "调整阶段"
    RESTART = "再启动阶段"


class FullHistoryLayer(str, Enum):
    GLOBAL = "Global Fib"
    SEGMENT = "Segment Fib"
    MID = "Mid Fib"
    SHORT = "Short Fib"
    MICRO = "Micro Fib"


class FullHistoryDecision(str, Enum):
    BUY = "BUY"
    WAIT = "WAIT"
    AVOID = "AVOID"


TIME_WEIGHTS: dict[FullHistoryLayer, float] = {
    FullHistoryLayer.GLOBAL: 0.4,
    FullHistoryLayer.SEGMENT: 0.3,
    FullHistoryLayer.MID: 0.2,
    FullHistoryLayer.SHORT: 0.1,
}


@dataclass(frozen=True)
class HistoryBar:
    timestamp: str
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class GlobalAnchor:
    ipo_low: float
    all_time_high: float
    all_time_low: float
    full_history_range: float


@dataclass(frozen=True)
class FullHistoryFibLevel:
    ratio: float
    fib_price: float
    level_type: str
    distance_to_current_price: float


@dataclass(frozen=True)
class SegmentFib:
    stage: LifecycleStage
    anchor_low: float
    anchor_high: float
    fib_levels: tuple[FullHistoryFibLevel, ...]
    timeframe: str
    validity_score: float


@dataclass(frozen=True)
class LayerFib:
    layer: FullHistoryLayer
    name: str
    anchor_low: float
    anchor_high: float
    fib_levels: tuple[FullHistoryFibLevel, ...]
    timeframe: str
    validity_score: float


@dataclass(frozen=True)
class FullHistoryConfluenceMember:
    layer: FullHistoryLayer
    name: str
    ratio: float
    fib_price: float
    validity_score: float


@dataclass(frozen=True)
class FullHistoryConfluenceZone:
    zone_low: float
    zone_high: float
    overlap_count: int
    included_levels: tuple[FullHistoryConfluenceMember, ...]
    weighted_support: float
    strength: str


@dataclass(frozen=True)
class FullHistoryFibInput:
    symbol: str
    current_price: float
    history: tuple[HistoryBar, ...]
    mid_wave: WaveSegment
    short_wave: WaveSegment
    micro_wave: WaveSegment
    short_stop_fall_confirmed: bool
    volume_supported: bool


@dataclass(frozen=True)
class FullHistoryFibResult:
    symbol: str
    current_price: float
    global_anchor: GlobalAnchor
    global_fib: LayerFib
    segment_fibs: tuple[SegmentFib, ...]
    mid_fib: LayerFib
    short_fib: LayerFib
    micro_fib: LayerFib
    confluence_zones: tuple[FullHistoryConfluenceZone, ...]
    probability_score: float
    decision: FullHistoryDecision
    reasons: tuple[str, ...]


def run_full_history_fib_system(data: FullHistoryFibInput) -> FullHistoryFibResult:
    _validate_input(data)
    global_anchor = build_global_anchor(data.history)
    global_fib = build_layer_fib(
        FullHistoryLayer.GLOBAL,
        "全历史",
        global_anchor.all_time_low,
        global_anchor.all_time_high,
        data.current_price,
        "IPO至今",
        validity_score=100.0,
    )
    segment_fibs = build_lifecycle_segment_fibs(data.history, data.current_price)
    mid_fib = build_wave_layer_fib(FullHistoryLayer.MID, "中期", data.mid_wave, data.current_price)
    short_fib = build_wave_layer_fib(FullHistoryLayer.SHORT, "短期", data.short_wave, data.current_price)
    micro_fib = build_wave_layer_fib(FullHistoryLayer.MICRO, "微结构", data.micro_wave, data.current_price)
    zones = detect_full_history_confluence_zones((global_fib, *segment_fibs_to_layers(segment_fibs), mid_fib, short_fib, micro_fib))
    probability_score = calculate_full_history_probability_score(
        zones=zones,
        current_price=data.current_price,
        global_fib=global_fib,
        segment_fibs=segment_fibs,
        mid_fib=mid_fib,
        short_stop_fall_confirmed=data.short_stop_fall_confirmed,
    )
    decision, reasons = evaluate_full_history_decision(
        current_price=data.current_price,
        global_fib=global_fib,
        segment_fibs=segment_fibs,
        mid_fib=mid_fib,
        zones=zones,
        short_stop_fall_confirmed=data.short_stop_fall_confirmed,
        volume_supported=data.volume_supported,
        probability_score=probability_score,
    )
    return FullHistoryFibResult(
        symbol=data.symbol,
        current_price=data.current_price,
        global_anchor=global_anchor,
        global_fib=global_fib,
        segment_fibs=segment_fibs,
        mid_fib=mid_fib,
        short_fib=short_fib,
        micro_fib=micro_fib,
        confluence_zones=zones,
        probability_score=probability_score,
        decision=decision,
        reasons=reasons,
    )


def build_global_anchor(history: tuple[HistoryBar, ...]) -> GlobalAnchor:
    ipo_low = history[0].low
    all_time_high = max(bar.high for bar in history)
    all_time_low = min(bar.low for bar in history)
    return GlobalAnchor(
        ipo_low=ipo_low,
        all_time_high=all_time_high,
        all_time_low=all_time_low,
        full_history_range=round(all_time_high - all_time_low, 3),
    )


def build_lifecycle_segment_fibs(history: tuple[HistoryBar, ...], current_price: float) -> tuple[SegmentFib, ...]:
    chunks = _split_lifecycle(history)
    return tuple(
        SegmentFib(
            stage=stage,
            anchor_low=min(bar.low for bar in bars),
            anchor_high=max(bar.high for bar in bars),
            fib_levels=build_fib_levels(min(bar.low for bar in bars), max(bar.high for bar in bars), current_price),
            timeframe=f"{bars[0].timestamp} -> {bars[-1].timestamp}",
            validity_score=_segment_validity_score(bars),
        )
        for stage, bars in chunks
    )


def build_layer_fib(
    layer: FullHistoryLayer,
    name: str,
    anchor_low: float,
    anchor_high: float,
    current_price: float,
    timeframe: str,
    validity_score: float,
) -> LayerFib:
    if anchor_low <= 0 or anchor_high <= 0 or anchor_high <= anchor_low:
        raise ValueError("Full History Fib anchors must be positive and ordered.")
    return LayerFib(
        layer=layer,
        name=name,
        anchor_low=anchor_low,
        anchor_high=anchor_high,
        fib_levels=build_fib_levels(anchor_low, anchor_high, current_price),
        timeframe=timeframe,
        validity_score=round(validity_score, 2),
    )


def build_wave_layer_fib(layer: FullHistoryLayer, name: str, wave: WaveSegment, current_price: float) -> LayerFib:
    _validate_wave(layer, wave)
    return build_layer_fib(
        layer=layer,
        name=name,
        anchor_low=wave.low.price,
        anchor_high=wave.high.price,
        current_price=current_price,
        timeframe=f"{wave.low.timeframe}/{wave.high.timeframe}",
        validity_score=85.0 if wave.confirmed else 0.0,
    )


def build_fib_levels(anchor_low: float, anchor_high: float, current_price: float) -> tuple[FullHistoryFibLevel, ...]:
    price_range = anchor_high - anchor_low
    return tuple(
        FullHistoryFibLevel(
            ratio=ratio,
            fib_price=round(anchor_high - price_range * ratio if ratio in RETRACEMENT_RATIOS else anchor_high + price_range * (ratio - 1), 3),
            level_type="retracement" if ratio in RETRACEMENT_RATIOS else "extension",
            distance_to_current_price=round((anchor_high - price_range * ratio if ratio in RETRACEMENT_RATIOS else anchor_high + price_range * (ratio - 1)) - current_price, 3),
        )
        for ratio in FULL_HISTORY_RATIOS
    )


def segment_fibs_to_layers(segment_fibs: tuple[SegmentFib, ...]) -> tuple[LayerFib, ...]:
    return tuple(
        LayerFib(
            layer=FullHistoryLayer.SEGMENT,
            name=fib.stage.value,
            anchor_low=fib.anchor_low,
            anchor_high=fib.anchor_high,
            fib_levels=fib.fib_levels,
            timeframe=fib.timeframe,
            validity_score=fib.validity_score,
        )
        for fib in segment_fibs
    )


def detect_full_history_confluence_zones(
    layers: Iterable[LayerFib],
    tolerance: float = CONFLUENCE_TOLERANCE,
) -> tuple[FullHistoryConfluenceZone, ...]:
    levels = tuple(
        FullHistoryConfluenceMember(
            layer=layer.layer,
            name=layer.name,
            ratio=level.ratio,
            fib_price=level.fib_price,
            validity_score=layer.validity_score,
        )
        for layer in layers
        for level in layer.fib_levels
    )
    zones: list[FullHistoryConfluenceZone] = []
    seen: set[tuple[tuple[str, str, float, float], ...]] = set()
    for base in levels:
        cluster = tuple(item for item in levels if _same_price_band(base.fib_price, item.fib_price, tolerance))
        if len({(item.layer, item.name) for item in cluster}) < 2:
            continue
        key = tuple(sorted((item.layer.value, item.name, item.ratio, item.fib_price) for item in cluster))
        if key in seen:
            continue
        seen.add(key)
        weighted_support = _weighted_support(cluster)
        zones.append(
            FullHistoryConfluenceZone(
                zone_low=round(min(item.fib_price for item in cluster), 3),
                zone_high=round(max(item.fib_price for item in cluster), 3),
                overlap_count=len(cluster),
                included_levels=cluster,
                weighted_support=weighted_support,
                strength=_confluence_strength(weighted_support, len(cluster)),
            )
        )
    return tuple(sorted(zones, key=lambda zone: (-zone.weighted_support, -zone.overlap_count, zone.zone_low)))


def calculate_full_history_probability_score(
    zones: tuple[FullHistoryConfluenceZone, ...],
    current_price: float,
    global_fib: LayerFib,
    segment_fibs: tuple[SegmentFib, ...],
    mid_fib: LayerFib,
    short_stop_fall_confirmed: bool,
) -> float:
    global_score = 100.0 if current_price >= global_fib.anchor_low else 0.0
    segment_score = 100.0 if _current_segment_confluence_count(zones, current_price) >= 2 else 0.0
    mid_score = 100.0 if _current_in_retracement_band(mid_fib, current_price, 0.382, 0.786) else 0.0
    short_score = 100.0 if short_stop_fall_confirmed else 0.0
    return round(
        global_score * TIME_WEIGHTS[FullHistoryLayer.GLOBAL]
        + segment_score * TIME_WEIGHTS[FullHistoryLayer.SEGMENT]
        + mid_score * TIME_WEIGHTS[FullHistoryLayer.MID]
        + short_score * TIME_WEIGHTS[FullHistoryLayer.SHORT],
        2,
    )


def evaluate_full_history_decision(
    current_price: float,
    global_fib: LayerFib,
    segment_fibs: tuple[SegmentFib, ...],
    mid_fib: LayerFib,
    zones: tuple[FullHistoryConfluenceZone, ...],
    short_stop_fall_confirmed: bool,
    volume_supported: bool,
    probability_score: float,
) -> tuple[FullHistoryDecision, tuple[str, ...]]:
    reasons: list[str] = []
    if current_price < global_fib.anchor_low:
        return FullHistoryDecision.AVOID, ("Global Fib结构已破，全历史结构失效。",)
    if _current_segment_confluence_count(zones, current_price) < 2:
        reasons.append("Segment Fib未形成至少2层生命周期共振。")
    if not _current_in_retracement_band(mid_fib, current_price, 0.382, 0.786):
        reasons.append("Mid Fib未进入0.382-0.786回撤区。")
    if not short_stop_fall_confirmed:
        reasons.append("Short Fib未确认止跌。")
    if not volume_supported:
        reasons.append("成交量不支持。")
    if probability_score < 70:
        reasons.append("全历史概率融合分低于70。")
    if reasons:
        return FullHistoryDecision.WAIT, tuple(reasons)
    return FullHistoryDecision.BUY, ("Global未破、生命周期共振、中期回撤、短期止跌和成交量同时满足。",)


def full_history_fib_to_output(result: FullHistoryFibResult) -> dict[str, object]:
    return {
        "Locust Plan V7": "Full History Market Structure System + Multi-Layer Fibonacci Engine + Lifecycle Decomposition Model + Probability Confluence System",
        "Global Anchor": {
            "ipo_low": result.global_anchor.ipo_low,
            "all_time_high": result.global_anchor.all_time_high,
            "all_time_low": result.global_anchor.all_time_low,
            "full_history_range": result.global_anchor.full_history_range,
        },
        "Lifecycle Segments": tuple(_segment_to_output(item) for item in result.segment_fibs),
        "Global Fib": _layer_to_output(result.global_fib),
        "Segment Fib": tuple(_segment_to_output(item) for item in result.segment_fibs),
        "Mid Fib": _layer_to_output(result.mid_fib),
        "Short Fib": _layer_to_output(result.short_fib),
        "Micro Fib": _layer_to_output(result.micro_fib),
        "Time Weights": {
            "Global Fib": 40,
            "Segment Fib": 30,
            "Mid Fib": 20,
            "Short Fib": 10,
        },
        "Confluence Zone": tuple(_zone_to_output(zone) for zone in result.confluence_zones),
        "Probability Score": result.probability_score,
        "Trade Rule": {
            "BUY ONLY IF": (
                "Global Fib结构不破",
                "Segment Fib至少2层共振",
                "Mid Fib进入0.382-0.786",
                "Short Fib确认止跌",
                "成交量支持",
            ),
            "decision": result.decision.value,
            "reasons": result.reasons,
        },
        "Forbidden": {
            "禁止单周期Fib": True,
            "禁止忽略IPO结构": True,
            "禁止无生命周期分析": True,
            "禁止单Fib决策": True,
            "禁止短周期覆盖长期结构": True,
        },
    }


def _split_lifecycle(history: tuple[HistoryBar, ...]) -> tuple[tuple[LifecycleStage, tuple[HistoryBar, ...]], ...]:
    stages = tuple(LifecycleStage)
    size = len(history)
    chunks: list[tuple[LifecycleStage, tuple[HistoryBar, ...]]] = []
    for index, stage in enumerate(stages):
        start = round(index * size / len(stages))
        end = round((index + 1) * size / len(stages))
        bars = history[start:end] or history[max(0, start - 1):start + 1]
        chunks.append((stage, tuple(bars)))
    return tuple(chunks)


def _segment_validity_score(bars: tuple[HistoryBar, ...]) -> float:
    if not bars:
        return 0.0
    price_range = max(bar.high for bar in bars) - min(bar.low for bar in bars)
    avg_close = sum(bar.close for bar in bars) / len(bars)
    volume_trend = bars[-1].volume / bars[0].volume if bars[0].volume > 0 else 1.0
    return round(min(100.0, 45 + min(35.0, price_range / avg_close * 100) + min(20.0, max(0.0, volume_trend - 1) * 10)), 2)


def _validate_input(data: FullHistoryFibInput) -> None:
    if data.current_price <= 0:
        raise ValueError("Full History Fib requires a positive current price.")
    if len(data.history) < 10:
        raise ValueError("Full History Fib requires IPO-to-now history with at least 10 bars.")
    for bar in data.history:
        if min(bar.high, bar.low, bar.close, bar.volume) <= 0:
            raise ValueError("Full History Fib history bars must be positive.")
        if bar.high < max(bar.low, bar.close) or bar.low > min(bar.high, bar.close):
            raise ValueError("Full History Fib history bar is inconsistent.")


def _validate_wave(layer: FullHistoryLayer, wave: WaveSegment) -> None:
    if not wave.confirmed:
        raise ValueError(f"{layer.value} requires confirmed anchors.")
    if wave.low.kind is not SwingKind.LOW or wave.high.kind is not SwingKind.HIGH:
        raise ValueError(f"{layer.value} requires confirmed swing low/high anchors.")
    if wave.low.price <= 0 or wave.high.price <= 0 or wave.high.price <= wave.low.price:
        raise ValueError(f"{layer.value} anchors must be positive and ordered.")
    if _forbidden_timeframe(wave.low.timeframe) or _forbidden_timeframe(wave.high.timeframe):
        raise ValueError("Full History Fib forbids current price, tick, and intraday high as anchors.")


def _current_segment_confluence_count(zones: tuple[FullHistoryConfluenceZone, ...], current_price: float) -> int:
    current_zones = tuple(zone for zone in zones if zone.zone_low <= current_price <= zone.zone_high)
    if not current_zones:
        return 0
    return max(
        sum(1 for member in zone.included_levels if member.layer is FullHistoryLayer.SEGMENT)
        for zone in current_zones
    )


def _current_in_retracement_band(layer: LayerFib, current_price: float, high_ratio: float, low_ratio: float) -> bool:
    high_price = _level_price(layer, high_ratio)
    low_price = _level_price(layer, low_ratio)
    return min(high_price, low_price) <= current_price <= max(high_price, low_price)


def _level_price(layer: LayerFib, ratio: float) -> float:
    for level in layer.fib_levels:
        if abs(level.ratio - ratio) < 1e-9:
            return level.fib_price
    raise ValueError(f"Missing Fib ratio: {ratio}")


def _weighted_support(cluster: tuple[FullHistoryConfluenceMember, ...]) -> float:
    layers = {item.layer for item in cluster if item.layer in TIME_WEIGHTS}
    segment_bonus = min(0.3, 0.1 * len({item.name for item in cluster if item.layer is FullHistoryLayer.SEGMENT}))
    return round((sum(TIME_WEIGHTS[layer] for layer in layers) + segment_bonus) * 100, 2)


def _confluence_strength(weighted_support: float, overlap_count: int) -> str:
    if weighted_support >= 80 or overlap_count >= 4:
        return "强共振"
    if weighted_support >= 50 or overlap_count >= 3:
        return "中共振"
    return "弱共振"


def _same_price_band(price_a: float, price_b: float, tolerance: float) -> bool:
    reference = (price_a + price_b) / 2
    return reference > 0 and abs(price_a - price_b) / reference < tolerance


def _forbidden_timeframe(timeframe: str) -> bool:
    return timeframe.strip().lower() in {"tick", "current_price", "day_high", "日内高点", "分时"}


def _layer_to_output(layer: LayerFib) -> dict[str, object]:
    return {
        "name": layer.name,
        "anchor_low": layer.anchor_low,
        "anchor_high": layer.anchor_high,
        "timeframe": layer.timeframe,
        "validity_score": layer.validity_score,
        "fib_levels": _levels_to_output(layer.fib_levels),
    }


def _segment_to_output(segment: SegmentFib) -> dict[str, object]:
    return {
        "stage": segment.stage.value,
        "anchor_low": segment.anchor_low,
        "anchor_high": segment.anchor_high,
        "fib_levels": _levels_to_output(segment.fib_levels),
        "timeframe": segment.timeframe,
        "validity_score": segment.validity_score,
    }


def _levels_to_output(levels: tuple[FullHistoryFibLevel, ...]) -> dict[str, object]:
    return {
        f"{level.ratio:g}": {
            "fib_price": level.fib_price,
            "type": level.level_type,
            "distance_to_current_price": level.distance_to_current_price,
        }
        for level in levels
    }


def _zone_to_output(zone: FullHistoryConfluenceZone) -> dict[str, object]:
    return {
        "zone_low": zone.zone_low,
        "zone_high": zone.zone_high,
        "overlap_count": zone.overlap_count,
        "weighted_support": zone.weighted_support,
        "strength": zone.strength,
        "included_levels": tuple(
            {
                "layer": member.layer.value,
                "name": member.name,
                "ratio": member.ratio,
                "fib_price": member.fib_price,
                "validity_score": member.validity_score,
            }
            for member in zone.included_levels
        ),
    }
