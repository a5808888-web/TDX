import sys
import types
import unittest
from unittest.mock import Mock, patch

from locust_global_market_system import DataSource, MarketType
from market_data_connectors import (
    AKShareMarketConnector,
    AShareQuery,
    EastmoneyFlowConnector,
    FutuOpenDConnector,
    FutuQuery,
)


class MarketDataConnectorsTest(unittest.TestCase):
    def test_akshare_connector_builds_a_share_snapshot_from_realtime_quote(self):
        def spot_fetcher():
            return [{"代码": "300750", "最新价": "150.25", "成交量": "1234567"}]

        connector = AKShareMarketConnector(spot_fetcher=spot_fetcher)
        snapshot = connector.fetch_snapshot(AShareQuery(symbol="300750.SZ", set_code=0, trend=80.0, volatility=22.0))

        self.assertEqual(snapshot.market_type, MarketType.A_SHARE)
        self.assertEqual(snapshot.source, DataSource.AKSHARE)
        self.assertEqual(snapshot.price, 150.25)
        self.assertEqual(snapshot.volume, 1234567.0)

    def test_akshare_connector_builds_bulk_snapshot_map_with_per_symbol_errors(self):
        def spot_fetcher():
            return [
                {"代码": "300750", "最新价": "150.25", "成交量": "1234567"},
                {"代码": "600000", "最新价": "9.25", "成交量": "456"},
            ]

        connector = AKShareMarketConnector(spot_fetcher=spot_fetcher)
        snapshots, errors = connector.fetch_snapshot_map(
            (
                AShareQuery(symbol="300750.SZ", set_code=0, trend=80.0, volatility=22.0),
                AShareQuery(symbol="000003.SZ", set_code=0, trend=20.0, volatility=80.0),
            )
        )

        self.assertEqual(snapshots["300750.SZ"].price, 150.25)
        self.assertIn("000003.SZ", errors)

    def test_akshare_connector_retries_sina_spot_fetch(self):
        fake_module = types.SimpleNamespace()
        calls = {"count": 0}

        def stock_zh_a_spot():
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("temporary decode error")
            return [{"代码": "sh601689", "最新价": "61.85", "成交量": "26757696"}]

        fake_module.stock_zh_a_spot = stock_zh_a_spot
        fake_module.stock_zh_a_spot_em = Mock(side_effect=RuntimeError("eastmoney unavailable"))

        with patch.dict(sys.modules, {"akshare": fake_module}), patch("market_data_connectors.time.sleep"):
            snapshot = AKShareMarketConnector().fetch_snapshot(
                AShareQuery(symbol="601689.SH", set_code=0, trend=50.0, volatility=30.0)
            )

        self.assertEqual(snapshot.price, 61.85)
        self.assertEqual(calls["count"], 2)

    def test_akshare_connector_falls_back_to_single_symbol_sina_quote(self):
        fake_module = types.SimpleNamespace(
            stock_zh_a_spot=Mock(side_effect=RuntimeError("full market unavailable")),
            stock_zh_a_spot_em=Mock(side_effect=RuntimeError("eastmoney unavailable")),
        )

        with (
            patch.dict(sys.modules, {"akshare": fake_module}),
            patch("market_data_connectors.time.sleep"),
            patch(
                "market_data_connectors._fetch_sina_quote_payload",
                return_value=[{"代码": "sh601689", "最新价": "61.85", "成交量": "26757696"}],
            ),
        ):
            snapshot = AKShareMarketConnector().fetch_snapshot(
                AShareQuery(symbol="601689.SH", set_code=0, trend=50.0, volatility=30.0)
            )

        self.assertEqual(snapshot.price, 61.85)
        self.assertEqual(snapshot.volume, 26757696.0)

    def test_akshare_strategy_snapshot_adds_eastmoney_fund_flow_score(self):
        def spot_fetcher():
            return [{"代码": "300750", "最新价": "150", "成交量": "1000000"}]

        def flow_fetcher(symbol, period):
            return {"data": {"主力净流入": "50000000"}}

        connector = AKShareMarketConnector(
            spot_fetcher=spot_fetcher,
            eastmoney_connector=EastmoneyFlowConnector(flow_fetcher=flow_fetcher),
        )
        snapshot = connector.fetch_strategy_snapshot(AShareQuery(symbol="300750.SZ", set_code=0, trend=80.0, volatility=22.0))

        self.assertEqual(snapshot.source, DataSource.AKSHARE)
        self.assertEqual(snapshot.locust_score, 65.0)
        self.assertEqual(snapshot.risk_score, 22.0)

    def test_eastmoney_fund_flow_score_handles_outflow(self):
        connector = EastmoneyFlowConnector(flow_fetcher=lambda symbol, period: {"主力净流入": "-30000000"})

        self.assertEqual(connector.fetch_fund_flow_score("300750.SZ"), 47.0)

    def test_futu_connector_builds_global_snapshot_from_opend(self):
        fake_module = types.SimpleNamespace()
        fake_module.RET_OK = 0

        class FakeRow:
            def to_dict(self):
                return {"last_price": 150.5, "volume": 9876543}

        class FakeFrame:
            @property
            def iloc(self):
                return [FakeRow()]

        class FakeQuoteContext:
            def __init__(self, host, port):
                self.host = host
                self.port = port

            def get_market_snapshot(self, symbols):
                return fake_module.RET_OK, FakeFrame()

            def close(self):
                return None

        fake_module.OpenQuoteContext = FakeQuoteContext

        with patch.dict(sys.modules, {"futu": fake_module}):
            snapshot = FutuOpenDConnector().fetch_snapshot(
                FutuQuery(symbol="US.NVDA", market_type=MarketType.US, trend=90.0, volatility=28.0)
            )

        self.assertEqual(snapshot.symbol, "US.NVDA")
        self.assertEqual(snapshot.market_type, MarketType.US)
        self.assertEqual(snapshot.source, DataSource.FUTU_OPENAPI)
        self.assertEqual(snapshot.price, 150.5)
        self.assertEqual(snapshot.volume, 9876543.0)


if __name__ == "__main__":
    unittest.main()
