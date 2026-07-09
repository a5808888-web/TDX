import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import app
from app import LocustDashboardHandler


class LocustV5UIContractTest(unittest.TestCase):
    def test_trading_cockpit_contains_data_status_mount_points(self):
        html = Path("trading_cockpit.html").read_text(encoding="utf-8")
        js = Path("trading_cockpit.js").read_text(encoding="utf-8")
        css = Path("trading_cockpit.css").read_text(encoding="utf-8")

        self.assertIn("dataStatusPanel", html)
        self.assertIn("syncCountdown", html)
        self.assertIn("anchorModePanel", html)
        self.assertIn("anchorModeState", html)
        self.assertIn("data-manual-sync", js)
        self.assertIn("topActionRow", js)
        self.assertIn("手动一键同步", js)
        self.assertIn("斐波那契专业页", js)
        self.assertIn("force=1", js)
        self.assertIn("select option", css)
        self.assertIn(".anchor-input option", css)
        self.assertIn("#111827", css)
        self.assertIn("#2563eb", css)
        self.assertIn("topStatusBar", html)
        self.assertIn("bottom-actions", html)
        self.assertIn("institutionPanel", html)
        self.assertIn("机构资金流", html)
        self.assertIn("corePoolPanel", html)
        self.assertIn("长期核心推荐池", html)
        self.assertIn("oneClickExecutionPanel", html)
        self.assertIn("今日交易决策", html)
        self.assertIn("交易包", html)
        self.assertIn("<details", html)
        self.assertIn("同步中", html)
        self.assertIn("正在连接 AKShare", html)
        self.assertIn("等待原始价格", html)
        self.assertIn("renderBootState", js)
        self.assertIn("renderSyncFailure", js)
        self.assertIn("行情同步异常", js)
        self.assertIn("decision-hero", js)
        self.assertIn("market-state-row", js)
        self.assertIn("risk-strip", js)
        self.assertIn("当前动作", js)
        self.assertIn("今日总判断", js)
        self.assertIn("热力图下钻树状系统", js)
        self.assertIn("HEATMAP_UI_STATE_SCHEMA", js)
        self.assertIn("UI_STATE = { level: 1 | 2 | 3 | 4, selected_sector, selected_subsector, selected_stock }", js)
        self.assertIn("全球热力图树", js)
        self.assertIn("A股热力图树", js)
        self.assertIn("loadHeatmapLevelData", js)
        self.assertIn("destroyHeatmapLayerRender", js)
        self.assertIn("setHeatmapUiState", js)
        self.assertIn("data-heatmap-drill", js)
        self.assertIn("data-heatmap-back", js)
        self.assertIn("第1层", js)
        self.assertIn("第2层", js)
        self.assertIn("第3层", js)
        self.assertIn("第4层", js)
        self.assertIn("独占模式", js)
        self.assertIn("市场结论", js)
        self.assertIn("热度评分", js)
        self.assertIn("资金方向", js)
        self.assertIn("industry-treemap", js)
        self.assertIn("treemap-tile", js)
        self.assertIn("selectedHeatmapTimeframe", js)
        self.assertIn("resampleByTimeframe", js)
        self.assertIn("applyMarketHeatmapLinkage", js)
        self.assertIn("斐波那契权重+20%", js)
        self.assertIn("禁止进入推荐池", js)
        self.assertIn("人形机器人 / 具身智能", js)
        self.assertIn("人工智能服务器", js)
        self.assertIn("光通信 / CPO / 光模块", js)
        self.assertIn("电力 / 电网 / 电力设备 / 电算协同", js)
        self.assertIn("存储 / 半导体存储 / DRAM / NAND", js)
        self.assertIn("锂电 / 储能 / 新能源电池", js)
        self.assertIn("医药 / 创新药 / 医疗器械", js)
        self.assertIn("消费 / 食品饮料 / 可选消费", js)
        self.assertIn("有色金属 / 黄金 / 铜", js)
        self.assertIn("工业自动化 / 制造业升级", js)
        self.assertIn("低估值红利 / 银行 / 保险 / 公用事业", js)
        self.assertIn("sectorFrameworks", js)
        self.assertIn("产业链结构", js)
        self.assertIn("展开价值链", js)
        self.assertIn("订单/量产/技术", js)
        self.assertIn("humanoidCostTree", js)
        self.assertIn("HumanoidScore", js)
        self.assertIn("renderHumanoidRobotCockpit", js)
        self.assertIn("执行器", js)
        self.assertIn("减速器", js)
        self.assertIn("丝杠", js)
        self.assertIn("传感器", js)
        self.assertIn("控制器", js)
        self.assertIn("结构件", js)
        self.assertIn("calculateHeatScore", js)
        self.assertIn("classifyHeatStatus", js)
        self.assertIn("账户执行区", js)
        self.assertIn("SYNC_INTERVAL_SECONDS = 180", js)
        self.assertIn("price:", js)
        self.assertIn("timestamp", js)
        self.assertIn("verifyRefreshStatus", js)
        self.assertIn("sourceTagForPrice", js)
        self.assertIn("stockFields.buyPoint1", js)
        self.assertIn("stockFields.stopLoss", js)
        self.assertIn("analyzeSignalsWithAI", js)
        self.assertIn("buildAutonomousAIAnalysis", js)
        self.assertIn("renderAIAnalysis", js)
        self.assertIn("institutionalBlueprints", js)
        self.assertIn("renderInstitutionalFlowPanel", js)
        self.assertIn("全球机构", js)
        self.assertIn("中国机构", js)
        self.assertIn("A股映射机会", js)
        self.assertIn("资金流入：斐波那契买点可信度+20%", js)
        self.assertIn("资金流出：斐波那契买点失效概率+30%", js)
        self.assertIn("buildEquityHierarchy", js)
        self.assertIn("applyEquityHierarchy", js)
        self.assertIn("renderEquityHierarchy", js)
        self.assertIn("股票分级体系", js)
        self.assertIn("龙头股", js)
        self.assertIn("中军股", js)
        self.assertIn("趋势股", js)
        self.assertIn("补涨股", js)
        self.assertIn("禁买股", js)
        self.assertIn("斐波那契优先级", js)
        self.assertIn("是否假龙头", js)
        self.assertIn("buildTopCoreEquityPool", js)
        self.assertIn("renderTopCoreEquityPool", js)
        self.assertIn("长期核心推荐池", js)
        self.assertIn("buildOneClickTradingPackage", js)
        self.assertIn("renderOneClickExecutionSystem", js)
        self.assertIn("buildLuckyZoneSystem", js)
        self.assertIn("renderLuckyZoneSystem", js)
        self.assertIn("buildDynamicRecalculationSnapshot", js)
        self.assertIn("buildDynamicChangeLog", js)
        self.assertIn("renderDynamicChangeLog", js)
        self.assertIn("dynamicRecalculationPipeline", js)
        self.assertIn("全系统动态同步更新机制", js)
        self.assertIn("推荐已更新", js)
        self.assertIn("动态重算日志", html)
        self.assertIn("changeLogPanel", html)
        self.assertIn("幸运区核心资产", html)
        self.assertIn("luckyZonePanel", html)
        self.assertIn("幸运区 > 龙头 > 中军 > 趋势", js)
        self.assertIn("是否进入幸运区", js)
        self.assertIn("不频繁交易 / 只做回撤买点 / 长期持有为主 / 斐波那契作为加仓点", js)
        self.assertIn("一键导出同花顺", js)
        self.assertIn("龙头股池", js)
        self.assertIn("中军股池", js)
        self.assertIn("趋势股池", js)
        self.assertIn("今日买点表", js)
        self.assertIn("tonghuashun_watchlist", js)
        self.assertIn("tonghuashun_execution", js)
        self.assertIn("/api/one-click-trading-package", Path("app.py").read_text(encoding="utf-8"))
        self.assertIn("/api/lucky-zone-system", Path("app.py").read_text(encoding="utf-8"))
        self.assertIn("/api/dynamic-recalculation-sample", Path("app.py").read_text(encoding="utf-8"))
        self.assertIn("/exports/tonghuashun_watchlist.txt", Path("app.py").read_text(encoding="utf-8"))
        self.assertIn("/exports/tonghuashun_execution.csv", Path("app.py").read_text(encoding="utf-8"))
        self.assertIn("核心评分 = 0.3×机构资金 + 0.2×板块热力 + 0.2×斐波那契结构 + 0.2×智能分析 + 0.1×龙头属性", js)
        self.assertIn("产业属性", js)
        self.assertIn("交易状态", js)
        self.assertIn("核心推荐", js)
        self.assertIn("大中军", js)
        self.assertIn("/api/top-core-equity-sample", Path("app.py").read_text(encoding="utf-8"))
        self.assertIn("aiAnalysis.deepseek", js)
        self.assertIn("buildAnchorState", js)
        self.assertIn("manualAnchorByName", js)
        self.assertIn("renderAnchorModePanel", js)
        self.assertIn("ACCOUNT_HOLDINGS", js)
        self.assertIn("buildFibonacciSignals", js)
        self.assertIn("Fibonacci Master System", js)
        self.assertIn("标准化多工具斐波那契量化引擎", js)
        self.assertIn("共振评分", js)
        self.assertIn("三重共振", js)
        self.assertIn("fetchFibonacciMaster", js)
        self.assertIn("renderFibonacciKline", js)
        self.assertIn("601689.SH", js)
        self.assertIn("000977.SZ", js)
        self.assertIn("FIBONACCI_MEASUREMENT_SYMBOLS", js)
        self.assertIn("东阳光", js)
        self.assertIn("600673.SH", js)
        fib_html = Path("fibonacci_quant.html").read_text(encoding="utf-8")
        fib_css = Path("fibonacci_quant.css").read_text(encoding="utf-8")
        fib_js = Path("fibonacci_quant.js").read_text(encoding="utf-8")
        self.assertIn("table-column", fib_html)
        self.assertIn("table-column", fib_css)
        self.assertIn("align-items: stretch", fib_css)
        self.assertIn("#aiPanel", fib_css)
        self.assertIn("#riskTable", fib_css)
        self.assertIn("flex: 1 1 auto", fib_css)
        self.assertIn("manualAnchorPanel", fib_html)
        self.assertIn("manual-anchor-card", fib_css)
        self.assertIn("applyManualAnchor", fib_js)
        self.assertIn("manual_anchor_wave", fib_js)
        self.assertIn("手动主波段回撤0.786", fib_js)
        self.assertIn("riskRewardRow", fib_js)
        self.assertIn("findWinRateStat", fib_js)
        self.assertIn("样本不足", fib_js)
        self.assertIn("table-scroll", fib_js)
        self.assertIn("table-scroll", fib_css)
        self.assertIn("#riskTable table", fib_css)
        self.assertIn("white-space: nowrap", fib_css)
        self.assertIn("buildOverlayLabelPlacements", fib_js)
        self.assertIn("label-guide", fib_js)
        self.assertIn("label-guide", fib_css)
        self.assertIn("buildAiOneLineSummary", fib_js)
        self.assertIn("ai-summary-card", fib_js)
        self.assertIn("-webkit-line-clamp: 3", fib_css)
        self.assertIn("300308.SZ", fib_html)
        self.assertIn("601899.SH", fib_html)
        self.assertIn("手动一键同步", fib_html)
        self.assertIn("force=1", fib_js)
        self.assertIn("600673.SH", Path("fibonacci_quant.html").read_text(encoding="utf-8"))
        self.assertIn("fibonacci_quant.html", Path("trading_cockpit.html").read_text(encoding="utf-8"))
        self.assertIn("/api/fibonacci-master", Path("fibonacci_quant.js").read_text(encoding="utf-8"))
        self.assertIn("K线图与斐波那契价格轴", Path("fibonacci_quant.js").read_text(encoding="utf-8"))
        self.assertIn("buildMultiTimeframeFibView", js)
        self.assertIn("renderMultiTimeframeFibSummary", js)
        self.assertIn("Multi-Timeframe Fibonacci Intelligence System", js)
        self.assertIn("多周期斐波智能", js)
        self.assertIn("概率融合分", js)
        self.assertIn("/api/full-history-fib-sample", Path("app.py").read_text(encoding="utf-8"))
        self.assertIn("syncMarketDataFromSources", js)
        self.assertIn("buildMarketState", js)
        self.assertIn("静态（非交易日）", js)
        self.assertIn("冻结（收盘）", js)
        self.assertIn("实时（交易中）", js)
        self.assertIn("引用历史收盘数据", js)
        self.assertIn("allowNewKline", js)
        self.assertIn("locked.price.value", js)
        self.assertIn("fetchLockedMarketData", js)
        self.assertIn("/api/locked-market-data", js)
        self.assertIn("assertPriceLock", js)
        self.assertIn("PRICE MISMATCH", js)
        self.assertIn("raw_price", js)
        self.assertIn("api_price", js)
        self.assertIn("ui_price", js)
        self.assertIn("diff", js)
        self.assertIn("AKShare", js)
        self.assertIn("Eastmoney", js)
        self.assertIn("东方财富资金 / AKShare成交量", js)
        old_source_name = "\u56fd\u4fe1 " + "".join(["S", "k", "i", "l", "l"])
        old_price_error = "A股价格必须来自" + "".join(["S", "k", "i", "l", "l"])
        self.assertNotIn(old_source_name, js)
        self.assertNotIn(old_price_error, js)
        self.assertNotIn("buildRealtimePrice", js)
        self.assertNotIn("previousPriceByName", js)
        self.assertNotIn("basePriceForName", js)
        self.assertNotIn("readPriceFromSource", js)
        self.assertNotIn("sourceBasePrice", js)
        self.assertIn("data-status-grid", css)
        self.assertIn("anchor-mode-grid", css)
        self.assertIn("refresh-realtime", css)
        self.assertIn("ai-analysis-module", css)
        self.assertIn("top-status-bar", css)
        self.assertIn("decision-value", css)
        self.assertIn("market-state-card", css)
        self.assertIn("risk-strip", css)
        self.assertIn("heat-score-row", css)
        self.assertIn("industry-treemap", css)
        self.assertIn("heatmap-state-bar", css)
        self.assertIn("heatmap-tree-split", css)
        self.assertIn("heatmap-exclusive-layer", css)
        self.assertIn("heatmap-drill-card", css)
        self.assertIn("heatmap-stock-button", css)
        self.assertIn("institution-card", css)
        self.assertIn("core-pool-card", css)
        self.assertIn("core-score-row", css)
        self.assertIn("lucky-zone-card", css)
        self.assertIn("lucky-zone-rule", css)
        self.assertIn("change-log-card", css)
        self.assertIn("pipeline-grid", css)
        self.assertIn("one-click-card", css)
        self.assertIn("execution-summary-grid", css)
        self.assertIn("one-click-export-button", css)
        self.assertIn("equity-hierarchy-module", css)
        self.assertIn("equity-tier-card", css)
        self.assertIn("timeframe-pill", css)
        self.assertIn("tile-strong", css)
        self.assertIn("hot-strong", css)
        self.assertIn("hot-mid", css)
        self.assertIn("hot-cold", css)
        self.assertIn("mobile-cockpit", css)
        self.assertIn("bottom-actions", css)

    def test_mobile_ui_avoids_forbidden_english_labels(self):
        html = Path("trading_cockpit.html").read_text(encoding="utf-8")
        js = Path("trading_cockpit.js").read_text(encoding="utf-8")
        visible_text = html + "\n" + js

        self.assertNotIn("MARKET STATUS", visible_text)
        self.assertNotIn("TRADE SIGNALS", visible_text)
        self.assertNotIn("EXECUTION PANEL", visible_text)

    def test_app_realtime_sample_api_shape(self):
        payload = _call_handler_json("/api/realtime-sample")
        first = payload["stocks"][0]

        self.assertIn("股票", first)
        self.assertIn("价格（实时）", first)
        self.assertIn("更新时间", first)
        self.assertIn("数据来源", first)
        self.assertIn("是否刷新", first)
        self.assertIn("timestamp", first["价格（实时）"])
        self.assertIn("source", first["价格（实时）"])

    def test_app_sync_status_api_shape(self):
        payload = _call_handler_json("/api/sync-status")
        panel = payload["DATA SYNC STATUS PANEL"]

        self.assertIn("A股数据状态（AKShare）", panel)
        self.assertIn("全球数据状态（Futu）", panel)
        self.assertIn("AI策略状态", panel)
        self.assertIn("市场状态", panel)
        self.assertIn(panel["市场状态"]["state"], {"LIVE", "FROZEN", "STATIC"})
        self.assertEqual(panel["sync_interval"], 180)
        self.assertIn("OpenAPI状态", panel["全球数据状态（Futu）"])

    def test_app_market_state_api_shape(self):
        payload = _call_handler_json("/api/market-state")
        state = payload["Market State"]

        self.assertIn(state["state"], {"LIVE", "FROZEN", "STATIC"})
        self.assertIn("reference_time", state)
        self.assertIn("allow_price_update", state)
        self.assertIn("allow_new_kline", state)
        self.assertTrue(state["allow_ai_analysis"])
        self.assertTrue(state["allow_fib_calculation"])

    def test_app_locked_market_data_api_shape(self):
        class FakeSnapshot:
            price = 64.72
            volume = 130129724

        fake_connector = Mock()
        fake_connector.fetch_snapshot_map.return_value = ({"601138.SH": FakeSnapshot()}, {})

        app._LOCKED_MARKET_CACHE = None
        app._LOCKED_MARKET_CACHE_AT = None
        with patch("app.A_SHARE_COCKPIT_SYMBOLS", ("601138.SH",)), patch("app.AKShareMarketConnector", return_value=fake_connector):
            payload = _call_handler_json("/api/locked-market-data")

        item = payload["items"]["601138.SH"]
        self.assertEqual(payload["source_policy"]["A股"], "AKShare")
        self.assertEqual(item["price"]["value"], 64.72)
        self.assertEqual(item["price"]["raw_price"], 64.72)
        self.assertEqual(item["price"]["api_price"], 64.72)
        self.assertEqual(item["price"]["ui_price"], 64.72)
        self.assertEqual(item["price"]["diff"], 0)
        self.assertEqual(item["price_lock"], "LOCKED")

    def test_app_locked_market_data_force_refresh_bypasses_cache(self):
        class FakeSnapshot:
            volume = 130129724

            def __init__(self, price):
                self.price = price

        fake_connector = Mock()
        fake_connector.fetch_snapshot_map.side_effect = [
            ({"601138.SH": FakeSnapshot(64.72)}, {}),
            ({"601138.SH": FakeSnapshot(65.88)}, {}),
        ]

        app._LOCKED_MARKET_CACHE = None
        app._LOCKED_MARKET_CACHE_AT = None
        with patch("app.A_SHARE_COCKPIT_SYMBOLS", ("601138.SH",)), patch("app.AKShareMarketConnector", return_value=fake_connector):
            first = _call_handler_json("/api/locked-market-data")
            second = _call_handler_json("/api/locked-market-data?force=1")

        self.assertEqual(first["items"]["601138.SH"]["price"]["value"], 64.72)
        self.assertEqual(second["items"]["601138.SH"]["price"]["value"], 65.88)
        self.assertTrue(second["manual_refresh"])

    def test_app_humanoid_robot_module_api_shape(self):
        payload = _call_handler_json("/api/humanoid-robot-module")

        self.assertEqual(payload["module_name"], "蝗虫计划 · 人形机器人产业链模块")
        self.assertEqual(payload["sector_name"], "人形机器人 / 具身智能")
        self.assertIn("cost_structure", payload)
        self.assertIn("subsector_heatmap", payload)
        self.assertIn("stock_pool", payload)
        self.assertIn("top_picks", payload)
        self.assertTrue(all(item["source_name"] for item in payload["cost_structure"]))
        self.assertTrue(all("humanoid_score" in item for item in payload["stock_pool"]))

    def test_app_sector_framework_api_shape(self):
        payload = _call_handler_json("/api/sector-framework")
        framework = payload["Locust Sector Framework"]
        first = framework["sectors"][0]

        self.assertEqual(framework["sector_count"], 11)
        self.assertIn("产业链结构", first)
        self.assertIn("Module Value Chain", first)
        self.assertIn("选股池三层", first)
        self.assertIn("Fibonacci分析", framework["required_sections"])

    def test_app_ai_analysis_sample_api_shape(self):
        payload = _call_handler_json("/api/ai-analysis-sample")
        first = next(iter(payload["stocks"].values()))

        self.assertIn("deepseek_view", first)
        self.assertIn("doubao_view", first)
        self.assertIn("merged_view", first)
        self.assertIn(first["decision"], {"BUY", "WAIT", "AVOID"})
        self.assertGreaterEqual(first["confidence"], 0)
        self.assertLessEqual(first["confidence"], 100)

    def test_app_anchor_intelligence_sample_api_shape(self):
        payload = _call_handler_json("/api/anchor-intelligence-sample")
        mode = payload["FIBONACCI ANCHOR MODE"]

        self.assertIn("AI Anchor", mode)
        self.assertIn("Manual Anchor", mode)
        self.assertIn("Active Anchor", mode)
        self.assertIn(mode["anchor_source"], {"ai", "manual", "ai_provisional"})
        self.assertIn("FibMatrix", payload)
        self.assertIn("TradeLevels", payload)

    def test_app_fib_hypothesis_sample_api_shape(self):
        payload = _call_handler_json("/api/fib-hypothesis-sample")

        self.assertIn("HypothesisWave", payload)
        self.assertIn("FibAccuracyScore", payload)
        self.assertIn("ConfluenceZone", payload)
        self.assertIn("OptimalEntryZone", payload)
        self.assertIn("高概率买点区", payload["OptimalEntryZone"])
        self.assertIn("无效Fib区", payload["OptimalEntryZone"])

    def test_app_fib_probability_sample_api_shape(self):
        payload = _call_handler_json("/api/fib-probability-sample")

        self.assertIn("Wave Set", payload)
        self.assertIn("Fib Probability Score", payload)
        self.assertIn("Confluence Zone", payload)
        self.assertIn("BUY_ZONE", payload)
        self.assertIn("Trade Rule", payload)
        self.assertIn("0.5 accuracy", payload["Fib Probability Score"]["primary_wave"])
        self.assertGreater(payload["BUY_ZONE"]["probability_score"], 70)
        self.assertGreaterEqual(len(payload["BUY_ZONE"]["supporting_waves"]), 2)
        self.assertEqual(payload["Trade Rule"]["decision"], "BUY")

    def test_app_multitimeframe_fib_sample_api_shape(self):
        payload = _call_handler_json("/api/multitimeframe-fib-sample")

        self.assertEqual(payload["Locust Plan V6"], "Multi-Timeframe Fibonacci Intelligence System")
        self.assertIn("LONG WAVE Fib", payload)
        self.assertIn("MID WAVE Fib", payload)
        self.assertIn("SHORT WAVE Fib", payload)
        self.assertIn("MICRO WAVE Fib", payload)
        self.assertIn("Multi-Fib Confluence Zone", payload)
        self.assertIn("Probability Score", payload)
        self.assertIn("BUY_ZONE", payload)
        self.assertIn("SELL_ZONE", payload)
        self.assertEqual(payload["Probability Score"]["weights"]["LONG WAVE"], 40)
        self.assertEqual(payload["Final Advice"]["decision"], "BUY")

    def test_app_full_history_fib_sample_api_shape(self):
        payload = _call_handler_json("/api/full-history-fib-sample")

        self.assertEqual(payload["Locust Plan V7"], "Full History Market Structure System + Multi-Layer Fibonacci Engine + Lifecycle Decomposition Model + Probability Confluence System")
        self.assertIn("Global Anchor", payload)
        self.assertEqual(payload["Global Anchor"]["ipo_low"], 50.0)
        self.assertEqual(payload["Global Anchor"]["all_time_high"], 250.0)
        self.assertEqual(len(payload["Lifecycle Segments"]), 5)
        self.assertIn("IPO阶段", [item["stage"] for item in payload["Lifecycle Segments"]])
        self.assertIn("Global Fib", payload)
        self.assertIn("Segment Fib", payload)
        self.assertIn("Mid Fib", payload)
        self.assertIn("Short Fib", payload)
        self.assertIn("Micro Fib", payload)
        self.assertEqual(payload["Time Weights"]["Global Fib"], 40)
        self.assertEqual(payload["Time Weights"]["Segment Fib"], 30)
        self.assertEqual(payload["Time Weights"]["Mid Fib"], 20)
        self.assertEqual(payload["Time Weights"]["Short Fib"], 10)
        self.assertTrue(payload["Confluence Zone"])
        self.assertEqual(payload["Trade Rule"]["decision"], "BUY")
        self.assertTrue(payload["Forbidden"]["禁止忽略IPO结构"])

    def test_app_market_heatmap_sample_api_shape(self):
        payload = _call_handler_json("/api/market-heatmap-sample")
        first = payload["行业热力图矩阵"][0]

        self.assertIn("Market Heatmap System", payload)
        self.assertEqual(payload["sync_interval"], 180)
        self.assertIn("timeframe", payload)
        self.assertIn("Global Heatmap", payload)
        self.assertIn("联动结果", payload)
        self.assertIn("heat_score", first)
        self.assertIn("capital_flow_direction", first)
        self.assertIn("leader_stock", first)
        self.assertIn("tradable", first)
        self.assertIn("Fib权重", payload["联动结果"])
        self.assertTrue(payload["UI规则"]["Treemap"])

    def test_app_institutional_flow_sample_api_shape(self):
        payload = _call_handler_json("/api/institutional-flow-sample")
        first_global = payload["全球机构动向"][0]

        self.assertIn("Institution Module", payload)
        self.assertEqual(payload["sync_interval"], 180)
        self.assertIn("全球机构动向", payload)
        self.assertIn("中国机构动向", payload)
        self.assertIn("行业资金流变化", payload)
        self.assertIn("逻辑解释（Why）", payload)
        self.assertIn("A股映射机会", payload)
        self.assertIn("Top 3可交易标的", payload)
        self.assertIn("Fib买点", payload)
        self.assertIn("reason_analysis", first_global)
        self.assertIn("a_share_mapping", first_global)
        self.assertIn("Fib联动", first_global)

    def test_app_equity_hierarchy_sample_api_shape(self):
        payload = _call_handler_json("/api/equity-hierarchy-sample")

        self.assertIn("Equity Hierarchy System", payload)
        self.assertIn("HeatScore", payload)
        self.assertIn("LocustScore", payload)
        self.assertIn("RiskScore", payload)
        self.assertIn("🟢 龙头股", payload)
        self.assertIn("🟡 中军股", payload)
        self.assertIn("🔵 趋势股", payload)
        self.assertIn("⚪ 补涨股", payload)
        self.assertIn("🔴 禁买股", payload)
        self.assertTrue(payload["🟢 龙头股"])
        self.assertTrue(payload["🔴 禁买股"])
        self.assertIn("Fib绑定", payload["🟢 龙头股"][0])
        self.assertIn("DeepSeek判断", payload["🟢 龙头股"][0])
        self.assertIn("豆包判断", payload["🟢 龙头股"][0])

    def test_app_top_core_equity_sample_api_shape(self):
        payload = _call_handler_json("/api/top-core-equity-sample")
        first = payload["长期核心推荐池"][0]

        self.assertIn("核心优质股票推荐引擎", payload)
        self.assertEqual(payload["首页唯一入口"], "长期核心推荐池")
        self.assertIn("核心评分公式", payload)
        self.assertIn("股票名称", first)
        self.assertIn(first["产业属性"], {"龙头", "大中军"})
        self.assertIn("资金状态", first)
        self.assertIn("斐波那契结构", first)
        self.assertIn("智能分析结论", first)
        self.assertIn(first["推荐动作"], {"买入", "持有", "观察"})
        self.assertTrue(payload["禁止规则"]["不输出小票"])

    def test_app_one_click_trading_package_api_shape(self):
        payload = _call_handler_json("/api/one-click-trading-package")

        self.assertIn("今日交易决策", payload)
        self.assertIn("龙头股池", payload)
        self.assertIn("中军股池", payload)
        self.assertIn("趋势股池", payload)
        self.assertIn("今日买点表", payload)
        self.assertIn("同花顺导入文件", payload)
        self.assertIn("TXT", payload["同花顺导入文件"])
        self.assertIn("CSV", payload["同花顺导入文件"])
        self.assertIn("板块,分类,代码,名称,角色,HeatScore,FibScore", payload["同花顺导入文件"]["CSV"])
        self.assertIn("300308", payload["同花顺导入文件"]["TXT"])
        first = payload["今日买点表"][0]
        self.assertIn("买点1", first)
        self.assertIn("买点2", first)
        self.assertIn("最佳买点区间", first)
        self.assertIn(first["是否可交易"], {"YES", "NO", "WAIT"})

    def test_app_lucky_zone_system_api_shape(self):
        payload = _call_handler_json("/api/lucky-zone-system")

        self.assertIn("幸运区核心资产", payload)
        self.assertEqual(payload["优先级"], "Lucky Zone > 龙头 > 中军 > 趋势")
        self.assertIn("不频繁交易", payload["交易规则"])
        first = payload["幸运区核心资产"][0]
        for key in ("股票", "代码", "所属板块", "产业地位", "增长结构", "资金结构", "Fib结构", "趋势结构", "风险等级", "是否进入幸运区"):
            self.assertIn(key, first)
        self.assertIn(first["是否进入幸运区"], {"YES", "NO"})
        self.assertTrue(any(item["股票"] == "立讯精密" for item in payload["幸运区核心资产"]))

    def test_app_dynamic_recalculation_api_shape(self):
        payload = _call_handler_json("/api/dynamic-recalculation-sample")

        self.assertIn("Dynamic Recalculation", payload["系统"])
        self.assertIn("重算流水线", payload)
        self.assertIn("变化日志", payload)
        self.assertIn("市场状态", payload)
        self.assertIn("FROZEN", payload["市场状态"])
        self.assertIn("幸运区", payload["重算流水线"])
        first = payload["变化日志"][0]
        for key in ("时间", "模块", "对象", "旧状态", "新状态", "变化原因", "数据来源"):
            self.assertIn(key, first)
        self.assertTrue(payload["禁止事项"]["静态幸运区"])

    def test_app_one_click_export_endpoints(self):
        txt = _call_handler_text("/exports/tonghuashun_watchlist.txt")
        csv = _call_handler_text("/exports/tonghuashun_execution.csv")

        self.assertIn("300308", txt)
        self.assertIn("板块,分类,代码,名称,角色,HeatScore,FibScore", csv)

    def test_app_price_guard_sample_api_shape(self):
        payload = _call_handler_json("/api/price-guard-sample")
        first = payload["items"][0]

        self.assertIn("symbol", first)
        self.assertIn("price", first)
        self.assertIn("value", first["price"])
        self.assertIn("source", first["price"])
        self.assertIn("timestamp", first["price"])
        self.assertIn("STATUS", first["price"])
        self.assertEqual(first["price"]["source"], "AKShare")


def _call_handler_json(path):
    handler = object.__new__(LocustDashboardHandler)
    handler.path = path
    handler.request_version = "HTTP/1.1"
    handler.command = "GET"
    handler.responses = []
    body = bytearray()

    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.wfile = Mock()
    handler.wfile.write = lambda chunk: body.extend(chunk)

    LocustDashboardHandler.do_GET(handler)
    return json.loads(bytes(body).decode("utf-8"))


def _call_handler_text(path):
    handler = object.__new__(LocustDashboardHandler)
    handler.path = path
    handler.request_version = "HTTP/1.1"
    handler.command = "GET"
    body = bytearray()

    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.wfile = Mock()
    handler.wfile.write = lambda chunk: body.extend(chunk)

    LocustDashboardHandler.do_GET(handler)
    return bytes(body).decode("utf-8-sig")


if __name__ == "__main__":
    unittest.main()
