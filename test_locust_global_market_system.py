import unittest

from fibonacci_wave_system import SwingKind, SwingPoint, TrendDirection, WaveSegment, WaveTier
from locust_global_market_system import (
    DataSource,
    Decision,
    GlobalRiskContext,
    MarketSnapshot,
    MarketType,
    RiskRegime,
    build_market_object,
    build_unified_market_result,
    classify_locust_score,
    classify_risk_score,
    output_trade_decision,
    validate_data_source,
)
from locust_wave_fib_heatmap import LevelKind, PriceReference


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


def confluence_waves():
    return (
        wave(100.0, 200.0, "weekly", WaveTier.PRIMARY, "1W"),
        wave(80.0, 220.0, "daily", WaveTier.OPERATING, "1D"),
    )


class LocustGlobalMarketSystemTest(unittest.TestCase):
    def test_a_share_must_use_akshare_source(self):
        validate_data_source(MarketType.A_SHARE, DataSource.AKSHARE)

        with self.assertRaisesRegex(ValueError, "AKShare"):
            validate_data_source(MarketType.A_SHARE, DataSource.FUTU_OPENAPI)

    def test_global_markets_must_use_futu_or_mcp(self):
        validate_data_source(MarketType.US, DataSource.FUTU_OPENAPI)
        validate_data_source(MarketType.HK, DataSource.MCP_FUTU)

        with self.assertRaisesRegex(ValueError, "Futu"):
            validate_data_source(MarketType.US, DataSource.AKSHARE)

    def test_builds_a_share_market_object_from_akshare(self):
        snapshot = MarketSnapshot(
            symbol="300750.SZ",
            market_type=MarketType.A_SHARE,
            source=DataSource.AKSHARE,
            price=150.0,
            volume=8_000_000,
            trend=78.0,
            volatility=24.0,
            locust_score=82.0,
            risk_score=25.0,
        )

        obj = build_market_object(
            snapshot=snapshot,
            waves=confluence_waves(),
            moving_averages=(PriceReference(LevelKind.MOVING_AVERAGE, "MA60", 150.1),),
            prior_levels=(PriceReference(LevelKind.PRIOR_HIGH, "前高", 150.2),),
        )

        self.assertEqual(obj.symbol, "300750.SZ")
        self.assertEqual(obj.market_type, MarketType.A_SHARE)
        self.assertEqual(obj.data_source, DataSource.AKSHARE)
        self.assertEqual(obj.price, 150.0)
        self.assertEqual(obj.fib_structure.anchor_low, 100.0)
        self.assertEqual(obj.fib_structure.anchor_high, 200.0)
        self.assertGreaterEqual(obj.confluence_score, 55.0)

    def test_a_share_requires_eastmoney_locust_score(self):
        snapshot = MarketSnapshot(
            symbol="600519.SH",
            market_type=MarketType.A_SHARE,
            source=DataSource.AKSHARE,
            price=150.0,
            volume=3_000_000,
            trend=60.0,
            volatility=20.0,
        )

        with self.assertRaisesRegex(ValueError, "LocustScore"):
            build_market_object(snapshot=snapshot, waves=confluence_waves())

    def test_builds_us_market_object_from_futu(self):
        snapshot = MarketSnapshot(
            symbol="NVDA",
            market_type=MarketType.US,
            source=DataSource.FUTU_OPENAPI,
            price=150.0,
            volume=25_000_000,
            trend=88.0,
            volatility=32.0,
        )
        risk_context = GlobalRiskContext(vix=18.0, soxx_trend=82.0, qqq_trend=78.0, gold_trend=45.0, sector_ebb_score=20.0)

        obj = build_market_object(
            snapshot=snapshot,
            waves=confluence_waves(),
            moving_averages=(PriceReference(LevelKind.MOVING_AVERAGE, "MA20", 150.1),),
            global_risk_context=risk_context,
        )

        self.assertEqual(obj.data_source, DataSource.FUTU_OPENAPI)
        self.assertGreater(obj.locust_score, 60)
        self.assertLess(obj.risk_score, 60)

    def test_decision_output_contains_required_trade_fields(self):
        snapshot = MarketSnapshot(
            symbol="NVDA",
            market_type=MarketType.US,
            source=DataSource.FUTU_OPENAPI,
            price=150.0,
            volume=40_000_000,
            trend=92.0,
            volatility=20.0,
            risk_score=20.0,
        )
        obj = build_market_object(
            snapshot=snapshot,
            waves=confluence_waves(),
            moving_averages=(PriceReference(LevelKind.MOVING_AVERAGE, "MA20", 150.1),),
            prior_levels=(PriceReference(LevelKind.PRIOR_HIGH, "previous_high", 150.2),),
        )
        result = build_unified_market_result([obj])
        output = output_trade_decision(result.unified_rank[0])

        self.assertEqual(output["decision"], Decision.BUY.value)
        self.assertEqual(output["price"], 150.0)
        self.assertEqual(output["fib_zone"], "BUY_ZONE")
        self.assertIn("confluence", output)
        self.assertEqual(len(output["buy_points"]), 2)
        self.assertLess(output["stop_loss"], output["price"])
        self.assertGreater(output["take_profit"], output["price"])
        self.assertTrue(output["tradable"])
        self.assertEqual(output["anchor_low"], 100.0)
        self.assertEqual(output["anchor_high"], 200.0)

    def test_unified_result_outputs_top_lists_and_single_ranking(self):
        snapshots = [
            MarketSnapshot("300750.SZ", MarketType.A_SHARE, DataSource.AKSHARE, 150.0, 9_000_000, 82.0, 20.0, 85.0, 20.0),
            MarketSnapshot("000938.SZ", MarketType.A_SHARE, DataSource.AKSHARE, 150.0, 7_000_000, 75.0, 25.0, 76.0, 26.0),
            MarketSnapshot("NVDA", MarketType.US, DataSource.FUTU_OPENAPI, 150.0, 30_000_000, 90.0, 25.0, None, 20.0),
            MarketSnapshot("AMD", MarketType.US, DataSource.FUTU_OPENAPI, 150.0, 22_000_000, 76.0, 30.0, None, 28.0),
            MarketSnapshot("0700.HK", MarketType.HK, DataSource.FUTU_OPENAPI, 150.0, 15_000_000, 72.0, 28.0, None, 35.0),
            MarketSnapshot("9988.HK", MarketType.HK, DataSource.MCP_FUTU, 150.0, 12_000_000, 68.0, 32.0, None, 38.0),
        ]
        objects = [
            build_market_object(
                snapshot=item,
                waves=confluence_waves(),
                moving_averages=(PriceReference(LevelKind.MOVING_AVERAGE, "MA", 150.1),),
                prior_levels=(PriceReference(LevelKind.PRIOR_HIGH, "前高", 150.2),),
            )
            for item in snapshots
        ]

        result = build_unified_market_result(objects)

        self.assertEqual(len(result.a_share_top), 2)
        self.assertEqual(len(result.us_top), 2)
        self.assertEqual(len(result.hk_top), 2)
        self.assertEqual(len(result.unified_rank), 6)
        self.assertGreaterEqual(result.unified_rank[0].final_score, result.unified_rank[-1].final_score)

    def test_rejects_unconfirmed_or_intraday_wave_for_any_market(self):
        snapshot = MarketSnapshot("TSLA", MarketType.US, DataSource.FUTU_OPENAPI, 150.0, 20_000_000, 70.0, 30.0)

        with self.assertRaisesRegex(ValueError, "Unconfirmed"):
            build_market_object(snapshot=snapshot, waves=(wave(100.0, 200.0, "bad", confirmed=False),))

        with self.assertRaisesRegex(ValueError, "Intraday"):
            build_market_object(snapshot=snapshot, waves=(wave(100.0, 200.0, "bad", timeframe="intraday"),))

    def test_score_regimes(self):
        self.assertEqual(classify_locust_score(81).value, "主升")
        self.assertEqual(classify_locust_score(65).value, "趋势")
        self.assertEqual(classify_locust_score(45).value, "震荡")
        self.assertEqual(classify_locust_score(39).value, "退潮")
        self.assertEqual(classify_risk_score(20), RiskRegime.SAFE)
        self.assertEqual(classify_risk_score(45), RiskRegime.NORMAL)
        self.assertEqual(classify_risk_score(70), RiskRegime.RISK)
        self.assertEqual(classify_risk_score(81), RiskRegime.FORBIDDEN)


if __name__ == "__main__":
    unittest.main()
