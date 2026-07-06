from datetime import datetime, timedelta, timezone
import unittest

from ashare_data_layer import (
    AStockKLine,
    AStockPrice,
    AStockSource,
    AStockValidationStatus,
    EastmoneyFlow,
    astock_data_to_output,
    build_astock_data,
)


class AShareDataLayerTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 5, 10, 32, 12, tzinfo=timezone.utc)

    def test_builds_astock_data_from_akshare_and_eastmoney(self):
        item = build_astock_data(
            symbol="601138.SH",
            price=AStockPrice(51.88, AStockSource.AKSHARE, self.now),
            volume=1234567,
            kline=AStockKLine(AStockSource.AKSHARE, ({"close": 51.88},)),
            flow=EastmoneyFlow(sector_flow=88, capital_flow=66, reference_price=51.9, timestamp=self.now),
            now=self.now,
        )
        output = astock_data_to_output(item)["AStockData"]

        self.assertEqual(output["price"]["source"], "AKShare")
        self.assertEqual(output["kline"]["source"], "AKShare")
        self.assertEqual(output["sector_flow"]["source"], "Eastmoney")
        self.assertEqual(output["capital_flow"]["source"], "Eastmoney")
        self.assertEqual(output["validation"]["status"], "REALTIME")

    def test_price_cross_check_warns_when_akshare_and_eastmoney_diverge(self):
        item = build_astock_data(
            symbol="601138.SH",
            price=AStockPrice(100.0, AStockSource.AKSHARE, self.now),
            volume=1,
            kline=AStockKLine(AStockSource.AKSHARE, ({"close": 100.0},)),
            flow=EastmoneyFlow(sector_flow=1, capital_flow=1, reference_price=100.4, timestamp=self.now),
            now=self.now,
        )

        self.assertEqual(item.validation.status, AStockValidationStatus.DATA_WARNING)
        self.assertGreater(item.validation.price_deviation, 0.003)

    def test_delayed_after_sixty_seconds(self):
        item = build_astock_data(
            symbol="601138.SH",
            price=AStockPrice(100.0, AStockSource.AKSHARE, self.now - timedelta(seconds=61)),
            volume=1,
            kline=AStockKLine(AStockSource.AKSHARE, ({"close": 100.0},)),
            flow=EastmoneyFlow(sector_flow=1, capital_flow=1, reference_price=100.0, timestamp=self.now),
            now=self.now,
        )

        self.assertEqual(item.validation.status, AStockValidationStatus.DELAYED)

    def test_rejects_non_akshare_price_or_non_eastmoney_flow(self):
        with self.assertRaisesRegex(ValueError, "AKShare"):
            build_astock_data(
                symbol="601138.SH",
                price=AStockPrice(100.0, AStockSource.EASTMONEY, self.now),
                volume=1,
                kline=AStockKLine(AStockSource.AKSHARE, ({"close": 100.0},)),
                flow=EastmoneyFlow(sector_flow=1, capital_flow=1, reference_price=100.0, timestamp=self.now),
                now=self.now,
            )


if __name__ == "__main__":
    unittest.main()
