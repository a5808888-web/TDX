from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


SYNC_INTERVAL_SECONDS = 180


class HeatmapTimeframe(str, Enum):
    DAYS_7 = "近7天"
    DAYS_30 = "近30天"
    MONTH_1 = "近1个月"
    MONTH_3 = "近3个月"
    MONTH_6 = "近6个月"
    YEAR_1 = "近1年"


class StrengthLevel(str, Enum):
    STRONG = "强"
    NEUTRAL = "中性"
    WEAK = "弱"


class SectorLayer(str, Enum):
    MAINLINE = "Level 1（主线）"
    ROTATION = "Level 2（轮动）"
    DEFENSIVE = "Level 3（防守）"
    WEAK = "Level 4（弱势）"


class SectorStatus(str, Enum):
    MAINLINE = "主线"
    ROTATION = "轮动"
    FADE = "退潮"
    WATCH = "观察"


@dataclass(frozen=True)
class SectorHeatmapSource:
    name: str
    change_pct: float
    capital_flow: float
    limit_up_spread: float
    volume_change: float
    leader_strength: float
    leader_stock: str
    stock_list: tuple[str, ...]
    previous_heat_score: float = 50.0


@dataclass(frozen=True)
class HeatmapTile:
    name: str
    change_pct: float
    heat_score: int
    capital_flow: float
    capital_flow_direction: str
    strength_level: StrengthLevel
    stock_list: tuple[str, ...]
    leader_stock: str
    current_status: SectorStatus
    sector_layer: SectorLayer
    tradable: bool
    rank_change: int
    treemap_weight: float
    color: str
    top_picks_action: str
    fib_weight_adjustment: float
    reselection_triggered: bool


@dataclass(frozen=True)
class GlobalHeatmapTile:
    name: str
    change_pct: float
    heat_score: int
    impact_to_a_share: str
    capital_flow_direction: str


@dataclass(frozen=True)
class MarketHeatmapInput:
    timeframe: HeatmapTimeframe
    sectors: tuple[SectorHeatmapSource, ...]
    global_tiles: tuple[GlobalHeatmapTile, ...] = ()
    source: str = "AKShare / Eastmoney"
    timestamp: str = ""


@dataclass(frozen=True)
class MarketHeatmapResult:
    timeframe: HeatmapTimeframe
    tiles: tuple[HeatmapTile, ...]
    global_tiles: tuple[GlobalHeatmapTile, ...]
    top_picks_pool: tuple[str, ...]
    forbidden_pool: tuple[str, ...]
    reselection_triggers: tuple[str, ...]
    fib_weight_by_sector: dict[str, float]
    global_linkage: dict[str, str]
    sync_interval: int
    source: str
    timestamp: str


def run_market_heatmap_system(data: MarketHeatmapInput) -> MarketHeatmapResult:
    tiles = tuple(
        sorted(
            (_build_tile(_resample_source(item, data.timeframe)) for item in data.sectors),
            key=lambda item: item.heat_score,
            reverse=True,
        )
    )
    top_picks = tuple(item.name for item in tiles if item.heat_score > 80)
    forbidden = tuple(item.name for item in tiles if item.heat_score < 40)
    triggers = tuple(item.name for item in tiles if item.reselection_triggered)
    fib_weights = {item.name: item.fib_weight_adjustment for item in tiles}
    return MarketHeatmapResult(
        timeframe=data.timeframe,
        tiles=tiles,
        global_tiles=data.global_tiles,
        top_picks_pool=top_picks,
        forbidden_pool=forbidden,
        reselection_triggers=triggers,
        fib_weight_by_sector=fib_weights,
        global_linkage=_build_global_linkage(data.global_tiles),
        sync_interval=SYNC_INTERVAL_SECONDS,
        source=data.source,
        timestamp=data.timestamp,
    )


