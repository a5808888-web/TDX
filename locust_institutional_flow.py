from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InstitutionScope(str, Enum):
    GLOBAL = "Global Institutional Flow"
    CHINA = "China Institutional Flow"


class InstitutionActionType(str, Enum):
    BUY = "增持"
    SELL = "减持"
    NEW_POSITION = "新建仓"
    EXIT = "清仓"
    ROTATION = "调仓"
    SECTOR_SHIFT = "行业切换"


@dataclass(frozen=True)
class InstitutionObservation:
    institution_name: str
    scope: InstitutionScope
    portfolio_change: float
    top_buy: tuple[str, ...]
    top_sell: tuple[str, ...]
    sector_from: str
    sector_to: str
    capital_flow: float
    sector_impact: float
    historical_accuracy: float
    market_resonance: float
    source: str


@dataclass(frozen=True)
class InstitutionReport:
    institution_name: str
    scope: InstitutionScope
    portfolio_change: float
    top_buy: tuple[str, ...]
    top_sell: tuple[str, ...]
    sector_shift: str
    capital_flow: float
    action_types: tuple[InstitutionActionType, ...]
    reason_analysis: str
    macro_or_sector: str
    offense_or_defense: str
    new_cycle: str
    a_share_mapping: tuple[str, ...]
    institution_score: float
    fib_weight_adjustment: float
    fib_invalid_probability_adjustment: float
    source: str


@dataclass(frozen=True)
class AShareMappedOpportunity:
    sector: str
    reason: str
    probability_delta: float
    mapped_stocks: tuple[str, ...]
    fib_weight_adjustment: float


@dataclass(frozen=True)
class InstitutionTradeCandidate:
    stock_name: str
    sector: str
    fib_buy_point: str
    institution_score: float
    action: str
    risk_note: str


@dataclass(frozen=True)
class InstitutionalFlowResult:
    global_reports: tuple[InstitutionReport, ...]
    china_reports: tuple[InstitutionReport, ...]
    sector_flow_changes: tuple[AShareMappedOpportunity, ...]
    top_trade_candidates: tuple[InstitutionTradeCandidate, ...]
    risk_notes: tuple[str, ...]
    sync_interval: int = 180


def run_institutional_flow_intelligence(
    observations: tuple[InstitutionObservation, ...],
    top_trade_candidates: tuple[InstitutionTradeCandidate, ...] = (),
) -> InstitutionalFlowResult:
    reports = tuple(_build_report(item) for item in observations)
    global_reports = tuple(item for item in reports if item.scope is InstitutionScope.GLOBAL)
    china_reports = tuple(item for item in reports if item.scope is InstitutionScope.CHINA)
    opportunities = _build_sector_opportunities(reports)
    candidates = top_trade_candidates or _default_trade_candidates(opportunities, reports)
    return InstitutionalFlowResult(
        global_reports=global_reports,
        china_reports=china_reports,
        sector_flow_changes=opportunities,
        top_trade_candidates=candidates[:3],
        risk_notes=_build_risk_notes(reports),
    )


def calculate_institution_score(
    capital_flow: float,
    sector_impact: float,
    historical_accuracy: float,
    market_resonance: float,
) -> float:
    flow_strength = min(100.0, abs(capital_flow))
    return round(
        0.4 * flow_strength
        + 0.3 * _clamp(sector_impact)
        + 0.2 * _clamp(historical_accuracy)
        + 0.1 * _clamp(market_resonance),
        2,
    )


def institutional_flow_to_output(result: InstitutionalFlowResult) -> dict[str, object]:
    return {
        "Institution Module": "全球机构行为追踪 + 中国资金流追踪 + 行业轮动识别 + AI逻辑解释 + A股映射交易信号 + Fibonacci交易系统联动",
        "sync_interval": result.sync_interval,
        "全球机构动向": tuple(_report_to_output(item) for item in result.global_reports),
        "中国机构动向": tuple(_report_to_output(item) for item in result.china_reports),
        "行业资金流变化": tuple(_opportunity_to_output(item) for item in result.sector_flow_changes),
        "逻辑解释（Why）": tuple(item.reason_analysis for item in result.global_reports + result.china_reports),
        "A股映射机会": tuple(_opportunity_to_output(item) for item in result.sector_flow_changes),
        "Top 3可交易标的": tuple(_candidate_to_output(item) for item in result.top_trade_candidates),
        "Fib买点": tuple({"stock_name": item.stock_name, "fib_buy_point": item.fib_buy_point, "institution_score": item.institution_score} for item in result.top_trade_candidates),
        "风险提示": result.risk_notes,
        "数据源": {
            "全球机构": "富途机构追踪 / Futu OpenAPI",
            "中国机构": "北向资金 / 公募基金 / 券商自营 / 保险资金 / 社保基金",
            "市场数据": "AKShare / Futu OpenAPI",
            "AI分析": "DeepSeek / 豆包",
        },
        "禁止规则": {
            "不只展示持仓": True,
            "区分全球和中国": True,
            "必须A股映射": True,
            "必须Fib交易连接": True,
        },
    }


