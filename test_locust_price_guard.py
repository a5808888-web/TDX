from datetime import datetime, timedelta, timezone
import unittest

from locust_price_guard import (
    GuardedPrice,
    KLinePayload,
    MarketData,
    MarketType,
    PriceGuardError,
    PriceGuardLayer,
    PriceSource,
    PriceStatus,
    market_data_to_output,
    price_status,
    validate_market_data,
)


class LocustPriceGuardTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 5, 10, 32, 12, tzinfo=timezone.utc)

    def market_data(self, symbol="601138.SH", market_type=MarketType.A_SHARE, source=PriceSource.AKSHARE, value=51.88):
        return MarketData(
            symbol=symbol,
            market_type=market_type,
            price=GuardedPrice(value=value, source=source, timestamp=self.now),
            volume=1000000,
            kline=KLinePayload("1D", ({"close": value},)),
        )

    def test_a_share_price_must_come_from_akshare(self):
        validate_market_data(self.market_data())
        with self.assertRaisesRegex(PriceGuardError, "AKShare"):
            validate_market_data(self.market_data(source=PriceSource.FUTU))

    def test_global_price_must_come_from_futu(self):
        validate_market_data(self.market_data("US.NVDA", MarketType.GLOBAL, PriceSource.FUTU, 194.83))
        with self.assertRaisesRegex(PriceGuardError, "富途 OpenAPI"):
            validate_market_data(self.market_data("US.NVDA", MarketType.GLOBAL, PriceSource.AKSHARE, 194.83))

    def test_status_delayed_and_data_error(self):
        delayed = GuardedPrice(100.0, PriceSource.FUTU, self.now - timedelta(seconds=181))
        broken = GuardedPrice(None, PriceSource.FUTU, self.now)

        self.assertEqual(price_status(delayed, self.now), PriceStatus.DELAYED)
        self.assertEqual(price_status(broken, self.now), PriceStatus.DATA_ERROR)

    def test_output_uses_market_data_price_contract(self):
        output = market_data_to_output(self.market_data(), self.now)["MarketData"]

        self.assertEqual(output["symbol"], "601138.SH")
        self.assertEqual(output["price"]["value"], 51.88)
        self.assertEqual(output["price"]["source"], "AKShare")
        self.assertEqual(output["price"]["STATUS"], "REALTIME")
        self.assertIn("timestamp", output["price"])

    def test_guard_layer_syncs_every_three_minutes(self):
        calls = []

        def sync_fn():
            calls.append("sync")
            return (self.market_data(),)

        guard = PriceGuardLayer(sync_fn)
        self.assertTrue(guard.should_sync(self.now))
        guard.sync_once(self.now)
        self.assertFalse(guard.should_sync(self.now + timedelta(seconds=179)))
        self.assertTrue(guard.should_sync(self.now + timedelta(seconds=180)))
        self.assertEqual(calls, ["sync"])


if __name__ == "__main__":
    unittest.main()