def calculate_heat_score(
    change_pct: float,
    capital_flow: float,
    limit_up_spread: float,
    volume_change: float,
    leader_strength: float,
) -> int:
    change_strength = _score_change_pct(change_pct)
    capital_strength = _score_signed_metric(capital_flow)
    limit_strength = _score_unit_metric(limit_up_spread)
    volume_strength = _score_signed_metric(volume_change)
    leader = _score_unit_metric(leader_strength)
    return _clamp_int(
        0.35 * change_strength
        + 0.25 * capital_strength
        + 0.20 * limit_strength
        + 0.15 * volume_strength
        + 0.05 * leader
    )


def market_heatmap_to_output(result: MarketHeatmapResult) -> dict[str, object]:
    return {
        "Market Heatmap System": "实时资金流地图 + 板块强弱识别 + 选股池驱动引擎 + Fib交易权重系统 + AI决策输入层",
        "sync_interval": result.sync_interval,
        "timeframe": result.timeframe.value,
        "source": result.source,
        "timestamp": result.timestamp,
        "行业热力图矩阵": tuple(_tile_to_output(item) for item in result.tiles),
        "Global Heatmap": tuple(_global_tile_to_output(item) for item in result.global_tiles),
        "联动结果": {
            "Top Picks池": result.top_picks_pool,
            "禁买池": result.forbidden_pool,
            "重新选股触发": result.reselection_triggers,
            "Fib权重": result.fib_weight_by_sector,
            "全球联动": result.global_linkage,
        },
        "UI规则": {
            "Treemap": True,
            "默认Top10": True,
            "禁止表格": True,
            "支持周期切换": tuple(item.value for item in HeatmapTimeframe),
        },
    }


def _build_tile(source: SectorHeatmapSource) -> HeatmapTile:
    heat_score = calculate_heat_score(
        source.change_pct,
        source.capital_flow,
        source.limit_up_spread,
        source.volume_change,
        source.leader_strength,
    )
    return HeatmapTile(
        name=source.name,
        change_pct=round(source.change_pct, 2),
        heat_score=heat_score,
        capital_flow=round(source.capital_flow, 2),
        capital_flow_direction="流入" if source.capital_flow >= 0 else "流出",
        strength_level=_classify_strength(source.change_pct),
        stock_list=source.stock_list,
        leader_stock=source.leader_stock,
        current_status=_classify_status(heat_score),
        sector_layer=_classify_layer(source.name, heat_score),
        tradable=heat_score >= 60,
        rank_change=round(heat_score - source.previous_heat_score),
        treemap_weight=max(6.0, float(heat_score)),
        color=_tile_color(source.change_pct),
        top_picks_action=_top_picks_action(heat_score),
        fib_weight_adjustment=_fib_weight_adjustment(heat_score),
        reselection_triggered=abs(heat_score - source.previous_heat_score) > 10,
    )


def _resample_source(source: SectorHeatmapSource, timeframe: HeatmapTimeframe) -> SectorHeatmapSource:
    multiplier = {
        HeatmapTimeframe.DAYS_7: 1.0,
        HeatmapTimeframe.DAYS_30: 1.18,
        HeatmapTimeframe.MONTH_1: 1.18,
        HeatmapTimeframe.MONTH_3: 1.42,
        HeatmapTimeframe.MONTH_6: 1.68,
        HeatmapTimeframe.YEAR_1: 2.15,
    }[timeframe]
    return SectorHeatmapSource(
        name=source.name,
        change_pct=source.change_pct * multiplier,
        capital_flow=source.capital_flow * multiplier,
        limit_up_spread=min(1.0, source.limit_up_spread * (0.88 + multiplier * 0.12)),
        volume_change=source.volume_change * multiplier,
        leader_strength=source.leader_strength,
        leader_stock=source.leader_stock,
        stock_list=source.stock_list,
        previous_heat_score=source.previous_heat_score,
    )


