import unittest

from fibonacci_wave_system import SwingKind, SwingPoint, TrendDirection, WaveSegment, WaveTier
from locust_wave_fib_heatmap import (
    FinalDecision,
    LevelKind,
    LocustWaveFibHeatmapInput,
    PriceReference,
    WavePattern,
    heatmap_result_to_output,
    identify_confirmed_wave,
    run_wave_fib_confluence_heatmap,
)


def swing(price, kind, tier=WaveTier.OPERATING, timeframe="1D", confirmed=True):
    return SwingPoint(
        price=price,
        kind=kind,
        timestamp="2026-07-05",
        timeframe=timeframe,
        tier=tier,
        confirmed=confirmed,
    )


def wave(low, high, name, tier=WaveTier.OPERATING, timeframe="1D", confirmed=True):
    return WaveSegment(
        low=swing(low, SwingKind.LOW, tier=tier, timeframe=timeframe, confirmed=confirmed),
        high=swing(high, SwingKind.HIGH, tier=tier, timeframe=timeframe, confirmed=confirmed),
        tier=tier,
        direction=TrendDirection.UP,
        name=name,
    )


class LocustWaveFibHeatmapTest(unittest.TestCase):
    def test_outputs_wave_fib_confluence_and_buy_signal(self):
        result = run_wave_fib_confluence_heatmap(
            LocustWaveFibHeatmapInput(
                waves=(
                    wave(100.0, 200.0, "main", WaveTier.PRIMARY, "1W"),
                    wave(80.0, 220.0, "recent", WaveTier.OPERATING, "1D"),
                    wave(132.0, 168.0, "micro", WaveTier.EXECUTION, "60min"),
                ),
                current_price=150.0,
                locust_score=75.0,
                risk_score=20.0,
                moving_averages=(PriceReference(LevelKind.MOVING_AVERAGE, "MA60", 150.1),),
                prior_levels=(PriceReference(LevelKind.PRIOR_HIGH, "previous_high", 150.2),),
            )
        )
        output = heatmap_result_to_output(result)

        self.assertEqual(result.trade_signal.decision, FinalDecision.BUY)
        self.assertEqual(set(output.keys()), {"WaveSegment", "FibMatrix", "ConfluenceZone", "TradeSignal"})
        self.assertEqual(output["WaveSegment"][0]["pattern"], WavePattern.IMPULSE.value)
        self.assertEqual(set(output["FibMatrix"][0]["levels"].keys()), {"0.236", "0.382", "0.5", "0.618", "0.786", "1.272", "1.618"})
        self.assertAlmostEqual(output["FibMatrix"][0]["levels"]["0.5"]["fib_price"], 150.0)
        self.assertTrue(output["ConfluenceZone"])
        self.assertEqual(output["ConfluenceZone"][0]["strength"], "core")
        self.assertEqual(output["ConfluenceZone"][0]["role"], "core")
        self.assertEqual(output["TradeSignal"]["decision"], "BUY")

    def test_watch_when_structure_exists_but_price_not_in_confluence_zone(self):
        result = run_wave_fib_confluence_heatmap(
            LocustWaveFibHeatmapInput(
                waves=(
                    wave(100.0, 200.0, "main", WaveTier.PRIMARY, "1W"),
                    wave(80.0, 220.0, "recent", WaveTier.OPERATING, "1D"),
                    wave(132.0, 168.0, "micro", WaveTier.EXECUTION, "60min"),
                ),
                current_price=170.0,
                locust_score=75.0,
                risk_score=20.0,
            )
        )

        self.assertEqual(result.trade_signal.decision, FinalDecision.WATCH)
        self.assertIn("结构存在，但价格尚未进入共振区", result.trade_signal.reasons)

    def test_avoid_when_risk_is_high(self):
        result = run_wave_fib_confluence_heatmap(
            LocustWaveFibHeatmapInput(
                waves=(
                    wave(100.0, 200.0, "main", WaveTier.PRIMARY, "1W"),
                    wave(80.0, 220.0, "recent", WaveTier.OPERATING, "1D"),
                    wave(132.0, 168.0, "micro", WaveTier.EXECUTION, "60min"),
                ),
                current_price=150.0,
                locust_score=85.0,
                risk_score=80.0,
            )
        )

        self.assertEqual(result.trade_signal.decision, FinalDecision.AVOID)
        self.assertIn("风险过高，禁止开仓", result.trade_signal.reasons)

    def test_sell_when_recent_structure_breaks(self):
        result = run_wave_fib_confluence_heatmap(
            LocustWaveFibHeatmapInput(
                waves=(
                    wave(100.0, 200.0, "main", WaveTier.PRIMARY, "1W"),
                    wave(80.0, 220.0, "recent", WaveTier.OPERATING, "1D"),
                    wave(132.0, 168.0, "micro", WaveTier.EXECUTION, "60min"),
                ),
                current_price=120.0,
                locust_score=75.0,
                risk_score=20.0,
            )
        )

        self.assertEqual(result.trade_signal.decision, FinalDecision.SELL)
        self.assertIn("结构破坏", result.trade_signal.reasons[0])

    def test_rejects_unconfirmed_and_intraday_anchor_waves(self):
        with self.assertRaisesRegex(ValueError, "Unconfirmed"):
            identify_confirmed_wave(wave(100.0, 200.0, "bad", confirmed=False))

        with self.assertRaisesRegex(ValueError, "Intraday"):
            identify_confirmed_wave(wave(100.0, 200.0, "bad", timeframe="intraday"))

    def test_wave_pattern_classification(self):
        self.assertEqual(identify_confirmed_wave(wave(100.0, 104.0, "range")).pattern, WavePattern.RANGE)
        self.assertEqual(identify_confirmed_wave(wave(100.0, 115.0, "trend")).pattern, WavePattern.TREND)
        self.assertEqual(identify_confirmed_wave(wave(100.0, 125.0, "impulse")).pattern, WavePattern.IMPULSE)


if __name__ == "__main__":
    unittest.main()
