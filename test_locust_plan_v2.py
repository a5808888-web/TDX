import unittest

from fibonacci_wave_system import SwingKind, SwingPoint, TrendDirection, WaveSegment, WaveTier
from locust_plan_v2 import (
    CoolingInput,
    GlobalFilterInput,
    LocustPlanInput,
    LocustScoreInput,
    RiskScoreInput,
    TradeState,
    calculate_locust_score,
    calculate_risk_score,
    run_cooling_system,
    run_global_filter,
    run_locust_plan_v2,
)


def swing(price, kind, confirmed=True):
    return SwingPoint(
        price=price,
        kind=kind,
        timestamp="2026-07-05",
        timeframe="1D",
        tier=WaveTier.OPERATING,
        confirmed=confirmed,
    )


def wave(low=100.0, high=200.0, name="daily"):
    return WaveSegment(
        low=swing(low, SwingKind.LOW),
        high=swing(high, SwingKind.HIGH),
        tier=WaveTier.OPERATING,
        direction=TrendDirection.UP,
        name=name,
    )


def healthy_input(**overrides):
    data = {
        "operating_wave": wave(),
        "current_price": 150.0,
        "stop_fall_confirmed": True,
        "near_intraday_high": False,
        "locust_score": LocustScoreInput(
            capital_flow_score=82.0,
            sector_breadth_score=76.0,
            leader_strength_score=78.0,
            volume_confirmation_score=72.0,
        ),
        "risk_score": RiskScoreInput(
            volatility_risk=24.0,
            drawdown_risk=26.0,
            liquidity_risk=20.0,
            event_risk=18.0,
        ),
        "global_filter": GlobalFilterInput(
            us_market_supported=True,
            china_market_supported=True,
            usd_cnh_stable=True,
            vix_safe=True,
        ),
        "cooling": CoolingInput(
            trades_today=0,
            max_trades_per_day=3,
            consecutive_losses=0,
            cooldown_active=False,
        ),
        "comparison_waves": (wave(80.0, 193.2, name="weekly"),),
    }
    data.update(overrides)
    return LocustPlanInput(**data)


class LocustPlanV2Test(unittest.TestCase):
    def test_locust_score_requires_funding_support(self):
        result = calculate_locust_score(
            LocustScoreInput(
                capital_flow_score=45.0,
                sector_breadth_score=70.0,
                leader_strength_score=70.0,
                volume_confirmation_score=70.0,
            )
        )

        self.assertFalse(result.supported)
        self.assertIn("主资金流偏弱", result.reasons)

    def test_risk_score_blocks_high_event_risk(self):
        result = calculate_risk_score(
            RiskScoreInput(
                volatility_risk=30.0,
                drawdown_risk=30.0,
                liquidity_risk=30.0,
                event_risk=80.0,
            )
        )

        self.assertFalse(result.acceptable)
        self.assertIn("事件风险过高", result.reasons)

    def test_global_filter_and_cooling_return_blocking_reasons(self):
        global_result = run_global_filter(
            GlobalFilterInput(
                us_market_supported=False,
                china_market_supported=True,
                usd_cnh_stable=True,
                vix_safe=False,
            )
        )
        cooling_result = run_cooling_system(
            CoolingInput(
                trades_today=3,
                max_trades_per_day=3,
                consecutive_losses=2,
                cooldown_active=False,
            )
        )

        self.assertFalse(global_result.passed)
        self.assertIn("美股环境不支持", global_result.reasons)
        self.assertFalse(cooling_result.allowed)
        self.assertIn("今日交易次数已达上限", cooling_result.reasons)

    def test_full_plan_outputs_buy_with_position_when_all_modules_align(self):
        result = run_locust_plan_v2(healthy_input())

        self.assertEqual(result.decision, "buy")
        self.assertEqual(result.label, "🟢 买点")
        self.assertEqual(result.state, TradeState.READY_TO_BUY)
        self.assertGreater(result.position.position_pct, 0.0)
        self.assertTrue(result.locust_score.supported)
        self.assertTrue(result.risk_score.acceptable)
        self.assertTrue(result.global_filter.passed)
        self.assertTrue(result.cooling.allowed)
        self.assertTrue(any(match.strength == "strong" for match in result.resonance))

    def test_full_plan_blocks_when_global_or_cooling_rules_fail(self):
        result = run_locust_plan_v2(
            healthy_input(
                global_filter=GlobalFilterInput(
                    us_market_supported=True,
                    china_market_supported=False,
                    usd_cnh_stable=True,
                    vix_safe=True,
                ),
                cooling=CoolingInput(
                    trades_today=3,
                    max_trades_per_day=3,
                    consecutive_losses=0,
                    cooldown_active=False,
                ),
            )
        )

        self.assertEqual(result.decision, "blocked")
        self.assertEqual(result.label, "⛔ 暂停交易")
        self.assertEqual(result.state, TradeState.BLOCKED_BY_RISK)
        self.assertEqual(result.position.position_pct, 0.0)
        self.assertIn("中概/A股环境不支持", result.reasons)
        self.assertIn("今日交易次数已达上限", result.reasons)

    def test_full_plan_watches_when_price_has_not_entered_fib_zone(self):
        result = run_locust_plan_v2(healthy_input(current_price=190.0))

        self.assertEqual(result.decision, "watch")
        self.assertEqual(result.state, TradeState.WAITING_FOR_PULLBACK)
        self.assertEqual(result.position.position_pct, 0.0)
        self.assertIn("尚未进入 38.2~61.8 回撤区", result.reasons)


if __name__ == "__main__":
    unittest.main()
