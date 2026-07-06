import unittest

from locust_top_core_equity_engine import (
    CoreEquityInput,
    CoreEquityType,
    calculate_core_score,
    run_top_core_equity_engine,
    top_core_equity_to_output,
)


class TopCoreEquityEngineTest(unittest.TestCase):
    def test_calculates_required_core_score_formula(self):
        score = calculate_core_score(
            CoreEquityInput(
                "工业富联",
                "601138.SH",
                "AI服务器 / 算力 / AI硬件",
                CoreEquityType.LEADER,
                heat_score=86,
                institution_flow_score=90,
                institution_inflow=True,
                fib_zone="0.382–0.618",
                fib_score=80,
                ai_decision="BUY",
                ai_confidence=85,
                leader_attribute_score=100,
            )
        )

        self.assertEqual(score, 87.2)

    def test_filters_to_leader_and_core_institution_only(self):
        result = run_top_core_equity_engine(sample_inputs(), max_items=5)

        names = [item.stock_name for item in result.recommendations]
        self.assertEqual(names, ["工业富联", "中际旭创"])
        self.assertTrue(all(item.equity_type in {CoreEquityType.LEADER, CoreEquityType.CORE_INSTITUTION} for item in result.recommendations))
        self.assertTrue(any(item["stock_name"] == "补涨样本" for item in result.rejected))
        self.assertTrue(any(item["stock_name"] == "情绪样本" for item in result.rejected))
        self.assertLessEqual(len(result.recommendations), 5)

    def test_output_contract_is_homepage_core_pool(self):
        output = top_core_equity_to_output(run_top_core_equity_engine(sample_inputs()))
        first = output["长期核心推荐池"][0]

        self.assertEqual(output["首页唯一入口"], "长期核心推荐池")
        self.assertIn("核心评分公式", output)
        self.assertIn("股票名称", first)
        self.assertIn("产业属性", first)
        self.assertIn("所属板块", first)
        self.assertIn("资金状态", first)
        self.assertIn("斐波那契结构", first)
        self.assertIn("智能分析结论", first)
        self.assertIn(first["推荐动作"], {"买入", "持有", "观察"})
        self.assertTrue(output["禁止规则"]["不输出小票"])


def sample_inputs():
    return (
        CoreEquityInput("工业富联", "601138.SH", "AI服务器 / 算力 / AI硬件", CoreEquityType.LEADER, 86, 90, True, "0.382–0.618", 80, "BUY", 85, 100),
        CoreEquityInput("中际旭创", "300308.SZ", "光通信 / CPO / 光模块", CoreEquityType.CORE_INSTITUTION, 91, 82, True, "buy", 78, "WAIT", 78, 88),
        CoreEquityInput("趋势样本", "000001.SZ", "AI服务器 / 算力 / AI硬件", CoreEquityType.TREND, 90, 85, True, "buy", 82, "BUY", 80, 72),
        CoreEquityInput("补涨样本", "000002.SZ", "光通信 / CPO / 光模块", CoreEquityType.LAGGING, 92, 88, True, "buy", 80, "BUY", 82, 60),
        CoreEquityInput("无资金样本", "000003.SZ", "人形机器人 / 具身智能", CoreEquityType.LEADER, 88, 42, False, "buy", 78, "BUY", 75, 90),
        CoreEquityInput("无Fib样本", "000004.SZ", "有色金属 / 黄金 / 铜", CoreEquityType.CORE_INSTITUTION, 84, 75, True, "neutral", 50, "WAIT", 70, 86),
        CoreEquityInput("情绪样本", "000005.SZ", "动态新增池", CoreEquityType.LEADER, 86, 78, True, "buy", 76, "BUY", 72, 82, emotion_stock=True),
    )


if __name__ == "__main__":
    unittest.main()
