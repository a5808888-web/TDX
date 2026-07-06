import unittest

from locust_sector_framework import build_unified_sector_frameworks, sector_frameworks_to_output


class LocustSectorFrameworkTest(unittest.TestCase):
    def test_framework_covers_required_eleven_sectors(self):
        frameworks = build_unified_sector_frameworks()
        names = {item.name for item in frameworks}

        self.assertEqual(len(frameworks), 11)
        self.assertIn("AI服务器 / 算力 / AI硬件", names)
        self.assertIn("光通信 / CPO / 光模块", names)
        self.assertIn("电力 / 电网 / 电力设备 / 电算协同", names)
        self.assertIn("存储 / 半导体存储 / DRAM / NAND", names)
        self.assertIn("锂电 / 储能 / 新能源电池", names)
        self.assertIn("医药 / 创新药 / 医疗器械", names)
        self.assertIn("消费 / 食品饮料 / 可选消费", names)
        self.assertIn("机器人 / 具身智能", names)
        self.assertIn("有色金属 / 黄金 / 铜", names)
        self.assertIn("工业自动化 / 制造业升级", names)
        self.assertIn("低估值红利 / 银行 / 保险 / 公用事业", names)

    def test_each_sector_has_structure_value_chain_and_stock_roles(self):
        for framework in build_unified_sector_frameworks():
            self.assertGreaterEqual(len(framework.structure.upstream), 3)
            self.assertGreaterEqual(len(framework.structure.midstream), 3)
            self.assertGreaterEqual(len(framework.structure.downstream), 3)
            self.assertGreaterEqual(len(framework.structure.drivers), 3)
            self.assertGreaterEqual(len(framework.value_chain), 3)
            self.assertIn("中军", framework.stock_roles)
            self.assertIn("趋势票", framework.stock_roles)
            self.assertIn("弹性票", framework.stock_roles)

    def test_output_contract_contains_required_sections(self):
        output = sector_frameworks_to_output()["Locust Sector Framework"]
        first = output["sectors"][0]

        self.assertEqual(output["sector_count"], 11)
        self.assertIn("产业链结构", first)
        self.assertIn("Module Value Chain", first)
        self.assertIn("选股池三层", first)
        self.assertIn("上游", first["产业链结构"])
        self.assertIn("环节", first["Module Value Chain"][0])


if __name__ == "__main__":
    unittest.main()
