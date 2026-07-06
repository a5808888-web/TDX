from datetime import datetime, timedelta, timezone
import unittest

from locust_realtime_verification import (
    DataSourceTag,
    OpenApiState,
    PricePayload,
    RefreshStatus,
    RealTimeSyncEngine,
    SYNC_INTERVAL_SECONDS,
    build_data_sync_status_panel,
    build_verified_stock_data,
    sync_status_to_output,
    verified_stock_to_output,
    verify_price_refresh,
)


class LocustRealtimeVerificationTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 5, 10, 32, 12, tzinfo=timezone.utc)
        self.last_sync = self.now - timedelta(seconds=10)

    def price(self, value=100.0, source=DataSourceTag.AKSHARE, seconds_after_last_sync=1):
        return PricePayload(
            value=value,
            source=source,
            timestamp=self.last_sync + timedelta(seconds=seconds_after_last_sync),
        )

    def test_realtime_requires_timestamp_after_last_sync(self):
        self.assertEqual(verify_price_refresh(self.price(), self.last_sync, self.now), RefreshStatus.REALTIME)

    def test_delayed_and_stale_detection(self):
        delayed_price = PricePayload(100.0, DataSourceTag.FUTU, self.now - timedelta(seconds=120))
        stale_price = PricePayload(100.0, DataSourceTag.FUTU, self.now - timedelta(seconds=360))

        self.assertEqual(verify_price_refresh(delayed_price, self.now, self.now), RefreshStatus.DELAYED)
        self.assertEqual(verify_price_refresh(stale_price, self.now, self.now), RefreshStatus.STALE)

    def test_verified_stock_output_contains_required_v5_fields(self):
        item = build_verified_stock_data(
            stock_name="英伟达",
            symbol="US.NVDA",
            price=self.price(source=DataSourceTag.FUTU),
            last_sync_time=self.last_sync,
            fib_zone="BUY_ZONE",
            confluence_layers=3,
            buy_point_1=190.123,
            buy_point_2=198.456,
            stop_loss=184.4,
            take_profit=220.8,
            locust_score=82,
            risk_score=24,
            now=self.now,
        )
        output = verified_stock_to_output(item)

        self.assertEqual(output["股票"], "英伟达")
        self.assertEqual(output["价格（实时）"]["source"], "Futu")
        self.assertEqual(output["数据来源"], "Futu")
        self.assertEqual(output["是否刷新"], "REALTIME")
        self.assertIn("更新时间", output)
        self.assertIn("买点1", output)
        self.assertIn("买点2", output)
        self.assertIn("止损", output)
        self.assertIn("止盈", output)

    def test_stale_stock_is_tagged_as_stale(self):
        stale_price = PricePayload(100.0, DataSourceTag.AKSHARE, self.now - timedelta(seconds=360))
        item = build_verified_stock_data(
            stock_name="工业富联",
            symbol="601138",
            price=stale_price,
            last_sync_time=self.now,
            fib_zone="NEUTRAL_ZONE",
            confluence_layers=2,
            buy_point_1=95,
            buy_point_2=104,
            stop_loss=91,
            take_profit=115,
            locust_score=60,
            risk_score=40,
            now=self.now,
        )

        self.assertEqual(item.refresh_status, RefreshStatus.STALE)
        self.assertEqual(item.data_source_tag, DataSourceTag.STALE)

    def test_data_sync_status_panel_outputs_akshare_futu_and_ai_status(self):
        ashare_price = self.price(source=DataSourceTag.AKSHARE)
        futu_price = self.price(source=DataSourceTag.FUTU)
        panel = build_data_sync_status_panel((ashare_price,), (futu_price,), ai_deepseek_ok=True, now=self.now)
        output = sync_status_to_output(panel)["DATA SYNC STATUS PANEL"]

        self.assertEqual(output["A股数据状态（AKShare）"]["是否连接"], "YES")
        self.assertEqual(output["A股数据状态（AKShare）"]["是否实时更新"], "NO")
        self.assertEqual(output["全球数据状态（Futu）"]["OpenAPI状态"], OpenApiState.RUNNING.value)
        self.assertEqual(output["AI策略状态"]["Codex运行状态"], "RUNNING")
        self.assertEqual(output["AI策略状态"]["DeepSeek调用状态"], "OK")
        self.assertEqual(output["市场状态"]["state"], "STATIC")
        self.assertEqual(output["市场状态"]["ui_note"], "引用历史收盘数据")
        self.assertEqual(output["sync_interval"], SYNC_INTERVAL_SECONDS)
        self.assertFalse(output["System"]["3-minute sync active"])

    def test_sync_engine_runs_every_three_minutes(self):
        calls = []

        def sync_fn():
            calls.append("sync")
            return ()

        engine = RealTimeSyncEngine(sync_fn)
        self.assertTrue(engine.should_sync(self.now))
        engine.sync_once(self.now)
        self.assertFalse(engine.should_sync(self.now + timedelta(seconds=179)))
        self.assertTrue(engine.should_sync(self.now + timedelta(seconds=180)))

        self.assertEqual(calls, ["sync"])

    def test_rejects_missing_price_metadata(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            build_verified_stock_data(
                stock_name="测试",
                symbol="TEST",
                price=PricePayload(1.0, DataSourceTag.AKSHARE, datetime(2026, 7, 5, 10, 0, 0)),
                last_sync_time=self.last_sync,
                fib_zone="BUY_ZONE",
                confluence_layers=2,
                buy_point_1=1,
                buy_point_2=2,
                stop_loss=0.9,
                take_profit=3,
                locust_score=50,
                risk_score=30,
            )


if __name__ == "__main__":
    unittest.main()