def _build_global_linkage(global_tiles: tuple[GlobalHeatmapTile, ...]) -> dict[str, str]:
    linkage: dict[str, str] = {}
    ai_heat = max((item.heat_score for item in global_tiles if item.name in {"半导体（美股）", "AI芯片", "纳斯达克"}), default=0)
    if ai_heat >= 80:
        linkage["A股AI权重"] = "提升"
    elif ai_heat <= 40:
        linkage["A股AI权重"] = "降低"
    else:
        linkage["A股AI权重"] = "中性"
    gold_heat = next((item.heat_score for item in global_tiles if item.name == "黄金"), 0)
    if gold_heat >= 75:
        linkage["避险链"] = "黄金/有色权重提升"
    return linkage


def _tile_to_output(tile: HeatmapTile) -> dict[str, object]:
    return {
        "name": tile.name,
        "change_pct": tile.change_pct,
        "heat_score": tile.heat_score,
        "capital_flow": tile.capital_flow,
        "capital_flow_direction": tile.capital_flow_direction,
        "strength_level": tile.strength_level.value,
        "stock_list": tile.stock_list,
        "leader_stock": tile.leader_stock,
        "current_status": tile.current_status.value,
        "sector_layer": tile.sector_layer.value,
        "tradable": "YES" if tile.tradable else "NO",
        "rank_change": tile.rank_change,
        "treemap_weight": tile.treemap_weight,
        "color": tile.color,
        "top_picks_action": tile.top_picks_action,
        "fib_weight_adjustment": tile.fib_weight_adjustment,
        "reselection_triggered": tile.reselection_triggered,
    }


def _global_tile_to_output(tile: GlobalHeatmapTile) -> dict[str, object]:
    return {
        "name": tile.name,
        "change_pct": tile.change_pct,
        "heat_score": tile.heat_score,
        "capital_flow_direction": tile.capital_flow_direction,
        "impact_to_a_share": tile.impact_to_a_share,
    }


def _classify_strength(change_pct: float) -> StrengthLevel:
    if change_pct >= 2:
        return StrengthLevel.STRONG
    if -1 <= change_pct <= 1:
        return StrengthLevel.NEUTRAL
    if change_pct <= -3:
        return StrengthLevel.WEAK
    return StrengthLevel.NEUTRAL


def _classify_status(heat_score: int) -> SectorStatus:
    if heat_score > 80:
        return SectorStatus.MAINLINE
    if heat_score >= 60:
        return SectorStatus.ROTATION
    if heat_score < 40:
        return SectorStatus.FADE
    return SectorStatus.WATCH


def _classify_layer(name: str, heat_score: int) -> SectorLayer:
    if name in {"AI服务器", "光通信", "算力网络"} or heat_score > 80:
        return SectorLayer.MAINLINE
    if name in {"机器人", "人形机器人", "电力", "存储"} or heat_score >= 60:
        return SectorLayer.ROTATION
    if name in {"银行", "消费", "医药", "红利防守"}:
        return SectorLayer.DEFENSIVE
    return SectorLayer.WEAK


def _tile_color(change_pct: float) -> str:
    if change_pct >= 2:
        return "green"
    if -1 <= change_pct <= 1:
        return "yellow"
    if change_pct <= -3:
        return "red"
    return "yellow"


def _top_picks_action(heat_score: int) -> str:
    if heat_score > 80:
        return "加入Top Picks池"
    if heat_score < 40:
        return "加入禁买池"
    return "维持观察"


def _fib_weight_adjustment(heat_score: int) -> float:
    if heat_score > 80:
        return 0.2
    if heat_score < 40:
        return -1.0
    return 0.0


def _score_change_pct(change_pct: float) -> float:
    return max(0.0, min(100.0, 50.0 + change_pct * 12.5))


def _score_signed_metric(value: float) -> float:
    return max(0.0, min(100.0, 50.0 + value * 0.5))


def _score_unit_metric(value: float) -> float:
    if value <= 1:
        return max(0.0, min(100.0, value * 100.0))
    return max(0.0, min(100.0, value))


def _clamp_int(value: float) -> int:
    return int(round(max(0.0, min(100.0, value))))
