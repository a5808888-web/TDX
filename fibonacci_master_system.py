from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from ai_consensus_layer import AIAnalysisRequest, AIConsensusError, AIConsensusResult, DualAIAnalysisLayer


RETRACEMENT_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786, 1.0)
UPWARD_RATIOS: tuple[float, ...] = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.382, 1.618, 2.0, 2.618)
EXTENSION_RATIOS: tuple[float, ...] = (1.0, 1.272, 1.382, 1.618, 2.0, 2.618)
CHANNEL_RATIOS: tuple[float, ...] = (0.0, 0.382, 0.5, 0.618, 1.0, 1.618)
TIME_RATIOS: tuple[int, ...] = (3, 5, 8, 13, 21, 34, 55)
GEOMETRY_RATIOS: tuple[float, ...] = (0.382, 0.5, 0.618, 1.0, 1.618)
TOUCH_TOLERANCE = 0.006
REACTION_LOOKAHEAD_DAYS = 5
REACTION_THRESHOLD = 0.018
VALID_ACTIONS: tuple[str, ...] = ("可买", "等待", "观察", "回避", "持有", "减仓", "止盈", "止损")


@dataclass(frozen=True)
class MasterPriceBar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class ManualWave:
    name: str
    anchor_low: float
    anchor_high: float
    start_date: str
    end_date: str


@dataclass(frozen=True)
class FibonacciMasterInput:
    stock_name: str
    symbol: str
    current_price: float
    data_source: str
    updated_at: str
    history: tuple[MasterPriceBar, ...]
    manual_waves: tuple[ManualWave, ...] = ()
    log_path: str | None = "reports/fibonacci_master_log.jsonl"
    sector: str = ""
    stock_identity: str = "交易池"
    is_holding: bool = False
    holding_cost: float | None = None
    holding_quantity: float | None = None
    t1_locked: bool = False
    is_core_or_lucky: bool = False
    is_trade_pool: bool = True
    data_status: str = "实时"
    day_high: float | None = None
    sector_heat: float | None = None
    institutional_flow_score: float | None = None


class AILayer(Protocol):
    def analyze(self, request: AIAnalysisRequest) -> AIConsensusResult:
        ...


