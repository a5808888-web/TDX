import unittest

from fibonacci_wave_system import SwingKind, SwingPoint, TrendDirection, WaveSegment, WaveTier
from locust_multitimeframe_fib_intelligence import (
    MultiTimeframeDecision,
    MultiTimeframeFibInput,
    MultiTimeframeLayer,
    MultiTimeframeWaveSet,
    multitimeframe_fib_result_to_output,
    run_multitimeframe_fib_intelligence,
)


def swing(price, kind, tier, timeframe, confirmed=True):
    return SwingPoint(
        price=price,
        kind=kind,
        timestamp="2026-07-05",
        timeframe=timeframe,
        tier=tier,
        confirmed=confirmed,
    )


def wave(low, high, name, tier, timeframe, confirmed=True):
    return WaveSegment(
        low=swing(low, SwingKind.LOW, tier, timeframe, confirmed),
        high=swing(high, SwingKind.HIGH, tier, timeframe, confirmed),
        tier=tier,
        direction=TrendDirection.UP,
        name=name,
    )


def wave_set():
    return MultiTimeframeWaveSet(
        long_wave=wave(100.0, 200.0, "长期战略", WaveTier.PRIMARY, "1W"),
        mid_wave=wave(80.0, 220.0, "中期趋势", WaveTier.OPERATING, "1D"),
        short_wave=wave(120.0, 180.0, "短期交易", WaveTier.EXECUTION, "60min"),
        micro_wave=wave(140.0, 160.0, "执行确认", WaveTier.MICRO, "15min"),
    )


class LocustMultiTimeframeFibIntelligenceTest(unittest.TestCase):
    def test_outputs_four_waves_overlay_probability_buy_and_sell_zones(self):
        result = run_multitimeframe_fib_intelligence(
            MultiTimeframeFibInput(
                symbol="601138.SH",
                current_price=150.0,
                wave_set=wave_set(),
                micro_structure_confirmed=True,
                trend_alignment=True,
            )
        )
        output = multitimeframe_fib_result_to_output(result)

        self.assertEqual(result.decision, MultiTimeframeDecision.BUY)
        self.assertEqual(len(result.waves), 4)
        self.assertEqual(output["Probability Score"]["score"], 100.0)
        self.assertEqual(output["Probability Score"]["weights"]["LONG WAVE"], 40)
        self.assertIsNotNone(output["BUY_ZONE"])
        self.assertEqual(output["BUY_ZONE"]["supporting_waves"], ("LONG WAVE", "MID WAVE", "SHORT WAVE", "MICRO WAVE"))
        self.assertEqual(output["SELL_ZONE"]["LONG WAVE 破位"], 100.0)
        self.assertIn("SHORT WAVE 失效", output["SELL_ZONE"])
        self.assertEqual(set(output.keys()), {
            "Locust Plan V6",
            "LONG WAVE Fib",
            "MID WAVE Fib",
            "SHORT WAVE Fib",
            "MICRO WAVE Fib",
            "Multi-Fib Confluence Zone",
            "Probability Score",
            "BUY_ZONE",
            "SELL_ZONE",
            "Final Advice",
            "Forbidden",
        })
        self.assertEqual(set(output["LONG WAVE Fib"]["fib_levels"].keys()), {"0.236", "0.382", "0.5", "0.618", "0.786", "1.272", "1.618"})

    def test_blocks_trade_without_micro_confirmation_even_when_big_waves_overlap(self):
        result = run_multitimeframe_fib_intelligence(
            MultiTimeframeFibInput(
                symbol="601138.SH",
                current_price=150.0,
                wave_set=wave_set(),
                micro_structure_confirmed=False,
                trend_alignment=True,
            )
        )

        self.assertEqual(result.decision, MultiTimeframeDecision.WAIT)
        self.assertIn("MICRO WAVE 没有执行级确认。", result.reasons)
        self.assertEqual(result.layer_consistency[MultiTimeframeLayer.MICRO], 0.0)

    def test_short_period_cannot_override_long_wave_structure(self):
        result = run_multitimeframe_fib_intelligence(
            MultiTimeframeFibInput(
                symbol="601138.SH",
                current_price=175.0,
                wave_set=wave_set(),
                micro_structure_confirmed=True,
                trend_alignment=True,
            )
        )

        self.assertEqual(result.decision, MultiTimeframeDecision.WAIT)
        self.assertIn("未处于 LONG WAVE 支撑区。", result.reasons)
        self.assertIsNone(result.buy_zone)

    def test_avoid_when_long_wave_breaks(self):
        result = run_multitimeframe_fib_intelligence(
            MultiTimeframeFibInput(
                symbol="601138.SH",
                current_price=95.0,
                wave_set=wave_set(),
                micro_structure_confirmed=True,
                trend_alignment=True,
            )
        )

        self.assertEqual(result.decision, MultiTimeframeDecision.AVOID)
        self.assertEqual(result.reasons, ("LONG WAVE 已破位，清仓级风险。",))

    def test_rejects_unconfirmed_current_price_or_wrong_timeframe_anchor(self):
        with self.assertRaisesRegex(ValueError, "confirmed"):
            run_multitimeframe_fib_intelligence(
                MultiTimeframeFibInput(
                    symbol="601138.SH",
                    current_price=150.0,
                    wave_set=MultiTimeframeWaveSet(
                        long_wave=wave(100.0, 200.0, "长期", WaveTier.PRIMARY, "1W", confirmed=False),
                        mid_wave=wave(80.0, 220.0, "中期", WaveTier.OPERATING, "1D"),
                        short_wave=wave(120.0, 180.0, "短期", WaveTier.EXECUTION, "60min"),
                        micro_wave=wave(140.0, 160.0, "微观", WaveTier.MICRO, "15min"),
                    ),
                    micro_structure_confirmed=True,
                    trend_alignment=True,
                )
            )

        with self.assertRaisesRegex(ValueError, "Current price"):
            run_multitimeframe_fib_intelligence(
                MultiTimeframeFibInput(
                    symbol="601138.SH",
                    current_price=150.0,
                    wave_set=MultiTimeframeWaveSet(
                        long_wave=wave(100.0, 200.0, "长期", WaveTier.PRIMARY, "current_price"),
                        mid_wave=wave(80.0, 220.0, "中期", WaveTier.OPERATING, "1D"),
                        short_wave=wave(120.0, 180.0, "短期", WaveTier.EXECUTION, "60min"),
                        micro_wave=wave(140.0, 160.0, "微观", WaveTier.MICRO, "15min"),
                    ),
                    micro_structure_confirmed=True,
                    trend_alignment=True,
                )
            )

        with self.assertRaisesRegex(ValueError, "MICRO WAVE requires"):
            run_multitimeframe_fib_intelligence(
                MultiTimeframeFibInput(
                    symbol="601138.SH",
                    current_price=150.0,
                    wave_set=MultiTimeframeWaveSet(
                        long_wave=wave(100.0, 200.0, "长期", WaveTier.PRIMARY, "1W"),
                        mid_wave=wave(80.0, 220.0, "中期", WaveTier.OPERATING, "1D"),
                        short_wave=wave(120.0, 180.0, "短期", WaveTier.EXECUTION, "60min"),
                        micro_wave=wave(140.0, 160.0, "微观", WaveTier.MICRO, "60min"),
                    ),
                    micro_structure_confirmed=True,
                    trend_alignment=True,
                )
            )


if __name__ == "__main__":
    unittest.main()
