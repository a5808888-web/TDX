from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from html import escape

from fibonacci_wave_system import SwingKind, WaveSegment


RETRACEMENT_RATIOS: tuple[float, ...] = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)
EXTENSION_RATIOS: tuple[float, ...] = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.0)
ALL_DISPLAY_RATIOS: tuple[float, ...] = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.0)
INTRADAY_TIMEFRAMES = {"1m", "3m", "5m", "15m", "30m", "60m", "1min", "3min", "5min", "15min", "30min", "60min", "intraday"}


class LevelType(str, Enum):
    RETRACEMENT = "retracement"
    EXTENSION = "extension"
    ANCHOR = "anchor"


class ContractDecision(str, Enum):
    BUY = "BUY"
    WATCH = "WATCH"
    AVOID = "AVOID"


@dataclass(frozen=True)
class ContractAnalysisInput:
    wave: WaveSegment
    current_price: float
    symbol: str = ""
    stock_name: str = ""
    confluence_strength: float = 50.0
    trend_strength: float = 50.0
    volume_fit: float = 50.0
    capital_flow: float = 50.0
    stop_fall_confirmed: bool = False
    volume_confirmed: bool = False
    risk_score: float = 40.0


@dataclass(frozen=True)
class PriceLevel:
    level_type: LevelType
    ratio: float
    label: str
    price: float
    distance_to_current_price: float
    role: str


@dataclass(frozen=True)
class ContractBuyPoint:
    name: str
    level_type: LevelType
    ratio: float
    price: float
    role: str
    entry_rule: str
    stop_loss: float
    take_profit_targets: tuple[float, ...]
    risk_level: str


@dataclass(frozen=True)
class ScoreSystem:
    wave_structure_stability: float
    confluence_strength: float
    trend_strength: float
    volume_fit: float
    capital_flow: float
    fib_score: float


@dataclass(frozen=True)
class RiskControl:
    single_trade_risk_pct: tuple[float, float]
    stop_loss_rule: str
    position_rule: str
    add_position_rule: str
    exit_rule: str


@dataclass(frozen=True)
class ContractStrategy:
    buy_point_1: ContractBuyPoint
    buy_point_2: ContractBuyPoint
    position_advice: str
    risk_level: str


@dataclass(frozen=True)
class KeyConclusion:
    current_wave_position: str
    buy_point_1_valid: bool
    buy_point_2_watchable: bool
    trend_view: str
    action: ContractDecision
    risk_warning: str


@dataclass(frozen=True)
class TradePlan:
    buy_plan: str
    add_plan: str
    stop_loss_plan: str
    take_profit_plan: str
    leave_conditions: str


@dataclass(frozen=True)
class ContractFibAnalysis:
    symbol: str
    stock_name: str
    anchor_low: float
    anchor_high: float
    wave_range: float
    current_price: float
    retracement_levels: tuple[PriceLevel, ...]
    extension_levels: tuple[PriceLevel, ...]
    extension_targets: tuple[PriceLevel, ...]
    key_price_zones: tuple[PriceLevel, ...]
    best_buy_zone: tuple[float, float]
    strategy: ContractStrategy
    risk_control: RiskControl
    scores: ScoreSystem
    conclusion: KeyConclusion
    trade_plan: TradePlan


