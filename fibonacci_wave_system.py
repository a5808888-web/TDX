from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Literal


class WaveTier(str, Enum):
    PRIMARY = "primary"
    OPERATING = "operating"
    EXECUTION = "execution"
    MAIN = "main"
    RECENT = "recent"
    MICRO = "micro"


class SwingKind(str, Enum):
    HIGH = "high"
    LOW = "low"


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"


FibKind = Literal["retracement", "extension"]
ResonanceStrength = Literal["strong", "medium", "none"]
Decision = Literal["buy", "watch"]
ConfluenceStrength = Literal["weak", "strong", "core"]
MarketScope = Literal["a_share", "global", "tradingview"]
MarketDataSource = Literal["akshare", "eastmoney", "futu_api", "tradingview"]


RETRACEMENT_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786)
EXTENSION_RATIOS: tuple[float, ...] = (1.272, 1.414, 1.618)
CONFLUENCE_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786, 1.272)
CONFLUENCE_TOLERANCE = 0.003

MAIN_WAVE_TIERS = {WaveTier.PRIMARY, WaveTier.MAIN}
RECENT_WAVE_TIERS = {WaveTier.OPERATING, WaveTier.RECENT}
MICRO_WAVE_TIERS = {WaveTier.EXECUTION, WaveTier.MICRO}

DATA_SOURCE_RULES: dict[MarketScope, tuple[MarketDataSource, ...]] = {
    "a_share": ("akshare",),
    "global": ("futu_api",),
    "tradingview": ("tradingview",),
}


@dataclass(frozen=True)
class SwingPoint:
    price: float
    kind: SwingKind
    timestamp: str
    timeframe: str
    tier: WaveTier
    confirmed: bool


@dataclass(frozen=True)
class WaveSegment:
    low: SwingPoint
    high: SwingPoint
    tier: WaveTier
    direction: TrendDirection = TrendDirection.UP
    name: str | None = None

    @property
    def confirmed(self) -> bool:
        return self.low.confirmed and self.high.confirmed

    @property
    def price_range(self) -> float:
        return self.high.price - self.low.price

    def validate_anchor_pair(self) -> None:
        if self.tier is not WaveTier.OPERATING:
            raise ValueError("Fibonacci can only be calculated from the operating wave.")
        if self.low.tier is not WaveTier.OPERATING or self.high.tier is not WaveTier.OPERATING:
            raise ValueError("Fibonacci anchors must both belong to the operating wave.")
        if self.low.kind is not SwingKind.LOW or self.high.kind is not SwingKind.HIGH:
            raise ValueError("Fibonacci requires one confirmed swing low and one confirmed swing high.")
        if not self.confirmed:
            raise ValueError("Fibonacci anchors must be confirmed before calculation.")
        if self.low.price <= 0 or self.high.price <= 0:
            raise ValueError("Anchor prices must be positive.")
        if self.high.price <= self.low.price:
            raise ValueError("anchor_high must be greater than anchor_low for an upward operating wave.")


@dataclass(frozen=True)
class FibLevel:
    ratio: float
    fib_kind: FibKind
    fib_price: float
    distance_to_current_price: float


@dataclass(frozen=True)
class FibMatrix:
    anchor_low: float
    anchor_high: float
    range: float
    current_price: float
    retracements: tuple[FibLevel, ...]
    extensions: tuple[FibLevel, ...]
    wave_name: str | None = None

    @property
    def all_levels(self) -> tuple[FibLevel, ...]:
        return self.retracements + self.extensions


@dataclass(frozen=True)
class ResonanceMatch:
    first_wave: str
    first_ratio: float
    first_price: float
    second_wave: str
    second_ratio: float
    second_price: float
    delta: float
    strength: ResonanceStrength
    price_band: tuple[float, float] | None


@dataclass(frozen=True)
class BuyPointContext:
    operating_wave_confirmed: bool
    stop_fall_confirmed: bool
    locust_score_supported: bool
    near_intraday_high: bool


@dataclass(frozen=True)
class BuyPointSignal:
    decision: Decision
    label: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ConfluenceFibPoint:
    wave_layer: str
    wave_name: str
    ratio: float
    fib_price: float
    distance_to_current_price: float


