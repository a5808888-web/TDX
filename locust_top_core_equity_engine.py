from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CoreEquityType(str, Enum):
    LEADER = "龙头"
    CORE_INSTITUTION = "大中军"
    TREND = "趋势股"
    LAGGING = "补涨"
    BLOCKED = "禁买"


class CoreAction(str, Enum):
    BUY = "买入"
    HOLD = "持有"
    WATCH = "观察"


@dataclass(frozen=True)
class CoreEquityInput:
    stock_name: str
    code: str
    sector: str
    equity_type: CoreEquityType
    heat_score: float
    institution_flow_score: float
    institution_inflow: bool
    fib_zone: str
    fib_score: float
    ai_decision: str
    ai_confidence: float
    leader_attribute_score: float
    market_cap_rank: int = 1
    emotion_stock: bool = False
    funding_status: str = "机构持续流入"
    fib_structure: str = "0.382–0.618健康回撤"
    ai_summary: str = "DeepSeek与豆包结论一致"


@dataclass(frozen=True)
class CoreRecommendation:
    stock_name: str
    code: str
    equity_type: CoreEquityType
    sector: str
    funding_status: str
    fib_structure: str
    ai_conclusion: str
    recommendation_action: CoreAction
    core_score: float


@dataclass(frozen=True)
class TopCoreEquityResult:
    recommendations: tuple[CoreRecommendation, ...]
    rejected: tuple[dict[str, object], ...]
    max_items: int = 5
    sync_interval: int = 180


def calculate_core_score(item: CoreEquityInput) -> float:
    return round(
        0.3 * _clamp(item.institution_flow_score)
        + 0.2 * _clamp(item.heat_score)
        + 0.2 * _clamp(item.fib_score)
        + 0.2 * _clamp(item.ai_confidence)
        + 0.1 * _clamp(item.leader_attribute_score),
        2,
    )


def run_top_core_equity_engine(items: tuple[CoreEquityInput, ...], max_items: int = 5) -> TopCoreEquityResult:
    accepted: list[CoreRecommendation] = []
    rejected: list[dict[str, object]] = []
    for item in items:
        reason = _reject_reason(item)
        if reason:
            rejected.append({"stock_name": item.stock_name, "code": item.code, "reason": reason})
            continue
        score = calculate_core_score(item)
        accepted.append(
            CoreRecommendation(
                stock_name=item.stock_name,
                code=item.code,
                equity_type=item.equity_type,
                sector=item.sector,
                funding_status=item.funding_status,
                fib_structure=item.fib_structure,
                ai_conclusion=f"{_decision_text(item.ai_decision)}｜置信度{item.ai_confidence:.0f}",
                recommendation_action=_action_for_score(score),
                core_score=score,
            )
        )
    ranked = tuple(sorted(accepted, key=lambda item: item.core_score, reverse=True)[:max_items])
    return TopCoreEquityResult(recommendations=ranked, rejected=tuple(rejected), max_items=max_items)


def top_core_equity_to_output(result: TopCoreEquityResult) -> dict[str, object]:
    return {
        "核心优质股票推荐引擎": "交易热力图 + 机构资金流 + 选股池 + 斐波那契 + 智能分析 -> 长期核心推荐池",
        "sync_interval": result.sync_interval,
        "首页唯一入口": "长期核心推荐池",
        "长期核心推荐池": tuple(_recommendation_to_output(item) for item in result.recommendations),
        "核心评分公式": "0.3×机构资金 + 0.2×板块热力 + 0.2×斐波那契结构 + 0.2×智能分析 + 0.1×龙头属性",
        "筛选条件": {
            "板块热度评分 >= 80": True,
            "机构资金持续流入": True,
            "斐波那契结构健康": "0.382–0.618",
            "智能分析一致": True,
            "只允许龙头或大中军": True,
        },
        "股票分类": ("龙头", "大中军", "趋势股", "补涨"),
        "剔除记录": result.rejected,
        "禁止规则": {
            "不输出小票": True,
            "不输出情绪股": True,
            "不输出无资金支持股票": True,
            "不输出无斐波那契结构股票": True,
            "不输出模糊推荐": True,
        },
    }


def _recommendation_to_output(item: CoreRecommendation) -> dict[str, object]:
    return {
        "股票名称": item.stock_name,
        "代码": item.code,
        "产业属性": item.equity_type.value,
        "所属板块": item.sector,
        "资金状态": item.funding_status,
        "斐波那契结构": item.fib_structure,
        "智能分析结论": item.ai_conclusion,
        "推荐动作": item.recommendation_action.value,
        "核心评分": item.core_score,
    }


def _reject_reason(item: CoreEquityInput) -> str | None:
    if item.equity_type not in {CoreEquityType.LEADER, CoreEquityType.CORE_INSTITUTION}:
        return "只推荐龙头或大中军，趋势股/补涨股不进入长期核心推荐池。"
    if item.heat_score < 80:
        return "板块热度评分低于80，交易状态为观察，禁止进入核心推荐池。"
    if not item.institution_inflow or item.institution_flow_score < 60:
        return "机构资金未形成持续流入。"
    if not _is_healthy_fib_zone(item.fib_zone):
        return "斐波那契结构未处于0.382–0.618健康回撤。"
    if item.ai_decision not in {"BUY", "HOLD", "WAIT", "买入", "持有", "观察"} or item.ai_confidence < 60:
        return "智能分析不一致或置信度不足。"
    if item.market_cap_rank > 2:
        return "市值层级不足，疑似小票，不进入长期核心池。"
    if item.emotion_stock:
        return "情绪股剔除。"
    return None


def _is_healthy_fib_zone(zone: str) -> bool:
    normalized = zone.strip().lower()
    return normalized in {"0.382-0.618", "0.382–0.618", "buy_zone", "buy", "健康回撤", "买入区"}


def _action_for_score(score: float) -> CoreAction:
    if score >= 84:
        return CoreAction.BUY
    if score >= 76:
        return CoreAction.HOLD
    return CoreAction.WATCH


def _decision_text(decision: str) -> str:
    return {
        "BUY": "买入",
        "HOLD": "持有",
        "WAIT": "观察",
        "AVOID": "回避",
    }.get(decision, decision)


def _clamp(value: float) -> float:
    return min(100.0, max(0.0, float(value)))
