from __future__ import annotations

from i18n import get_i18n


def get_dashboard_text(locale: str = "zh-CN") -> dict[str, str]:
    text = get_i18n(locale)
    return {
        "market_status": text["sections"]["marketStatus"],
        "flow_map": text["sections"]["flowMap"],
        "stock_universe": text["sections"]["stockUniverse"],
        "trade_signals": text["sections"]["tradeSignals"],
        "execution_panel": text["sections"]["executionPanel"],
    }