def _build_report(item: InstitutionObservation) -> InstitutionReport:
    actions = _classify_actions(item)
    score = calculate_institution_score(item.capital_flow, item.sector_impact, item.historical_accuracy, item.market_resonance)
    mapping = _map_to_a_share(item)
    return InstitutionReport(
        institution_name=item.institution_name,
        scope=item.scope,
        portfolio_change=item.portfolio_change,
        top_buy=item.top_buy,
        top_sell=item.top_sell,
        sector_shift=f"{item.sector_from} -> {item.sector_to}" if item.sector_from and item.sector_to else "无明显行业切换",
        capital_flow=item.capital_flow,
        action_types=actions,
        reason_analysis=_reason_analysis(item, actions, mapping),
        macro_or_sector=_macro_or_sector(item),
        offense_or_defense=_offense_or_defense(item),
        new_cycle="是" if item.sector_to in {"AI", "AI硬件", "半导体", "机器人", "创新药"} and item.capital_flow > 0 else "否",
        a_share_mapping=mapping,
        institution_score=score,
        fib_weight_adjustment=0.2 if item.capital_flow > 0 else 0.0,
        fib_invalid_probability_adjustment=0.3 if item.capital_flow < 0 else 0.0,
        source=item.source,
    )


def _classify_actions(item: InstitutionObservation) -> tuple[InstitutionActionType, ...]:
    actions: list[InstitutionActionType] = []
    if item.portfolio_change > 0:
        actions.append(InstitutionActionType.BUY)
    if item.portfolio_change < 0:
        actions.append(InstitutionActionType.SELL)
    if item.top_buy and abs(item.portfolio_change) >= 8:
        actions.append(InstitutionActionType.NEW_POSITION)
    if item.top_sell and item.portfolio_change <= -8:
        actions.append(InstitutionActionType.EXIT)
    if item.sector_from and item.sector_to and item.sector_from != item.sector_to:
        actions.extend((InstitutionActionType.ROTATION, InstitutionActionType.SECTOR_SHIFT))
    return tuple(dict.fromkeys(actions))


def _map_to_a_share(item: InstitutionObservation) -> tuple[str, ...]:
    text = " ".join((item.sector_to, item.sector_from, *item.top_buy, item.institution_name)).lower()
    if "ai" in text or "nvda" in text or "semiconductor" in text or "半导体" in text:
        return ("AI服务器 / 算力 / AI硬件", "光通信 / CPO / 光模块", "算力网络")
    if "robot" in text or "机器人" in text or "tesla" in text:
        return ("人形机器人 / 具身智能", "工业自动化 / 制造业升级")
    if "consumer" in text or "消费" in text or "berkshire" in text:
        return ("消费 / 食品饮料 / 可选消费", "医药 / 创新药 / 医疗器械", "低估值红利 / 银行 / 保险 / 公用事业")
    if "risk" in text or "bridgewater" in text or "债" in text or item.capital_flow < 0:
        return ("低估值红利 / 银行 / 保险 / 公用事业", "有色金属 / 黄金 / 铜")
    if item.scope is InstitutionScope.CHINA and item.capital_flow > 0:
        return ("AI服务器 / 算力 / AI硬件", "电力 / 电网 / 电力设备 / 电算协同", "人形机器人 / 具身智能")
    return ("动态新增池",)


def _reason_analysis(
    item: InstitutionObservation,
    actions: tuple[InstitutionActionType, ...],
    mapping: tuple[str, ...],
) -> str:
    action_text = "、".join(action.value for action in actions) or "观察"
    driver = _macro_or_sector(item)
    stance = _offense_or_defense(item)
    return (
        f"{item.institution_name}出现{action_text}，核心驱动偏{driver}；"
        f"资金姿态为{stance}。行业从{item.sector_from or '原持仓'}迁移到{item.sector_to or '原行业'}，"
        f"A股映射关注{' / '.join(mapping)}。"
    )


def _macro_or_sector(item: InstitutionObservation) -> str:
    if item.institution_name in {"Bridgewater", "Soros Fund"} or item.sector_to in {"黄金", "债券", "红利"}:
        return "宏观驱动"
    return "行业驱动"


def _offense_or_defense(item: InstitutionObservation) -> str:
    if item.capital_flow > 0 and item.sector_to in {"AI", "AI硬件", "半导体", "机器人", "创新药"}:
        return "进攻"
    if item.capital_flow < 0 or item.sector_to in {"消费", "红利", "黄金", "债券"}:
        return "防御"
    return "均衡"


