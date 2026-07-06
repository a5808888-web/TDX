from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from fibonacci_wave_system import (
    BuyPointContext,
    BuyPointSignal,
    FibMatrix,
    ResonanceMatch,
    WaveSegment,
    build_fib_matrix,
    detect_fib_resonance,
    evaluate_buy_point,
)


Decision = Literal["buy", "watch", "blocked"]


class TradeState(str, Enum):
    WAITING_FOR_STRUCTURE = "waiting_for_structure"
    WAITING_FOR_PULLBACK = "waiting_for_pullback"
    READY_TO_BUY = "ready_to_buy"
    BLOCKED_BY_RISK = "blocked_by_risk"
    COOLDOWN = "cooldown"
    HOLDING = "holding"


@dataclass(frozen=True)
class LocustScoreInput:
    capital_flow_score: float
    sector_breadth_score: float
    leader_strength_score: float
    volume_confirmation_score: float


@dataclass(frozen=True)
class LocustScoreResult:
    score: float
    supported: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RiskScoreInput:
    volatility_risk: float
    drawdown_risk: float
    liquidity_risk: float
    event_risk: float


@dataclass(frozen=True)
class RiskScoreResult:
    score: float
    acceptable: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class GlobalFilterInput:
    us_market_supported: bool
    china_market_supported: bool
    usd_cnh_stable: bool
    vix_safe: bool


@dataclass(frozen=True)
class GlobalFilterResult:
    passed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CoolingInput:
    trades_today: int
    max_trades_per_day: int
    consecutive_losses: int
    cooldown_active: bool


@dataclass(frozen=True)
class CoolingResult:
    allowed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PositionResult:
    position_pct: float
    max_loss_pct: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class LocustPlanInput:
    operating_wave: WaveSegment
    current_price: float
    stop_fall_confirmed: bool
    near_intraday_high: bool
    locust_score: LocustScoreInput
    risk_score: RiskScoreInput
    global_filter: GlobalFilterInput
    cooling: CoolingInput
    comparison_waves: tuple[WaveSegment, ...] = ()


@dataclass(frozen=True)
class LocustPlanResult:
    decision: Decision
    label: str
    state: TradeState
    fib_matrix: FibMatrix
    resonance: tuple[ResonanceMatch, ...]
    locust_score: LocustScoreResult
    risk_score: RiskScoreResult
    global_filter: GlobalFilterResult
    cooling: CoolingResult
    position: PositionResult
    buy_signal: BuyPointSignal
    reasons: tuple[str, ...]


def calculate_locust_score(data: LocustScoreInput, support_threshold: float = 60.0) -> LocustScoreResult:
    _validate_score(data.capital_flow_score, "capital_flow_score")
    _validate_score(data.sector_breadth_score, "sector_breadth_score")
    _validate_score(data.leader_strength_score, "leader_strength_score")
    _validate_score(data.volume_confirmation_score, "volume_confirmation_score")

    score = (
        data.capital_flow_score * 0.35
        + data.sector_breadth_score * 0.25
        + data.leader_strength_score * 0.25
        + data.volume_confirmation_score * 0.15
    )
    reasons: list[str] = []
    if score < support_threshold:
        reasons.append("LocustScore 资金支持不足")
    if data.capital_flow_score < 50:
        reasons.append("主资金流偏弱")
    if data.sector_breadth_score < 50:
        reasons.append("板块扩散不足")

    return LocustScoreResult(
        score=score,
        supported=score >= support_threshold and not reasons,
        reasons=tuple(reasons) or ("资金结构支持",),
    )


def calculate_risk_score(data: RiskScoreInput, max_acceptable: float = 55.0) -> RiskScoreResult:
    _validate_score(data.volatility_risk, "volatility_risk")
    _validate_score(data.drawdown_risk, "drawdown_risk")
    _validate_score(data.liquidity_risk, "liquidity_risk")
    _validate_score(data.event_risk, "event_risk")

    score = (
        data.volatility_risk * 0.3
        + data.drawdown_risk * 0.3
        + data.liquidity_risk * 0.2
        + data.event_risk * 0.2
    )
    reasons: list[str] = []
    if score > max_acceptable:
        reasons.append("RiskScore 超过允许阈值")
    if data.event_risk >= 70:
        reasons.append("事件风险过高")
    if data.liquidity_risk >= 70:
        reasons.append("流动性风险过高")

    return RiskScoreResult(
        score=score,
        acceptable=score <= max_acceptable and not reasons,
        reasons=tuple(reasons) or ("风险可接受",),
    )


def run_global_filter(data: GlobalFilterInput) -> GlobalFilterResult:
    reasons: list[str] = []
    if not data.us_market_supported:
        reasons.append("美股环境不支持")
    if not data.china_market_supported:
        reasons.append("中概/A股环境不支持")
    if not data.usd_cnh_stable:
        reasons.append("离岸人民币波动不稳定")
    if not data.vix_safe:
        reasons.append("VIX 风险环境偏高")

    return GlobalFilterResult(passed=not reasons, reasons=tuple(reasons) or ("全球过滤通过",))


