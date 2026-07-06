from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Protocol

from ai_consensus_layer import AIAnalysisRequest, AIConsensusError, OpenAICompatibleProvider, Transport, load_ai_api_key
from fibonacci_wave_system import (
    FibMatrix,
    SwingKind,
    SwingPoint,
    TrendDirection,
    WaveSegment,
    WaveTier,
    build_fib_matrix,
    fib_matrix_to_output,
)


class AnchorMode(str, Enum):
    AI_AUTO = "AI_AUTO"
    MANUAL = "MANUAL"
    HYBRID = "HYBRID"


class AnchorSource(str, Enum):
    AI = "ai"
    AI_PROVISIONAL = "ai_provisional"
    MANUAL = "manual"


class AnchorStatus(str, Enum):
    CONFIRMED = "confirmed"
    WEAK = "weak"
    INVALID = "invalid"


class StructureFlag(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    CONFLICT = "CONFLICT"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"


@dataclass(frozen=True)
class KLine:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str = "1D"


@dataclass(frozen=True)
class WaveAnchor:
    anchor_low: float
    anchor_high: float
    confidence: float
    status: AnchorStatus
    source: AnchorSource
    low_timestamp: str | None = None
    high_timestamp: str | None = None


@dataclass(frozen=True)
class ManualAnchorInput:
    manual_anchor_low: float
    manual_anchor_high: float


@dataclass(frozen=True)
class AnchorIntelligenceInput:
    symbol: str
    current_price: float
    klines: tuple[KLine, ...]
    mode: AnchorMode = AnchorMode.AI_AUTO
    manual_anchor: ManualAnchorInput | None = None
    ai_anchor: WaveAnchor | None = None


@dataclass(frozen=True)
class AnchorConsistency:
    flag: StructureFlag
    low_delta: float | None
    high_delta: float | None
    message: str


@dataclass(frozen=True)
class AnchorTradeLevels:
    buy_point_1: float
    buy_point_2: float
    sell_point_1: float
    sell_point_2: float
    risk_zone: tuple[float, float]


@dataclass(frozen=True)
class AnchorIntelligenceResult:
    symbol: str
    mode: AnchorMode
    ai_anchor: WaveAnchor
    manual_anchor: WaveAnchor | None
    active_anchor: WaveAnchor | None
    anchor_source: AnchorSource | None
    consistency: AnchorConsistency
    fib_matrix: FibMatrix | None
    trade_levels: AnchorTradeLevels | None
    warnings: tuple[str, ...]


class AnchorAIClient(Protocol):
    def detect_anchor(self, data: AnchorIntelligenceInput, technical_anchor: WaveAnchor) -> WaveAnchor:
        ...


class TechnicalAnchorModel:
    def detect_anchor(self, data: AnchorIntelligenceInput) -> WaveAnchor:
        return detect_technical_anchor(data.klines)


class DeepSeekAnchorClient:
    def __init__(self, provider: OpenAICompatibleProvider):
        self.provider = provider

    def detect_anchor(self, data: AnchorIntelligenceInput, technical_anchor: WaveAnchor) -> WaveAnchor:
        response = self.provider.analyze(
            AIAnalysisRequest(
                task=(
                    "Fibonacci Anchor Detection: 基于K线、成交量、局部高低点、ATR波动和趋势结构，"
                    "只输出JSON：anchor_low, anchor_high, confidence, status。"
                    "status只能是confirmed/weak/invalid。confidence<60必须invalid，60-80为weak，>80为confirmed。"
                ),
                payload={
                    "symbol": data.symbol,
                    "current_price": data.current_price,
                    "technical_anchor": _anchor_to_output(technical_anchor),
                    "klines": tuple(candle.__dict__ for candle in data.klines),
                },
            )
        )
        parsed = _extract_anchor_json(response.content)
        return WaveAnchor(
            anchor_low=float(parsed["anchor_low"]),
            anchor_high=float(parsed["anchor_high"]),
            confidence=float(parsed["confidence"]),
            status=_status_from_confidence(float(parsed["confidence"]), str(parsed.get("status", ""))),
            source=AnchorSource.AI,
        )


class FibonacciAnchorIntelligenceLayer:
    def __init__(self, ai_client: AnchorAIClient | None = None, technical_model: TechnicalAnchorModel | None = None):
        self.ai_client = ai_client
        self.technical_model = technical_model or TechnicalAnchorModel()

    def evaluate(self, data: AnchorIntelligenceInput) -> AnchorIntelligenceResult:
        if data.current_price <= 0:
            raise ValueError("current_price must be positive.")
        if not data.klines and data.ai_anchor is None:
            raise ValueError("AI anchor detection requires K-line data or a supplied AI anchor.")

        technical_anchor = self.technical_model.detect_anchor(data) if data.klines else data.ai_anchor
        if technical_anchor is None:
            raise ValueError("technical anchor detection failed.")

        ai_anchor = data.ai_anchor or self._detect_ai_anchor(data, technical_anchor)
        manual_anchor = _build_manual_anchor(data.manual_anchor) if data.manual_anchor else None
        active_anchor, source, warnings = _select_active_anchor(data.mode, ai_anchor, manual_anchor)
        consistency = _check_consistency(ai_anchor, manual_anchor, active_anchor)

        fib_matrix = None
        trade_levels = None
        if active_anchor is not None and (
            active_anchor.status is AnchorStatus.CONFIRMED or active_anchor.source is AnchorSource.MANUAL
        ):
            fib_matrix = build_fib_matrix(_anchor_to_wave(active_anchor, data.symbol), data.current_price)
            trade_levels = _build_trade_levels(fib_matrix)

        return AnchorIntelligenceResult(
            symbol=data.symbol,
            mode=data.mode,
            ai_anchor=ai_anchor,
            manual_anchor=manual_anchor,
            active_anchor=active_anchor,
            anchor_source=source,
            consistency=consistency,
            fib_matrix=fib_matrix,
            trade_levels=trade_levels,
            warnings=tuple(warnings),
        )

    def _detect_ai_anchor(self, data: AnchorIntelligenceInput, technical_anchor: WaveAnchor) -> WaveAnchor:
        if self.ai_client is None:
            return technical_anchor
        ai_anchor = self.ai_client.detect_anchor(data, technical_anchor)
        if ai_anchor.source is not AnchorSource.AI:
            return WaveAnchor(
                anchor_low=ai_anchor.anchor_low,
                anchor_high=ai_anchor.anchor_high,
                confidence=ai_anchor.confidence,
                status=ai_anchor.status,
                source=AnchorSource.AI,
                low_timestamp=ai_anchor.low_timestamp,
                high_timestamp=ai_anchor.high_timestamp,
            )
        return ai_anchor


def build_default_anchor_intelligence_layer(transport: Transport | None = None) -> FibonacciAnchorIntelligenceLayer:
    try:
        provider = OpenAICompatibleProvider(
            name="DeepSeek",
            endpoint=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions"),
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            api_key=load_ai_api_key("deepseek"),
            transport=transport,
        )
        return FibonacciAnchorIntelligenceLayer(ai_client=DeepSeekAnchorClient(provider))
    except AIConsensusError:
        return FibonacciAnchorIntelligenceLayer()


def detect_technical_anchor(klines: Iterable[KLine]) -> WaveAnchor:
    candles = tuple(klines)
    if len(candles) < 5:
        raise ValueError("Anchor detection requires at least 5 K-lines.")
    _validate_klines(candles)

    low_index = min(range(len(candles)), key=lambda index: candles[index].low)
    high_index = max(range(low_index + 1, len(candles)), key=lambda index: candles[index].high, default=None)
    if high_index is None:
        return WaveAnchor(0, 0, 0, AnchorStatus.INVALID, AnchorSource.AI_PROVISIONAL)

    low_candle = candles[low_index]
    high_candle = candles[high_index]
    low_confirmed = _low_has_reversal(candles, low_index)
    high_confirmed = _high_has_pullback(candles, high_index)
    volume_confirmed = _volume_confirms(candles, low_index, high_index)
    not_random = (high_candle.high - low_candle.low) / low_candle.low >= 0.05

    confidence = 45
    confidence += 18 if low_confirmed else 0
    confidence += 18 if high_confirmed else 0
    confidence += 10 if volume_confirmed else 0
    confidence += 9 if not_random else 0
    confidence = min(100, confidence)

    if confidence > 80:
        status = AnchorStatus.CONFIRMED
        source = AnchorSource.AI
    elif confidence >= 60:
        status = AnchorStatus.WEAK
        source = AnchorSource.AI_PROVISIONAL
    else:
        status = AnchorStatus.INVALID
        source = AnchorSource.AI_PROVISIONAL

    return WaveAnchor(
        anchor_low=round(low_candle.low, 3),
        anchor_high=round(high_candle.high, 3),
        confidence=round(confidence, 2),
        status=status,
        source=source,
        low_timestamp=low_candle.timestamp,
        high_timestamp=high_candle.timestamp,
    )


def anchor_intelligence_to_output(result: AnchorIntelligenceResult) -> dict[str, object]:
    return {
        "FIBONACCI ANCHOR MODE": {
            "symbol": result.symbol,
            "Mode": result.mode.value,
            "anchor_source": result.anchor_source.value if result.anchor_source else None,
            "AI Anchor": _anchor_to_output(result.ai_anchor),
            "Manual Anchor": _anchor_to_output(result.manual_anchor),
            "Active Anchor": _anchor_to_output(result.active_anchor),
            "当前状态": result.consistency.flag.value,
            "Consistency Check": {
                "low_delta": result.consistency.low_delta,
                "high_delta": result.consistency.high_delta,
                "message": result.consistency.message,
            },
            "warnings": result.warnings,
        },
        "FibMatrix": fib_matrix_to_output(result.fib_matrix) if result.fib_matrix else None,
        "TradeLevels": _trade_levels_to_output(result.trade_levels),
    }


def _select_active_anchor(
    mode: AnchorMode,
    ai_anchor: WaveAnchor,
    manual_anchor: WaveAnchor | None,
) -> tuple[WaveAnchor | None, AnchorSource | None, list[str]]:
    warnings: list[str] = []
    if mode is AnchorMode.MANUAL:
        if manual_anchor is None:
            warnings.append("Manual Mode requires manual_anchor_low and manual_anchor_high.")
            return None, None, warnings
        return manual_anchor, AnchorSource.MANUAL, warnings

    if mode is AnchorMode.HYBRID and manual_anchor is not None:
        return manual_anchor, AnchorSource.MANUAL, warnings

    if ai_anchor.confidence < 60 or ai_anchor.status is AnchorStatus.INVALID:
        warnings.append("AI confidence < 60, fallback = manual required.")
        return None, None, warnings

    if ai_anchor.status is AnchorStatus.CONFIRMED:
        return ai_anchor, AnchorSource.AI, warnings

    warnings.append("AI anchor is provisional; use as reference only and do not calculate trading Fib.")
    return ai_anchor, AnchorSource.AI_PROVISIONAL, warnings


def _build_manual_anchor(manual: ManualAnchorInput | None) -> WaveAnchor | None:
    if manual is None:
        return None
    if manual.manual_anchor_low <= 0 or manual.manual_anchor_high <= 0:
        raise ValueError("Manual anchors must be positive.")
    if manual.manual_anchor_high <= manual.manual_anchor_low:
        raise ValueError("manual_anchor_high must be greater than manual_anchor_low.")
    return WaveAnchor(
        anchor_low=manual.manual_anchor_low,
        anchor_high=manual.manual_anchor_high,
        confidence=100,
        status=AnchorStatus.CONFIRMED,
        source=AnchorSource.MANUAL,
    )


def _check_consistency(
    ai_anchor: WaveAnchor,
    manual_anchor: WaveAnchor | None,
    active_anchor: WaveAnchor | None,
) -> AnchorConsistency:
    if active_anchor is None:
        return AnchorConsistency(StructureFlag.MANUAL_REQUIRED, None, None, "AI锚点不可用，需要手动输入。")
    if manual_anchor is None:
        if active_anchor.status is AnchorStatus.WEAK:
            return AnchorConsistency(StructureFlag.MANUAL_REQUIRED, None, None, "AI观察锚点未确认，需要手动确认。")
        if active_anchor.status is AnchorStatus.INVALID:
            return AnchorConsistency(StructureFlag.INVALID, None, None, "锚点无效。")
        return AnchorConsistency(StructureFlag.VALID, None, None, "VALID STRUCTURE")

    low_delta = abs(ai_anchor.anchor_low - manual_anchor.anchor_low) / ai_anchor.anchor_low if ai_anchor.anchor_low else None
    high_delta = (
        abs(ai_anchor.anchor_high - manual_anchor.anchor_high) / ai_anchor.anchor_high if ai_anchor.anchor_high else None
    )
    if low_delta is not None and high_delta is not None and (low_delta > 0.05 or high_delta > 0.05):
        return AnchorConsistency(StructureFlag.CONFLICT, low_delta, high_delta, "STRUCTURE CONFLICT")
    return AnchorConsistency(StructureFlag.VALID, low_delta, high_delta, "VALID STRUCTURE")


def _anchor_to_wave(anchor: WaveAnchor, symbol: str) -> WaveSegment:
    low = SwingPoint(
        price=anchor.anchor_low,
        kind=SwingKind.LOW,
        timestamp=anchor.low_timestamp or "manual",
        timeframe="1D",
        tier=WaveTier.OPERATING,
        confirmed=anchor.status is AnchorStatus.CONFIRMED or anchor.source is AnchorSource.MANUAL,
    )
    high = SwingPoint(
        price=anchor.anchor_high,
        kind=SwingKind.HIGH,
        timestamp=anchor.high_timestamp or "manual",
        timeframe="1D",
        tier=WaveTier.OPERATING,
        confirmed=anchor.status is AnchorStatus.CONFIRMED or anchor.source is AnchorSource.MANUAL,
    )
    return WaveSegment(low=low, high=high, tier=WaveTier.OPERATING, direction=TrendDirection.UP, name=symbol)


def _build_trade_levels(matrix: FibMatrix) -> AnchorTradeLevels:
    retracements = {level.ratio: level.fib_price for level in matrix.retracements}
    extensions = {level.ratio: level.fib_price for level in matrix.extensions}
    return AnchorTradeLevels(
        buy_point_1=round(retracements[0.618], 3),
        buy_point_2=round(retracements[0.786], 3),
        sell_point_1=round(extensions[1.272], 3),
        sell_point_2=round(extensions[1.618], 3),
        risk_zone=(round(matrix.anchor_low * 0.98, 3), round(matrix.anchor_low, 3)),
    )


def _validate_klines(candles: tuple[KLine, ...]) -> None:
    for candle in candles:
        if min(candle.open, candle.high, candle.low, candle.close) <= 0:
            raise ValueError("K-line prices must be positive.")
        if candle.high < max(candle.open, candle.close, candle.low):
            raise ValueError("K-line high is inconsistent.")
        if candle.low > min(candle.open, candle.close, candle.high):
            raise ValueError("K-line low is inconsistent.")
        if candle.timeframe.strip().lower() in {"tick", "1min", "5min", "15min", "30min", "intraday", "分时"}:
            raise ValueError("Intraday K-lines cannot be used as Fibonacci anchors.")


def _low_has_reversal(candles: tuple[KLine, ...], low_index: int) -> bool:
    if low_index > len(candles) - 3:
        return False
    next_two = candles[low_index + 1 : low_index + 3]
    return all(candle.close > candles[low_index].low for candle in next_two)


def _high_has_pullback(candles: tuple[KLine, ...], high_index: int) -> bool:
    if high_index > len(candles) - 3:
        return False
    next_two = candles[high_index + 1 : high_index + 3]
    return all(candle.close < candles[high_index].high for candle in next_two)


def _volume_confirms(candles: tuple[KLine, ...], low_index: int, high_index: int) -> bool:
    avg_volume = sum(candle.volume for candle in candles) / len(candles)
    low_volume = candles[low_index].volume
    high_volume = candles[high_index].volume
    return low_volume <= avg_volume * 0.9 or high_volume >= avg_volume * 1.05


def _anchor_to_output(anchor: WaveAnchor | None) -> dict[str, object] | None:
    if anchor is None:
        return None
    return {
        "High": anchor.anchor_high,
        "Low": anchor.anchor_low,
        "Confidence": anchor.confidence,
        "status": anchor.status.value,
        "anchor_source": anchor.source.value,
    }


def _trade_levels_to_output(levels: AnchorTradeLevels | None) -> dict[str, object] | None:
    if levels is None:
        return None
    return {
        "买点1": levels.buy_point_1,
        "买点2": levels.buy_point_2,
        "卖点1": levels.sell_point_1,
        "卖点2": levels.sell_point_2,
        "风险区": levels.risk_zone,
    }


def _extract_anchor_json(content: str) -> dict[str, object]:
    match = re.search(r"\{.*\}", content, flags=re.S)
    if not match:
        raise AIConsensusError("DeepSeek anchor response did not contain JSON.")
    parsed = json.loads(match.group(0))
    required = {"anchor_low", "anchor_high", "confidence"}
    if not required.issubset(parsed):
        raise AIConsensusError("DeepSeek anchor JSON missing required fields.")
    if float(parsed["anchor_high"]) <= float(parsed["anchor_low"]):
        raise AIConsensusError("DeepSeek anchor JSON has invalid high/low.")
    return parsed


def _status_from_confidence(confidence: float, requested_status: str) -> AnchorStatus:
    if confidence < 60:
        return AnchorStatus.INVALID
    if confidence <= 80:
        return AnchorStatus.WEAK
    if requested_status == AnchorStatus.INVALID.value:
        return AnchorStatus.INVALID
    return AnchorStatus.CONFIRMED