def _build_sector_opportunities(reports: tuple[InstitutionReport, ...]) -> tuple[AShareMappedOpportunity, ...]:
    grouped: dict[str, list[InstitutionReport]] = {}
    for report in reports:
        for sector in report.a_share_mapping:
            grouped.setdefault(sector, []).append(report)
    opportunities: list[AShareMappedOpportunity] = []
    for sector, items in grouped.items():
        avg_score = sum(item.institution_score for item in items) / len(items)
        net_flow = sum(item.capital_flow for item in items)
        opportunities.append(
            AShareMappedOpportunity(
                sector=sector,
                reason=f"{len(items)}个机构信号映射，净流向{'流入' if net_flow >= 0 else '流出'}，平均机构分{avg_score:.1f}。",
                probability_delta=round(min(0.3, max(-0.3, net_flow / 300)), 2),
                mapped_stocks=_default_stocks_for_sector(sector),
                fib_weight_adjustment=0.2 if net_flow > 0 else -0.3,
            )
        )
    return tuple(sorted(opportunities, key=lambda item: item.probability_delta, reverse=True))


def _default_trade_candidates(
    opportunities: tuple[AShareMappedOpportunity, ...],
    reports: tuple[InstitutionReport, ...],
) -> tuple[InstitutionTradeCandidate, ...]:
    score = max((item.institution_score for item in reports), default=50.0)
    candidates: list[InstitutionTradeCandidate] = []
    for opportunity in opportunities[:3]:
        stock = opportunity.mapped_stocks[0] if opportunity.mapped_stocks else "待筛选"
        candidates.append(
            InstitutionTradeCandidate(
                stock_name=stock,
                sector=opportunity.sector,
                fib_buy_point="等待多周期Fib共振区",
                institution_score=round(score, 2),
                action="观察" if opportunity.fib_weight_adjustment >= 0 else "回避",
                risk_note="机构流入增强Fib可信度，但仍禁止脱离真实价格和确认锚点交易。",
            )
        )
    return tuple(candidates)


def _build_risk_notes(reports: tuple[InstitutionReport, ...]) -> tuple[str, ...]:
    notes = ["机构资金只提升或降低Fib权重，不能替代真实价格和confirmed wave。"]
    if any(item.capital_flow < 0 for item in reports):
        notes.append("存在机构流出信号，相关板块Fib买点失效概率上升30%。")
    if any(item.offense_or_defense == "防御" for item in reports):
        notes.append("防御型资金占比上升时，降低追涨和高弹性仓位。")
    return tuple(notes)


def _default_stocks_for_sector(sector: str) -> tuple[str, ...]:
    mapping = {
        "AI服务器 / 算力 / AI硬件": ("工业富联", "浪潮信息", "中科曙光"),
        "光通信 / CPO / 光模块": ("中际旭创", "新易盛", "天孚通信"),
        "算力网络": ("中科曙光", "紫光股份", "拓维信息"),
        "人形机器人 / 具身智能": ("三花智控", "拓普集团", "绿的谐波"),
        "工业自动化 / 制造业升级": ("汇川技术", "埃斯顿", "机器人"),
        "消费 / 食品饮料 / 可选消费": ("贵州茅台", "五粮液", "美的集团"),
        "医药 / 创新药 / 医疗器械": ("恒瑞医药", "药明康德", "迈瑞医疗"),
        "低估值红利 / 银行 / 保险 / 公用事业": ("中国神华", "长江电力", "招商银行"),
        "有色金属 / 黄金 / 铜": ("紫金矿业", "山东黄金", "洛阳钼业"),
        "电力 / 电网 / 电力设备 / 电算协同": ("国电南瑞", "许继电气", "思源电气"),
    }
    return mapping.get(sector, ("动态候选",))


def _report_to_output(report: InstitutionReport) -> dict[str, object]:
    return {
        "institution_name": report.institution_name,
        "portfolio_change": report.portfolio_change,
        "top_buy": report.top_buy,
        "top_sell": report.top_sell,
        "sector_shift": report.sector_shift,
        "capital_flow": report.capital_flow,
        "action_types": tuple(item.value for item in report.action_types),
        "reason_analysis": report.reason_analysis,
        "macro_or_sector": report.macro_or_sector,
        "offense_or_defense": report.offense_or_defense,
        "new_cycle": report.new_cycle,
        "a_share_mapping": report.a_share_mapping,
        "InstitutionScore": report.institution_score,
        "Fib联动": {
            "资金流入": f"Fib买点可信度 +{int(report.fib_weight_adjustment * 100)}%" if report.fib_weight_adjustment else "无",
            "资金流出": f"Fib买点失效概率 +{int(report.fib_invalid_probability_adjustment * 100)}%" if report.fib_invalid_probability_adjustment else "无",
        },
        "source": report.source,
    }


def _opportunity_to_output(item: AShareMappedOpportunity) -> dict[str, object]:
    return {
        "sector": item.sector,
        "reason": item.reason,
        "probability_delta": item.probability_delta,
        "mapped_stocks": item.mapped_stocks,
        "fib_weight_adjustment": item.fib_weight_adjustment,
    }


def _candidate_to_output(item: InstitutionTradeCandidate) -> dict[str, object]:
    return {
        "stock_name": item.stock_name,
        "sector": item.sector,
        "fib_buy_point": item.fib_buy_point,
        "InstitutionScore": item.institution_score,
        "action": item.action,
        "risk_note": item.risk_note,
    }


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))
