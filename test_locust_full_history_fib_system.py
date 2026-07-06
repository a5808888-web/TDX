import unittest

from fibonacci_wave_system import SwingKind, SwingPoint, TrendDirection, WaveSegment, WaveTier
from locust_full_history_fib_system import (
    FullHistoryDecision,
    FullHistoryFibInput,
    LifecycleStage,
    full_history_fib_to_output,
    run_full_history_fib_system,
)


class LocustFullHistoryFibSystemTest(unittest.TestCase):
    def test_outputs_global_anchor_lifecycle_layers_and_buy_signal(self):
        result = run_full_history_fib_system(sample_input())
        output = full_history_fib_to_output(result)

        self.assertEqual(result.global_anchor.ipo_low, 50.0)
        self.assertEqual(result.global_anchor.all_time_high, 250.0)
        self.assertEqual(result.global_anchor.all_time_low, 50.0)
        self.assertEqual(result.global_anchor.full_history_range, 200.0)
        self.assertEqual(tuple(item.stage for item in result.segment_fibs), tuple(LifecycleStage))
        self.assertEqual(set(output["Global Fib"]["fib_levels"].keys()), {"0.236", "0.382", "0.5", "0.618", "0.786", "1.272", "1.618"})
        self.assertIn("Segment Fib", output)
        self.assertIn("Mid Fib", output)
        self.assertIn("Short Fib", output)
        self.assertIn("Micro Fib", output)
        self.assertEqual(output["Time Weights"]["Global Fib"], 40)
        self.assertEqual(output["Time Weights"]["Segment Fib"], 30)
        self.assertEqual(output["Time Weights"]["Mid Fib"], 20)
        self.assertEqual(output["Time Weights"]["Short Fib"], 10)
        self.assertTrue(output["Confluence Zone"])
        self.assertGreaterEqual(result.probability_score, 70)
        self.assertEqual(result.decision, FullHistoryDecision.BUY)

    def test_waits_without_segment_confluence_volume_or_short_confirmation(self):
        no_short = run_full_history_fib_system(
            FullHistoryFibInput(
                symbol="601138.SH",
                current_price=150.0,
                history=sample_history(),
                mid_wave=wave(80, 220, WaveTier.OPERATING, "1D"),
                short_wave=wave(120, 180, WaveTier.EXECUTION, "60min"),
                micro_wave=wave(140, 160, WaveTier.MICRO, "15min"),
                short_stop_fall_confirmed=False,
                volume_supported=False,
            )
        )

        self.assertEqual(no_short.decision, FullHistoryDecision.WAIT)
        self.assertIn("Short Fib未确认止跌。", no_short.reasons)
        self.assertIn("成交量不支持。", no_short.reasons)

    def test_avoids_when_global_structure_breaks(self):
        broken = run_full_history_fib_system(
            FullHistoryFibInput(
                symbol="601138.SH",
                current_price=40.0,
                history=sample_history(),
                mid_wave=wave(80, 220, WaveTier.OPERATING, "1D"),
                short_wave=wave(120, 180, WaveTier.EXECUTION, "60min"),
                micro_wave=wave(140, 160, WaveTier.MICRO, "15min"),
                short_stop_fall_confirmed=True,
                volume_supported=True,
            )
        )

        self.assertEqual(broken.decision, FullHistoryDecision.AVOID)
        self.assertIn("Global Fib结构已破", broken.reasons[0])

    def test_rejects_short_history_unconfirmed_and_current_price_anchor(self):
        with self.assertRaisesRegex(ValueError, "at least 10 bars"):
            run_full_history_fib_system(
                FullHistoryFibInput(
                    symbol="601138.SH",
                    current_price=150.0,
                    history=sample_history()[:5],
                    mid_wave=wave(80, 220, WaveTier.OPERATING, "1D"),
                    short_wave=wave(120, 180, WaveTier.EXECUTION, "60min"),
                    micro_wave=wave(140, 160, WaveTier.MICRO, "15min"),
                    short_stop_fall_confirmed=True,
                    volume_supported=True,
                )
            )
        with self.assertRaisesRegex(ValueError, "confirmed anchors"):
            run_full_history_fib_system(
                FullHistoryFibInput(
                    symbol="601138.SH",
                    current_price=150.0,
                    history=sample_history(),
                    mid_wave=wave(80, 220, WaveTier.OPERATING, "1D", confirmed=False),
                    short_wave=wave(120, 180, WaveTier.EXECUTION, "60min"),
                    micro_wave=wave(140, 160, WaveTier.MICRO, "15min"),
                    short_stop_fall_confirmed=True,
                    volume_supported=True,
                )
            )
        with self.assertRaisesRegex(ValueError, "forbids current price"):
            run_full_history_fib_system(
                FullHistoryFibInput(
                    symbol="601138.SH",
                    current_price=150.0,
                    history=sample_history(),
                    mid_wave=wave(80, 220, WaveTier.OPERATING, "current_price"),
                    short_wave=wave(120, 180, WaveTier.EXECUTION, "60min"),
                    micro_wave=wave(140, 160, WaveTier.MICRO, "15min"),
                    short_stop_fall_confirmed=True,
                    volume_supported=True,
                )
            )


def sample_input():
    return FullHistoryFibInput(
        symbol="601138.SH",
        current_price=150.0,
        history=sample_history(),
        mid_wave=wave(80, 220, WaveTier.OPERATING, "1D"),
        short_wave=wave(120, 180, WaveTier.EXECUTION, "60min"),
        micro_wave=wave(140, 160, WaveTier.MICRO, "15min"),
        short_stop_fall_confirmed=True,
        volume_supported=True,
    )


def sample_history():
    from locust_full_history_fib_system import HistoryBar

    return (
        HistoryBar("IPO-01", 80.0, 50.0, 70.0, 100.0),
        HistoryBar("IPO-02", 100.0, 60.0, 90.0, 120.0),
        HistoryBar("GROWTH-01", 200.0, 100.0, 150.0, 150.0),
        HistoryBar("GROWTH-02", 180.0, 120.0, 150.0, 180.0),
        HistoryBar("IMPULSE-01", 220.0, 80.0, 150.0, 230.0),
        HistoryBar("IMPULSE-02", 210.0, 90.0, 150.0, 260.0),
        HistoryBar("CORRECTION-01", 180.0, 120.0, 150.0, 210.0),
        HistoryBar("CORRECTION-02", 170.0, 130.0, 150.0, 190.0),
        HistoryBar("RESTART-01", 250.0, 130.0, 150.0, 260.0),
        HistoryBar("RESTART-02", 200.0, 140.0, 170.0, 310.0),
    )


def wave(low, high, tier, timeframe, confirmed=True):
    return WaveSegment(
        low=SwingPoint(low, SwingKind.LOW, "2026-01-01", timeframe, tier, confirmed),
        high=SwingPoint(high, SwingKind.HIGH, "2026-06-01", timeframe, tier, confirmed),
        tier=tier,
        direction=TrendDirection.UP,
        name=f"{timeframe}-wave",
    )


if __name__ == "__main__":
    unittest.main()
