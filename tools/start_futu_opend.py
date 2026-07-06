from __future__ import annotations

import subprocess
from pathlib import Path


FUTU_OPEND_APP = Path.home() / "Applications" / "FutuOpenD" / "Futu_OpenD.app"


def main() -> None:
    if not FUTU_OPEND_APP.exists():
        raise SystemExit(f"未找到 Futu OpenD：{FUTU_OPEND_APP}")
    subprocess.run(["open", str(FUTU_OPEND_APP)], check=True)
    print("Futu OpenD 已启动；如首次使用，请在弹出的窗口中登录。")


if __name__ == "__main__":
    main()
