from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


I18N_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "i18n.yaml"


@lru_cache(maxsize=1)
def _load_i18n_config() -> dict[str, Any]:
    with I18N_CONFIG_PATH.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError("i18n config must be a mapping.")
    return data


def get_i18n(locale: str = "zh-CN") -> dict[str, Any]:
    config = _load_i18n_config()
    default_locale = config.get("default_locale", "zh-CN")
    translations = config.get("translations", {})
    if locale not in translations:
        locale = default_locale
    return translations[locale]


def translate(path: str, locale: str = "zh-CN", **values: object) -> str:
    node: Any = get_i18n(locale)
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return path
        node = node[part]
    if not isinstance(node, str):
        return path
    return node.format(**values)