@dataclass(frozen=True)
class ConfluenceFibMatrix:
    wave_layer: str
    wave_name: str
    anchor_low: float
    anchor_high: float
    range: float
    current_price: float
    levels: tuple[ConfluenceFibPoint, ...]


@dataclass(frozen=True)
class ConfluenceZone:
    price_range: tuple[float, float]
    involved_fibs: tuple[ConfluenceFibPoint, ...]
    overlap_count: int
    strength: ConfluenceStrength


@dataclass(frozen=True)
class ConfluenceSignalContext:
    volume_confirmed: bool
    near_intraday_high: bool
    locust_score_supported: bool


@dataclass(frozen=True)
class FibonacciConfluenceResult:
    main_wave: ConfluenceFibMatrix
    recent_wave: ConfluenceFibMatrix
    micro_wave: ConfluenceFibMatrix
    confluence_zones: tuple[ConfluenceZone, ...]
    signal: BuyPointSignal


def confirmed_swings(swings: Iterable[SwingPoint], tier: WaveTier) -> tuple[SwingPoint, ...]:
    return tuple(swing for swing in swings if swing.tier is tier and swing.confirmed)


def validate_market_data_source(scope: MarketScope, source: MarketDataSource) -> None:
    allowed_sources = DATA_SOURCE_RULES[scope]
    if source not in allowed_sources:
        raise ValueError(f"{scope} data must come from: {', '.join(allowed_sources)}.")


def build_fibonacci_confluence_system(
    main_wave: WaveSegment,
    recent_wave: WaveSegment,
    micro_wave: WaveSegment,
    current_price: float,
    context: ConfluenceSignalContext,
) -> FibonacciConfluenceResult:
    if current_price <= 0:
        raise ValueError("current_price must be positive.")

    matrices = (
        build_confluence_fib_matrix(main_wave, "main", current_price),
        build_confluence_fib_matrix(recent_wave, "recent", current_price),
        build_confluence_fib_matrix(micro_wave, "micro", current_price),
    )
    zones = detect_confluence_zones(matrices)
    signal = evaluate_confluence_signal(matrices, zones, current_price, context)

    return FibonacciConfluenceResult(
        main_wave=matrices[0],
        recent_wave=matrices[1],
        micro_wave=matrices[2],
        confluence_zones=zones,
        signal=signal,
    )


def build_confluence_fib_matrix(wave: WaveSegment, wave_layer: str, current_price: float) -> ConfluenceFibMatrix:
    _validate_confluence_wave(wave, wave_layer)

    anchor_low = wave.low.price
    anchor_high = wave.high.price
    price_range = wave.price_range
    wave_name = wave.name or wave_layer
    levels = tuple(
        ConfluenceFibPoint(
            wave_layer=wave_layer,
            wave_name=wave_name,
            ratio=ratio,
            fib_price=anchor_high - ratio * price_range,
            distance_to_current_price=anchor_high - ratio * price_range - current_price,
        )
        for ratio in CONFLUENCE_RATIOS
    )

    return ConfluenceFibMatrix(
        wave_layer=wave_layer,
        wave_name=wave_name,
        anchor_low=anchor_low,
        anchor_high=anchor_high,
        range=price_range,
        current_price=current_price,
        levels=levels,
    )


def detect_confluence_zones(
    matrices: Iterable[ConfluenceFibMatrix],
    tolerance: float = CONFLUENCE_TOLERANCE,
) -> tuple[ConfluenceZone, ...]:
    points = sorted((point for matrix in matrices for point in matrix.levels), key=lambda point: point.fib_price)
    zones: list[ConfluenceZone] = []
    seen: set[tuple[tuple[str, str, float], ...]] = set()

    for base in points:
        cluster = tuple(
            point
            for point in points
            if _same_price_band(base.fib_price, point.fib_price, tolerance)
        )
        if len({point.wave_layer for point in cluster}) < 2:
            continue

        key = tuple(sorted((point.wave_layer, point.wave_name, point.ratio) for point in cluster))
        if key in seen:
            continue
        seen.add(key)

        price_range = (
            min(point.fib_price for point in cluster),
            max(point.fib_price for point in cluster),
        )
        zones.append(
            ConfluenceZone(
                price_range=price_range,
                involved_fibs=cluster,
                overlap_count=len(cluster),
                strength=_classify_confluence_strength(len(cluster)),
            )
        )

    return tuple(sorted(zones, key=lambda zone: (-zone.overlap_count, zone.price_range[0])))


