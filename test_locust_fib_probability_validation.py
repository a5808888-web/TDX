import unittest

from fibonacci_wave_system import SwingKind, SwingPoint, TrendDirection, WaveSegment, WaveTier
from locust_fib_probability_validation import (
    FibProbabilityValidationInput,
    FibReaction,
    ProbabilityDecision,
    PriceBar,
    WaveSet,
    fib_probability_result_to_output,
    run_fib_probability_validation,
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
    return WaveSet(
        primary_wave=wave(100.0, 200.0, "主波段", WaveTier.PRIMARY, "1W"),
        secondary_wave=wave(80.0, 220.0, "中波段", WaveTier.OPERATING, "1D"),
        micro_wave=wave(120.0, 180.0, "小波段", WaveTier.EXECUTION, "60min"),
    )


def high_probability_prices():
    return (
        PriceBar("2026-06-20", 150.3, 149.7, 149.9),
        PriceBar("2026-06-21", 156.0, 153.0, 154.0),
        PriceBar("2026-06-22", 150.2, 149.6, 149.8),
        PriceBar("2026-06-23", 155.0, 152.0, 154.2),
        PriceBar("2026-06-24", 150.1, 149.5, 149.7),
        PriceBar("2026-06-25", 149.0, 145.5, 146.0),
    )


def mixed_reaction_prices():
    return (
        PriceBar("2026-06-20", 150.3, 149.7, 149.9),
        PriceBar("2026-06-21", 156.0, 153.0, 154.0),
        PriceBar("2026-06-22", 150.2, 149.6, 149.8),
        PriceBar("2026-06-23", 149.0, 145.5, 146.0),
        PriceBar("2026-06-24", 150.3, 149.7, 150.2),
        PriceBar("2026-06-25", 149.0, 147.5, 148.0),
        PriceBar("2026-06-26", 150.2, 149.8, 150.0),
        PriceBar("2026-06-27", 150.3, 149.9, 150.1),
    )


class LocustFibProbabilityValidationTest(unittest.TestCase):
    def test_outputs_multi_wave_probability_scores_and_highest_buy_zone(self):
        result = run_fib_probability_validation(
            FibProbabilityValidationInput(
                wave_set=wave_set(),
                historical_prices=high_probability_prices(),
                risk_score=28,
                trend_alignment=True,
            )
        )
        output = fib_probability_result_to_output(result)

        self.assertEqual(result.decision, ProbabilityDecision.BUY)
        self.assertEqual(len(result.waves), 3)
        self.assertIn("0.5 accuracy", output["Fib Probability Score"]["primary_wave"])
        self.assertGreater(output["Fib Probability Score"]["primary_wave"]["0.5 accuracy"], 70)
        self.assertIsNotNone(output["BUY_ZONE"])
        self.assertGreater(output["BUY_ZONE"]["probability_score"], 70)
        self.assertEqual(len(output["BUY_ZONE"]["supporting_waves"]), 3)
        self.assertGreaterEqual(output["Confluence Zone"][0]["ConfluenceScore"], 200)

    def test_records_touch_events_with_required_reaction_types(self):
        result = run_fib_probability_validation(
            FibProbabilityValidationInput(
                wave_set=wave_set(),
                historical_prices=mixed_reaction_prices(),
                risk_score=28,
                trend_alignment=True,
            )
        )
        primary = result.waves[0]
        half_level = next(level for level in primary.fib_levels if level.ratio == 0.5)
        reactions = {event.reaction for event in half_level.touch_events}

        self.assertIn(FibReaction.BOUNCE, reactions)
        self.assertIn(FibReaction.REJECTION, reactions)
        self.assertIn(FibReaction.BREAK, reactions)
        self.assertIn(FibReaction.CONSOLIDATION, reactions)
        self.assertEqual(half_level.total_touches, 4)
        self.assertEqual(half_level.successful_reactions, 2)
        self.assertEqual(half_level.accuracy, 50.0)

    def test_blocks_buy_when_risk_or_trend_filter_fails(self):
        risky = run_fib_probability_validation(
            FibProbabilityValidationInput(
                wave_set=wave_set(),
                historical_prices=high_probability_prices(),
                risk_score=45,
                trend_alignment=True,
            )
        )
        no_trend = run_fib_probability_validation(
            FibProbabilityValidationInput(
                wave_set=wave_set(),
                historical_prices=high_probability_prices(),
                risk_score=28,
                trend_alignment=False,
            )
        )

        self.assertEqual(risky.decision, ProbabilityDecision.WATCH)
        self.assertEqual(no_trend.decision, ProbabilityDecision.WATCH)
        self.assertIn("风险分不低于40。", risky.reasons)
        self.assertIn("趋势未对齐。", no_trend.reasons)

    def test_rejects_unconfirmed_intraday_or_too_short_history(self):
        with self.assertRaisesRegex(ValueError, "confirmed"):
            run_fib_probability_validation(
                FibProbabilityValidationInput(
                    wave_set=WaveSet(
                        primary_wave=wave(100, 200, "主", WaveTier.PRIMARY, "1W", confirmed=False),
                        secondary_wave=wave(80, 220, "中", WaveTier.OPERATING, "1D"),
                        micro_wave=wave(120, 180, "小", WaveTier.EXECUTION, "60min"),
                    ),
                    historical_prices=high_probability_prices(),
                    risk_score=28,
                    trend_alignment=True,
                )
            )

        with self.assertRaisesRegex(ValueError, "at least 3"):
            run_fib_probability_validation(
                FibProbabilityValidationInput(
                    wave_set=wave_set(),
                    historical_prices=high_probability_prices()[:2],
                    risk_score=28,
                    trend_alignment=True,
                )
            )


if __name__ == "__main__":
    unittest.main()
