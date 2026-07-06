from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EquityTier(str, Enum):
    LEADER = "龙头股"
    CORE = "中军股"
    TREND = "趋势股"
    LAGGING = "补涨股"
    BLOCKED = "禁买股"


TIER_PRIORITY: dict[EquityTier, int] = {
    EquityTier.LEADER: 5,
    EquityTier.CORE: 4,
    EquityTier.TREND: 3,
    EquityTier.LAGGING: 2,
    EquityTier.BLOCKED: 0,
}


@dataclass(frozen=True)
class EquityMetrics:
    stock_name: str
    code: str
    role: str
    locust_score: float
    fib_score: float
    confluence_layers: int
    institution_score: float
    risk_score: float
    beta: float
    volatility: float
    capital_concentration: float
    price_position: float
    fib_valid: bool = True
    blocked: bool = False


@dataclass(frozen=True)
class SectorHierarchyInput:
    sector_name: str
    heat_score: float
    locust_score: float
    risk_score: float
    equities: tuple[EquityMetrics, ...]


@dataclass(frozen=True)
class ClassifiedEquity:
    metrics: EquityMetrics
    tier: EquityTier
    hierarchy_score: float
    priority: int
    fib_binding: dict[str, object]
    deepseek_check: str
    doubao_check: str
    warning: str


@dataclass(frozen=True)
class SectorEquityHierarchy:
    sector_name: str
    heat_score: float
    locust_score: float
    risk_score: float
    leader: tuple[ClassifiedEquity, ...]
    core: tuple[ClassifiedEquity, ...]
    trend: tuple[ClassifiedEquity, ...]
    lagging: tuple[ClassifiedEquity, ...]
    blocked: tuple[ClassifiedEquity, ...]


def build_equity_hierarchy(sector: SectorHierarchyInput) -> SectorEquityHierarchy:
    classified = [_classify_equity(item, sector) for item in sector.equities]
    leaders = [item for item in classified if item.tier is EquityTier.LEADER]
    if len(leaders) > 1:
        true_leader = max(leaders, key=lambda item: item.hierarchy_score)
        classified = [
            item
            if item.tier is not EquityTier.LEADER or item.metrics.stock_name == true_leader.metrics.stock_name
            else _replace_tier(item, _non_leader_tier(item.metrics))
            for item in classified
        ]
    tradable = [item for item in classified if item.tier is not EquityTier.BLOCKED]
    if tradable and not any(item.tier is EquityTier.LEADER for item in tradable):
        best = max(tradable, key=lambda item: item.hierarchy_score)
        classified = [
            _replace_tier(item, EquityTier.LEADER) if item.metrics.stock_name == best.metrics.stock_name else item
            for item in classified
        ]
    if tradable and not any(item.tier is EquityTier.CORE for item in classified):
        core_candidate = max(
            (item for item in classified if item.tier not in {EquityTier.LEADER, EquityTier.BLOCKED}),
            key=lambda item: item.hierarchy_score,
            default=None,
        )
        if core_candidate:
            classified = [
                _replace_tier(item, EquityTier.CORE) if item.metrics.stock_name == core_candidate.metrics.stock_name else item
                for item in classified
            ]
    return SectorEquityHierarchy(
        sector_name=sector.sector_name,
        heat_score=sector.heat_score,
        locust_score=sector.locust_score,
        risk_score=sector.risk_score,
        leader=_tier_items(classified, EquityTier.LEADER),
        core=_tier_items(classified, EquityTier.CORE),
        trend=_tier_items(classified, EquityTier.TREND),
        lagging=_tier_items(classified, EquityTier.LAGGING),
        blocked=_tier_items(classified, EquityTier.BLOCKED),
    )


def equity_hierarchy_to_output(hierarchy: SectorEquityHierarchy) -> dict[str, object]:
    return {
        "Equity Hierarchy System": "板块主线识别 + 龙头定位 + 资金结构识别 + 轮动预测 + Fib交易绑定",
        "板块名称": hierarchy.sector_name,
        "HeatScore": hierarchy.heat_score,
        "LocustScore": hierarchy.locust_score,
        "RiskScore": hierarchy.risk_score,
        "🟢 龙头股": tuple(_classified_to_output(item) for item in hierarchy.leader),
        "🟡 中军股": tuple(_classified_to_output(item) for item in hierarchy.core),
        "🔵 趋势股": tuple(_classified_to_output(item) for item in hierarchy.trend),
        "⚪ 补涨股": tuple(_classified_to_output(item) for item in hierarchy.lagging),
        "🔴 禁买股": tuple(_classified_to_output(item) for item in hierarchy.blocked),
        "Fib优先级": "龙头 > 中军 > 趋势 > 补涨；禁买股禁止生成交易动作。",
        "AI分析要求": {
            "DeepSeek": "判断是否龙头、是否中军、是否趋势、是否补涨、是否假龙头。",
            "豆包": "判断市场情绪、是否追高、是否轮动。",
        },
        "禁止规则": {
            "不只输出最强票": True,
            "不允许所有股票同权重": True,
            "必须识别龙头": True,
            "必须保留禁买池": True,
        },
    }