def run_cooling_system(data: CoolingInput) -> CoolingResult:
    reasons: list[str] = []
    if data.cooldown_active:
        reasons.append("冷却期仍在生效")
    if data.trades_today >= data.max_trades_per_day:
        reasons.append("今日交易次数已达上限")
    if data.consecutive_losses >= 2:
        reasons.append("连续亏损触发行为降温")

    return CoolingResult(allowed=not reasons, reasons=tuple(reasons) or ("行为控制允许交易",))


def calculate_position(
    buy_signal: BuyPointSignal,
    locust_score: LocustScoreResult,
    risk_score: RiskScoreResult,
    resonance: tuple[ResonanceMatch, ...],
    cooling: CoolingResult,
) -> PositionResult:
    if buy_signal.decision != "buy" or not risk_score.acceptable or not cooling.allowed:
        return PositionResult(position_pct=0.0, max_loss_pct=0.0, reasons=("未满足开仓条件",))

    base_position = 0.1
    if locust_score.score >= 75:
        base_position += 0.05
    if any(match.strength == "strong" for match in resonance):
        base_position += 0.03
    if risk_score.score <= 30:
        base_position += 0.02

    position_pct = min(base_position, 0.2)
    return PositionResult(position_pct=position_pct, max_loss_pct=0.015, reasons=("仓位由结构、资金、风险、共振共同确认",))


def run_state_machine(
    buy_signal: BuyPointSignal,
    risk_score: RiskScoreResult,
    global_filter: GlobalFilterResult,
    cooling: CoolingResult,
) -> TradeState:
    if not global_filter.passed or not risk_score.acceptable:
        return TradeState.BLOCKED_BY_RISK
    if not cooling.allowed:
        return TradeState.COOLDOWN
    if buy_signal.decision == "buy":
        return TradeState.READY_TO_BUY
    if any("38.2~61.8" in reason for reason in buy_signal.reasons):
        return TradeState.WAITING_FOR_PULLBACK
    return TradeState.WAITING_FOR_STRUCTURE


def run_locust_plan_v2(data: LocustPlanInput) -> LocustPlanResult:
    fib_matrix = build_fib_matrix(data.operating_wave, data.current_price)
    comparison_matrices = tuple(build_fib_matrix(wave, data.current_price) for wave in data.comparison_waves)
    resonance = detect_fib_resonance((fib_matrix,) + comparison_matrices)

    locust_score = calculate_locust_score(data.locust_score)
    risk_score = calculate_risk_score(data.risk_score)
    global_filter = run_global_filter(data.global_filter)
    cooling = run_cooling_system(data.cooling)

    buy_signal = evaluate_buy_point(
        fib_matrix,
        BuyPointContext(
            operating_wave_confirmed=data.operating_wave.confirmed,
            stop_fall_confirmed=data.stop_fall_confirmed,
            locust_score_supported=locust_score.supported,
            near_intraday_high=data.near_intraday_high,
        ),
    )
    state = run_state_machine(buy_signal, risk_score, global_filter, cooling)
    position = calculate_position(buy_signal, locust_score, risk_score, resonance, cooling)

    blocking_reasons = _collect_blocking_reasons(buy_signal, risk_score, global_filter, cooling)
    decision: Decision = "buy" if state is TradeState.READY_TO_BUY and position.position_pct > 0 else "watch"
    label = buy_signal.label if decision == "buy" else "🟡 观察（等待回踩）"
    if state in {TradeState.BLOCKED_BY_RISK, TradeState.COOLDOWN}:
        decision = "blocked"
        label = "⛔ 暂停交易"

    return LocustPlanResult(
        decision=decision,
        label=label,
        state=state,
        fib_matrix=fib_matrix,
        resonance=resonance,
        locust_score=locust_score,
        risk_score=risk_score,
        global_filter=global_filter,
        cooling=cooling,
        position=position,
        buy_signal=buy_signal,
        reasons=blocking_reasons or ("七模块条件通过",),
    )


def _collect_blocking_reasons(
    buy_signal: BuyPointSignal,
    risk_score: RiskScoreResult,
    global_filter: GlobalFilterResult,
    cooling: CoolingResult,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if buy_signal.decision != "buy":
        reasons.extend(buy_signal.reasons)
    if not risk_score.acceptable:
        reasons.extend(risk_score.reasons)
    if not global_filter.passed:
        reasons.extend(global_filter.reasons)
    if not cooling.allowed:
        reasons.extend(cooling.reasons)
    return tuple(reasons)


def _validate_score(value: float, field_name: str) -> None:
    if value < 0 or value > 100:
        raise ValueError(f"{field_name} must be between 0 and 100.")
