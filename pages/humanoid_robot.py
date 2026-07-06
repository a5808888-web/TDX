from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from humanoid_robot_module import humanoid_robot_to_output, load_humanoid_robot_module
from market_state_engine import determine_a_share_market_state


def build_page_model(now: datetime | None = None) -> dict[str, object]:
    state = determine_a_share_market_state(now)
    result = load_humanoid_robot_module(
        updated_at=state.reference_time.strftime("%Y-%m-%d %H:%M:%S"),
        market_state=state.ui_label,
    )
    output = humanoid_robot_to_output(result)
    return {
        "页面名称": "蝗虫计划 · 人形机器人产业链模块",
        "人形机器人总览": {
            "定位": output["positioning"],
            "市场状态": output["market_state"],
            "更新时间": output["updated_at"],
            "Top股票": tuple(item["stock_name"] for item in output["top_picks"][:3]),
        },
        "2026成本结构": output["cost_structure"],
        "四大模块成本权重": _top_cost_modules(output["cost_structure"]),
        "子板块热力图": output["subsector_heatmap"],
        "A股标的池": output["stock_pool"],
        "Top Picks": output["top_picks"],
        "Fibonacci买卖点": "接入现有Fibonacci系统，实时价格仅来自AKShare/Futu行情层。",
        "AI自动分析": "每次同步后自动生成 DeepSeek 结构分析 + 豆包新闻/公告/情绪摘要。",
        "数据来源与更新时间": {
            "数据来源": output["data_sources"],
            "更新时间": output["updated_at"],
            "状态": output["market_state"],
        },
    }


def _top_cost_modules(cost_rows: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    grouped: dict[str, dict[str, float]] = {}
    for row in cost_rows:
        item = grouped.setdefault(str(row["module"]), {"low": 0.0, "high": 0.0})
        item["low"] += float(row["cost_ratio_low"])
        item["high"] += float(row["cost_ratio_high"])
    ranked = sorted(grouped.items(), key=lambda pair: pair[1]["high"], reverse=True)[:4]
    return tuple({"module": name, "cost_ratio_low": round(values["low"], 2), "cost_ratio_high": round(values["high"], 2)} for name, values in ranked)


if __name__ == "__main__":
    import json

    print(json.dumps(build_page_model(), ensure_ascii=False, indent=2))
