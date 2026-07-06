import unittest

from i18n import get_i18n, translate
from ui import get_dashboard_text, get_execution_panel_text, localize_signal


class I18nTest(unittest.TestCase):
    def test_default_locale_is_chinese(self):
        text = get_i18n()

        self.assertEqual(text["sections"]["marketStatus"], "市场状态")
        self.assertEqual(text["sections"]["flowMap"], "资金热力图")
        self.assertEqual(text["sections"]["tradeSignals"], "交易信号")
        self.assertEqual(text["sections"]["executionPanel"], "执行面板")

    def test_english_fallback_locale_exists(self):
        text = get_i18n("en-US")

        self.assertEqual(text["sections"]["marketStatus"], "Market Status")
        self.assertEqual(text["action"]["AVOID"], "Avoid")

    def test_ui_components_use_translation_layer(self):
        dashboard = get_dashboard_text()
        execution = get_execution_panel_text()

        self.assertEqual(dashboard["market_status"], "市场状态")
        self.assertEqual(dashboard["flow_map"], "资金热力图")
        self.assertEqual(execution["BUY"], "买入")
        self.assertEqual(execution["WAIT"], "观察")
        self.assertEqual(execution["AVOID"], "回避")

    def test_strategy_signal_remains_language_neutral(self):
        strategy_signal = "BUY"

        self.assertEqual(strategy_signal, "BUY")
        self.assertEqual(localize_signal(strategy_signal), "买入")

    def test_template_interpolation(self):
        self.assertEqual(translate("units.stocks", count=8), "8只")


if __name__ == "__main__":
    unittest.main()
