import unittest

from locust_institutional_flow import (
    InstitutionActionType,
    InstitutionObservation,
    InstitutionScope,
    calculate_institution_score,
    institutional_flow_to_output,
    run_institutional_flow_intelligence,
)


class LocustInstitutionalFlowTest(unittest.TestCase):
    def test_calculates_institution_score_with_required_weights(self):
        score = calculate_institution_score(
            capital_flow=80,
            sector_impact=90,
            historical_accuracy=70,
            market_resonance=60,
        )

        self.assertEqual(score, 79.0)

    def test_outputs_global_china_reports_mapping_and_fib_linkage(self):
        result = run_institutional_flow_intelligence(sample_observations())
        output = institutional_flow_to_output(result)

        self.assertEqual(result.sync_interval, 180)
        self.assertEqual(len(result.global_reports), 3)
        self.assertEqual(len(result.china_reports), 2)
        self.assertIn(InstitutionActionType.SECTOR_SHIFT, result.global_reports[0].action_types)
        self.assertIn("AI服务器 / 算力 / AI硬件", result.global_reports[0].a_share_mapping)
        self.assertEqual(result.global_reports[0].fib_weight_adjustment, 0.2)
        self.assertEqual(result.global_reports[2].fib_invalid_probability_adjustment, 0.3)
        self.assertTrue(result.sector_flow_changes)
        self.assertEqual(len(result.top_trade_candidates), 3)
        self.assertIn("全球机构动向", output)
        self.assertIn("中国机构动向", output)
        self.assertIn("A股映射机会", output)
        self.assertIn("Fib买点", output)
        self.assertIn("DeepSeek / 豆包", output["数据源"]["AI分析"])

    def test_berkshire_consumption_and_bridgewater_risk_rules(self):
        result = run_institutional_flow_intelligence(sample_observations())
        berkshire = next(item for item in result.global_reports if item.institution_name == "Berkshire Hathaway")
        bridgewater = next(item for item in result.global_reports if item.institution_name == "Bridgewater")

        self.assertIn("消费 / 食品饮料 / 可选消费", berkshire.a_share_mapping)
        self.assertEqual(berkshire.offense_or_defense, "防御")
        self.assertIn("低估值红利 / 银行 / 保险 / 公用事业", bridgewater.a_share_mapping)
        self.assertEqual(bridgewater.macro_or_sector, "宏观驱动")


def sample_observations():
    return (
        InstitutionObservation(
            institution_name="ARK Invest",
            scope=InstitutionScope.GLOBAL,
            portfolio_change=12.0,
            top_buy=("NVDA", "TSLA", "ROBOT ETF"),
            top_sell=("Cash",),
            sector_from="现金",
            sector_to="AI",
            capital_flow=86,
            sector_impact=92,
            historical_accuracy=68,
            market_resonance=82,
            source="富途机构追踪",
        ),
        InstitutionObservation(
            institution_name="Berkshire Hathaway",
            scope=InstitutionScope.GLOBAL,
            portfolio_change=5.0,
            top_buy=("Consumer Staples", "Healthcare"),
            top_sell=("High Beta Tech",),
            sector_from="科技",
            sector_to="消费",
            capital_flow=42,
            sector_impact=74,
            historical_accuracy=86,
            market_resonance=55,
            source="富途机构追踪",
        ),
        InstitutionObservation(
            institution_name="Bridgewater",
            scope=InstitutionScope.GLOBAL,
            portfolio_change=-10.0,
            top_buy=("Gold", "Treasury"),
            top_sell=("Risk Assets", "Cyclicals"),
            sector_from="风险资产",
            sector_to="黄金",
            capital_flow=-66,
            sector_impact=80,
            historical_accuracy=78,
            market_resonance=70,
            source="富途机构追踪",
        ),
        InstitutionObservation(
            institution_name="北向资金",
            scope=InstitutionScope.CHINA,
            portfolio_change=8.0,
            top_buy=("工业富联", "中际旭创"),
            top_sell=("地产链",),
            sector_from="地产",
            sector_to="AI硬件",
            capital_flow=72,
            sector_impact=84,
            historical_accuracy=64,
            market_resonance=76,
            source="北向资金",
        ),
        InstitutionObservation(
            institution_name="公募基金",
            scope=InstitutionScope.CHINA,
            portfolio_change=6.0,
            top_buy=("三花智控", "拓普集团"),
            top_sell=("低成交板块",),
            sector_from="红利",
            sector_to="机器人",
            capital_flow=58,
            sector_impact=78,
            historical_accuracy=62,
            market_resonance=68,
            source="公募基金",
        ),
    )


if __name__ == "__main__":
    unittest.main()
