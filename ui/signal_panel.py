from __future__ import annotations

from i18n import get_i18n


def localize_signal(signal: str, locale: str = "zh-CN") -> str:
    text = get_i18n(locale)
    return text["status"].get(signal, signal)
