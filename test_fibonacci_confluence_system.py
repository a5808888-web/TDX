import unittest

from fibonacci_wave_system import (
    ConfluenceSignalContext,
    SwingKind,
    SwingPoint,
    TrendDirection,
    WaveSegment,
    WaveTier,
    build_fibonacci_confluence_system,
    fibonacci_confluence_to_output,
    validate_market_data_source,
)


def swing(price, kind, tier, timeframe="1D", confirmed=True):
    return SwingPoint(
        price=price,
        kind=kind,
        timestamp="2026-07-05",
        timeframe=timeframe,
        tier=tier,
        confirmed=confirmed,
    )


def wave(low, high, tier, name, low_timeframe="1D", high_timeframe="1D"):
    return WaveSegment(
        low=swing(low, SwingKind.LOW, tier, timeframe=low_timeframe),
        high=swing(high, SwingKind.HIGH, tier, timeframe=high_timeframe),
        tier=tier,
        direction=TrendDirection.UP,
        name=name,
    )


def healthy_context(**overrides):
    data = {
        "volume_confirmed": True,
        "near_intraday_high": False,
        "locust_score_supported": True,
    }
    data.update(overrides)
    return ConfluenceSignalContext(**data)


class FibonacciConfluenceSystemTest(unittest.TestCase):
    def test_outputs_three_layer_fib_price_matrix(self):
        result = build_fibonacci_confluence_system(
            main_wave=wave(100.0, 200.0, WaveTier.PRIMARY, "weekly", "1W", "1W"),
            recent_wave=wave(105.0, 180.0, WaveTier.OPERATING, "daily"),
            micro_wave=wave(120.0, 168.0, WaveTier.EXECUTION, "60min", "60min", "60min"),
            current_price=150.0,
            context=healthy_context(),
        )
        output = fibonacci_confluence_to_output(result)

        self.assertEqual(output["main_wave"]["anchor_low"], 100.0)
        self.assertEqual(output["main_wave"]["anchor_high"], 200.0)
        self.assertEqual(set(output["main_wave"]["levels"].keys()), {"0.236", "0.382", "0.5", "0.618", "0.786", "1.272"})
        self.assertAlmostEqual(output["main_wave"]["levels"]["0.382"]["fib_price"], 161.8)
        self.assertAlmostEqual(output["main_wave"]["levels"]["1.272"]["fib_price"], 72.8)

    def test_generates_confluence_zone_from_different_wave_fibs(self):
        result = build_fibonacci_confluence_system(
            main_wave=wave(100.0, 200.0, WaveTier.PRIMARY, "weekly", "1W", "1W"),
            recent_wave=wave(80.0, 220.0, WaveTier.OPERATING, "daily"),
            micro_wave=wave(132.0, 168.0, WaveTier.EXECUTION, "60min", "60min", "60min"),
            current_price=150.0,
            context=healthy_context(),
        )

        best_zone = result.confluence_zones[0]

        self.assertGreaterEqual(best_zone.overlap_count, 3)
        self.assertEqual(best_zone.strength, "strong")
        self.assertLessEqual(best_zone.price_range[1] - best_zone.price_range[0], 0.5)
        self.assertGreaterEqual(len({point.wave_layer for point in best_zone.involved_fibs}), 2)

    def test_allows_buy_only_inside_retracement_and_active_confluence_zone(self):
        result = build_fibonacci_confluence_system(
            main_wave=wave(100.0, 200.0, WaveTier.PRIMARY, "weekly", "1W", "1W"),
            recent_wave=wave(80.0, 220.0, WaveTier.OPERATING, "daily"),
            micro_wave=wave(132.0, 168.0, WaveTier.EXECUTION, "60min", "60min", "60min"),
            current_price=150.0,
            context=healthy_context(),
        )

        self.assertEqual(result.signal.decision, "buy")
        self.assertEqual(result.signal.label, "🟢 买点")

    def test_watches_when_single_fib_or_volume_is_missing(self):
        result = build_fibonacci_confluence_system(
            main_wave=wave(100.0, 200.0, WaveTier.PRIMARY, "weekly", "1W", "1W"),
            recent_wave=wave(70.0, 190.0, WaveTier.OPERATING, "daily"),
            micro_wave=wave(130.0, 170.0, WaveTier.EXECUTION, "60min", "60min", "60min"),
            current_price=150.0,
            context=healthy_context(volume_confirmed=False),
        )

        self.assertEqual(result.signal.decision, "watch")
        self.assertEqual(result.signal.label, "🟡 观察，不生成买点")
        self.assertIn("缺少成交量确认", result.signal.reasons)

    def test_rejects_unconfirmed_wave_and_intraday_high_anchor(self):
        unconfirmed_recent = WaveSegment(
            low=swing(80.0, SwingKind.LOW, WaveTier.OPERATING),
            high=swing(220.0, SwingKind.HIGH, WaveTier.OPERATING, confirmed=False),
            tier=WaveTier.OPERATING,
        )
        with self.assertRaisesRegex(ValueError, "Unconfirmed"):
            build_fibonacci_confluence_system(
                main_wave=wave(100.0, 200.0, WaveTier.PRIMARY, "weekly", "1W", "1W"),
                recent_wave=unconfirmed_recent,
                micro_wave=wave(140.0, 168.0, WaveTier.EXECUTION, "60min", "60min", "60min"),
                current_price=150.0,
                context=healthy_context(),
            )

        with self.assertRaisesRegex(ValueError, "Intraday high"):
            build_fibonacci_confluence_system(
                main_wave=wave(100.0, 200.0, WaveTier.PRIMARY, "weekly", "1W"),
                recent_wave=wave(80.0, 220.0, WaveTier.OPERATING, "daily", high_timeframe="intraday"),
                micro_wave=wave(140.0, 168.0, WaveTier.EXECUTION, "60min", "60min", "60min"),
                current_price=150.0,
                context=healthy_context(),
            )

    def test_validates_market_data_source_rules(self):
        validate_market_data_source("a_share", "akshare")
        validate_market_data_source("global", "futu_api")
        validate_market_data_source("tradingview", "tradingview")

        with self.assertRaisesRegex(ValueError, "a_share data"):
            validate_market_data_source("a_share", "tradingview")


if __name__ == "__main__":
    unittest.main()
