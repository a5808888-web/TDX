from datetime import datetime
from datetime import date
import unittest
from zoneinfo import ZoneInfo

from market_state_engine import (
    MarketState,
    determine_a_share_market_state,
    market_state_to_output,
)


CN = ZoneInfo("Asia/Shanghai")


class MarketStateEngineTest(unittest.TestCase):
    def test_live_during_a_share_session(self):
        snapshot = determine_a_share_market_state(datetime(2026, 7, 6, 10, 0, 0, tzinfo=CN))

        self.assertEqual(snapshot.state, MarketState.LIVE)
        self.assertTrue(snapshot.trading_day)
        self.assertTrue(snapshot.market_open)
        self.assertTrue(snapshot.allow_price_update)
        self.assertTrue(snapshot.allow_new_kline)
        self.assertEqual(snapshot.data_source, "AKShare real-time")

    def test_frozen_after_close_uses_freeze_trigger_point(self):
        snapshot = determine_a_share_market_state(datetime(2026, 7, 6, 15, 1, 0, tzinfo=CN))
        output = market_state_to_output(snapshot)["Market State"]

        self.assertEqual(snapshot.state, MarketState.FROZEN)
        self.assertTrue(snapshot.trading_day)
        self.assertTrue(snapshot.market_closed)
        self.assertFalse(snapshot.allow_price_update)
        self.assertFalse(snapshot.allow_new_kline)
        self.assertTrue(snapshot.allow_fib_calculation)
        self.assertEqual(output["reference_time"], "2026-07-06 15:00:00")
        self.assertEqual(output["ui_label"], "FROZEN（收盘）")

    def test_static_on_non_trading_day_uses_last_trading_day_close(self):
        snapshot = determine_a_share_market_state(datetime(2026, 7, 5, 10, 0, 0, tzinfo=CN))
        output = market_state_to_output(snapshot)["Market State"]

        self.assertEqual(snapshot.state, MarketState.STATIC)
        self.assertFalse(snapshot.trading_day)
        self.assertEqual(snapshot.data_source, "last_trading_day_close")
        self.assertEqual(output["reference_time"], "2026-07-03 15:00:00")
        self.assertFalse(snapshot.allow_price_update)
        self.assertFalse(snapshot.allow_new_kline)
        self.assertTrue(snapshot.allow_ai_analysis)
        self.assertTrue(snapshot.allow_fib_calculation)
        self.assertEqual(snapshot.ui_note, "引用历史收盘数据")

    def test_custom_calendar_can_mark_weekday_as_static(self):
        snapshot = determine_a_share_market_state(
            datetime(2026, 7, 6, 10, 0, 0, tzinfo=CN),
            trading_days={date(2026, 7, 3)},
        )

        self.assertEqual(snapshot.state, MarketState.STATIC)
        self.assertFalse(snapshot.allow_price_update)
        self.assertEqual(snapshot.reference_time.strftime("%Y-%m-%d %H:%M:%S"), "2026-07-03 15:00:00")


if __name__ == "__main__":
    unittest.main()
