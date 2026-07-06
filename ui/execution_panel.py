from __future__ import annotations

from i18n import get_i18n


def get_execution_panel_text(locale: str = "zh-CN") -> dict[str, str]:
    text = get_i18n(locale)
    return {
        "BUY": text["action"]["BUY"],
        "WAIT": text["action"]["WAIT"],
        "AVOID": text["action"]["AVOID"],
    }