def build_contract_fib_analysis(data: ContractAnalysisInput) -> ContractFibAnalysis:
    _validate_contract_input(data)
    wave = data.wave
    anchor_low = _money(wave.low.price)
    anchor_high = _money(wave.high.price)
    wave_range = _money(anchor_high - anchor_low)
    current_price = _money(data.current_price)

    retracements = tuple(
        PriceLevel(
            level_type=LevelType.RETRACEMENT if ratio not in {0.0, 1.0} else LevelType.ANCHOR,
            ratio=ratio,
            label=_retracement_label(ratio),
            price=_money(anchor_high - wave_range * ratio),
            distance_to_current_price=_money(anchor_high - wave_range * ratio - current_price),
            role=_retracement_role(ratio),
        )
        for ratio in RETRACEMENT_RATIOS
    )
    extensions = tuple(
        PriceLevel(
            level_type=LevelType.EXTENSION,
            ratio=ratio,
            label=f"扩展 {ratio:g}",
            price=_money(anchor_low + wave_range * ratio),
            distance_to_current_price=_money(anchor_low + wave_range * ratio - current_price),
            role=_extension_role(ratio),
        )
        for ratio in EXTENSION_RATIOS
    )

    buy_zone_low = _level_price(retracements, 0.786)
    buy_zone_high = _level_price(retracements, 0.618)
    key_levels = _build_key_price_zones(retracements, extensions)
    extension_targets = _build_extension_targets(extensions)
    scores = _build_scores(data, current_price, buy_zone_low, buy_zone_high)
    strategy = _build_strategy(retracements, extensions, anchor_low, anchor_high, wave_range, scores)
    conclusion = _build_conclusion(data, current_price, buy_zone_low, buy_zone_high, strategy, scores)
    trade_plan = _build_trade_plan(strategy, conclusion)

    return ContractFibAnalysis(
        symbol=data.symbol,
        stock_name=data.stock_name,
        anchor_low=anchor_low,
        anchor_high=anchor_high,
        wave_range=wave_range,
        current_price=current_price,
        retracement_levels=retracements,
        extension_levels=extensions,
        extension_targets=extension_targets,
        key_price_zones=key_levels,
        best_buy_zone=(_money(buy_zone_low), _money(buy_zone_high)),
        strategy=strategy,
        risk_control=RiskControl(
            single_trade_risk_pct=(1.0, 2.0),
            stop_loss_rule="严格执行止损，不抗单；跌破关键支撑需减仓或离场。",
            position_rule="分批止盈，保留趋势仓位。",
            add_position_rule="突破关键位置并放量确认后再加仓。",
            exit_rule="跌破关键支撑、共振失效或风险分过高时离场。",
        ),
        scores=scores,
        conclusion=conclusion,
        trade_plan=trade_plan,
    )


def contract_analysis_to_output(result: ContractFibAnalysis) -> dict[str, object]:
    return {
        "主图": {
            "symbol": result.symbol,
            "stock_name": result.stock_name,
            "anchor_low": result.anchor_low,
            "anchor_high": result.anchor_high,
            "range": result.wave_range,
            "current_price": result.current_price,
            "retracement_levels": _levels_to_output(result.retracement_levels),
            "extension_levels": _levels_to_output(result.extension_levels),
            "extension_targets": _levels_to_output(result.extension_targets),
            "best_buy_zone": result.best_buy_zone,
        },
        "斐波那契参考表": {
            "回撤位": _reference_table("retracement"),
            "扩展位": _reference_table("extension"),
        },
        "买点详细信息": {
            "买点1": _buy_point_to_output(result.strategy.buy_point_1),
            "买点2": _buy_point_to_output(result.strategy.buy_point_2),
        },
        "我的理解": {
            "wave_structure": "完整上升波段：低点到高点；回撤找支撑，扩展找突破后的目标与压力。",
            "current_position": result.conclusion.current_wave_position,
            "buy_points": {
                "买点1": result.strategy.buy_point_1.role,
                "买点2": result.strategy.buy_point_2.role,
            },
            "trend_view": result.conclusion.trend_view,
        },
        "两个买点的作用": {
            "买点1": _buy_point_to_output(result.strategy.buy_point_1),
            "买点2": _buy_point_to_output(result.strategy.buy_point_2),
        },
        "关键价格区间": _levels_to_output(result.key_price_zones),
        "波段目标位": _levels_to_output(result.extension_targets),
        "交易策略": {
            "position_advice": result.strategy.position_advice,
            "risk_level": result.strategy.risk_level,
        },
        "风险控制": {
            "single_trade_risk_pct": result.risk_control.single_trade_risk_pct,
            "stop_loss_rule": result.risk_control.stop_loss_rule,
            "position_rule": result.risk_control.position_rule,
            "add_position_rule": result.risk_control.add_position_rule,
            "exit_rule": result.risk_control.exit_rule,
        },
        "评分系统": {
            "wave_structure_stability": result.scores.wave_structure_stability,
            "confluence_strength": result.scores.confluence_strength,
            "trend_strength": result.scores.trend_strength,
            "volume_fit": result.scores.volume_fit,
            "capital_flow": result.scores.capital_flow,
            "FibScore": result.scores.fib_score,
        },
        "关键结论": {
            "action": result.conclusion.action.value,
            "buy_point_1_valid": result.conclusion.buy_point_1_valid,
            "buy_point_2_watchable": result.conclusion.buy_point_2_watchable,
            "risk_warning": result.conclusion.risk_warning,
        },
        "交易计划": {
            "buy_plan": result.trade_plan.buy_plan,
            "add_plan": result.trade_plan.add_plan,
            "stop_loss_plan": result.trade_plan.stop_loss_plan,
            "take_profit_plan": result.trade_plan.take_profit_plan,
            "leave_conditions": result.trade_plan.leave_conditions,
        },
    }


