from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Protocol

from ai_consensus_layer import AIAnalysisRequest, OpenAICompatibleProvider, build_default_dual_ai_layer
from locust_realtime_verification import VerifiedStockData, verified_stock_to_output


class AITrigger(str, Enum):
    DATA_SYNC = "DATA_SYNC"
    FIB_STRUCTURE_UPDATE = "FIB_STRUCTURE_UPDATE"
    LOCUST_SCORE_DELTA = "LOCUST_SCORE_DELTA"
    NEW_TOP_PICK = "NEW_TOP_PICK"
    TRADE_POINT_UPDATE = "TRADE_POINT_UPDATE"


class AIDecision(str, Enum):
    BUY = "BUY"
    WAIT = "WAIT"
    AVOID = "AVOID"


@dataclass(frozen=True)
class ModelView:
    provider: str
    content: str
    score: float


@dataclass(frozen=True)
class AIAnalysis:
    deepseek_view: str
    doubao_view: str
    merged_view: str
    decision: AIDecision
    confidence: float
    supports_fib_signal: bool
    supports_buy_point: bool
    avoid_required: bool
    trigger_reasons: tuple[AITrigger, ...]
    analyzed_at: datetime


class AutonomousAIClient(Protocol):
    def analyze_deepseek(self, stock: VerifiedStockData, triggers: tuple[AITrigger, ...]) -> ModelView:
        ...

    def analyze_doubao(self, stock: VerifiedStockData, triggers: tuple[AITrigger, ...]) -> ModelView:
        ...


class OpenAIProviderAutonomousClient:
    def __init__(self, deepseek: OpenAICompatibleProvider, doubao: OpenAICompatibleProvider) -> None:
        self.deepseek = deepseek
        self.doubao = doubao

    def analyze_deepseek(self, stock: VerifiedStockData, triggers: tuple[AITrigger, ...]) -> ModelView:
        response = self.deepseek.analyze(
            AIAnalysisRequest(
                task="DeepSeek策略分析：判断Wave结构、Fibonacci有效性、买卖点、共振区、主升浪、风险结构和假突破。",
                payload=_stock_payload(stock, triggers),
            )
        )
        return ModelView("DeepSeek", response.content, _deepseek_score(stock, response.content))

    def analyze_doubao(self, stock: VerifiedStockData, triggers: tuple[AITrigger, ...]) -> ModelView:
        response = self.doubao.analyze(
            AIAnalysisRequest(
                task="豆包信息归纳：归纳市场新闻、板块情绪、资金热点、政策消息影响和个股舆情。",
                payload=_stock_payload(stock, triggers),
            )
        )
        return ModelView("Doubao", response.content, _doubao_score(stock, response.content))


class AutonomousAIAnalysisLayer:
    def __init__(self, client: AutonomousAIClient) -> None:
        self.client = client
        self.latest_by_symbol: dict[str, AIAnalysis] = {}
        self.previous_stocks: dict[str, VerifiedStockData] = {}

    def analyze_after_sync(self, stocks: tuple[VerifiedStockData, ...], now: datetime | None = None) -> dict[str, AIAnalysis]:
        now = now or datetime.now(timezone.utc)
        result: dict[str, AIAnalysis] = {}
        current_symbols = {stock.symbol for stock in stocks}
        for stock in stocks:
            triggers = detect_triggers(self.previous_stocks.get(stock.symbol), stock, stock.symbol not in self.previous_stocks)
            if not triggers:
                triggers = (AITrigger.DATA_SYNC,)
            analysis = self.analyze_stock(stock, triggers, now=now)
            result[stock.symbol] = analysis
            self.latest_by_symbol[stock.symbol] = analysis

        self.previous_stocks = {stock.symbol: stock for stock in stocks if stock.symbol in current_symbols}
        return result

    def analyze_stock(self, stock: VerifiedStockData, triggers: tuple[AITrigger, ...], now: datetime | None = None) -> AIAnalysis:
        deepseek = self.client.analyze_deepseek(stock, triggers)
        doubao = self.client.analyze_doubao(stock, triggers)
        if deepseek.provider.lower() != "deepseek" or doubao.provider.lower() != "doubao":
            raise ValueError("AI分析必须同时包含 DeepSeek 与 Doubao。")
        return merge_ai_views(stock, deepseek, doubao, triggers, now or datetime.now(timezone.utc))


def build_default_autonomous_ai_layer() -> AutonomousAIAnalysisLayer:
    dual = build_default_dual_ai_layer()
    providers = {provider.name.lower(): provider for provider in dual.providers}
    return AutonomousAIAnalysisLayer(
        OpenAIProviderAutonomousClient(
            deepseek=providers["deepseek"],
            doubao=providers["doubao"],
        )
    )