def evaluate_confluence_signal(
    matrices: Iterable[ConfluenceFibMatrix],
    zones: Iterable[ConfluenceZone],
    current_price: float,
    context: ConfluenceSignalContext,
) -> BuyPointSignal:
    matrix_tuple = tuple(matrices)
    zone_tuple = tuple(zones)
    reasons: list[str] = []

    if not _current_price_in_any_retracement_zone(matrix_tuple, current_price):
        reasons.append("尚未进入 0.382~0.618 Fib 回撤区")
    if not _active_confluence_zones(zone_tuple, current_price):
        reasons.append("当前价格附近没有至少 2 个波段 Fib 共振")
    if not context.volume_confirmed:
        reasons.append("缺少成交量确认")
    if context.near_intraday_high:
        reasons.append("处于日内高位")
    if not context.locust_score_supported:
        reasons.append("板块 LocustScore 不支持")

    if reasons:
        return BuyPointSignal(decision="watch", label="🟡 观察，不生成买点", reasons=tuple(reasons))

    return BuyPointSignal(decision="buy", label="🟢 买点", reasons=("Fib 共振区、量能、位置和板块资金均确认",))


def fibonacci_confluence_to_output(result: FibonacciConfluenceResult) -> dict[str, object]:
    return {
        "main_wave": _confluence_matrix_to_output(result.main_wave),
        "recent_wave": _confluence_matrix_to_output(result.recent_wave),
        "micro_wave": _confluence_matrix_to_output(result.micro_wave),
        "confluence_zones": tuple(_confluence_zone_to_output(zone) for zone in result.confluence_zones),
        "signal": {
            "decision": result.signal.decision,
            "label": result.signal.label,
            "reasons": result.signal.reasons,
        },
        "data_source_rules": {
            "a_share": "AKShare（实时价格 / 成交量 / K线）+ Eastmoney（资金流 / 板块）",
            "global": "富途 API",
            "technical_calculation": "本地 Codex",
            "tradingview": "辅助验证，不作为唯一数据源",
        },
    }


def build_fib_matrix(operating_wave: WaveSegment, current_price: float) -> FibMatrix:
    operating_wave.validate_anchor_pair()
    if current_price <= 0:
        raise ValueError("current_price must be positive.")

    anchor_low = operating_wave.low.price
    anchor_high = operating_wave.high.price
    price_range = operating_wave.price_range

    retracements = tuple(
        FibLevel(
            ratio=ratio,
            fib_kind="retracement",
            fib_price=anchor_high - price_range * ratio,
            distance_to_current_price=anchor_high - price_range * ratio - current_price,
        )
        for ratio in RETRACEMENT_RATIOS
    )

    extensions = tuple(
        FibLevel(
            ratio=ratio,
            fib_kind="extension",
            fib_price=anchor_low + price_range * ratio,
            distance_to_current_price=anchor_low + price_range * ratio - current_price,
        )
        for ratio in EXTENSION_RATIOS
    )

    return FibMatrix(
        anchor_low=anchor_low,
        anchor_high=anchor_high,
        range=price_range,
        current_price=current_price,
        retracements=retracements,
        extensions=extensions,
        wave_name=operating_wave.name,
    )


def fib_matrix_to_output(matrix: FibMatrix) -> dict[str, object]:
    return {
        "anchor_low": matrix.anchor_low,
        "anchor_high": matrix.anchor_high,
        "range": matrix.range,
        "current_price": matrix.current_price,
        "retracements": _levels_to_output(matrix.retracements),
        "extensions": _levels_to_output(matrix.extensions),
    }


def classify_resonance(delta: float) -> ResonanceStrength:
    abs_delta = abs(delta)
    if abs_delta < 0.003:
        return "strong"
    if abs_delta <= 0.008:
        return "medium"
    return "none"


