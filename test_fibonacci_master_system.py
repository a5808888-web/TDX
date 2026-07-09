from __future__ import annotations

import unittest
from datetime import date, timedelta
from unittest.mock import patch

import app
from ai_consensus_layer import AIConsensusResult, AIProviderResponse
from fibonacci_master_system import FibonacciMasterInput, MasterPriceBar, run_fibonacci_master_system


class FakeDualAILayer:
    def __init__(self, deepseek_text: str = "可买", doubao_text: str = "可买") -> None:
        self.calls = []
        self.deepseek_text = deepseek_text
        self.doubao_text = doubao_text

    def analyze(self, request):
        self.calls.append(request)
        return AIConsensusResult(
            task=request.task,
            responses=(
                AIProviderResponse("DeepSeek", self.deepseek_text, {"ok": True}),
                AIProviderResponse("Doubao", self.doubao_text, {"ok": True}),
            ),
            consensus=f"DeepSeek:{self.deepseek_text}\nDoubao:{self.doubao_text}",
        )


class FibonacciMasterSystemTest(unittest.TestCase):
    def test_builds_standardized_multi_tool_engine_output(self):
        ai = FakeDualAILayer()
        result = run_fibonacci_master_system(
            FibonacciMasterInput(
                stock_name="样本股",
                symbol="000001.SZ",
                current_price=24.8,
                data_source="AKShare",
                updated_at="2026-07-08 10:00:00",
                history=sample_history(),
                log_path=None,
            ),
            ai_layer=ai,
        )

        self.assertEqual(result["system"], "Standardized Multi-Tool Fibonacci Quant Engine")
        self.assertEqual(result["legacy_system"], "Fibonacci Master System")
        self.assertEqual(len(ai.calls), 1)
        ai_payload = ai.calls[0].payload
        self.assertNotIn("data", ai_payload)
        self.assertIn("stock_context", ai_payload)
        self.assertIn("history_summary", ai_payload["stock_context"])
        self.assertLessEqual(len(ai_payload["stock_context"]["recent_bars"]), 60)
        tool_names = {item["tool_name"] for item in result["tool_family"]}
        self.assertIn("Fibonacci Retracement", tool_names)
        self.assertIn("Fibonacci Trend Extension", tool_names)
        self.assertIn("Fibonacci Channel", tool_names)
        self.assertIn("Fibonacci Time Zone", tool_names)
        self.assertIn("Fibonacci Speed Resistance Fan", tool_names)
        self.assertIn("Fibonacci Trend-Based Time", tool_names)
        self.assertIn("Fibonacci Circles", tool_names)
        self.assertIn("Fibonacci Spiral", tool_names)
        self.assertIn("Fibonacci Speed Resistance Arcs", tool_names)
        self.assertIn("Fibonacci Wedge / Fan", tool_names)
        self.assertEqual(result["buy_point1"]["source"], "fibonacci_retracement 0.786")
        self.assertEqual(result["buy_point2"]["source"], "upward_projection 0.236")
        self.assertGreaterEqual(len(result["multi_wave_table"]), 6)
        self.assertGreater(len(result["win_rate_table"]), 20)
        self.assertIn("sample_count", result["buy_point1"])
        self.assertIn("failure_count", result["buy_point1"])
        self.assertFalse(result["standardized_tools"]["upward_extension"]["extension_used_for_entry"])
        self.assertEqual(result["standardized_output"]["买点"]["买点1来源"], "主波段回撤0.786")
        self.assertEqual(result["standardized_output"]["买点"]["买点2来源"], "主波段上升映射0.236")
        self.assertEqual(result["standardized_output"]["卖点"]["第一止盈"], result["take_profit"]["target1"]["price"])
        self.assertIn("是否满足三重共振", result["standardized_output"]["共振"])
        self.assertIn(result["final_action"], {"可买", "等待", "观察", "回避", "持有", "减仓", "止盈", "止损"})
        self.assertTrue(result["required_guards"]["no_ai_generated_price"])

    def test_missing_dual_ai_never_outputs_buy_or_trade_allowed(self):
        result = run_fibonacci_master_system(
            FibonacciMasterInput(
                stock_name="样本股",
                symbol="000001.SZ",
                current_price=24.8,
                data_source="AKShare",
                updated_at="2026-07-08 10:00:00",
                history=sample_history(),
                log_path=None,
            ),
            ai_layer=None,
        )

        self.assertEqual(result["final_action"], "观察")
        self.assertFalse(result["ai_fusion"]["trade_allowed"])
        self.assertIn("DeepSeek", result["reason"])

    def test_api_helper_uses_locked_market_price_and_history(self):
        fake_price = {
            "value": 78.17,
            "source": "AKShare",
            "timestamp": "2026-07-08 10:00:00",
        }
        with (
            patch.object(app, "_fresh_locked_market_items", return_value={}),
            patch.object(app, "_locked_price_for_symbol", return_value=fake_price),
            patch.object(app, "fetch_akshare_history", return_value=sample_history()),
            patch.object(app, "build_default_dual_ai_layer", return_value=FakeDualAILayer()),
        ):
            payload = app._fibonacci_master_api_output({"symbols": ["000977.SZ"]})

        self.assertEqual(payload["system"], "Fibonacci Master System")
        self.assertEqual(payload["errors"], {})
        self.assertEqual(payload["analyses"][0]["system"], "Standardized Multi-Tool Fibonacci Quant Engine")
        self.assertEqual(payload["analyses"][0]["symbol"], "000977.SZ")
        self.assertEqual(payload["analyses"][0]["current_price"], 78.17)
        self.assertEqual(payload["analyses"][0]["data_source"], "AKShare")

    def test_api_helper_supports_dongyangguang_as_non_holding_watch_symbol(self):
        fake_price = {
            "value": 34.56,
            "source": "AKShare",
            "timestamp": "2026-07-09 10:00:00",
        }
        with (
            patch.object(app, "_fresh_locked_market_items", return_value={}),
            patch.object(app, "_locked_price_for_symbol", return_value=fake_price),
            patch.object(app, "fetch_akshare_history", return_value=sample_history()),
            patch.object(app, "build_default_dual_ai_layer", return_value=FakeDualAILayer()),
        ):
            payload = app._fibonacci_master_api_output({"symbols": ["600673.SH"]})

        self.assertEqual(payload["errors"], {})
        analysis = payload["analyses"][0]
        self.assertEqual(analysis["symbol"], "600673.SH")
        self.assertEqual(analysis["stock_name"], "东阳光")
        self.assertEqual(analysis["standardized_output"]["是否持仓"], False)
        self.assertEqual(analysis["standardized_output"]["股票身份"], "朋友测算/观察")


def sample_history() -> tuple[MasterPriceBar, ...]:
    start = date(2025, 1, 1)
    bars = []
    for index in range(260):
        base = 18 + index * 0.045
        wave = (index % 18 - 9) * 0.18
        close = base + wave
        open_price = close - 0.12
        high = close + 0.75 + (index % 5) * 0.04
        low = close - 0.75 - (index % 7) * 0.03
        bars.append(
            MasterPriceBar(
                date=(start + timedelta(days=index)).isoformat(),
                open=round(open_price, 3),
                high=round(high, 3),
                low=round(low, 3),
                close=round(close, 3),
                volume=1_000_000 + index * 1000,
            )
        )
    return tuple(bars)


if __name__ == "__main__":
    unittest.main()
