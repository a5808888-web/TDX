import unittest

from fibonacci_wave_system import (
    BuyPointContext,
    SwingKind,
    SwingPoint,
    TrendDirection,
    WaveSegment,
    WaveTier,
    build_fib_matrix,
    classify_resonance,
    confirmed_swings,
    detect_fib_resonance,
    evaluate_buy_point,
    fib_matrix_to_output,
    is_current_price_in_retracement_zone,
    resonance_to_output,
)


def swing(price, kind, tier=WaveTier.OPERATING, confirmed=True):
    return SwingPoint(
        price=price,
        kind=kind,
        timestamp="2026-07-05",
        timeframe="1D",
        tier=tier,
        confirmed=confirmed,
    )


def operating_wave(low=100.0, high=200.0, name="daily"):
    return WaveSegment(
        low=swing(low, SwingKind.LOW),
        high=swing(high, SwingKind.HIGH),
        tier=WaveTier.OPERATING,
        direction=TrendDirection.UP,
        name=name,
    )


class FibonacciWaveSystemTest(unittest.TestCase):
    def test_builds_complete_fib_matrix_from_confirmed_operating_wave(self):
        matrix = build_fib_matrix(operating_wave(), current_price=150.0)

        self.assertEqual(matrix.anchor_low, 100.0)
        self.assertEqual(matrix.anchor_high, 200.0)
        self.assertEqual(matrix.range, 100.0)
        self.assertEqual(matrix.current_price, 150.0)
        self.assertEqual([level.ratio for level in matrix.retracements], [0.236, 0.382, 0.5, 0.618, 0.786])
        self.assertEqual([level.ratio for level in matrix.extensions], [1.272, 1.414, 1.618])

        retracement_382 = matrix.retracements[1]
        self.assertAlmostEqual(retracement_382.fib_price, 161.8)
        self.assertAlmostEqual(retracement_382.distance_to_current_price, 11.8)

        extension_1618 = matrix.extensions[-1]
        self.assertAlmostEqual(extension_1618.fib_price, 261.8)
        self.assertAlmostEqual(extension_1618.distance_to_current_price, 111.8)

    def test_fib_output_contains_required_matrix_fields(self):
        matrix = build_fib_matrix(operating_wave(), current_price=150.0)
        output = fib_matrix_to_output(matrix)

        self.assertEqual(output["anchor_low"], 100.0)
        self.assertEqual(output["anchor_high"], 200.0)
        self.assertEqual(output["range"], 100.0)
        self.assertEqual(output["current_price"], 150.0)
        self.assertEqual(set(output["retracements"].keys()), {"0.236", "0.382", "0.5", "0.618", "0.786"})
        self.assertEqual(set(output["extensions"].keys()), {"1.272", "1.414", "1.618"})
        self.assertIn("fib_price", output["retracements"]["0.382"])
        self.assertIn("distance_to_current_price", output["retracements"]["0.382"])

    def test_confirmed_swings_only_returns_confirmed_points_for_requested_tier(self):
        swings = [
            swing(200.0, SwingKind.HIGH, tier=WaveTier.PRIMARY, confirmed=True),
            swing(180.0, SwingKind.LOW, tier=WaveTier.PRIMARY, confirmed=False),
            swing(150.0, SwingKind.HIGH, tier=WaveTier.OPERATING, confirmed=True),
        ]

        filtered = confirmed_swings(swings, WaveTier.PRIMARY)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].price, 200.0)

    def test_rejects_execution_wave_for_fibonacci(self):
        wave = WaveSegment(
            low=swing(100.0, SwingKind.LOW, tier=WaveTier.EXECUTION),
            high=swing(200.0, SwingKind.HIGH, tier=WaveTier.EXECUTION),
            tier=WaveTier.EXECUTION,
        )

        with self.assertRaisesRegex(ValueError, "operating wave"):
            build_fib_matrix(wave, current_price=150.0)

    def test_rejects_unconfirmed_anchor(self):
        wave = WaveSegment(
            low=swing(100.0, SwingKind.LOW, confirmed=False),
            high=swing(200.0, SwingKind.HIGH),
            tier=WaveTier.OPERATING,
        )

        with self.assertRaisesRegex(ValueError, "confirmed"):
            build_fib_matrix(wave, current_price=150.0)

    def test_rejects_wrong_anchor_kinds(self):
        wave = WaveSegment(
            low=swing(100.0, SwingKind.HIGH),
            high=swing(200.0, SwingKind.HIGH),
            tier=WaveTier.OPERATING,
        )

        with self.assertRaisesRegex(ValueError, "swing low"):
            build_fib_matrix(wave, current_price=150.0)

    def test_detects_resonance_between_multiple_operating_waves(self):
        first = build_fib_matrix(operating_wave(100.0, 200.0, name="daily"), current_price=150.0)
        second = build_fib_matrix(operating_wave(80.0, 193.2, name="weekly"), current_price=150.0)

        matches = detect_fib_resonance([first, second])
        output = resonance_to_output(matches)
        strong_matches = [match for match in matches if match.strength == "strong"]

        self.assertTrue(strong_matches)
        self.assertTrue(any(item["forms_price_band"] for item in output))
        best = min(strong_matches, key=lambda match: match.delta)
        self.assertLess(abs(best.delta), 0.003)
        self.assertIsNotNone(best.price_band)

    def test_resonance_thresholds(self):
        self.assertEqual(classify_resonance(0.0029), "strong")
        self.assertEqual(classify_resonance(0.003), "medium")
        self.assertEqual(classify_resonance(0.008), "medium")
        self.assertEqual(classify_resonance(0.0081), "none")

    def test_buy_point_requires_all_conditions(self):
        matrix = build_fib_matrix(operating_wave(), current_price=150.0)
        context = BuyPointContext(
            operating_wave_confirmed=True,
            stop_fall_confirmed=True,
            locust_score_supported=True,
            near_intraday_high=False,
        )

        signal = evaluate_buy_point(matrix, context)

        self.assertTrue(is_current_price_in_retracement_zone(matrix))
        self.assertEqual(signal.decision, "buy")
        self.assertEqual(signal.label, "🟢 买点")

    def test_watch_when_price_has_not_pulled_back_or_intraday_high_is_near(self):
        matrix = build_fib_matrix(operating_wave(), current_price=190.0)
        context = BuyPointContext(
            operating_wave_confirmed=True,
            stop_fall_confirmed=True,
            locust_score_supported=True,
            near_intraday_high=True,
        )

        signal = evaluate_buy_point(matrix, context)

        self.assertEqual(signal.decision, "watch")
        self.assertEqual(signal.label, "🟡 观察（等待回踩）")
        self.assertIn("尚未进入 38.2~61.8 回撤区", signal.reasons)
        self.assertIn("接近日内高点", signal.reasons)


if __name__ == "__main__":
    unittest.main()