def detect_fib_resonance(matrices: Iterable[FibMatrix]) -> tuple[ResonanceMatch, ...]:
    matrix_list = list(matrices)
    matches: list[ResonanceMatch] = []

    for first_index, first_matrix in enumerate(matrix_list):
        for second_index, second_matrix in enumerate(matrix_list[first_index + 1 :], start=first_index + 1):
            first_wave = first_matrix.wave_name or f"wave_{first_index + 1}"
            second_wave = second_matrix.wave_name or f"wave_{second_index + 1}"

            for first_level in first_matrix.all_levels:
                for second_level in second_matrix.all_levels:
                    reference_price = (first_level.fib_price + second_level.fib_price) / 2
                    if reference_price <= 0:
                        continue

                    delta = abs(first_level.fib_price - second_level.fib_price) / reference_price
                    strength = classify_resonance(delta)
                    price_band = None
                    if strength != "none":
                        price_band = (
                            min(first_level.fib_price, second_level.fib_price),
                            max(first_level.fib_price, second_level.fib_price),
                        )

                    matches.append(
                        ResonanceMatch(
                            first_wave=first_wave,
                            first_ratio=first_level.ratio,
                            first_price=first_level.fib_price,
                            second_wave=second_wave,
                            second_ratio=second_level.ratio,
                            second_price=second_level.fib_price,
                            delta=delta,
                            strength=strength,
                            price_band=price_band,
                        )
                    )

    return tuple(matches)


def resonance_to_output(matches: Iterable[ResonanceMatch]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "first_wave": match.first_wave,
            "first_ratio": match.first_ratio,
            "first_price": match.first_price,
            "second_wave": match.second_wave,
            "second_ratio": match.second_ratio,
            "second_price": match.second_price,
            "delta": match.delta,
            "strength": match.strength,
            "forms_price_band": match.price_band is not None,
            "price_band": match.price_band,
        }
        for match in matches
    )


def is_current_price_in_retracement_zone(matrix: FibMatrix) -> bool:
    level_382 = _level_price(matrix.retracements, 0.382)
    level_618 = _level_price(matrix.retracements, 0.618)
    lower_bound = min(level_382, level_618)
    upper_bound = max(level_382, level_618)
    return lower_bound <= matrix.current_price <= upper_bound


def evaluate_buy_point(matrix: FibMatrix, context: BuyPointContext) -> BuyPointSignal:
    reasons: list[str] = []

    if not context.operating_wave_confirmed:
        reasons.append("操作波段未 confirmed")
    if not is_current_price_in_retracement_zone(matrix):
        reasons.append("尚未进入 38.2~61.8 回撤区")
    if not context.stop_fall_confirmed:
        reasons.append("缺少止跌确认")
    if not context.locust_score_supported:
        reasons.append("板块 LocustScore 不支持")
    if context.near_intraday_high:
        reasons.append("接近日内高点")

    if reasons:
        return BuyPointSignal(decision="watch", label="🟡 观察（等待回踩）", reasons=tuple(reasons))

    return BuyPointSignal(decision="buy", label="🟢 买点", reasons=("全部买点条件满足",))


def _validate_confluence_wave(wave: WaveSegment, wave_layer: str) -> None:
    allowed_tiers = {
        "main": MAIN_WAVE_TIERS,
        "recent": RECENT_WAVE_TIERS,
        "micro": MICRO_WAVE_TIERS,
    }
    if wave_layer not in allowed_tiers:
        raise ValueError("wave_layer must be one of: main, recent, micro.")
    if wave.tier not in allowed_tiers[wave_layer]:
        raise ValueError(f"{wave_layer} wave received an invalid tier: {wave.tier.value}.")
    if wave.low.tier not in allowed_tiers[wave_layer] or wave.high.tier not in allowed_tiers[wave_layer]:
        raise ValueError(f"{wave_layer} wave anchors must belong to the same layer.")
    if wave.low.kind is not SwingKind.LOW or wave.high.kind is not SwingKind.HIGH:
        raise ValueError("Confluence Fibonacci requires one confirmed swing low and one confirmed swing high.")
    if not wave.confirmed:
        raise ValueError("Unconfirmed waves cannot participate in Fibonacci confluence calculation.")
    if _is_forbidden_intraday_anchor(wave.high):
        raise ValueError("Intraday high or current-price high cannot be used as a Fibonacci anchor.")
    if wave.low.price <= 0 or wave.high.price <= 0:
        raise ValueError("Anchor prices must be positive.")
    if wave.high.price <= wave.low.price:
        raise ValueError("anchor_high must be greater than anchor_low.")


