import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from humanoid_robot_module import (
    build_subsector_heatmap,
    classify_humanoid_score,
    humanoid_robot_to_output,
    load_cost_structure,
    load_humanoid_robot_module,
    load_stock_pool,
)
from pages.humanoid_robot import build_page_model


class HumanoidRobotModuleTest(unittest.TestCase):
    def test_cost_structure_requires_sources_and_confidence(self):
        rows = load_cost_structure()

        self.assertGreaterEqual(len(rows), 20)
        self.assertTrue(all(row.source_name and row.source_type and row.url_or_page for row in rows))
        self.assertTrue(all(row.confidence_score > 0 for row in rows))

    def test_stock_pool_has_required_subsectors_and_three_candidates_each(self):
        stocks = load_stock_pool()
        required = {
            "执行器 / 伺服系统",
            "丝杠 / 精密传动",
            "减速器",
            "电机 / 驱动",
            "传感器",
            "控制器 / 计算",
            "结构件 / 轻量化系统",
        }
        modules = {stock.module for stock in stocks}

        self.assertTrue(required.issubset(modules))
        for module in required:
            self.assertGreaterEqual(len([stock for stock in stocks if stock.module == module]), 3)
        self.assertTrue(all(stock.code.endswith((".SH", ".SZ")) for stock in stocks))

    def test_humanoid_score_tiers_and_top_picks(self):
        self.assertEqual(classify_humanoid_score(82), "核心标的")
        self.assertEqual(classify_humanoid_score(70), "观察标的")
        self.assertEqual(classify_humanoid_score(45), "概念标的")
        self.assertEqual(classify_humanoid_score(30), "剔除或禁买")

        result = load_humanoid_robot_module("2026-07-03 15:00:00", "STATIC（非交易日）")

        self.assertEqual(result.sector_name, "人形机器人 / 具身智能")
        self.assertTrue(result.top_picks)
        self.assertGreaterEqual(result.top_picks[0].humanoid_score, result.top_picks[-1].humanoid_score)

    def test_subsector_heatmap_outputs_trade_fields(self):
        heatmap = build_subsector_heatmap(load_stock_pool())
        first = heatmap[0]

        self.assertGreaterEqual(len(heatmap), 6)
        self.assertIn(first.action, {"买入", "观察", "回避"})
        self.assertGreater(first.heat_score, 0)
        self.assertTrue(first.representative)

    def test_output_and_page_model_include_required_sections(self):
        result = load_humanoid_robot_module("2026-07-03 15:00:00", "STATIC（非交易日）")
        output = humanoid_robot_to_output(result)
        page = build_page_model(datetime(2026, 7, 5, 10, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai")))

        self.assertEqual(output["module_name"], "蝗虫计划 · 人形机器人产业链模块")
        self.assertIn("cost_structure", output)
        self.assertIn("subsector_heatmap", output)
        self.assertIn("stock_pool", output)
        self.assertIn("Top Picks", page)
        self.assertIn("Fibonacci买卖点", page)
        self.assertIn("AI自动分析", page)


if __name__ == "__main__":
    unittest.main()
