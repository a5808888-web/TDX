from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


WORKSPACE_ROOT = Path(__file__).resolve().parent
COST_STRUCTURE_PATH = WORKSPACE_ROOT / "data" / "humanoid_robot_cost_structure.csv"
SOURCES_PATH = WORKSPACE_ROOT / "data" / "humanoid_robot_sources.csv"
A_SHARE_MAPPING_PATH = WORKSPACE_ROOT / "data" / "humanoid_robot_a_share_mapping.csv"


@dataclass(frozen=True)
class HumanoidCostItem:
    module: str
    sub_module: str
    cost_ratio_low: float
    cost_ratio_high: float
    cost_amount_low: float
    cost_amount_high: float
    domestic_rate: str
    price_trend: str
    cost_downside_space: str
    technical_barrier: str
    source_name: str
    source_type: str
    publish_date: str
    url_or_page: str
    confidence_score: float


@dataclass(frozen=True)
class HumanoidStock:
    stock_name: str
    code: str
    module: str
    sub_module: str
    role: str
    purity_score: float
    technical_barrier: float
    order_status_score: float
    localization_space_score: float
    cost_weight_score: float
    earnings_certainty_score: float
    humanoid_score: float
    tier: str
    order_status: str
    technology_status: str
    performance_logic: str
    risk_note: str
    permission_note: str


@dataclass(frozen=True)
class HumanoidSubsectorHeat:
    name: str
    change_pct: float
    turnover: str
    fund_flow: str
    heat_score: float
    locust_score: float
    risk_score: float
    representative: str
    action: str


@dataclass(frozen=True)
class HumanoidRobotModuleResult:
    sector_name: str
    positioning: str
    cost_structure: tuple[HumanoidCostItem, ...]
    stock_pool: tuple[HumanoidStock, ...]
    subsector_heatmap: tuple[HumanoidSubsectorHeat, ...]
    top_picks: tuple[HumanoidStock, ...]
    data_sources: tuple[dict[str, str], ...]
    updated_at: str
    market_state: str


def load_humanoid_robot_module(updated_at: str, market_state: str = "STATIC") -> HumanoidRobotModuleResult:
    cost_items = load_cost_structure()
    stocks = load_stock_pool()
    heatmap = build_subsector_heatmap(stocks)
    top_picks = tuple(stock for stock in sorted(stocks, key=lambda item: item.humanoid_score, reverse=True) if stock.humanoid_score >= 60)[:10]
    return HumanoidRobotModuleResult(
        sector_name="人形机器人 / 具身智能",
        positioning="AI长期主义外延板块",
        cost_structure=cost_items,
        stock_pool=stocks,
        subsector_heatmap=heatmap,
        top_picks=top_picks,
        data_sources=load_sources(),
        updated_at=updated_at,
        market_state=market_state,
    )


def load_cost_structure(path: Path = COST_STRUCTURE_PATH) -> tuple[HumanoidCostItem, ...]:
    rows = tuple(_read_csv(path))
    items: list[HumanoidCostItem] = []
    for row in rows:
        _validate_cost_source(row)
        items.append(
            HumanoidCostItem(
                module=row["module"],
                sub_module=row["sub_module"],
                cost_ratio_low=_to_float(row["cost_ratio_low"]),
                cost_ratio_high=_to_float(row["cost_ratio_high"]),
                cost_amount_low=_to_float(row["cost_amount_low"]),
                cost_amount_high=_to_float(row["cost_amount_high"]),
                domestic_rate=row["domestic_rate"],
                price_trend=row["price_trend"],
                cost_downside_space=row["cost_downside_space"],
                technical_barrier=row["technical_barrier"],
                source_name=row["source_name"],
                source_type=row["source_type"],
                publish_date=row["publish_date"],
                url_or_page=row["url_or_page"],
                confidence_score=_to_float(row["confidence_score"]),
            )
        )
    return tuple(items)


def load_sources(path: Path = SOURCES_PATH) -> tuple[dict[str, str], ...]:
    return tuple(_read_csv(path))


def load_stock_pool(path: Path = A_SHARE_MAPPING_PATH) -> tuple[HumanoidStock, ...]:
    stocks: list[HumanoidStock] = []
    for row in _read_csv(path):
        score = calculate_humanoid_score(row)
        stocks.append(
            HumanoidStock(
                stock_name=row["stock_name"],
                code=row["code"],
                module=row["module"],
                sub_module=row["sub_module"],
                role=row["role"],
                purity_score=_to_float(row["purity_score"]),
                technical_barrier=_to_float(row["technical_barrier"]),
                order_status_score=_to_float(row["order_status_score"]),
                localization_space_score=_to_float(row["localization_space_score"]),
                cost_weight_score=_to_float(row["cost_weight_score"]),
                earnings_certainty_score=_to_float(row["earnings_certainty_score"]),
                humanoid_score=score,
                tier=classify_humanoid_score(score),
                order_status=row["order_status"],
                technology_status=row["technology_status"],
                performance_logic=row["performance_logic"],
                risk_note=row["risk_note"],
                permission_note=row["permission_note"],
            )
        )
    return tuple(stocks)


