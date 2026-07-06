from datetime import datetime, timedelta, timezone
import unittest

from locust_autonomous_ai_analysis import (
    AIDecision,
    AITrigger,
    AutonomousAIAnalysisLayer,
    ModelView,
    ai_analysis_to_output,
    detect_triggers,
)
from locust_realtime_verification import DataSourceTag, PricePayload, build_verified_stock_data


class FakeAIClient:
    def __init__(self):
        self.calls = []

    def analyze_deepseek(self, stock, triggers):
        self.calls.append(("DeepSeek", stock.symbol, triggers))
        return ModelView("DeepSeek", "结构判断：Wave有效，Fib合理，存在共振区，主升结构未破坏。交易建议：等待买点确认。风险判断：无假突破。", 82)

    def analyze_doubao(self, stock, triggers):
        self.calls.append(("Doubao", stock.symbol, triggers))
        return ModelView("Doubao", "情绪评分偏强，板块热点延续，资金流入，市场共识方向偏多。", 76)


class BadSingleModelClient:
    def analyze_deepseek(self, stock, triggers):
        return ModelView("DeepSeek", "ok", 80)

    def analyze_doubao(self, stock, triggers):
        return ModelView("DeepSeek", "wrong", 80)


def verified(symbol="601138.SH", name="工业富联", locust=80, fib_zone="BUY_ZONE", confluence=3, buy1=49, buy2=53):
    now = datetime(2026, 7, 5, 10, 0, 0, tzinfo=timezone.utc)
    return build_verified_stock_data(
        stock_name=name,
        symbol=symbol,
        price=PricePayload(52.0, DataSourceTag.AKSHARE, now),
        last_sync_time=now - timedelta(seconds=1),
        fib_zone=fib_zone,
        confluence_layers=confluence,
        buy_point_1=buy1,
        buy_point_2=buy2,
        stop_loss=47,
        take_profit=60,
        locust_score=locust,
        risk_score=28,
        now=now,
    )


class LocustAutonomousAIAnalysisTest(unittest.TestCase):
    def test_auto_sync_analyzes_every_stock_with_two_models(self):
        client = FakeAIClient()
        layer = AutonomousAIAnalysisLayer(client)
        stocks = (verified(), verified("300308.SZ", "中际旭创"),)

        result = layer.analyze_after_sync(stocks)

        self.assertEqual(set(result.keys()), {"601138.SH", "300308.SZ"})
        self.assertEqual(len(client.calls), 4)
        self.assertEqual([call[0] for call in client.calls], ["DeepSeek", "Doubao", "DeepSeek", "Doubao"])
        self.assertEqual(result["601138.SH"].decision, AIDecision.BUY)
        self.assertGreaterEqual(result["601138.SH"].confidence, 70)

    def test_rejects_missing_doubao_model(self):
        layer = AutonomousAIAnalysisLayer(BadSingleModelClient())

        with self.assertRaisesRegex(ValueError, "DeepSeek 与 Doubao"):
            layer.analyze_stock(verified(), (AITrigger.DATA_SYNC,))

    def test_detects_required_trigger_reasons(self):
        previous = verified(locust=70, fib_zone="NEUTRAL_ZONE", confluence=2, buy1=48)
        current = verified(locust=78, fib_zone="BUY_ZONE", confluence=3, buy1=49)

        triggers = detect_triggers(previous, current, is_new_top_pick=False)

        self.assertIn(AITrigger.DATA_SYNC, triggers)
        self.assertIn(AITrigger.FIB_STRUCTURE_UPDATE, triggers)
        self.assertIn(AITrigger.LOCUST_SCORE_DELTA, triggers)
        self.assertIn(AITrigger.TRADE_POINT_UPDATE, triggers)

    def test_new_top_pick_triggers_ai_analysis(self):
        triggers = detect_triggers(None, verified(), is_new_top_pick=True)

        self.assertEqual(triggers, (AITrigger.DATA_SYNC, AITrigger.NEW_TOP_PICK))

    def test_output_shape_is_ai_analysis_contract(self):
        client = FakeAIClient()
        layer = AutonomousAIAnalysisLayer(client)
        analysis = layer.analyze_stock(verified(), (AITrigger.DATA_SYNC,))
        output = ai_analysis_to_output(analysis)["AI_ANALYSIS"]

        self.assertIn("deepseek_view", output)
        self.assertIn("doubao_view", output)
        self.assertIn("merged_view", output)
        self.assertIn(output["decision"], {"BUY", "WAIT", "AVOID"})
        self.assertGreaterEqual(output["confidence"], 0)
        self.assertLessEqual(output["confidence"], 100)


if __name__ == "__main__":
    unittest.main()
