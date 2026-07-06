from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibonacci_contract_extension_system import ContractAnalysisInput, build_contract_fib_analysis, render_contract_analysis_html
from fibonacci_wave_system import SwingKind, SwingPoint, TrendDirection, WaveSegment, WaveTier


def main() -> None:
    parser = argparse.ArgumentParser(description="生成斐波那契回撤与扩展交易分析图")
    parser.add_argument("--low", type=float, required=True, help="确认波段起点低点")
    parser.add_argument("--high", type=float, required=True, help="确认波段终点高点")
    parser.add_argument("--current", type=float, required=True, help="当前价格")
    parser.add_argument("--symbol", default="", help="证券代码")
    parser.add_argument("--name", default="", help="证券名称")
    parser.add_argument("--timeframe", default="1D", help="波段周期，默认 1D")
    parser.add_argument("--confluence", type=float, default=50.0, help="共振强度 0~100")
    parser.add_argument("--trend", type=float, default=50.0, help="趋势强度 0~100")
    parser.add_argument("--volume", type=float, default=50.0, help="成交量配合度 0~100")
    parser.add_argument("--capital", type=float, default=50.0, help="资金流向 0~100")
    parser.add_argument("--risk", type=float, default=40.0, help="风险分 0~100")
    parser.add_argument("--stop-fall", action="store_true", help="是否出现止跌确认")
    parser.add_argument("--volume-confirmed", action="store_true", help="是否放量确认")
    parser.add_argument("--output", default="contract_fib_report.html", help="输出 HTML 文件")
    args = parser.parse_args()

    wave = WaveSegment(
        low=SwingPoint(args.low, SwingKind.LOW, "confirmed-low", args.timeframe, WaveTier.OPERATING, True),
        high=SwingPoint(args.high, SwingKind.HIGH, "confirmed-high", args.timeframe, WaveTier.OPERATING, True),
        tier=WaveTier.OPERATING,
        direction=TrendDirection.UP,
        name=args.symbol or args.name or "contract-wave",
    )
    result = build_contract_fib_analysis(
        ContractAnalysisInput(
            wave=wave,
            current_price=args.current,
            symbol=args.symbol,
            stock_name=args.name,
            confluence_strength=args.confluence,
            trend_strength=args.trend,
            volume_fit=args.volume,
            capital_flow=args.capital,
            risk_score=args.risk,
            stop_fall_confirmed=args.stop_fall,
            volume_confirmed=args.volume_confirmed,
        )
    )
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_contract_analysis_html(result), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
