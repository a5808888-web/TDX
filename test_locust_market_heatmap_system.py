import unittest

from locust_market_heatmap_system import (
    GlobalHeatmapTile,
    HeatmapTimeframe,
    MarketHeatmapInput,
    SectorHeatmapSource,
    calculate_heat_score,
    market_heatmap_to_output,
    run_market_heatmap_system,
)


class LocustMarketHeatmapSystemTest(unittest.TestCase):
    def test_calculates_heat_score_with_required_weights(self):
        score = calculate_heat_score(
            change_pct=3.0,
            capital_flow=60,
            limit_up_spread=0.8,
            volume_change=40,
            leader_strength=90,
        )

        self.assertEqual(score, 82)

    def test_outputs_treemap_tiles_and_linked_pools(self):
        result = run_market_heatmap_system(
            MarketHeatmapInput(
                timeframe=HeatmapTimeframe.DAYS_7,
                sectors=sample_sectors(),
                global_tiles=sample_global_tiles(),
                timestamp="2026-07-05 15:00:00",
            )
        )
        output = market_heatmap_to_output(result)

        self.assertEqual(result.sync_interval, 180)
        self.assertEqual(result.tiles[0].name, "AI服务器")
        self.assertIn("AI服务器", result.top_picks_pool)
        self.assertIn("地产", result.forbidden_pool)
        self.assertEqual(result.fib_weight_by_sector["AI服务器"], 0.2)
        self.assertEqual(result.fib_weight_by_sector["地产"], -1.0)
        self.assertIn("AI服务器", result.reselection_triggers)
        self.assertEqual(output["行业热力图矩阵"][0]["tradable"], "YES")
        self.assertEqual(output["UI规则"]["Treemap"], True)
        self.assertIn("近6个月", output["UI规则"]["支持周期切换"])

    def test_timeframe_resample_recalculates_ranking_and_heat(self):
        week = run_market_heatmap_system(MarketHeatmapInput(timeframe=HeatmapTimeframe.DAYS_7, sectors=sample_sectors()))
        half_year = run_market_heatmap_system(MarketHeatmapInput(timeframe=HeatmapTimeframe.MONTH_6, sectors=sample_sectors()))

        week_robot = next(item for item in week.tiles if item.name == "机器人")
        half_year_robot = next(item for item in half_year.tiles if item.name == "机器人")

        self.assertGreater(half_year_robot.change_pct, week_robot.change_pct)
        self.assertNotEqual(half_year_robot.heat_score, week_robot.heat_score)

    def test_global_ai_strength_lifts_a_share_ai_weight(self):
        result = run_market_heatmap_system(
            MarketHeatmapInput(
                timeframe=HeatmapTimeframe.DAYS_7,
                sectors=sample_sectors(),
                global_tiles=(
                    GlobalHeatmapTile("AI芯片", 3.2, 86, "A股AI权重提升", "流入"),
                    GlobalHeatmapTile("黄金", 1.0, 68, "避险中性", "流入"),
                ),
            )
        )

        self.assertEqual(result.global_linkage["A股AI权重"], "提升")


def sample_sectors():
    return (
        SectorHeatmapSource("AI服务器", 3.2, 72, 0.85, 58, 92, "工业富联", ("工业富联", "浪潮信息", "中科曙光"), 65),
        SectorHeatmapSource("光通信", 2.6, 66, 0.78, 45, 90, "中际旭创", ("中际旭创", "新易盛", "天孚通信"), 74),
        SectorHeatmapSource("机器人", 1.5, 38, 0.52, 28, 82, "三花智控", ("三花智控", "拓普集团", "绿的谐波"), 61),
        SectorHeatmapSource("银行", 0.3, 15, 0.12, 8, 64, "招商银行", ("招商银行", "工商银行", "建设银行"), 53),
        SectorHeatmapSource("地产", -3.5, -48, 0.03, -35, 25, "低成交样本", ("地产A", "地产B"), 48),
    )


def sample_global_tiles():
    return (
        GlobalHeatmapTile("半导体（美股）", 2.1, 82, "A股半导体提振", "流入"),
        GlobalHeatmapTile("AI芯片", 2.7, 88, "A股AI权重提升", "流入"),
        GlobalHeatmapTile("黄金", 1.3, 76, "有色黄金权重提升", "流入"),
    )


if __name__ == "__main__":
    unittest.main()