def _classify_equity(item: EquityMetrics, sector: SectorHierarchyInput) -> ClassifiedEquity:
    score = calculate_hierarchy_score(item)
    if item.blocked or not item.fib_valid or item.risk_score >= 78 or item.locust_score < 40:
        tier = EquityTier.BLOCKED
        warning = "破位、无资金或Fib失效，禁止交易。"
    elif _looks_like_leader(item, sector, score):
        tier = EquityTier.LEADER
        warning = "板块资金集中、Fib共振和机构主导同时较强。"
    elif item.role in {"中军", "核心标的"} or (item.institution_score >= 65 and item.volatility <= 45):
        tier = EquityTier.CORE
        warning = "机构持仓稳定，趋势持续，波动相对较低。"
    elif item.role in {"趋势票", "执行器", "控制器", "传感器", "减速器"} or item.beta >= 1.15:
        tier = EquityTier.TREND
        warning = "跟随龙头上涨，Beta较高，波段较明显。"
    else:
        tier = EquityTier.LAGGING
        warning = "轮动或低位补涨，优先级低于龙头/中军/趋势。"
    return ClassifiedEquity(
        metrics=item,
        tier=tier,
        hierarchy_score=score,
        priority=TIER_PRIORITY[tier],
        fib_binding=_fib_binding(item, tier),
        deepseek_check=_deepseek_check(item, tier),
        doubao_check=_doubao_check(item, tier),
        warning=warning,
    )


def calculate_hierarchy_score(item: EquityMetrics) -> float:
    return round(
        0.28 * _clamp(item.capital_concentration)
        + 0.22 * _clamp(item.locust_score)
        + 0.2 * _clamp(item.fib_score)
        + 0.16 * min(100.0, max(0.0, item.confluence_layers * 25.0))
        + 0.14 * _clamp(item.institution_score)
        - 0.12 * _clamp(item.risk_score),
        2,
    )


def _looks_like_leader(item: EquityMetrics, sector: SectorHierarchyInput, score: float) -> bool:
    return (
        score >= 70
        and item.capital_concentration >= 72
        and item.confluence_layers >= 3
        and item.institution_score >= 58
        and sector.heat_score >= 65
    )


def _fib_binding(item: EquityMetrics, tier: EquityTier) -> dict[str, object]:
    enabled = tier is not EquityTier.BLOCKED and item.fib_valid
    return {
        "Fib结构": "有效" if item.fib_valid else "失效",
        "买点1": "0.786回撤附近" if enabled else "禁止生成",
        "买点2": "0.236扩展附近" if enabled else "禁止生成",
        "止损": "confirmed anchor low下方" if enabled else "无",
        "止盈": "1.272 / 1.618扩展位" if enabled else "无",
        "Fib优先级": TIER_PRIORITY[tier],
    }


def _deepseek_check(item: EquityMetrics, tier: EquityTier) -> str:
    if tier is EquityTier.LEADER and item.risk_score > 68:
        return "疑似假龙头：资金集中但风险偏高，必须等待回踩确认。"
    return f"结构判断：{tier.value}；检查龙头/中军/趋势/补涨/假龙头并绑定Fib有效性。"


def _doubao_check(item: EquityMetrics, tier: EquityTier) -> str:
    if tier in {EquityTier.LEADER, EquityTier.TREND} and item.price_position > 0.82:
        return "情绪偏热，存在追高风险，等待轮动或回踩。"
    return "情绪判断：跟踪市场情绪、追高风险和轮动位置。"


def _replace_tier(item: ClassifiedEquity, tier: EquityTier) -> ClassifiedEquity:
    return ClassifiedEquity(
        metrics=item.metrics,
        tier=tier,
        hierarchy_score=item.hierarchy_score,
        priority=TIER_PRIORITY[tier],
        fib_binding=_fib_binding(item.metrics, tier),
        deepseek_check=_deepseek_check(item.metrics, tier),
        doubao_check=_doubao_check(item.metrics, tier),
        warning="板块综合分最高，自动提升为龙头候选。",
    )


def _non_leader_tier(item: EquityMetrics) -> EquityTier:
    if item.role in {"中军", "核心标的"} or item.institution_score >= 65:
        return EquityTier.CORE
    if item.role in {"趋势票", "执行器", "控制器", "传感器", "减速器"} or item.beta >= 1.15:
        return EquityTier.TREND
    return EquityTier.LAGGING


def _tier_items(items: list[ClassifiedEquity], tier: EquityTier) -> tuple[ClassifiedEquity, ...]:
    return tuple(sorted((item for item in items if item.tier is tier), key=lambda item: item.hierarchy_score, reverse=True))


def _classified_to_output(item: ClassifiedEquity) -> dict[str, object]:
    return {
        "stock_name": item.metrics.stock_name,
        "code": item.metrics.code,
        "tier": item.tier.value,
        "hierarchy_score": item.hierarchy_score,
        "priority": item.priority,
        "Fib绑定": item.fib_binding,
        "DeepSeek判断": item.deepseek_check,
        "豆包判断": item.doubao_check,
        "risk_note": item.warning,
    }


def _clamp(value: float) -> float:
    return min(100.0, max(0.0, float(value)))