def render_contract_analysis_html(result: ContractFibAnalysis) -> str:
    title = _title(result)
    svg = _render_price_svg(result)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{ margin: 0; background: #090d11; color: #eef4f8; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 18px; }}
    h1 {{ font-size: 24px; margin: 0 0 12px; color: #ffd54a; }}
    h2 {{ margin: 0 0 10px; font-size: 16px; color: #ffd54a; }}
    .grid {{ display: grid; grid-template-columns: 2fr 1.2fr 1.2fr; gap: 10px; }}
    .panel {{ border: 1px solid #394653; border-radius: 6px; padding: 12px; background: #0c1116; }}
    .wide {{ grid-column: span 2; }}
    .full {{ grid-column: 1 / -1; }}
    ul {{ margin: 0; padding-left: 18px; line-height: 1.7; }}
    .green {{ color: #39e66f; }}
    .red {{ color: #ff5757; }}
    .cyan {{ color: #62d9ff; }}
    .score {{ display: grid; grid-template-columns: 1fr auto; gap: 8px; }}
    .score strong {{ color: #39e66f; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #26323d; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #151c23; color: #ffd54a; }}
    .blue-row {{ background: rgba(25, 91, 150, 0.24); }}
    .red-row {{ background: rgba(150, 55, 38, 0.24); }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} .wide {{ grid-column: auto; }} }}
  </style>
</head>
<body>
  <main class="wrap">
    <h1>{escape(title)}</h1>
    <section class="panel full">{svg}</section>
    <section class="grid">
      {_reference_panel()}
      {_panel("我的理解（核心逻辑）", [
          "波段结构：低点到高点构成完整斐波那契契约波段。",
          f"当前位置：{result.conclusion.current_wave_position}",
          f"最佳买点波段：{result.best_buy_zone[0]:.2f} ~ {result.best_buy_zone[1]:.2f}",
          f"趋势判断：{result.conclusion.trend_view}",
      ])}
      {_panel("两个买点的作用", [
          f"买点1（回撤0.786）：{result.strategy.buy_point_1.price:.2f}，深度回撤支撑。",
          f"买点2（扩展0.236）：{result.strategy.buy_point_2.price:.2f}，突破后的二次入场点。",
      ])}
      {_buy_point_table(result)}
      {_panel("交易策略", [
          f"买点1入场：{result.strategy.buy_point_1.entry_rule}",
          f"买点2入场：{result.strategy.buy_point_2.entry_rule}",
          f"仓位建议：{result.strategy.position_advice}",
          f"风险等级：{result.strategy.risk_level}",
      ])}
      {_panel("关键价格区间", [f"{level.label}：{level.price:.2f}（{level.role}）" for level in result.key_price_zones], "wide")}
      {_panel("波段目标位（Extension Targets）", [f"{level.label}：{level.price:.2f}（{level.role}）" for level in result.extension_targets])}
      {_panel("风险控制", [
          "单笔风险控制在总资金的 1%~2%。",
          result.risk_control.stop_loss_rule,
          result.risk_control.position_rule,
          result.risk_control.add_position_rule,
          result.risk_control.exit_rule,
      ])}
      {_score_panel(result.scores)}
      {_panel("关键结论（总结）", [
          f"操作建议：{result.conclusion.action.value}",
          f"买点1有效：{'是' if result.conclusion.buy_point_1_valid else '否'}",
          f"买点2可关注：{'是' if result.conclusion.buy_point_2_watchable else '否'}",
          result.conclusion.risk_warning,
      ])}
      {_panel("交易计划", [
          result.trade_plan.buy_plan,
          result.trade_plan.add_plan,
          result.trade_plan.stop_loss_plan,
          result.trade_plan.take_profit_plan,
          result.trade_plan.leave_conditions,
      ], "full")}
    </section>
  </main>
</body>
</html>"""


def _validate_contract_input(data: ContractAnalysisInput) -> None:
    if data.current_price <= 0:
        raise ValueError("current_price must be positive.")
    _validate_score(data.confluence_strength, "confluence_strength")
    _validate_score(data.trend_strength, "trend_strength")
    _validate_score(data.volume_fit, "volume_fit")
    _validate_score(data.capital_flow, "capital_flow")
    _validate_score(data.risk_score, "risk_score")
    wave = data.wave
    if wave.low.kind is not SwingKind.LOW or wave.high.kind is not SwingKind.HIGH:
        raise ValueError("契约波段必须从确认低点到确认高点。")
    if not wave.confirmed:
        raise ValueError("禁止未确认波段参与计算。")
    if wave.low.price <= 0 or wave.high.price <= 0 or wave.high.price <= wave.low.price:
        raise ValueError("契约波段价格必须为正，且终点高于起点。")
    if _is_intraday(wave.low.timeframe) or _is_intraday(wave.high.timeframe):
        raise ValueError("禁止使用日内极值作为契约波段锚点。")


def _build_key_price_zones(retracements: tuple[PriceLevel, ...], extensions: tuple[PriceLevel, ...]) -> tuple[PriceLevel, ...]:
    ratio_order = [
        (LevelType.RETRACEMENT, 0.786),
        (LevelType.EXTENSION, 0.236),
        (LevelType.RETRACEMENT, 0.618),
        (LevelType.RETRACEMENT, 0.5),
        (LevelType.RETRACEMENT, 0.382),
        (LevelType.ANCHOR, 0.0),
        (LevelType.EXTENSION, 1.272),
        (LevelType.EXTENSION, 1.618),
        (LevelType.EXTENSION, 2.0),
    ]
    result: list[PriceLevel] = []
    for level_type, ratio in ratio_order:
        levels = extensions if level_type is LevelType.EXTENSION else retracements
        result.append(_level(levels, ratio))
    return tuple(result)


def _build_extension_targets(extensions: tuple[PriceLevel, ...]) -> tuple[PriceLevel, ...]:
    return tuple(_level(extensions, ratio) for ratio in (1.0, 1.272, 1.618, 2.0))


def _build_scores(data: ContractAnalysisInput, current_price: float, zone_low: float, zone_high: float) -> ScoreSystem:
    wave_score = 90.0
    if zone_low <= current_price <= zone_high:
        wave_score = 96.0
    elif current_price > data.wave.high.price:
        wave_score = 82.0
    risk_penalty = max(0.0, data.risk_score - 60.0) * 0.4
    fib_score = _clamp(
        wave_score * 0.25
        + data.confluence_strength * 0.25
        + data.trend_strength * 0.2
        + data.volume_fit * 0.15
        + data.capital_flow * 0.15
        - risk_penalty
    )
    return ScoreSystem(
        wave_structure_stability=_money(wave_score),
        confluence_strength=_money(data.confluence_strength),
        trend_strength=_money(data.trend_strength),
        volume_fit=_money(data.volume_fit),
        capital_flow=_money(data.capital_flow),
        fib_score=_money(fib_score),
    )


def _build_strategy(
    retracements: tuple[PriceLevel, ...],
    extensions: tuple[PriceLevel, ...],
    anchor_low: float,
    anchor_high: float,
    wave_range: float,
    scores: ScoreSystem,
) -> ContractStrategy:
    buy1_price = _level_price(retracements, 0.786)
    buy2_price = _level_price(extensions, 0.236)
    stop1 = _money(max(anchor_low * 0.98, buy1_price - wave_range * 0.05))
    stop2 = _money(max(anchor_low * 0.98, buy2_price - wave_range * 0.05))
    target_1000 = _level_price(extensions, 1.0)
    target_1272 = _level_price(extensions, 1.272)
    target_1618 = _level_price(extensions, 1.618)
    target_2000 = _level_price(extensions, 2.0)
    buy1 = ContractBuyPoint(
        name="买点1",
        level_type=LevelType.RETRACEMENT,
        ratio=0.786,
        price=buy1_price,
        role="深度回撤支撑，适合低吸区。",
        entry_rule="价格进入 0.786~0.618 回撤带，并出现止跌确认后分批入场。",
        stop_loss=stop1,
        take_profit_targets=(_level_price(retracements, 0.618), _level_price(retracements, 0.5), anchor_high, buy2_price),
        risk_level="中" if scores.fib_score >= 60 else "高",
    )
    buy2 = ContractBuyPoint(
        name="买点2",
        level_type=LevelType.EXTENSION,
        ratio=0.236,
        price=buy2_price,
        role="突破后的二次入场点，用于趋势延续确认。",
        entry_rule="有效突破扩展 0.236 并放量站稳后再入场。",
        stop_loss=stop2,
        take_profit_targets=(target_1000, target_1272, target_1618, target_2000),
        risk_level="低" if scores.fib_score >= 75 else "中",
    )
    return ContractStrategy(
        buy_point_1=buy1,
        buy_point_2=buy2,
        position_advice="买点1轻仓试错，买点2确认后加仓；单笔风险限制在 1%~2%。",
        risk_level="低" if scores.fib_score >= 80 else "中" if scores.fib_score >= 55 else "高",
    )


def _build_conclusion(
    data: ContractAnalysisInput,
    current_price: float,
    zone_low: float,
    zone_high: float,
    strategy: ContractStrategy,
    scores: ScoreSystem,
) -> KeyConclusion:
    in_best_zone = zone_low <= current_price <= zone_high
    at_buy2 = strategy.buy_point_2.price * 0.995 <= current_price <= strategy.buy_point_2.price * 1.015
    above_buy2 = current_price >= strategy.buy_point_2.price
    buy1_valid = in_best_zone and data.stop_fall_confirmed and scores.fib_score >= 60
    buy2_watchable = at_buy2 and data.volume_confirmed and scores.trend_strength >= 60
    if data.risk_score >= 80 or scores.fib_score < 40:
        action = ContractDecision.AVOID
    elif buy1_valid or buy2_watchable:
        action = ContractDecision.BUY
    else:
        action = ContractDecision.WATCH

    if in_best_zone:
        current_position = "当前处于最佳买点回撤波段。"
    elif at_buy2:
        current_position = "当前靠近扩展 0.236 二次入场点，需确认是否站稳。"
    elif above_buy2:
        current_position = "当前高于扩展 0.236，需等待回踩或放量确认。"
    elif current_price > data.wave.high.price:
        current_position = "当前高于波段终点，偏趋势延续。"
    elif current_price < zone_low:
        current_position = "当前跌破深度回撤支撑，风险抬升。"
    else:
        current_position = "当前处于中性观察区。"

    trend_view = "多头" if scores.trend_strength >= 65 else "空头" if scores.trend_strength <= 35 else "震荡"
    risk_warning = "风险分过高，禁止交易。" if data.risk_score >= 80 else "严格等待价格、成交量与共振确认。"
    return KeyConclusion(
        current_wave_position=current_position,
        buy_point_1_valid=buy1_valid,
        buy_point_2_watchable=buy2_watchable,
        trend_view=trend_view,
        action=action,
        risk_warning=risk_warning,
    )


def _build_trade_plan(strategy: ContractStrategy, conclusion: KeyConclusion) -> TradePlan:
    return TradePlan(
        buy_plan=f"买点1关注 {strategy.buy_point_1.price:.2f}；只在止跌确认后执行。",
        add_plan=f"买点2关注 {strategy.buy_point_2.price:.2f}；突破并放量站稳后加仓。",
        stop_loss_plan=f"买点1止损 {strategy.buy_point_1.stop_loss:.2f}；买点2止损 {strategy.buy_point_2.stop_loss:.2f}。",
        take_profit_plan="分批止盈：先看波段高点，再看扩展 1.272、1.618 与 2.0。",
        leave_conditions=f"离场条件：{conclusion.risk_warning}",
    )


def _render_price_svg(result: ContractFibAnalysis) -> str:
    levels = result.retracement_levels + result.extension_levels
    min_price = min(level.price for level in levels + (PriceLevel(LevelType.ANCHOR, -1, "现价", result.current_price, 0, ""),))
    max_price = max(level.price for level in levels + (PriceLevel(LevelType.ANCHOR, -1, "现价", result.current_price, 0, ""),))
    pad = (max_price - min_price) * 0.12 or 1
    min_price -= pad
    max_price += pad

    def y(price: float) -> float:
        return 520 - ((price - min_price) / (max_price - min_price)) * 450

    zone_y1 = y(result.best_buy_zone[1])
    zone_y2 = y(result.best_buy_zone[0])
    rows = [
        f'<rect x="170" y="{zone_y1:.1f}" width="880" height="{zone_y2 - zone_y1:.1f}" fill="#123d2a" opacity="0.5"/>',
        f'<text x="180" y="{zone_y1 + 22:.1f}" fill="#39e66f" font-size="15">最佳买点波段 {result.best_buy_zone[0]:.2f} ~ {result.best_buy_zone[1]:.2f}</text>',
    ]
    for level in levels:
        color = "#39e66f" if level.level_type is LevelType.RETRACEMENT else "#ffcc4d"
        if level.ratio == 0.786:
            color = "#20e0a0"
        if level.level_type is LevelType.EXTENSION:
            color = "#ff6b55"
        yy = y(level.price)
        rows.append(f'<line x1="140" y1="{yy:.1f}" x2="1060" y2="{yy:.1f}" stroke="{color}" stroke-width="1.2" opacity="0.85"/>')
        rows.append(f'<text x="24" y="{yy + 4:.1f}" fill="{color}" font-size="13">{escape(level.label)}</text>')
        rows.append(f'<text x="1075" y="{yy + 4:.1f}" fill="{color}" font-size="13">{level.price:.2f}</text>')
    current_y = y(result.current_price)
    buy2_y = y(result.strategy.buy_point_2.price)
    rows.append(f'<rect x="680" y="{buy2_y - 14:.1f}" width="260" height="38" rx="6" fill="#4a1512" stroke="#ff5757" opacity="0.85"/>')
    rows.append(f'<text x="695" y="{buy2_y + 8:.1f}" fill="#fff2f2" font-size="14">买点2 扩展0.236 {result.strategy.buy_point_2.price:.2f}</text>')
    rows.append(f'<line x1="120" y1="{current_y:.1f}" x2="1090" y2="{current_y:.1f}" stroke="#62d9ff" stroke-width="2.4"/>')
    rows.append(f'<text x="890" y="{current_y - 8:.1f}" fill="#62d9ff" font-size="15">当前价格 {result.current_price:.2f}</text>')
    rows.append(f'<circle cx="300" cy="{y(result.anchor_low):.1f}" r="6" fill="#39e66f"/><text x="315" y="{y(result.anchor_low)+5:.1f}" fill="#eef4f8" font-size="13">起点低点 {result.anchor_low:.2f}</text>')
    rows.append(f'<circle cx="820" cy="{y(result.anchor_high):.1f}" r="6" fill="#ffcc4d"/><text x="835" y="{y(result.anchor_high)+5:.1f}" fill="#eef4f8" font-size="13">终点高点 {result.anchor_high:.2f}</text>')
    rows.append(f'<line x1="300" y1="{y(result.anchor_low):.1f}" x2="820" y2="{y(result.anchor_high):.1f}" stroke="#eef4f8" stroke-width="2" opacity="0.7"/>')
    return f'<svg viewBox="0 0 1180 560" width="100%" role="img" aria-label="斐波那契回撤与扩展交易图">{"".join(rows)}</svg>'


def _panel(title: str, items: list[str], extra_class: str = "") -> str:
    lis = "".join(f"<li>{escape(item)}</li>" for item in items)
    class_name = f"panel {extra_class}".strip()
    return f'<section class="{class_name}"><h2>{escape(title)}</h2><ul>{lis}</ul></section>'


def _score_panel(scores: ScoreSystem) -> str:
    rows = [
        ("波段结构稳定性", scores.wave_structure_stability),
        ("共振强度", scores.confluence_strength),
        ("趋势强度", scores.trend_strength),
        ("成交量配合度", scores.volume_fit),
        ("资金流向", scores.capital_flow),
        ("综合 FibScore", scores.fib_score),
    ]
    body = "".join(f"<span>{escape(name)}</span><strong>{value:.2f}</strong>" for name, value in rows)
    return f'<section class="panel"><h2>评分系统</h2><div class="score">{body}</div></section>'


def _reference_panel() -> str:
    retracement_rows = "".join(
        f"<tr><td>{ratio:g}</td><td>{escape(text)}</td></tr>"
        for ratio, text in _reference_table("retracement")
    )
    extension_rows = "".join(
        f"<tr><td>{ratio:g}</td><td>{escape(text)}</td></tr>"
        for ratio, text in _reference_table("extension")
    )
    return (
        '<section class="panel wide"><h2>斐波那契参考表</h2>'
        '<div class="grid">'
        f'<div><table><thead><tr><th>回撤位</th><th>含义</th></tr></thead><tbody>{retracement_rows}</tbody></table></div>'
        f'<div><table><thead><tr><th>扩展位</th><th>含义</th></tr></thead><tbody>{extension_rows}</tbody></table></div>'
        '</div></section>'
    )


def _buy_point_table(result: ContractFibAnalysis) -> str:
    buy1 = result.strategy.buy_point_1
    buy2 = result.strategy.buy_point_2
    return (
        '<section class="panel"><h2>买点详细信息</h2><table>'
        '<thead><tr><th>买点类型</th><th>位置</th><th>价格</th><th>作用</th><th>风险</th></tr></thead>'
        '<tbody>'
        f'<tr class="blue-row"><td>买点1<br>回撤买点</td><td>回撤 {buy1.ratio:g}</td><td>{buy1.price:.2f}</td><td>{escape(buy1.role)}</td><td>{escape(buy1.risk_level)}</td></tr>'
        f'<tr class="red-row"><td>买点2<br>扩展买点</td><td>扩展 {buy2.ratio:g}</td><td>{buy2.price:.2f}</td><td>{escape(buy2.role)}</td><td>{escape(buy2.risk_level)}</td></tr>'
        '</tbody></table></section>'
    )


def _levels_to_output(levels: tuple[PriceLevel, ...]) -> dict[str, dict[str, object]]:
    return {
        level.label: {
            "level_type": level.level_type.value,
            "ratio": level.ratio,
            "price": level.price,
            "distance_to_current_price": level.distance_to_current_price,
            "role": level.role,
        }
        for level in levels
    }


def _buy_point_to_output(point: ContractBuyPoint) -> dict[str, object]:
    return {
        "level_type": point.level_type.value,
        "ratio": point.ratio,
        "price": point.price,
        "role": point.role,
        "entry_rule": point.entry_rule,
        "stop_loss": point.stop_loss,
        "take_profit_targets": point.take_profit_targets,
        "risk_level": point.risk_level,
    }


def _retracement_label(ratio: float) -> str:
    if ratio == 0.0:
        return "波段高点"
    if ratio == 1.0:
        return "波段起点"
    return f"回撤 {ratio:g}"


def _retracement_role(ratio: float) -> str:
    return {
        0.0: "波段高点",
        0.236: "浅回撤压力/支撑",
        0.382: "阻力/支撑观察位",
        0.5: "中轴",
        0.618: "黄金回撤支撑",
        0.786: "深度回撤支撑，买点1",
        1.0: "波段起点防守线",
    }[ratio]


def _extension_role(ratio: float) -> str:
    return {
        0.0: "波段低点",
        0.236: "突破后的二次入场点，买点2",
        0.382: "短期压力位",
        0.5: "中期压力位",
        0.618: "强压力位",
        0.786: "趋势确认区",
        1.0: "波段高点，关键阻力位",
        1.272: "第一扩展目标",
        1.618: "第二扩展目标",
        2.0: "强势延伸目标",
    }[ratio]


def _reference_table(kind: str) -> tuple[tuple[float, str], ...]:
    if kind == "retracement":
        return (
            (0.236, "浅回撤 / 弱支撑"),
            (0.382, "常规回撤 / 中支撑"),
            (0.5, "中性回撤 / 中等支撑"),
            (0.618, "深回撤 / 强支撑"),
            (0.786, "深深回撤 / 极强支撑，买点1"),
            (1.0, "关键支撑 / 趋势反转点"),
        )
    if kind == "extension":
        return (
            (0.236, "突破后回踩位，买点2"),
            (0.382, "短期压力位"),
            (0.5, "中期压力位"),
            (0.618, "强压力位"),
            (1.272, "第一目标位"),
            (1.618, "第二目标位"),
            (2.0, "强势延伸目标"),
        )
    raise ValueError(f"unknown reference table: {kind}")


def _level(levels: tuple[PriceLevel, ...], ratio: float) -> PriceLevel:
    for level in levels:
        if level.ratio == ratio:
            return level
    raise KeyError(ratio)


def _level_price(levels: tuple[PriceLevel, ...], ratio: float) -> float:
    return _level(levels, ratio).price


def _title(result: ContractFibAnalysis) -> str:
    name = result.stock_name or result.symbol or "标的"
    return f"{name} 斐波那契回撤 & 扩展交易系统"


def _is_intraday(timeframe: str) -> bool:
    return timeframe.strip().lower() in INTRADAY_TIMEFRAMES


def _validate_score(value: float, name: str) -> None:
    if value < 0 or value > 100:
        raise ValueError(f"{name} must be between 0 and 100.")


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _money(value: float) -> float:
    return round(value + 0.0, 2)