def _is_forbidden_intraday_anchor(anchor: SwingPoint) -> bool:
    normalized = anchor.timeframe.strip().lower()
    forbidden = {"tick", "1min", "5min", "15min", "30min", "intraday", "day_high", "current_price", "分时", "日内高点"}
    return normalized in forbidden


def _same_price_band(price_a: float, price_b: float, tolerance: float) -> bool:
    reference_price = (price_a + price_b) / 2
    if reference_price <= 0:
        return False
    return abs(price_a - price_b) / reference_price < tolerance


def _classify_confluence_strength(overlap_count: int) -> ConfluenceStrength:
    if overlap_count >= 4:
        return "core"
    if overlap_count == 3:
        return "strong"
    return "weak"


def _current_price_in_any_retracement_zone(matrices: Iterable[ConfluenceFibMatrix], current_price: float) -> bool:
    return any(_current_price_in_confluence_retracement_zone(matrix, current_price) for matrix in matrices)


def _current_price_in_confluence_retracement_zone(matrix: ConfluenceFibMatrix, current_price: float) -> bool:
    level_382 = _confluence_level_price(matrix.levels, 0.382)
    level_618 = _confluence_level_price(matrix.levels, 0.618)
    lower_bound = min(level_382, level_618)
    upper_bound = max(level_382, level_618)
    return lower_bound <= current_price <= upper_bound


def _active_confluence_zones(zones: Iterable[ConfluenceZone], current_price: float) -> tuple[ConfluenceZone, ...]:
    active: list[ConfluenceZone] = []
    for zone in zones:
        zone_mid = sum(zone.price_range) / 2
        zone_padding = zone_mid * CONFLUENCE_TOLERANCE
        lower_bound = zone.price_range[0] - zone_padding
        upper_bound = zone.price_range[1] + zone_padding
        if lower_bound <= current_price <= upper_bound and zone.overlap_count >= 2:
            active.append(zone)
    return tuple(active)


def _confluence_level_price(levels: Iterable[ConfluenceFibPoint], ratio: float) -> float:
    for level in levels:
        if level.ratio == ratio:
            return level.fib_price
    raise ValueError(f"Missing Fibonacci confluence level: {ratio}")


def _confluence_matrix_to_output(matrix: ConfluenceFibMatrix) -> dict[str, object]:
    return {
        "anchor_low": matrix.anchor_low,
        "anchor_high": matrix.anchor_high,
        "range": matrix.range,
        "current_price": matrix.current_price,
        "levels": {
            f"{level.ratio:g}": {
                "fib_price": level.fib_price,
                "distance_to_current_price": level.distance_to_current_price,
            }
            for level in matrix.levels
        },
    }


def _confluence_zone_to_output(zone: ConfluenceZone) -> dict[str, object]:
    return {
        "price_range": zone.price_range,
        "involved_fibs": tuple(
            {
                "wave_layer": point.wave_layer,
                "wave_name": point.wave_name,
                "ratio": point.ratio,
                "fib_price": point.fib_price,
            }
            for point in zone.involved_fibs
        ),
        "overlap_count": zone.overlap_count,
        "strength": zone.strength,
        "strength_label": _confluence_strength_label(zone.strength),
    }


def _confluence_strength_label(strength: ConfluenceStrength) -> str:
    labels = {
        "weak": "弱",
        "strong": "强",
        "core": "核心区",
    }
    return labels[strength]


def _level_price(levels: Iterable[FibLevel], ratio: float) -> float:
    for level in levels:
        if level.ratio == ratio:
            return level.fib_price
    raise ValueError(f"Missing Fibonacci level: {ratio}")


def _levels_to_output(levels: Iterable[FibLevel]) -> dict[str, dict[str, float]]:
    return {
        f"{level.ratio:g}": {
            "fib_price": level.fib_price,
            "distance_to_current_price": level.distance_to_current_price,
        }
        for level in levels
    }
