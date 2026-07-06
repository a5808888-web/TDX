import unittest

from locust_equity_hierarchy import (
    EquityMetrics,
    EquityTier,
    SectorHierarchyInput,
    build_equity_hierarchy,
    calculate_hierarchy_score,
    equity_hierarchy_to_output,
)


class LocustEquityHierarchyTest(unittest.TestCase):
    def test_calculates_hierarchy_score_from_required_factors(self):
        score = calculate_hierarchy_score(
            EquityMetrics(
                stock_name="工业富联",
                code="601138.SH",
                role="中军",
                locust_score=90,
                fib_score=85,
                confluence_layers=4,
                institution_score=80,
                risk_score=25,
                beta=1.0,
                volatility=35,
                capital_concentration=92,
                price_position=0.62,
            )
        )

        self.assertEqual(score, 86.76)

    def test_outputs_all_five_tiers_and_keeps_blocked_pool(self):
        hierarchy = build_equity_hierarchy(sample_sector())

        self.assertEqual(hierarchy.leader[0].metrics.stock_name, "工业富联")
        self.assertEqual(hierarchy.leader[0].tier, EquityTier.LEADER)
        self.assertEqual(hierarchy.core[0].metrics.stock_name, "浪潮信息")
        self.assertEqual(hierarchy.trend[0].metrics.stock_name, "中科曙光")
        self.assertEqual(hierarchy.lagging[0].metrics.stock_name, "拓维信息")
        self.assertEqual(hierarchy.blocked[0].metrics.stock_name, "退潮样本A")
        self.assertEqual(hierarchy.blocked[0].fib_binding["买点1"], "禁止生成")

    def test_output_contract_contains_fib_priority_and_ai_checks(self):
        output = equity_hierarchy_to_output(build_equity_hierarchy(sample_sector()))

        self.assertIn("Equity Hierarchy System", output)
        self.assertIn("🟢 龙头股", output)
        self.assertIn("🟡 中军股", output)
        self.assertIn("🔵 趋势股", output)
        self.assertIn("⚪ 补涨股", output)
        self.assertIn("🔴 禁买股", output)
        self.assertEqual(output["Fib优先级"], "龙头 > 中军 > 趋势 > 补涨；禁买股禁止生成交易动作。")
        self.assertIn("是否假龙头", output["AI分析要求"]["DeepSeek"])
        self.assertIn("是否追高", output["AI分析要求"]["豆包"])


def sample_sector():
    return SectorHierarchyInput(
        sector_name="AI服务器 / 算力 / AI硬件",
        heat_score=86,
        locust_score=82,
        risk_score=28,
        equities=(
            EquityMetrics("工业富联", "601138.SH", "中军", 92, 88, 4, 82, 26, 1.05, 34, 92, 0.62),
            EquityMetrics("浪潮信息", "000977.SZ", "中军", 86, 78, 3, 72, 34, 0.92, 38, 76, 0.58),
            EquityMetrics("中科曙光", "603019.SH", "趋势票", 84, 80, 3, 64, 36, 1.28, 56, 70, 0.68),
            EquityMetrics("拓维信息", "002261.SZ", "补涨票", 62, 58, 2, 42, 48, 0.96, 52, 48, 0.46),
            EquityMetrics("退潮样本A", "000001.SZ", "禁买票", 24, 0, 0, 18, 92, 1.6, 86, 12, 0.2, fib_valid=False, blocked=True),
        ),
    )


if __name__ == "__main__":
    unittest.main()