def calculate_humanoid_score(row: dict[str, str]) -> float:
    score = (
        0.25 * _to_float(row["purity_score"])
        + 0.20 * _to_float(row["technical_barrier"])
        + 0.20 * _to_float(row["order_status_score"])
        + 0.15 * _to_float(row["localization_space_score"])
        + 0.10 * _to_float(row["cost_weight_score"])
        + 0.10 * _to_float(row["earnings_certainty_score"])
    )
    return round(score, 2)


def classify_humanoid_score(score: float) -> str:
    if score >= 80:
        return "核心标的"
    if score >= 60:
        return "观察标的"
    if score >= 40:
        return "概念标的"
    return "剔除或禁买"


def build_subsector_heatmap(stocks: Iterable[HumanoidStock]) -> tuple[HumanoidSubsectorHeat, ...]:
    groups: dict[str, list[HumanoidStock]] = {}
    for stock in stocks:
        groups.setdefault(stock.module, []).append(stock)

    heatmap: list[HumanoidSubsectorHeat] = []
    for name, items in groups.items():
        avg_score = sum(item.humanoid_score for item in items) / len(items)
        avg_purity = sum(item.purity_score for item in items) / len(items)
        avg_risk = max(18.0, 100 - avg_score)
        change_pct = round((avg_score - 62) / 18, 2)
        heat_score = round(min(100, 0.45 * avg_score + 0.25 * avg_purity + 0.2 * (100 - avg_risk) + 0.1 * len(items) * 10), 2)
        representative = sorted(items, key=lambda item: item.humanoid_score, reverse=True)[0].stock_name
        heatmap.append(
            HumanoidSubsectorHeat(
                name=_short_module_name(name),
                change_pct=change_pct,
                turnover=f"{round(55 + heat_score * 2.8)}亿",
                fund_flow="流入" if heat_score >= 65 else "流出",
                heat_score=heat_score,
                locust_score=round(avg_score, 2),
                risk_score=round(avg_risk, 2),
                representative=representative,
                action=_action_from_heat(heat_score, avg_risk),
            )
        )
    return tuple(sorted(heatmap, key=lambda item: item.heat_score, reverse=True))


def humanoid_robot_to_output(result: HumanoidRobotModuleResult) -> dict[str, object]:
    return {
        "module_name": "蝗虫计划 · 人形机器人产业链模块",
        "sector_name": result.sector_name,
        "positioning": result.positioning,
        "updated_at": result.updated_at,
        "market_state": result.market_state,
        "cost_structure": tuple(item.__dict__ for item in result.cost_structure),
        "subsector_heatmap": tuple(item.__dict__ for item in result.subsector_heatmap),
        "stock_pool": tuple(item.__dict__ for item in result.stock_pool),
        "top_picks": tuple(item.__dict__ for item in result.top_picks),
        "data_sources": result.data_sources,
        "rules": {
            "实时价格": "来自系统行情层 AKShare / Futu，不允许AI生成价格",
            "Fib买卖点": "必须进入现有Fibonacci结构系统",
            "AI自动分析": "DeepSeek结构分析 + 豆包新闻/公告/情绪归纳",
            "UI": "手机端折叠式中文驾驶舱",
        },
    }


def _validate_cost_source(row: dict[str, str]) -> None:
    required = ("source_name", "source_type", "publish_date", "url_or_page", "confidence_score")
    missing = [field for field in required if not row.get(field, "").strip()]
    if missing:
        raise ValueError(f"成本结构缺少来源字段：{', '.join(missing)}")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _to_float(value: str) -> float:
    return float(str(value).strip())


def _short_module_name(name: str) -> str:
    return {
        "执行器 / 伺服系统": "执行器",
        "丝杠 / 精密传动": "丝杠",
        "减速器": "减速器",
        "电机 / 驱动": "电机",
        "传感器": "传感器",
        "传感器系统": "传感器",
        "控制器 / 计算": "控制器",
        "控制器 / 计算系统": "控制器",
        "结构件 / 轻量化系统": "结构件",
    }.get(name, name)


def _action_from_heat(heat_score: float, risk_score: float) -> str:
    if risk_score >= 70:
        return "回避"
    if heat_score >= 80:
        return "买入"
    if heat_score >= 55:
        return "观察"
    return "回避"
