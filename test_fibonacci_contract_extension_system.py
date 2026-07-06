import unittest

from fibonacci_contract_extension_system import (
    ContractAnalysisInput,
    ContractDecision,
    build_contract_fib_analysis,
    contract_analysis_to_output,
    render_contract_analysis_html,
)
from fibonacci_wave_system import SwingKind, SwingPoint, TrendDirection, WaveSegment, WaveTier


def swing(price, kind, confirmed=True, timeframe="1D"):
    return SwingPoint(
        price=price,
        kind=kind,
        timestamp="2026-07-05",
        timeframe=timeframe,
        tier=WaveTier.OPERATING,
        confirmed=confirmed,
    )


def wave(low=40.0, high=80.0, confirmed=True, timeframe="1D"):
    return WaveSegment(
        low=swing(low, SwingKind.LOW, confirmed=confirmed, timeframe=timeframe),
        high=swing(high, SwingKind.HIGH, confirmed=confirmed, timeframe=timeframe),
        tier=WaveTier.OPERATING,
        direction=TrendDirection.UP,
        name="contract-wave",
    )


class FibonacciContractExtensionSystemTest(unittest.TestCase):
    def test_calculates_retracement_extension_and_two_buy_points(self):
        result = build_contract_fib_analysis(
            ContractAnalysisInput(
                wave=wave(),
                current_price=52.0,
                symbol="TEST",
                stock_name="测试股份",
                confluence_strength=82,
                trend_strength=72,
                volume_fit=78,
                capital_flow=75,
                stop_fall_confirmed=True,
                volume_confirmed=True,
                risk_score=35,
            )
        )

        output = contract_analysis_to_output(result)

        self.assertEqual(result.anchor_low, 40.0)
        self.assertEqual(result.anchor_high, 80.0)
        self.assertEqual(result.wave_range, 40.0)
        self.assertEqual(output["主图"]["retracement_levels"]["回撤 0.618"]["price"], 55.28)
        self.assertEqual(output["主图"]["retracement_levels"]["回撤 0.786"]["price"], 48.56)
        self.assertEqual(output["主图"]["extension_levels"]["扩展 0.236"]["price"], 49.44)
        self.assertEqual(output["主图"]["extension_levels"]["扩展 2"]["price"], 120.0)
        self.assertEqual(result.best_buy_zone, (48.56, 55.28))
        self.assertEqual(result.strategy.buy_point_1.price, 48.56)
        self.assertEqual(result.strategy.buy_point_2.price, 49.44)
        self.assertEqual(result.conclusion.action, ContractDecision.BUY)

    def test_matches_image_fixture_prices_for_contract_template(self):
        result = build_contract_fib_analysis(
            ContractAnalysisInput(
                wave=wave(low=43.37, high=84.56),
                current_price=56.0,
                confluence_strength=80,
                trend_strength=70,
                volume_fit=70,
                capital_flow=70,
            )
        )
        output = contract_analysis_to_output(result)

        self.assertEqual(output["主图"]["retracement_levels"]["回撤 0.786"]["price"], 52.18)
        self.assertEqual(output["主图"]["retracement_levels"]["回撤 0.618"]["price"], 59.1)
        self.assertEqual(output["主图"]["extension_levels"]["扩展 0.236"]["price"], 53.09)
        self.assertEqual(output["主图"]["extension_levels"]["扩展 1.272"]["price"], 95.76)
        self.assertEqual(output["主图"]["extension_levels"]["扩展 1.618"]["price"], 110.02)
        self.assertEqual(output["主图"]["extension_levels"]["扩展 2"]["price"], 125.75)
        self.assertEqual(result.best_buy_zone, (52.18, 59.1))
        self.assertEqual(result.strategy.buy_point_1.price, 52.18)
        self.assertEqual(result.strategy.buy_point_2.price, 53.09)

    def test_output_contains_required_nine_sections_and_risk_controls(self):
        result = build_contract_fib_analysis(ContractAnalysisInput(wave=wave(), current_price=65.0))
        output = contract_analysis_to_output(result)

        self.assertEqual(
            set(output.keys()),
            {
                "主图",
                "斐波那契参考表",
                "买点详细信息",
                "我的理解",
                "两个买点的作用",
                "关键价格区间",
                "波段目标位",
                "交易策略",
                "风险控制",
                "评分系统",
                "关键结论",
                "交易计划",
            },
        )
        self.assertIn("stop_loss", output["两个买点的作用"]["买点1"])
        self.assertIn("single_trade_risk_pct", output["风险控制"])
        self.assertIn("FibScore", output["评分系统"])
        self.assertIn("buy_plan", output["交易计划"])

    def test_html_renderer_outputs_visual_chart_and_required_labels(self):
        result = build_contract_fib_analysis(ContractAnalysisInput(wave=wave(), current_price=52.0, stock_name="测试股份"))
        html = render_contract_analysis_html(result)

        self.assertIn("<svg", html)
        self.assertIn("最佳买点波段", html)
        self.assertIn("买点1（回撤0.786）", html)
        self.assertIn("买点2（扩展0.236）", html)
        self.assertIn("斐波那契参考表", html)
        self.assertIn("买点详细信息", html)
        self.assertIn("波段目标位", html)
        self.assertIn("风险控制", html)
        self.assertIn("交易计划", html)

    def test_rejects_unconfirmed_intraday_and_wrong_anchor_wave(self):
        with self.assertRaisesRegex(ValueError, "未确认"):
            build_contract_fib_analysis(ContractAnalysisInput(wave=wave(confirmed=False), current_price=52.0))

        with self.assertRaisesRegex(ValueError, "日内"):
            build_contract_fib_analysis(ContractAnalysisInput(wave=wave(timeframe="60min"), current_price=52.0))

        bad_wave = WaveSegment(
            low=swing(40, SwingKind.HIGH),
            high=swing(80, SwingKind.LOW),
            tier=WaveTier.OPERATING,
            direction=TrendDirection.UP,
        )
        with self.assertRaisesRegex(ValueError, "确认低点到确认高点"):
            build_contract_fib_analysis(ContractAnalysisInput(wave=bad_wave, current_price=52.0))

    def test_observes_when_single_price_is_not_confirmed_by_volume_or_stop_fall(self):
        result = build_contract_fib_analysis(
            ContractAnalysisInput(
                wave=wave(),
                current_price=52.0,
                confluence_strength=70,
                trend_strength=70,
                volume_fit=70,
                capital_flow=70,
                stop_fall_confirmed=False,
                volume_confirmed=False,
            )
        )

        self.assertEqual(result.conclusion.action, ContractDecision.WATCH)
        self.assertFalse(result.conclusion.buy_point_1_valid)


if __name__ == "__main__":
    unittest.main()