def run_fibonacci_master_system(
    data: FibonacciMasterInput,
    ai_layer: AILayer | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    _validate_input(data)
    generated_at = _format_time(now or datetime.now(timezone.utc))
    market_structure = _classify_market_structure(data.history, data.current_price)
    selected_tools = _select_tools(market_structure)
    waves = _build_waves(data)
    levels = [level for wave in waves for level in wave["levels"]]
    confluence_zones = _detect_confluence_zones(levels, data.history)
    primary = _choose_primary_wave(waves, market_structure)
    best_buy_low = _level_price(primary, "fibonacci_retracement", 0.786)
    best_buy_high = _level_price(primary, "fibonacci_retracement", 0.618)
    buy_point1 = _build_trade_point(primary, "fibonacci_retracement", 0.786, "buy_point1", data.current_price)
    buy_point2 = _build_trade_point(primary, "upward_projection", 0.236, "buy_point2", data.current_price)
    stop_loss = _build_stop_loss(primary, confluence_zones)
    take_profit = _build_take_profit(primary)
    standardized_tools = _build_standardized_tool_metrics(primary, data)
    account_context = _build_account_context(data)
    pre_ai_confluence = _score_confluence(data, standardized_tools, confluence_zones, None)

    ai_payload = _build_ai_payload(
        data=data,
        generated_at=generated_at,
        market_structure=market_structure,
        selected_tools=selected_tools,
        waves=waves,
        confluence_zones=confluence_zones,
        standardized_tools=standardized_tools,
        confluence_score=pre_ai_confluence,
        account_context=account_context,
        buy_point1=buy_point1,
        buy_point2=buy_point2,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )
    ai_result = _run_required_ai_review(ai_layer, ai_payload)
    confluence_score = _score_confluence(data, standardized_tools, confluence_zones, ai_result)
    final_decision = _merge_standardized_decision(
        data=data,
        ai_result=ai_result,
        tools=standardized_tools,
        confluence=confluence_score,
        buy_point1=buy_point1,
        buy_point2=buy_point2,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )
    standardized_output = _build_standardized_output(
        data=data,
        primary=primary,
        tools=standardized_tools,
        buy_point1=buy_point1,
        buy_point2=buy_point2,
        stop_loss=stop_loss,
        take_profit=take_profit,
        confluence=confluence_score,
        final_decision=final_decision,
        account_context=account_context,
    )

    output = {
        "system": "Standardized Multi-Tool Fibonacci Quant Engine",
        "legacy_system": "Fibonacci Master System",
        "version": "2.0",
        "stock_name": data.stock_name,
        "symbol": data.symbol,
        "current_price": round(data.current_price, 3),
        "data_source": data.data_source,
        "updated_at": data.updated_at,
        "generated_at": generated_at,
        "market_structure": market_structure,
        "primary_anchor": {
            "anchor_low": primary["anchor_low"],
            "anchor_high": primary["anchor_high"],
            "range": primary["range"],
            "start_date": primary["start_date"],
            "end_date": primary["end_date"],
            "source": primary["anchor_source"],
        },
        "chart_bars": _chart_bars(data.history),
        "selected_tools": selected_tools,
        "tool_family": _build_tool_family(primary, data.current_price),
        "multi_wave_table": waves,
        "win_rate_table": _build_win_rate_table(levels, data.current_price),
        "confluence_zones": confluence_zones,
        "buy_point1": buy_point1,
        "buy_point2": buy_point2,
        "best_buy_zone": {
            "price_range": [round(min(best_buy_low, best_buy_high), 3), round(max(best_buy_low, best_buy_high), 3)],
            "source": "retracement 0.786 to retracement 0.618",
            "confluence_strength": confluence_zones[0]["confluence_strength"] if confluence_zones else "no_valid_confluence",
            "combined_success_rate": confluence_zones[0]["combined_success_rate"] if confluence_zones else None,
        },
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "standardized_tools": standardized_tools,
        "confluence_score": confluence_score,
        "account_context": account_context,
        "standardized_output": standardized_output,
        "deepseek_review": ai_result["deepseek_review"],
        "doubao_review": ai_result["doubao_review"],
        "ai_fusion": final_decision,
        "final_action": final_decision["final_action"],
        "reason": final_decision["reason"],
        "required_guards": {
            "no_ai_generated_price": True,
            "price_source_required": data.data_source,
            "sample_lt_3_invalid": True,
            "dual_ai_required_for_buy": True,
            "ai_conflict_forces_observation": True,
        },
    }
    _write_log(data.log_path, output)
    return output


def fetch_akshare_history(symbol: str, adjust: str = "qfq") -> tuple[MasterPriceBar, ...]:
    try:
        import akshare as ak
    except Exception as exc:
        raise RuntimeError("akshare is required to fetch A-share history.") from exc

    code = symbol.split(".")[0]
    payload = _fetch_akshare_history_payload(ak, symbol, code, adjust)
    records = payload.to_dict("records") if hasattr(payload, "to_dict") else payload
    bars: list[MasterPriceBar] = []
    for row in records:
        date = str(row.get("日期") or row.get("date") or row.get("时间") or "")
        open_price = _number(row.get("开盘") or row.get("open"))
        high = _number(row.get("最高") or row.get("high"))
        low = _number(row.get("最低") or row.get("low"))
        close = _number(row.get("收盘") or row.get("close"))
        volume = _number(row.get("成交量") or row.get("volume") or 0.0)
        if date and open_price and high and low and close:
            bars.append(MasterPriceBar(date=date, open=open_price, high=high, low=low, close=close, volume=volume or 0.0))
    if len(bars) < 20:
        raise RuntimeError(f"AKShare returned insufficient history for {symbol}.")
    return tuple(bars)


def _fetch_akshare_history_payload(ak: Any, symbol: str, code: str, adjust: str) -> Any:
    errors: list[str] = []
    for current_adjust in (adjust, ""):
        for _ in range(3):
            try:
                return ak.stock_zh_a_hist(symbol=code, period="daily", adjust=current_adjust, timeout=15)
            except Exception as exc:
                errors.append(f"stock_zh_a_hist({current_adjust or 'none'}): {type(exc).__name__}")
                time.sleep(1)
    if hasattr(ak, "stock_zh_a_daily"):
        prefixed = _akshare_daily_symbol(symbol)
        for _ in range(3):
            try:
                return ak.stock_zh_a_daily(symbol=prefixed, adjust="")
            except Exception as exc:
                errors.append(f"stock_zh_a_daily: {type(exc).__name__}")
                time.sleep(1)
    raise RuntimeError("AKShare history fetch failed: " + " | ".join(errors))


def _akshare_daily_symbol(symbol: str) -> str:
    code = symbol.split(".")[0]
    suffix = symbol.split(".")[-1].lower()
    prefix = "sh" if suffix == "sh" or code.startswith(("6", "9")) else "sz"
    return f"{prefix}{code}"


def _validate_input(data: FibonacciMasterInput) -> None:
    if data.current_price <= 0:
        raise ValueError("Fibonacci Master requires a positive current price from real market data.")
    if len(data.history) < 20:
        raise ValueError("Fibonacci Master requires at least 20 historical daily bars.")
    for bar in data.history:
        if bar.high <= 0 or bar.low <= 0 or bar.close <= 0:
            raise ValueError("Historical bars must contain positive prices.")
        if bar.high < bar.low:
            raise ValueError("Historical bar high cannot be lower than low.")


def _build_waves(data: FibonacciMasterInput) -> list[dict[str, Any]]:
    specs = [
        ("full_history_wave", len(data.history), "listing low to historical high"),
        ("long_cycle_wave", max(180, min(360, len(data.history))), "180d+ long cycle"),
        ("middle_cycle_wave", min(180, max(60, min(120, len(data.history)))), "60d-180d middle cycle"),
        ("short_cycle_wave", min(60, max(20, min(40, len(data.history)))), "20d-60d short cycle"),
        ("micro_wave", min(20, max(5, min(15, len(data.history)))), "5d-20d micro wave"),
    ]
    waves = [_build_wave(name, data.history[-window:], data.current_price, source) for name, window, source in specs]
    waves.append(_build_auto_structure_wave(data.history, data.current_price))
    for manual in data.manual_waves:
        waves.append(_build_manual_wave(manual, data.history, data.current_price))
    return waves


def _choose_primary_wave(waves: list[dict[str, Any]], market_structure: dict[str, Any]) -> dict[str, Any]:
    by_name = {wave["wave_name"]: wave for wave in waves}
    scenario = market_structure["scenario"]
    priority = {
        "normal_uptrend_pullback": ("middle_cycle_wave", "short_cycle_wave", "auto_structure_wave"),
        "main_uptrend_breakout": ("auto_structure_wave", "short_cycle_wave", "middle_cycle_wave"),
        "long_term_core_review": ("long_cycle_wave", "full_history_wave", "auto_structure_wave"),
        "sideways_range": ("middle_cycle_wave", "short_cycle_wave", "auto_structure_wave"),
        "high_after_surge": ("short_cycle_wave", "auto_structure_wave", "middle_cycle_wave"),
        "breakdown_downtrend": ("middle_cycle_wave", "short_cycle_wave", "full_history_wave"),
    }.get(scenario, ("auto_structure_wave", "middle_cycle_wave", "full_history_wave"))
    for name in priority:
        wave = by_name.get(name)
        if wave and wave["is_valid"]:
            return wave
    return waves[0]


def _build_wave(name: str, bars: tuple[MasterPriceBar, ...], current_price: float, source: str) -> dict[str, Any]:
    low_bar = min(bars, key=lambda item: item.low)
    high_bar = max(bars, key=lambda item: item.high)
    anchor_low = round(low_bar.low, 3)
    anchor_high = round(high_bar.high, 3)
    return _wave_payload(
        name=name,
        anchor_low=anchor_low,
        anchor_high=anchor_high,
        start_date=bars[0].date,
        end_date=bars[-1].date,
        high_date=high_bar.date,
        low_date=low_bar.date,
        current_price=current_price,
        source=source,
        bars=bars,
    )


def _build_auto_structure_wave(history: tuple[MasterPriceBar, ...], current_price: float) -> dict[str, Any]:
    pivots = _detect_pivots(history)
    if len(pivots) >= 2:
        recent = pivots[-8:]
        low = min(recent, key=lambda item: item.low)
        high = max(recent, key=lambda item: item.high)
        bars = tuple(item for item in history if low.date <= item.date <= high.date or high.date <= item.date <= low.date)
        if len(bars) >= 5:
            return _wave_payload(
                name="auto_structure_wave",
                anchor_low=round(low.low, 3),
                anchor_high=round(high.high, 3),
                start_date=bars[0].date,
                end_date=bars[-1].date,
                high_date=high.date,
                low_date=low.date,
                current_price=current_price,
                source="auto pivots by local high/low and volume-aware structure",
                bars=bars,
            )
    return _build_wave("auto_structure_wave", history[-60:], current_price, "fallback recent 60d structure")


def _build_manual_wave(manual: ManualWave, history: tuple[MasterPriceBar, ...], current_price: float) -> dict[str, Any]:
    anchor_low = min(manual.anchor_low, manual.anchor_high)
    anchor_high = max(manual.anchor_low, manual.anchor_high)
    return _wave_payload(
        name=manual.name or "manual_wave",
        anchor_low=round(anchor_low, 3),
        anchor_high=round(anchor_high, 3),
        start_date=manual.start_date,
        end_date=manual.end_date,
        high_date=manual.end_date,
        low_date=manual.start_date,
        current_price=current_price,
        source="user manual anchor",
        bars=history,
    )


def _wave_payload(
    name: str,
    anchor_low: float,
    anchor_high: float,
    start_date: str,
    end_date: str,
    high_date: str,
    low_date: str,
    current_price: float,
    source: str,
    bars: tuple[MasterPriceBar, ...],
) -> dict[str, Any]:
    price_range = max(0.001, anchor_high - anchor_low)
    levels = []
    for ratio in RETRACEMENT_RATIOS:
        price = anchor_high - ratio * price_range
        levels.append(_level_payload("fibonacci_retracement", name, ratio, price, current_price, bars, "support_or_rebound_pressure"))
    for ratio in UPWARD_RATIOS:
        price = anchor_low + ratio * price_range
        levels.append(_level_payload("upward_projection", name, ratio, price, current_price, bars, "buy_point2_or_pressure"))
    for ratio in EXTENSION_RATIOS:
        price = anchor_low + ratio * price_range
        levels.append(_level_payload("fibonacci_trend_extension", name, ratio, price, current_price, bars, "take_profit_or_trend_target"))

    return {
        "wave_name": name,
        "anchor_low": round(anchor_low, 3),
        "anchor_high": round(anchor_high, 3),
        "range": round(price_range, 3),
        "start_date": start_date,
        "end_date": end_date,
        "high_date": high_date,
        "low_date": low_date,
        "anchor_source": source,
        "retracement_0_618": _price(anchor_high - 0.618 * price_range),
        "retracement_0_786": _price(anchor_high - 0.786 * price_range),
        "upward_projection_0_236": _price(anchor_low + 0.236 * price_range),
        "extension_1_272": _price(anchor_low + 1.272 * price_range),
        "extension_1_618": _price(anchor_low + 1.618 * price_range),
        "is_valid": anchor_high > anchor_low,
        "historical_success_rate": _aggregate_success_rate(levels),
        "included_in_final": name in {"full_history_wave", "long_cycle_wave", "middle_cycle_wave", "auto_structure_wave"},
        "levels": levels,
    }


def _level_payload(
    tool_name: str,
    wave_name: str,
    ratio: float,
    price: float,
    current_price: float,
    bars: tuple[MasterPriceBar, ...],
    role: str,
) -> dict[str, Any]:
    validation = _validate_level(price, bars)
    distance_pct = round((current_price - price) / price * 100, 2)
    return {
        "tool_name": tool_name,
        "wave_name": wave_name,
        "ratio": ratio,
        "price": _price(price),
        "formula": _formula(tool_name, ratio),
        "role": role,
        "current_distance_pct": distance_pct,
        "is_near_current": abs(distance_pct) <= 2.0,
        "is_support": current_price >= price and tool_name in {"fibonacci_retracement", "upward_projection"},
        "is_broken": current_price < price and tool_name == "fibonacci_retracement",
        "is_pressure": current_price < price and tool_name in {"upward_projection", "fibonacci_trend_extension"},
        "is_target": tool_name == "fibonacci_trend_extension",
        **validation,
        "confidence_by_sample": _sample_confidence(validation["touch_count"]),
        "effectiveness": _effectiveness(validation["success_rate"]),
        "included_in_final": validation["touch_count"] >= 3 and validation["success_rate"] >= 45,
    }


def _validate_level(level_price: float, bars: tuple[MasterPriceBar, ...]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for index, bar in enumerate(bars[:-REACTION_LOOKAHEAD_DAYS]):
        if not _touches(bar, level_price):
            continue
        future = bars[index + 1 : index + 1 + REACTION_LOOKAHEAD_DAYS]
        max_high = max(item.high for item in future)
        min_low = min(item.low for item in future)
        bounce_pct = (max_high - level_price) / level_price * 100
        drawdown_pct = (min_low - level_price) / level_price * 100
        success = bounce_pct >= REACTION_THRESHOLD * 100
        events.append(
            {
                "date": bar.date,
                "success": success,
                "reaction_pct": round(bounce_pct if success else drawdown_pct, 2),
                "reaction_days": _first_reaction_day(level_price, future),
                "max_failure_drawdown_pct": round(min(0.0, drawdown_pct), 2),
            }
        )
    successes = sum(1 for item in events if item["success"])
    failures = len(events) - successes
    success_rate = round(successes / len(events) * 100, 2) if events else 0.0
    return {
        "touch_count": len(events),
        "success_count": successes,
        "failure_count": failures,
        "success_rate": success_rate,
        "average_reaction_pct": round(sum(item["reaction_pct"] for item in events) / len(events), 2) if events else 0.0,
        "average_reaction_days": round(sum(item["reaction_days"] for item in events) / len(events), 2) if events else 0.0,
        "max_failure_drawdown_pct": min((item["max_failure_drawdown_pct"] for item in events), default=0.0),
        "sample_valid": len(events) >= 3,
    }


def _detect_confluence_zones(levels: list[dict[str, Any]], bars: tuple[MasterPriceBar, ...]) -> list[dict[str, Any]]:
    candidates = [item for item in levels if item["included_in_final"]]
    zones: list[dict[str, Any]] = []
    seen: set[tuple[float, ...]] = set()
    for base in candidates:
        cluster = [item for item in candidates if _pct_gap(base["price"], item["price"]) <= 2.0]
        if len({item["wave_name"] for item in cluster}) < 2 and len({item["tool_name"] for item in cluster}) < 2:
            continue
        key = tuple(sorted(item["price"] for item in cluster))
        if key in seen:
            continue
        seen.add(key)
        low = min(item["price"] for item in cluster)
        high = max(item["price"] for item in cluster)
        validation = _validate_level((low + high) / 2, bars)
        gap = _pct_gap(low, high)
        zones.append(
            {
                "price_range": [_price(low), _price(high)],
                "participating_wave_count": len({item["wave_name"] for item in cluster}),
                "participating_tool_count": len({item["tool_name"] for item in cluster}),
                "participating_lines": [f"{item['wave_name']}:{item['tool_name']}:{item['ratio']}" for item in cluster],
                "historical_touch_count": validation["touch_count"],
                "historical_success_count": validation["success_count"],
                "historical_failure_count": validation["failure_count"],
                "combined_success_rate": validation["success_rate"],
                "average_reaction_pct": validation["average_reaction_pct"],
                "max_failure_drawdown_pct": validation["max_failure_drawdown_pct"],
                "confluence_strength": _confluence_strength(gap),
                "included_in_final": validation["touch_count"] >= 3 and gap <= 2.0,
            }
        )
    return sorted(zones, key=lambda item: (-item["combined_success_rate"], item["price_range"][0]))[:8]


def _build_tool_family(primary: dict[str, Any], current_price: float) -> list[dict[str, Any]]:
    low = primary["anchor_low"]
    high = primary["anchor_high"]
    price_range = primary["range"]
    midpoint = (high + low) / 2
    return [
        _tool_block("Fibonacci Retracement", "上涨后回调支撑 / 下跌后反弹压力", primary["levels"], "fibonacci_retracement"),
        _tool_block("Fibonacci Trend Extension", "突破后的止盈和趋势目标", primary["levels"], "fibonacci_trend_extension"),
        {
            "tool_name": "Fibonacci Channel",
            "use_case": "趋势通道支撑、压力、加速线",
            "levels": [
                {"ratio": ratio, "price": _price(low + ratio * price_range), "label": _channel_label(ratio)}
                for ratio in CHANNEL_RATIOS
            ],
            "rule": "跌破通道下轨止损，靠近上轨分批止盈",
        },
        {
            "tool_name": "Fibonacci Time Zone",
            "use_case": "潜在变盘时间窗口，只能辅助",
            "time_windows": _time_windows(primary),
            "price_resonance": abs(current_price - midpoint) / midpoint <= 0.03,
        },
        {
            "tool_name": "Fibonacci Speed Resistance Fan",
            "use_case": "趋势速度、回撤支撑角度、趋势衰减",
            "speed_lines": [{"ratio": ratio, "support_price": _price(low + ratio * price_range)} for ratio in (0.382, 0.5, 0.618)],
            "weakening_rule": "跌破0.618速度线代表趋势明显变弱",
        },
        {
            "tool_name": "Fibonacci Trend-Based Time",
            "use_case": "用前一段趋势长度推演下一段周期",
            "time_targets": _time_windows(primary),
            "near_time_window": False,
        },
        {
            "tool_name": "Fibonacci Circles",
            "use_case": "价格与时间共同构成的辅助支撑/压力",
            "arc_support": _price(low + 0.382 * price_range),
            "arc_pressure": _price(low + 1.0 * price_range),
            "near_arc_area": any(abs(current_price - (low + ratio * price_range)) / current_price <= 0.02 for ratio in GEOMETRY_RATIOS),
            "standalone_signal_allowed": False,
        },
        {
            "tool_name": "Fibonacci Spiral",
            "use_case": "长期周期结构和潜在拐点辅助",
            "spiral_support_zone": [_price(low + 0.382 * price_range), _price(low + 0.5 * price_range)],
            "spiral_pressure_zone": [_price(low + 1.0 * price_range), _price(low + 1.618 * price_range)],
            "resonates_with_retracement_or_extension": True,
            "standalone_signal_allowed": False,
        },
        {
            "tool_name": "Fibonacci Speed Resistance Arcs",
            "use_case": "趋势变速、反弹衰减、主升后回调",
            "support_arc": _price(low + 0.5 * price_range),
            "pressure_arc": _price(low + 1.0 * price_range),
            "invalid_arc": _price(low + 0.382 * price_range),
        },
        {
            "tool_name": "Fibonacci Wedge / Fan",
            "use_case": "收敛、扩散、楔形突破",
            "upper_boundary": _price(high),
            "lower_boundary": _price(low + 0.382 * price_range),
            "breakout_direction": "up" if current_price > high else "pending",
            "breakout_valid": current_price > high * 1.01,
        },
    ]


def _run_required_ai_review(ai_layer: AILayer | None, payload: dict[str, Any]) -> dict[str, Any]:
    if ai_layer is None:
        return {
            "completed": False,
            "deepseek_review": _ai_pending("DeepSeek", "未配置AI层，不能输出可买结论。"),
            "doubao_review": _ai_pending("Doubao", "未配置AI层，不能输出可买结论。"),
            "error": "dual_ai_layer_missing",
        }
    try:
        result = ai_layer.analyze(
            AIAnalysisRequest(
                task="Fibonacci Master System dual review: DeepSeek handles structure; Doubao handles news, sentiment, sector heat and risk. Return cautious trading audit.",
                payload=payload,
            )
        )
    except (AIConsensusError, Exception) as exc:
        return {
            "completed": False,
            "deepseek_review": _ai_pending("DeepSeek", f"AI复核未完成：{type(exc).__name__}"),
            "doubao_review": _ai_pending("Doubao", f"AI复核未完成：{type(exc).__name__}"),
            "error": type(exc).__name__,
        }
    deepseek = _provider_content(result, "deepseek")
    doubao = _provider_content(result, "doubao")
    return {
        "completed": bool(deepseek and doubao),
        "deepseek_review": {
            "provider": "DeepSeek",
            "deepseek_structure_view": deepseek or "DeepSeek未返回结构分析。",
            "deepseek_anchor_view": deepseek or "DeepSeek未返回锚点分析。",
            "deepseek_fib_validity": deepseek or "DeepSeek未返回斐波那契有效性。",
            "deepseek_risk_view": deepseek or "DeepSeek未返回风险分析。",
            "deepseek_decision": _extract_decision(deepseek),
            "score": _score_text(deepseek),
        },
        "doubao_review": {
            "provider": "Doubao",
            "doubao_news_view": doubao or "豆包未返回新闻分析。",
            "doubao_sentiment_view": doubao or "豆包未返回情绪分析。",
            "doubao_sector_view": doubao or "豆包未返回板块分析。",
            "doubao_risk_view": doubao or "豆包未返回风险分析。",
            "doubao_decision": _extract_decision(doubao),
            "score": _score_text(doubao),
        },
        "raw_consensus": result.consensus,
    }


def _merge_final_decision(
    ai_result: dict[str, Any],
    buy_point1: dict[str, Any],
    buy_point2: dict[str, Any],
    confluence_zones: list[dict[str, Any]],
    current_price: float,
) -> dict[str, Any]:
    historical_score = _historical_score(buy_point1, buy_point2, confluence_zones)
    if not ai_result["completed"]:
        return {
            "final_action": "观察",
            "fusion_score": round(0.15 * historical_score, 2),
            "conflict": False,
            "reason": "DeepSeek与豆包复核未同时完成，禁止直接给可买结论，等待下一次同步确认。",
            "weights": {"deepseek": 0.55, "doubao": 0.30, "historical_validation": 0.15},
        }
    deepseek_score = ai_result["deepseek_review"]["score"]
    doubao_score = ai_result["doubao_review"]["score"]
    conflict = abs(deepseek_score - doubao_score) >= 25 or _decision_conflict(
        ai_result["deepseek_review"]["deepseek_decision"],
        ai_result["doubao_review"]["doubao_decision"],
    )
    fusion_score = round(0.55 * deepseek_score + 0.30 * doubao_score + 0.15 * historical_score, 2)
    chasing_high = current_price > max(buy_point1["price"], buy_point2["price"]) * 1.08
    if conflict:
        action = "观察"
        reason = "AI结论分歧，进入观察，等待下一次同步确认。"
    elif chasing_high:
        action = "等待"
        reason = "当前价明显高于核心买点，存在追高风险。"
    elif fusion_score >= 72 and historical_score >= 55:
        action = "可买"
        reason = "结构、情绪和历史验证形成一致共振。"
    elif fusion_score >= 55:
        action = "等待"
        reason = "存在有效区域但确认不足，等待价格回到买入波段。"
    else:
        action = "回避"
        reason = "历史验证或AI复核不足，不作为主要买点。"
    return {
        "final_action": action,
        "fusion_score": fusion_score,
        "conflict": conflict,
        "reason": reason,
        "weights": {"deepseek": 0.55, "doubao": 0.30, "historical_validation": 0.15},
    }


def _build_ai_payload(**kwargs: Any) -> dict[str, Any]:
    payload = dict(kwargs)
    payload["instruction"] = {
        "deepseek": [
            "检查波段结构是否合理",
            "检查高低点锚点是否合理",
            "判断当前适用工具、回撤/扩展/共振是否可靠",
            "检查样本数、追高风险、止损止盈合理性",
            "输出买入/等待/回避",
        ],
        "doubao": [
            "检查相关新闻、板块情绪、市场热度、资金情绪、政策事件和公告影响",
            "判断是否情绪高点、是否追高、是否存在利空风险",
            "输出买入/等待/回避",
        ],
    }
    return payload


def _build_win_rate_table(levels: list[dict[str, Any]], current_price: float) -> list[dict[str, Any]]:
    return [
        {
            "tool_name": level["tool_name"],
            "wave_name": level["wave_name"],
            "ratio": level["ratio"],
            "price": level["price"],
            "historical_touch_count": level["touch_count"],
            "success_count": level["success_count"],
            "failure_count": level["failure_count"],
            "success_rate": level["success_rate"],
            "average_reaction_pct": level["average_reaction_pct"],
            "average_reaction_days": level["average_reaction_days"],
            "max_failure_drawdown_pct": level["max_failure_drawdown_pct"],
            "is_near_current": level["is_near_current"],
            "included_in_final": level["included_in_final"],
            "confidence_by_sample": level["confidence_by_sample"],
            "effectiveness": level["effectiveness"],
        }
        for level in levels
    ]


def _build_standardized_tool_metrics(primary: dict[str, Any], data: FibonacciMasterInput) -> dict[str, Any]:
    low = primary["anchor_low"]
    high = primary["anchor_high"]
    price_range = primary["range"]
    current = data.current_price
    retracement = {f"{ratio:.3f}": _price(high - ratio * price_range) for ratio in RETRACEMENT_RATIOS}
    upward = {f"{ratio:.3f}": _price(low + ratio * price_range) for ratio in UPWARD_RATIOS}
    channel = _build_trend_channel(primary, data.history)
    arcs = _build_speed_resistance_arcs(primary, current)
    spiral = _build_spiral(primary, current)
    time_window = _build_time_window(primary, data.history)
    best_low = retracement["0.786"]
    best_high = retracement["0.618"]
    retracement_state = _retracement_state(current, low, best_low, best_high)
    return {
        "tool_weights": {
            "fibonacci_extension": {"trading_weight": "最高", "decision_weight": "止盈目标，不直接开仓"},
            "fibonacci_retracement": {"trading_weight": "高", "decision_weight": "核心回调入场"},
            "fibonacci_channel": {"trading_weight": "中高", "decision_weight": "趋势强弱与破位确认"},
            "speed_resistance_arcs": {"trading_weight": "中", "decision_weight": "动态支撑验证，不能单独开仓"},
            "fibonacci_spiral": {"trading_weight": "低", "decision_weight": "大周期拐点辅助，不能单独开仓"},
            "fibonacci_time_window": {"trading_weight": "最低", "decision_weight": "时间共振加分，不能单独开仓"},
        },
        "retracement": {
            "levels": retracement,
            "current_position": retracement_state,
            "in_best_buy_zone": best_low <= current <= best_high,
            "best_buy_zone": [_price(best_low), _price(best_high)],
        },
        "upward_extension": {
            "levels": upward,
            "take_profit_1": upward["1.272"],
            "take_profit_2": upward["1.618"],
            "take_profit_3": upward["2.618"],
            "extension_used_for_entry": False,
            "distances_pct": {key: round((current - value) / value * 100, 2) for key, value in upward.items() if float(key) >= 1.0},
        },
        "trend_channel": channel,
        "speed_resistance_arcs": arcs,
        "spiral": spiral,
        "time_window": time_window,
        "hard_rules": {
            "extension_is_take_profit_only": True,
            "time_window_cannot_open_trade_alone": True,
            "spiral_cannot_open_trade_alone": True,
            "single_wick_break_is_not_breakdown": True,
            "two_close_break_required": True,
        },
    }


def _build_trend_channel(primary: dict[str, Any], history: tuple[MasterPriceBar, ...]) -> dict[str, Any]:
    low = primary["anchor_low"]
    high = primary["anchor_high"]
    price_range = primary["range"]
    recent = history[-20:] if len(history) >= 20 else history
    mid = _price(low + 0.5 * price_range)
    strong = _price(low + 0.618 * price_range)
    lower = _price(low)
    upper = _price(high)
    consecutive_break = len(recent) >= 2 and recent[-1].close < strong and recent[-2].close < strong
    wick_only = bool(recent and recent[-1].low < strong and recent[-1].close >= strong)
    if consecutive_break:
        status = "趋势结构破坏"
    elif recent and recent[-1].close >= mid:
        status = "趋势偏强"
    elif recent and recent[-1].close >= strong:
        status = "趋势健康"
    else:
        status = "趋势转弱观察"
    return {
        "upper_track": upper,
        "middle_0_500": mid,
        "strong_0_618": strong,
        "lower_track": lower,
        "trend_status": status,
        "two_close_breakdown": consecutive_break,
        "single_wick_break_only": wick_only,
        "validity": "有效" if not consecutive_break else "破位",
    }


def _build_speed_resistance_arcs(primary: dict[str, Any], current_price: float) -> dict[str, Any]:
    low = primary["anchor_low"]
    price_range = primary["range"]
    levels = {f"{ratio:.3f}": _price(low + ratio * price_range) for ratio in (0.382, 0.5, 0.618)}
    near_0618 = _near_price(current_price, levels["0.618"], 2.0)
    return {
        "levels": levels,
        "core_0_618_validation": near_0618,
        "axis_locked": True,
        "validity": "有效，可做共振验证" if near_0618 else "仅作动态支撑参考",
        "standalone_signal_allowed": False,
    }


def _build_spiral(primary: dict[str, Any], current_price: float) -> dict[str, Any]:
    low = primary["anchor_low"]
    price_range = primary["range"]
    inner = _price(low + 0.618 * price_range)
    trend = _price(low + 1.0 * price_range)
    reversal = _price(low + 1.618 * price_range)
    axis_valid = True
    return {
        "center": primary["low_date"],
        "end": primary["high_date"],
        "inner_0_618_correction": inner,
        "trend_1_000": trend,
        "outer_1_618_reversal": reversal,
        "near_spiral_zone": _near_price(current_price, inner, 2.0) or _near_price(current_price, reversal, 2.0),
        "axis_scale_valid": axis_valid,
        "validity": "仅供大级别拐点辅助" if axis_valid else "坐标缩放扭曲，数据作废",
        "standalone_signal_allowed": False,
    }


def _build_time_window(primary: dict[str, Any], history: tuple[MasterPriceBar, ...]) -> dict[str, Any]:
    zero_date = primary["high_date"]
    zero_index = _find_bar_index(history, zero_date)
    current_index = len(history) - 1
    bars_from_zero = max(0, current_index - zero_index)
    windows = []
    in_core = False
    for window in TIME_RATIOS:
        distance = abs(bars_from_zero - window)
        hit = distance <= (1 if window in (8, 13, 21) else 2)
        if hit and window in (8, 13, 21):
            in_core = True
        windows.append({"window": window, "distance": distance, "active": hit, "core": window in (8, 13, 21)})
    return {
        "zero_bar_date": zero_date,
        "current_bar_index_from_zero": bars_from_zero,
        "windows": windows,
        "near_core_8_13_21": in_core,
        "description": "时间窗口只做共振加分，不能单独生成买卖信号",
    }


def _build_account_context(data: FibonacciMasterInput) -> dict[str, Any]:
    floating_pnl = None
    if data.is_holding and data.holding_cost and data.holding_cost > 0:
        floating_pnl = round((data.current_price - data.holding_cost) / data.holding_cost * 100, 2)
    return {
        "is_holding": data.is_holding,
        "holding_cost": data.holding_cost,
        "holding_quantity": data.holding_quantity,
        "floating_pnl_pct": floating_pnl,
        "t1_locked": data.t1_locked,
        "stock_identity": data.stock_identity,
        "is_core_or_lucky": data.is_core_or_lucky,
        "is_trade_pool": data.is_trade_pool,
        "sector": data.sector,
    }


def _score_confluence(
    data: FibonacciMasterInput,
    tools: dict[str, Any],
    confluence_zones: list[dict[str, Any]],
    ai_result: dict[str, Any] | None,
) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []
    participants: list[str] = []
    current = data.current_price
    retracement = tools["retracement"]
    upward = tools["upward_extension"]
    channel = tools["trend_channel"]
    arcs = tools["speed_resistance_arcs"]
    spiral = tools["spiral"]
    time_window = tools["time_window"]

    def add(points: int, label: str) -> None:
        nonlocal score
        score += points
        reasons.append(f"+{points} {label}")
        participants.append(label)

    def deduct(points: int, label: str) -> None:
        nonlocal score
        score -= points
        reasons.append(f"-{points} {label}")

    if _near_price(current, retracement["levels"]["0.786"], 2.0):
        add(25, "回撤0.786触发")
    if _near_price(current, retracement["levels"]["0.618"], 2.0):
        add(20, "回撤0.618触发")
    if _near_price(current, upward["levels"]["0.236"], 2.0):
        add(20, "上升映射0.236触发")
    if _near_price(current, channel["strong_0_618"], 2.0):
        add(15, "趋势通道0.618触发")
    if arcs["core_0_618_validation"]:
        add(10, "速度阻力弧0.618触发")
    if spiral["near_spiral_zone"] and spiral["axis_scale_valid"]:
        add(8, "螺旋0.618或1.618触发")
    if time_window["near_core_8_13_21"]:
        add(10, "时间窗口8/13/21触发")
    if _has_reversal_candle(data.history):
        add(8, "反转K线")
    if _has_volume_confirmation(data.history):
        add(8, "量能确认")
    if confluence_zones:
        add(min(12, 4 * confluence_zones[0]["participating_tool_count"]), "多波段斐波那契重叠")

    if current > retracement["best_buy_zone"][1]:
        deduct(20, "当前价高于最佳买入波段")
    day_high = data.day_high or data.history[-1].high
    if current >= day_high * 0.98:
        deduct(20, "当前价接近阶段/日内高点")
    if data.data_status in {"延迟", "数据延迟"}:
        deduct(30, "数据延迟")
    if data.data_status in {"失效", "数据失效"}:
        deduct(100, "数据失效")
    if channel["two_close_breakdown"]:
        deduct(50, "连续两根收盘破位")
    if data.sector_heat is not None and data.sector_heat < 60:
        deduct(20, "板块热度低于60")
    if data.institutional_flow_score is not None and data.institutional_flow_score < 45:
        deduct(20, "机构资金流出")
    if ai_result and ai_result.get("completed") and ai_result.get("deepseek_review") and ai_result.get("doubao_review"):
        if _decision_conflict(ai_result["deepseek_review"]["deepseek_decision"], ai_result["doubao_review"]["doubao_decision"]):
            deduct(15, "AI分析分歧严重")

    price_condition = (
        _near_price(current, channel["strong_0_618"], 2.0)
        or arcs["core_0_618_validation"]
        or (spiral["near_spiral_zone"] and spiral["axis_scale_valid"])
        or _near_price(current, upward["levels"]["1.272"], 2.0)
        or _near_price(current, upward["levels"]["1.618"], 2.0)
    )
    retrace_condition = (
        retracement["in_best_buy_zone"]
        or _near_price(current, retracement["levels"]["0.786"], 2.0)
        or _near_price(current, retracement["levels"]["0.618"], 2.0)
    )
    confirmation_condition = time_window["near_core_8_13_21"] or _has_reversal_candle(data.history) or _has_volume_confirmation(data.history)
    triple = price_condition and retrace_condition and confirmation_condition
    score = max(0, min(100, score))
    return {
        "score": score,
        "level": _confluence_score_level(score),
        "participants": tuple(dict.fromkeys(participants)),
        "reasons": tuple(reasons),
        "triple_confluence": triple,
        "triple_conditions": {
            "price_dynamic_tool": price_condition,
            "retracement_level": retrace_condition,
            "time_or_kline_confirmation": confirmation_condition,
        },
        "hard_rule": "评分只做辅助，不满足三重共振不得输出可买",
    }


def _merge_standardized_decision(
    data: FibonacciMasterInput,
    ai_result: dict[str, Any],
    tools: dict[str, Any],
    confluence: dict[str, Any],
    buy_point1: dict[str, Any],
    buy_point2: dict[str, Any],
    stop_loss: dict[str, Any],
    take_profit: dict[str, Any],
) -> dict[str, Any]:
    current = data.current_price
    best_zone = tools["retracement"]["best_buy_zone"]
    channel = tools["trend_channel"]
    ai_conflict = bool(
        ai_result.get("completed")
        and _decision_conflict(ai_result["deepseek_review"]["deepseek_decision"], ai_result["doubao_review"]["doubao_decision"])
    )
    data_invalid = data.data_status in {"失效", "数据失效"}
    near_tp1 = _near_price(current, take_profit["target1"]["price"], 2.0)
    near_tp2 = _near_price(current, take_profit["target2"]["price"], 2.0)
    if data_invalid:
        action, allowed, reason = "回避", False, "行情数据失效，禁止生成新的买入建议。"
    elif data.is_holding and current <= stop_loss["price"]:
        action, allowed, reason = "止损", True, "已持仓且当前价跌破止损价，执行风控优先。"
    elif data.is_holding and near_tp2:
        action, allowed, reason = "止盈", True, "已持仓且接近核心止盈1.618，优先保护利润。"
    elif data.is_holding and near_tp1:
        action, allowed, reason = "减仓", True, "已持仓且接近第一止盈1.272，可分批保护利润。"
    elif data.is_holding and not channel["two_close_breakdown"]:
        action, allowed, reason = "持有", True, "已持仓且趋势通道未被连续两根收盘破坏。"
    elif ai_conflict:
        action, allowed, reason = "观察", False, "DeepSeek与豆包结论分歧，进入观察，等待下一次同步确认。"
    elif channel["two_close_breakdown"]:
        action, allowed, reason = "回避", False, "连续两根收盘跌破趋势通道，结构破坏。"
    elif not ai_result.get("completed") and not data.is_holding:
        action, allowed, reason = "观察", False, "DeepSeek与豆包未同时完成复核，非持仓股票禁止输出可买或交易动作。"
    elif current > best_zone[1] and data.is_core_or_lucky:
        action, allowed, reason = "等待", False, "核心股/幸运区身份不等于今天可买，当前价高于最佳买入波段，等待回撤。"
    elif current > best_zone[1]:
        action, allowed, reason = "等待", False, "当前价格高于最佳买入波段，禁止追高。"
    elif confluence["triple_confluence"] and best_zone[0] <= current <= best_zone[1] and ai_result.get("completed"):
        action, allowed, reason = "可买", True, "价格、回撤关键位、时间或K线确认形成三重共振。"
    elif confluence["score"] >= 70:
        action, allowed, reason = "等待", False, "共振分达到中等以上，但三重共振或AI复核条件不足。"
    elif confluence["score"] >= 50:
        action, allowed, reason = "观察", False, "弱共振，只观察，不进入交易池。"
    else:
        action, allowed, reason = "回避", False, "无效信号，不交易。"

    return {
        "final_action": action,
        "fusion_score": confluence["score"],
        "conflict": ai_conflict,
        "reason": reason,
        "trade_allowed": allowed,
        "risk_warning": _risk_warning(data, tools, confluence),
        "weights": {"structure": 0.70, "historical_validation": 0.15, "ai_explanation": 0.15},
    }


def _build_standardized_output(
    data: FibonacciMasterInput,
    primary: dict[str, Any],
    tools: dict[str, Any],
    buy_point1: dict[str, Any],
    buy_point2: dict[str, Any],
    stop_loss: dict[str, Any],
    take_profit: dict[str, Any],
    confluence: dict[str, Any],
    final_decision: dict[str, Any],
    account_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "股票名称": data.stock_name,
        "股票代码": data.symbol,
        "当前价格": _price(data.current_price),
        "数据来源": data.data_source,
        "更新时间": data.updated_at,
        "数据状态": data.data_status,
        "所属板块": data.sector,
        "股票身份": data.stock_identity,
        "是否持仓": data.is_holding,
        "持仓成本": data.holding_cost,
        "浮动盈亏": account_context["floating_pnl_pct"],
        "主波段": {
            "A点日期": primary["low_date"],
            "A点价格": primary["anchor_low"],
            "B点日期": primary["high_date"],
            "B点价格": primary["anchor_high"],
            "波段方向": "上升" if primary["high_date"] >= primary["low_date"] else "下降",
            "波段有效性": "有效" if primary["is_valid"] else "无效",
        },
        "回撤斐波那契": tools["retracement"]["levels"],
        "上升映射与扩展": tools["upward_extension"]["levels"],
        "趋势通道": {
            "趋势状态": tools["trend_channel"]["trend_status"],
            "中线0.5": tools["trend_channel"]["middle_0_500"],
            "强支撑0.618": tools["trend_channel"]["strong_0_618"],
            "是否破位": tools["trend_channel"]["two_close_breakdown"],
        },
        "速度阻力弧": {
            "0.382": tools["speed_resistance_arcs"]["levels"]["0.382"],
            "0.500": tools["speed_resistance_arcs"]["levels"]["0.500"],
            "0.618": tools["speed_resistance_arcs"]["levels"]["0.618"],
            "有效性": tools["speed_resistance_arcs"]["validity"],
        },
        "螺旋": {
            "0.618修正区": tools["spiral"]["inner_0_618_correction"],
            "1.618反转区": tools["spiral"]["outer_1_618_reversal"],
            "有效性": tools["spiral"]["validity"],
        },
        "时间窗口": {
            "当前K线序号": tools["time_window"]["current_bar_index_from_zero"],
            "是否处于8/13/21窗口": tools["time_window"]["near_core_8_13_21"],
            "窗口说明": tools["time_window"]["description"],
        },
        "买点": {
            "买点1": buy_point1["price"],
            "买点1来源": "主波段回撤0.786",
            "买点2": buy_point2["price"],
            "买点2来源": "主波段上升映射0.236",
            "最佳买入区间": tools["retracement"]["best_buy_zone"],
        },
        "卖点": {
            "第一止盈": take_profit["target1"]["price"],
            "核心止盈": take_profit["target2"]["price"],
            "强趋势止盈": take_profit["target3"]["price"],
            "止损": stop_loss["price"],
        },
        "共振": {
            "共振评分": confluence["score"],
            "共振等级": confluence["level"],
            "参与共振工具": confluence["participants"],
            "是否满足三重共振": confluence["triple_confluence"],
        },
        "最终结论": {
            "当前动作": final_decision["final_action"],
            "是否允许交易": final_decision["trade_allowed"],
            "原因": final_decision["reason"],
            "风险提示": final_decision["risk_warning"],
        },
    }


def _retracement_state(current: float, anchor_low: float, best_low: float, best_high: float) -> str:
    if current > best_high:
        return "等待回撤"
    if best_low <= current <= best_high:
        return "进入最佳买入波段"
    if best_low > current >= anchor_low:
        return "跌破买入区，观察是否失效"
    return "波段结构失效"


def _chart_bars(history: tuple[MasterPriceBar, ...]) -> list[dict[str, Any]]:
    return [
        {
            "date": bar.date,
            "open": _price(bar.open),
            "high": _price(bar.high),
            "low": _price(bar.low),
            "close": _price(bar.close),
            "volume": round(float(bar.volume), 2),
        }
        for bar in history[-80:]
    ]


def _classify_market_structure(history: tuple[MasterPriceBar, ...], current_price: float) -> dict[str, Any]:
    recent = history[-60:] if len(history) >= 60 else history
    high = max(item.high for item in recent)
    low = min(item.low for item in recent)
    start = recent[0].close
    change_pct = (current_price - start) / start * 100
    from_high = (current_price - high) / high * 100
    range_pct = (high - low) / low * 100
    if from_high < -12 and change_pct < -8:
        scenario = "breakdown_downtrend"
    elif current_price > high * 0.99 and change_pct > 18:
        scenario = "high_after_surge"
    elif current_price > high * 0.98 and change_pct > 8:
        scenario = "main_uptrend_breakout"
    elif range_pct <= 12:
        scenario = "sideways_range"
    elif change_pct > 5 and from_high < -3:
        scenario = "normal_uptrend_pullback"
    else:
        scenario = "long_term_core_review"
    return {
        "scenario": scenario,
        "recent_change_pct": round(change_pct, 2),
        "distance_from_recent_high_pct": round(from_high, 2),
        "recent_range_pct": round(range_pct, 2),
        "is_chasing_high": current_price >= high * 0.98 and change_pct > 15,
    }


def _select_tools(market_structure: dict[str, Any]) -> list[str]:
    scenario = market_structure["scenario"]
    mapping = {
        "normal_uptrend_pullback": ["Fibonacci Retracement", "Upward Projection", "Multi-Wave Confluence"],
        "main_uptrend_breakout": ["Fibonacci Trend Extension", "Fibonacci Channel", "Fibonacci Speed Resistance Fan"],
        "long_term_core_review": ["Full History Retracement", "Long Cycle Extension", "Fibonacci Trend-Based Time", "Fibonacci Circles", "Fibonacci Spiral"],
        "sideways_range": ["Range Retracement", "Multi-Wave Dense Zone"],
        "high_after_surge": ["Fibonacci Trend Extension", "Fibonacci Speed Resistance Fan", "Risk Review"],
        "breakdown_downtrend": ["Retracement Failure", "Downtrend Rebound Pressure", "Risk Zone"],
    }
    return mapping.get(scenario, mapping["long_term_core_review"])


def _build_trade_point(primary: dict[str, Any], tool_name: str, ratio: float, kind: str, current_price: float) -> dict[str, Any]:
    level = next(item for item in primary["levels"] if item["tool_name"] == tool_name and item["ratio"] == ratio)
    return {
        "kind": kind,
        "price": level["price"],
        "source": f"{tool_name} {ratio}",
        "formula": level["formula"],
        "historical_success_rate": level["success_rate"],
        "sample_count": level["touch_count"],
        "failure_count": level["failure_count"],
        "confidence_by_sample": level["confidence_by_sample"],
        "effectiveness": level["effectiveness"],
        "current_distance_pct": round((current_price - level["price"]) / level["price"] * 100, 2),
        "not_high_confidence_if_sample_small": level["touch_count"] < 6,
    }


def _build_stop_loss(primary: dict[str, Any], confluence_zones: list[dict[str, Any]]) -> dict[str, Any]:
    retracement_0786 = _level_price(primary, "fibonacci_retracement", 0.786)
    candidates = [
        {"price": _price(retracement_0786 * 0.985), "source": "跌破回撤0.786下方"},
        {"price": _price(primary["anchor_low"] * 0.99), "source": "跌破主波段低点"},
    ]
    if confluence_zones:
        candidates.append({"price": _price(confluence_zones[0]["price_range"][0] * 0.985), "source": "跌破多波段共振区"})
    return candidates[0]


def _build_take_profit(primary: dict[str, Any]) -> dict[str, Any]:
    return {
        "target1": {"price": _level_price(primary, "upward_projection", 1.0), "source": "上升映射1.000"},
        "target2": {"price": _level_price(primary, "fibonacci_trend_extension", 1.272), "source": "趋势扩展1.272"},
        "target3": {"price": _level_price(primary, "fibonacci_trend_extension", 1.618), "source": "趋势扩展1.618"},
    }


def _tool_block(title: str, use_case: str, levels: list[dict[str, Any]], tool_name: str) -> dict[str, Any]:
    return {
        "tool_name": title,
        "use_case": use_case,
        "levels": [
            {
                "ratio": item["ratio"],
                "price": item["price"],
                "touch_count": item["touch_count"],
                "success_rate": item["success_rate"],
                "sample_valid": item["sample_valid"],
            }
            for item in levels
            if item["tool_name"] == tool_name
        ],
    }


def _detect_pivots(history: tuple[MasterPriceBar, ...]) -> list[MasterPriceBar]:
    pivots: list[MasterPriceBar] = []
    for index in range(2, len(history) - 2):
        window = history[index - 2 : index + 3]
        bar = history[index]
        if bar.high == max(item.high for item in window) or bar.low == min(item.low for item in window):
            pivots.append(bar)
    return pivots


def _touches(bar: MasterPriceBar, level_price: float) -> bool:
    tolerance = level_price * TOUCH_TOLERANCE
    return bar.low - tolerance <= level_price <= bar.high + tolerance


def _first_reaction_day(level_price: float, future: tuple[MasterPriceBar, ...]) -> int:
    for offset, bar in enumerate(future, start=1):
        if (bar.high - level_price) / level_price >= REACTION_THRESHOLD:
            return offset
    return len(future)


def _level_price(primary: dict[str, Any], tool_name: str, ratio: float) -> float:
    for item in primary["levels"]:
        if item["tool_name"] == tool_name and item["ratio"] == ratio:
            return item["price"]
    raise ValueError(f"Missing level {tool_name} {ratio}.")


def _formula(tool_name: str, ratio: float) -> str:
    if tool_name == "fibonacci_retracement":
        return f"retracement_price({ratio}) = anchor_high - {ratio} * (anchor_high - anchor_low)"
    if tool_name == "upward_projection":
        return f"upward_price({ratio}) = anchor_low + {ratio} * (anchor_high - anchor_low)"
    return f"extension_price({ratio}) = anchor_low + {ratio} * (anchor_high - anchor_low)"


def _sample_confidence(samples: int) -> str:
    if samples < 3:
        return "胜率无效，仅供参考"
    if samples <= 5:
        return "低置信度"
    if samples <= 10:
        return "中置信度"
    return "高置信度"


def _effectiveness(success_rate: float) -> str:
    if success_rate >= 70:
        return "高有效区域"
    if success_rate >= 55:
        return "中等有效区域"
    if success_rate >= 45:
        return "不明显"
    return "低效区域，不应作为主要买点"


def _confluence_strength(gap_pct: float) -> str:
    if gap_pct <= 0.5:
        return "强共振"
    if gap_pct <= 1.0:
        return "中共振"
    if gap_pct <= 2.0:
        return "弱共振"
    return "不构成有效共振"


def _confluence_score_level(score: float) -> str:
    if score >= 85:
        return "强共振，可进入交易池候选"
    if score >= 70:
        return "中共振，等待确认"
    if score >= 50:
        return "弱共振，只观察"
    return "无效信号，不交易"


def _near_price(current: float, target: float, tolerance_pct: float) -> bool:
    if target <= 0:
        return False
    return abs(current - target) / target * 100 <= tolerance_pct


def _find_bar_index(history: tuple[MasterPriceBar, ...], bar_date: str) -> int:
    for index, bar in enumerate(history):
        if bar.date == bar_date:
            return index
    return max(0, len(history) - 1)


def _has_reversal_candle(history: tuple[MasterPriceBar, ...]) -> bool:
    if len(history) < 2:
        return False
    prev = history[-2]
    last = history[-1]
    bullish_engulfing = last.close > last.open and prev.close < prev.open and last.close >= prev.open and last.open <= prev.close
    long_lower_shadow = last.close > last.open and (min(last.open, last.close) - last.low) >= abs(last.close - last.open) * 1.8
    return bullish_engulfing or long_lower_shadow


def _has_volume_confirmation(history: tuple[MasterPriceBar, ...]) -> bool:
    if len(history) < 21:
        return False
    recent_avg = sum(bar.volume for bar in history[-21:-1]) / 20
    last = history[-1]
    return last.volume >= recent_avg * 1.2 and last.close >= last.open


def _risk_warning(data: FibonacciMasterInput, tools: dict[str, Any], confluence: dict[str, Any]) -> str:
    warnings: list[str] = []
    if data.data_status in {"延迟", "数据延迟", "失效", "数据失效"}:
        warnings.append("数据状态异常，禁止生成新买入建议")
    if data.current_price > tools["retracement"]["best_buy_zone"][1]:
        warnings.append("当前价高于最佳买入波段，禁止追高")
    if tools["trend_channel"]["two_close_breakdown"]:
        warnings.append("连续两根收盘跌破趋势通道，结构破坏")
    if not confluence["triple_confluence"]:
        warnings.append("未满足三重共振，不能开仓")
    if tools["spiral"]["standalone_signal_allowed"] is False:
        warnings.append("螺旋和时间窗口只做辅助，不单独生成交易信号")
    return "；".join(warnings) if warnings else "暂无硬性风险触发，仍需按买点和止损执行"


def _pct_gap(a: float, b: float) -> float:
    base = max(0.001, min(abs(a), abs(b)))
    return abs(a - b) / base * 100


def _aggregate_success_rate(levels: list[dict[str, Any]]) -> float:
    samples = sum(item["touch_count"] for item in levels)
    successes = sum(item["success_count"] for item in levels)
    return round(successes / samples * 100, 2) if samples else 0.0


def _historical_score(buy_point1: dict[str, Any], buy_point2: dict[str, Any], confluence_zones: list[dict[str, Any]]) -> float:
    values = [buy_point1["historical_success_rate"], buy_point2["historical_success_rate"]]
    if confluence_zones:
        values.append(confluence_zones[0]["combined_success_rate"])
    return round(sum(values) / len(values), 2)


def _provider_content(result: AIConsensusResult, provider: str) -> str:
    for response in result.responses:
        if response.provider.lower() == provider:
            return response.content
    return ""


def _extract_decision(text: str) -> str:
    if any(token in text for token in ("回避", "avoid", "风险", "不买")):
        return "回避"
    if any(token in text for token in ("可买", "buy", "买入")):
        return "可买"
    return "等待"


def _score_text(text: str) -> float:
    decision = _extract_decision(text)
    if decision == "可买":
        return 78.0
    if decision == "回避":
        return 35.0
    return 58.0


def _decision_conflict(deepseek_decision: str, doubao_decision: str) -> bool:
    return {deepseek_decision, doubao_decision} == {"可买", "回避"}


def _ai_pending(provider: str, reason: str) -> dict[str, Any]:
    if provider == "DeepSeek":
        return {
            "provider": provider,
            "deepseek_structure_view": reason,
            "deepseek_anchor_view": reason,
            "deepseek_fib_validity": reason,
            "deepseek_risk_view": reason,
            "deepseek_decision": "等待",
            "score": 0.0,
        }
    return {
        "provider": provider,
        "doubao_news_view": reason,
        "doubao_sentiment_view": reason,
        "doubao_sector_view": reason,
        "doubao_risk_view": reason,
        "doubao_decision": "等待",
        "score": 0.0,
    }


def _time_windows(primary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "ratio": ratio,
            "time_target": f"{primary['end_date']} + {ratio:g} wave-length",
            "confidence": "辅助窗口，不能单独作为买卖依据",
        }
        for ratio in TIME_RATIOS
    ]


def _channel_label(ratio: float) -> str:
    labels = {0.0: "通道下轨", 0.5: "通道中轨", 1.0: "通道上轨"}
    return labels.get(ratio, f"{ratio:g} 通道")


def _price(value: float) -> float:
    return round(float(value), 3)


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_log(path: str | None, output: dict[str, Any]) -> None:
    if not path:
        return
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "time": output["generated_at"],
        "stock": output["stock_name"],
        "symbol": output["symbol"],
        "current_price": output["current_price"],
        "selected_tools": output["selected_tools"],
        "anchor": output["primary_anchor"],
        "buy_point1": output["buy_point1"],
        "buy_point2": output["buy_point2"],
        "best_buy_zone": output["best_buy_zone"],
        "deepseek_decision": output["deepseek_review"]["deepseek_decision"],
        "doubao_decision": output["doubao_review"]["doubao_decision"],
        "final_action": output["final_action"],
        "changed": None,
        "change_reason": output["reason"],
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
