import unittest

from fibonacci_wave_system import SwingKind, SwingPoint, TrendDirection, WaveSegment, WaveTier
from locust_fib_hypothesis_system import (
    FibHypothesisSystemInput,
    HypothesisLayer,
    PriceBar,
    ZoneType,
    fib_hypothesis_result_to_output,
    run_fib_hypothesis_system,
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


def historical_prices():
    return (
        PriceBar("2026-06-20", 151.0, 149.6, 150.1),
        PriceBar("2026-06-21", 156.0, 151.2, 155.0),
        PriceBar("2026-06-22", 150.4, 149.5, 149.8),
        PriceBar("2026-06-23", 149.0, 145.2, 146.0),
        PriceBar("2026-06-24", 139.0, 137.6, 138.4),
        PriceBar("2026-06-25", 143.0, 139.0, 142.5),
        PriceBar("2026-06-26", 167.0, 166.1, 166.5),
        PriceBar("2026-06-27", 164.0, 160.0, 161.0),
    )


class LocustFibHypothesisSystemTest(unittest.TestCase):
    def test_builds_three_hypothesis_waves_and_accuracy_scores(self):
        result = run_fib_hypothesis_system(sample_input())
        output = fib_hypothesis_result_to_output(result)

        self.assertEqual([item.layer for item in result.hypothesis_waves], [HypothesisLayer.MAIN, HypothesisLayer.MID, HypothesisLayer.SMALL])
        self.assertEqual(set(output["FibAccuracyScore"].keys()), {"main_weekly", "mid_daily", "small_60min"})
        self.assertGreater(output["FibAccuracyScore"]["main_weekly"], 0)
        self.assertGreater(output["FibAccuracyScore"]["mid_daily"], 0)
        self.assertGreater(output["FibAccuracyScore"]["small_60min"], 0)
        self.assertIn("HypothesisWave", output)

    def test_detects_statistical_confluence_and_primary_buy_zone(self):
        result = run_fib_hypothesis_system(sample_input())

        self.assertTrue(result.confluence_zones)
        best = result.confluence_zones[0]
        self.assertGreaterEqual(best.overlap_count, 3)
        self.assertLess((best.zone_high - best.zone_low) / ((best.zone_high + best.zone_low) / 2), 0.005)
        self.assertTrue(result.primary_buy_zones)
        self.assertEqual(result.primary_buy_zones[0].zone_type, ZoneType.PRIMARY_BUY_ZONE)
        self.assertGreaterEqual(result.primary_buy_zones[0].confidence_score, 70)

    def test_outputs_secondary_or_invalid_zones_for_unverified_fibs(self):
        result = run_fib_hypothesis_system(sample_input())
        output = fib_hypothesis_result_to_output(result)
        invalid = output["OptimalEntryZone"]["无效Fib区"]

        self.assertTrue(invalid)
        self.assertTrue(all(item["zone_type"] == "INVALID_FIB_ZONE" for item in invalid))
        self.assertTrue(all("禁止作为单一斐波买点" in item["reasons"] for item in invalid))

    def test_rejects_unconfirmed_and_current_price_anchor(self):
        with self.assertRaisesRegex(ValueError, "confirmed"):
            run_fib_hypothesis_system(
                FibHypothesisSystemInput(
                    main_wave=wave(100, 200, "main", WaveTier.PRIMARY, "1W", confirmed=False),
                    mid_wave=wave(80, 220, "mid", WaveTier.OPERATING, "1D"),
                    small_wave=wave(120, 180, "small", WaveTier.EXECUTION, "60min"),
                    historical_prices=historical_prices(),
                )
            )

        with self.assertRaisesRegex(ValueError, "Current price"):
            run_fib_hypothesis_system(
                FibHypothesisSystemInput(
                    main_wave=wave(100, 200, "main", WaveTier.PRIMARY, "current_price"),
                    mid_wave=wave(80, 220, "mid", WaveTier.OPERATING, "1D"),
                    small_wave=wave(120, 180, "small", WaveTier.EXECUTION, "60min"),
                    historical_prices=historical_prices(),
                )
            )

    def test_rejects_wrong_timeframe_for_hypothesis_layer(self):
        with self.assertRaisesRegex(ValueError, "small_60min"):
            run_fib_hypothesis_system(
                FibHypothesisSystemInput(
                    main_wave=wave(100, 200, "main", WaveTier.PRIMARY, "1W"),
                    mid_wave=wave(80, 220, "mid", WaveTier.OPERATING, "1D"),
                    small_wave=wave(120, 180, "small", WaveTier.EXECUTION, "1D"),
                    historical_prices=historical_prices(),
                )
            )


def sample_input():
    return FibHypothesisSystemInput(
        main_wave=wave(100.0, 200.0, "主波段", WaveTier.PRIMARY, "1W"),
        mid_wave=wave(80.0, 220.0, "中波段", WaveTier.OPERATING, "1D"),
        small_wave=wave(120.0, 180.0, "小波段", WaveTier.EXECUTION, "60min"),
        historical_prices=historical_prices(),
    )


if __name__ == "__main__":
    unittest.main()