def detect_triggers(previous: VerifiedStockData | None, current: VerifiedStockData, is_new_top_pick: bool) -> tuple[AITrigger, ...]:
    triggers = [AITrigger.DATA_SYNC]
    if previous is None or is_new_top_pick:
        triggers.append(AITrigger.NEW_TOP_PICK)
        return tuple(triggers)
    if previous.fib_zone != current.fib_zone or previous.confluence_layers != current.confluence_layers:
        triggers.append(AITrigger.FIB_STRUCTURE_UPDATE)
    if abs(previous.locust_score - current.locust_score) > 5:
        triggers.append(AITrigger.LOCUST_SCORE_DELTA)
    if (
        previous.buy_point_1 != current.buy_point_1
        or previous.buy_point_2 != current.buy_point_2
        or previous.stop_loss != current.stop_loss
        or previous.take_profit != current.take_profit
    ):
        triggers.append(AITrigger.TRADE_POINT_UPDATE)
    return tuple(dict.fromkeys(triggers))


def merge_ai_views(
    stock: VerifiedStockData,
    deepseek: ModelView,
    doubao: ModelView,
    triggers: tuple[AITrigger, ...],
    analyzed_at: datetime,
) -> AIAnalysis:
    confidence = round(_clamp(deepseek.score * 0.6 + doubao.score * 0.4), 2)
    avoid_required = stock.risk_score >= 80 or confidence < 40 or "风险" in deepseek.content and stock.risk_score >= 60
    supports_fib = stock.fib_zone == "BUY_ZONE" and stock.confluence_layers >= 2 and deepseek.score >= 60
    supports_buy = supports_fib and confidence >= 65 and not avoid_required
    if avoid_required:
        decision = AIDecision.AVOID
    elif supports_buy:
        decision = AIDecision.BUY
    else:
        decision = AIDecision.WAIT

    merged = (
        f"最终方向：{decision.value}；"
        f"DeepSeek结构权重60%，豆包情绪权重40%；"
        f"Fib支持：{'是' if supports_fib else '否'}；"
        f"买点支持：{'是' if supports_buy else '否'}；"
        f"置信度：{confidence:.2f}/100。"
    )
    return AIAnalysis(
        deepseek_view=deepseek.content,
        doubao_view=doubao.content,
        merged_view=merged,
        decision=decision,
        confidence=confidence,
        supports_fib_signal=supports_fib,
        supports_buy_point=supports_buy,
        avoid_required=avoid_required,
        trigger_reasons=triggers,
        analyzed_at=analyzed_at,
    )


def ai_analysis_to_output(analysis: AIAnalysis) -> dict[str, object]:
    return {
        "AI_ANALYSIS": {
            "deepseek_view": analysis.deepseek_view,
            "doubao_view": analysis.doubao_view,
            "merged_view": analysis.merged_view,
            "decision": analysis.decision.value,
            "confidence": analysis.confidence,
            "supports_fib_signal": analysis.supports_fib_signal,
            "supports_buy_point": analysis.supports_buy_point,
            "avoid_required": analysis.avoid_required,
            "trigger_reasons": tuple(item.value for item in analysis.trigger_reasons),
            "analyzed_at": analysis.analyzed_at.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
        }
    }


def _stock_payload(stock: VerifiedStockData, triggers: tuple[AITrigger, ...]) -> dict[str, object]:
    payload = verified_stock_to_output(stock)
    payload["trigger_reasons"] = tuple(trigger.value for trigger in triggers)
    return payload


def _deepseek_score(stock: VerifiedStockData, content: str) -> float:
    base = 55.0
    if stock.fib_zone == "BUY_ZONE":
        base += 18
    if stock.confluence_layers >= 3:
        base += 12
    if stock.locust_score >= 70:
        base += 8
    if stock.risk_score >= 60:
        base -= 18
    if "假突破" in content or "风险" in content:
        base -= 8
    if "主升" in content or "有效" in content:
        base += 6
    return _clamp(base)


def _doubao_score(stock: VerifiedStockData, content: str) -> float:
    base = 50.0 + (stock.locust_score - 50) * 0.35
    positive_terms = ("利好", "热点", "共识", "资金流入", "情绪改善")
    negative_terms = ("利空", "退潮", "分歧", "监管", "风险")
    base += sum(5 for term in positive_terms if term in content)
    base -= sum(6 for term in negative_terms if term in content)
    return _clamp(base)


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))
