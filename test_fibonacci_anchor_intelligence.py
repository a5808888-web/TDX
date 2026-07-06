import unittest

from fibonacci_anchor_intelligence import (
    AnchorIntelligenceInput,
    AnchorMode,
    AnchorSource,
    AnchorStatus,
    DeepSeekAnchorClient,
    FibonacciAnchorIntelligenceLayer,
    KLine,
    ManualAnchorInput,
    StructureFlag,
    WaveAnchor,
    anchor_intelligence_to_output,
)
from ai_consensus_layer import OpenAICompatibleProvider


def sample_klines():
    return (
        KLine("2026-06-24", 42.8, 44.1, 41.9, 43.2, 930000),
        KLine("2026-06-25", 43.2, 44.0, 40.8, 42.7, 860000),
        KLine("2026-06-26", 42.7, 46.6, 42.2, 45.8, 1180000),
        KLine("2026-06-29", 45.8, 51.3, 45.1, 50.6, 1460000),
        KLine("2026-06-30", 50.6, 56.8, 49.9, 55.2, 1760000),
        KLine("2026-07-01", 55.2, 59.4, 54.3, 58.1, 1680000),
        KLine("2026-07-02", 58.1, 58.4, 54.8, 55.6, 1390000),
        KLine("2026-07-03", 55.6, 56.2, 53.6, 54.4, 1250000),
    )


class FibonacciAnchorIntelligenceTest(unittest.TestCase):
    def test_ai_confirmed_anchor_rebuilds_fib_matrix_and_trade_levels(self):
        layer = FibonacciAnchorIntelligenceLayer()
        result = layer.evaluate(
            AnchorIntelligenceInput(
                symbol="601138.SH",
                current_price=51.88,
                klines=sample_klines(),
            )
        )

        self.assertEqual(result.ai_anchor.status, AnchorStatus.CONFIRMED)
        self.assertEqual(result.anchor_source, AnchorSource.AI)
        self.assertIsNotNone(result.fib_matrix)
        self.assertIsNotNone(result.trade_levels)
        self.assertEqual(result.fib_matrix.anchor_low, result.ai_anchor.anchor_low)
        self.assertEqual(result.fib_matrix.anchor_high, result.ai_anchor.anchor_high)

    def test_manual_mode_overrides_ai_and_marks_manual_source(self):
        layer = FibonacciAnchorIntelligenceLayer()
        result = layer.evaluate(
            AnchorIntelligenceInput(
                symbol="601138.SH",
                current_price=51.88,
                klines=sample_klines(),
                mode=AnchorMode.MANUAL,
                manual_anchor=ManualAnchorInput(manual_anchor_low=40.9, manual_anchor_high=59.2),
            )
        )

        self.assertEqual(result.anchor_source, AnchorSource.MANUAL)
        self.assertEqual(result.active_anchor.anchor_low, 40.9)
        self.assertEqual(result.active_anchor.anchor_high, 59.2)
        self.assertEqual(result.fib_matrix.anchor_low, 40.9)
        self.assertEqual(result.fib_matrix.anchor_high, 59.2)

    def test_conflict_when_manual_anchor_differs_from_ai_by_more_than_five_percent(self):
        layer = FibonacciAnchorIntelligenceLayer()
        result = layer.evaluate(
            AnchorIntelligenceInput(
                symbol="601138.SH",
                current_price=51.88,
                klines=sample_klines(),
                mode=AnchorMode.HYBRID,
                manual_anchor=ManualAnchorInput(manual_anchor_low=33.0, manual_anchor_high=72.0),
            )
        )

        self.assertEqual(result.consistency.flag, StructureFlag.CONFLICT)
        self.assertIn("STRUCTURE CONFLICT", result.consistency.message)

    def test_low_confidence_ai_anchor_requires_manual_and_does_not_build_fib(self):
        weak_anchor = WaveAnchor(
            anchor_low=42.0,
            anchor_high=49.0,
            confidence=58,
            status=AnchorStatus.INVALID,
            source=AnchorSource.AI_PROVISIONAL,
        )
        layer = FibonacciAnchorIntelligenceLayer()
        result = layer.evaluate(
            AnchorIntelligenceInput(
                symbol="601138.SH",
                current_price=45.0,
                klines=(),
                ai_anchor=weak_anchor,
            )
        )

        self.assertEqual(result.consistency.flag, StructureFlag.MANUAL_REQUIRED)
        self.assertIsNone(result.fib_matrix)
        self.assertTrue(any("manual required" in warning for warning in result.warnings))

    def test_output_contains_required_anchor_mode_shape(self):
        layer = FibonacciAnchorIntelligenceLayer()
        result = layer.evaluate(
            AnchorIntelligenceInput(
                symbol="601138.SH",
                current_price=51.88,
                klines=sample_klines(),
            )
        )
        output = anchor_intelligence_to_output(result)
        mode = output["FIBONACCI ANCHOR MODE"]

        self.assertIn("AI Anchor", mode)
        self.assertIn("Manual Anchor", mode)
        self.assertIn("Active Anchor", mode)
        self.assertIn("当前状态", mode)
        self.assertIn("FibMatrix", output)
        self.assertIn("TradeLevels", output)

    def test_deepseek_anchor_client_normalizes_ai_json_to_anchor_contract(self):
        def fake_transport(url, headers, body, timeout):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"anchor_low": 40.8, "anchor_high": 59.4, "confidence": 79, "status": "confirmed"}'
                        }
                    }
                ]
            }

        provider = OpenAICompatibleProvider(
            name="DeepSeek",
            endpoint="https://example.test/chat/completions",
            model="deepseek-chat",
            api_key="test-key",
            transport=fake_transport,
        )
        client = DeepSeekAnchorClient(provider)
        technical_anchor = WaveAnchor(40.8, 59.4, 100, AnchorStatus.CONFIRMED, AnchorSource.AI)
        anchor = client.detect_anchor(
            AnchorIntelligenceInput(symbol="601138.SH", current_price=51.88, klines=sample_klines()),
            technical_anchor,
        )

        self.assertEqual(anchor.anchor_low, 40.8)
        self.assertEqual(anchor.anchor_high, 59.4)
        self.assertEqual(anchor.confidence, 79)
        self.assertEqual(anchor.status, AnchorStatus.WEAK)
        self.assertEqual(anchor.source, AnchorSource.AI)


if __name__ == "__main__":
    unittest.main()
