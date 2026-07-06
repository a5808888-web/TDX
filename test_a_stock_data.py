from __future__ import annotations

import os
import sys
import time

from local_env import load_local_env


def main() -> int:
    load_local_env()
    symbols = [item.strip() for item in os.environ.get("A_STOCK_TEST_SYMBOLS", "601138.SH,300308.SZ,002475.SZ").split(",") if item.strip()]
    try:
        import akshare as ak
    except Exception as exc:
        print(f"[FAIL] AKShare 未安装或不可导入：{type(exc).__name__}")
        return 1

    spot = None
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            spot = ak.stock_zh_a_spot()
            break
        except Exception as exc:
            last_error = exc
            print(f"[WARN] AKShare A股行情接口第 {attempt} 次失败：{type(exc).__name__}: {exc}")
            time.sleep(2)
    if spot is None:
        print("[FAIL] AKShare A股行情接口失败：请检查新电脑网络、代理、防火墙，或稍后重试。")
        if last_error is not None:
            print(f"[FAIL] 最后错误：{type(last_error).__name__}: {last_error}")
        return 1

    failures: list[str] = []
    for symbol in symbols:
        code = normalize_a_share_code(symbol)
        row = spot[spot["代码"].astype(str).map(normalize_a_share_code) == code]
        if row.empty:
            failures.append(f"{symbol}: 未找到行情")
            continue
        price = row.iloc[0].get("最新价")
        print(f"[OK] AKShare {symbol}: 最新价={price}")

    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        return 1

    print("[OK] A股数据使用 AKShare 非东方财富通道；Eastmoney 资金流检查已跳过。")
    return 0


def normalize_a_share_code(symbol: str) -> str:
    code = symbol.split(".", 1)[0].strip().lower()
    return code.replace("sh", "").replace("sz", "").replace("bj", "")


def eastmoney_market(symbol: str) -> str:
    return "sh" if symbol.upper().endswith(".SH") else "sz"


if __name__ == "__main__":
    raise SystemExit(main())
