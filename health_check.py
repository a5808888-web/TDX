from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
from pathlib import Path

from local_env import load_local_env


ROOT = Path(__file__).resolve().parent


def main() -> int:
    load_local_env()
    args = parse_args()
    checks: list[tuple[str, bool, str]] = []
    checks.append(check_python_version())
    checks.append(check_required_files())
    checks.append(check_environment(args.quick))
    checks.append(check_imports())
    checks.append(check_compile())
    if not args.quick:
        if not args.skip_llm:
            checks.append(run_script("DeepSeek + 豆包连接", "test_llm_connection.py"))
        if not args.skip_futu:
            checks.append(run_script("Futu OpenD连接", "test_futu_connection.py"))
        if not args.skip_a_stock:
            checks.append(run_script("A股数据连接", "test_a_stock_data.py"))

    print("\n=== Locust Plan Health Check ===")
    failed = False
    for name, ok, message in checks:
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {name}: {message}")
        failed = failed or not ok
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Locust Plan health check")
    parser.add_argument("--quick", action="store_true", help="只检查本地结构、依赖导入和环境变量，不访问外部服务")
    parser.add_argument("--skip-llm", action="store_true", help="跳过 DeepSeek / 豆包连接")
    parser.add_argument("--skip-futu", action="store_true", help="跳过 Futu OpenD 连接")
    parser.add_argument("--skip-a-stock", action="store_true", help="跳过 AKShare / Eastmoney 连接")
    return parser.parse_args()


def check_python_version() -> tuple[str, bool, str]:
    version = sys.version_info
    ok = version >= (3, 10)
    return "Python版本", ok, f"{version.major}.{version.minor}.{version.micro}"


def check_required_files() -> tuple[str, bool, str]:
    required = (
        "app.py",
        "streamlit_app.py",
        "trading_cockpit.html",
        "trading_cockpit.js",
        "trading_cockpit.css",
        "requirements.txt",
        ".env.example",
        "README_DEPLOY.md",
        "health_check.py",
        "test_a_stock_data.py",
        "test_llm_connection.py",
        "test_futu_connection.py",
        "scripts/start_windows.ps1",
        "scripts/start_mac.sh",
    )
    missing = [name for name in required if not (ROOT / name).exists()]
    return "项目文件", not missing, "完整" if not missing else "缺失：" + ", ".join(missing)


def check_environment(quick: bool) -> tuple[str, bool, str]:
    required = ("DEEPSEEK_API_KEY", "ARK_API_KEY", "DOUBAO_MODEL", "FUTU_HOST", "FUTU_PORT")
    missing = [name for name in required if not os.environ.get(name)]
    if missing and quick:
        return "环境变量", False, "缺失：" + ", ".join(missing)
    if missing:
        return "环境变量", False, "缺失：" + ", ".join(missing)
    return "环境变量", True, "已配置；未输出任何密钥"


def check_imports() -> tuple[str, bool, str]:
    modules = ("yaml", "pandas", "numpy", "akshare", "futu", "streamlit")
    missing: list[str] = []
    for module in modules:
        try:
            importlib.import_module(module)
        except Exception:
            missing.append(module)
    return "依赖导入", not missing, "完整" if not missing else "缺失：" + ", ".join(missing)


def check_compile() -> tuple[str, bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", "app.py", "ai_consensus_layer.py", "market_data_connectors.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "核心模块语法", False, (result.stderr or result.stdout).strip()
    return "核心模块语法", True, "通过"


def run_script(name: str, script: str) -> tuple[str, bool, str]:
    result = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True)
    output = (result.stdout + "\n" + result.stderr).strip()
    message = summarize_script_output(output)
    if result.returncode != 0:
        return name, False, message or "失败"
    return name, True, message or "通过"


def summarize_script_output(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    status_lines = [
        line
        for line in lines
        if line.startswith(("[OK]", "[FAIL]", "[WARN]")) and "Please wait for a moment" not in line
    ]
    if status_lines:
        return status_lines[-1]
    return lines[-1] if lines else ""


if __name__ == "__main__":
    raise SystemExit(main())
