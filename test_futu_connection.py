from __future__ import annotations

import os
import socket
import sys

from local_env import load_local_env


def main() -> int:
    load_local_env()
    host = os.environ.get("FUTU_HOST", "127.0.0.1")
    port = int(os.environ.get("FUTU_PORT", "11111"))
    try:
        import futu  # noqa: F401
    except Exception as exc:
        print(f"[FAIL] futu-api 未安装或不可导入：{type(exc).__name__}")
        return 1

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect((host, port))
    except OSError as exc:
        print(f"[FAIL] Futu OpenD 未连接：{host}:{port} ({type(exc).__name__})")
        return 1
    finally:
        sock.close()

    print(f"[OK] Futu OpenD 已连接：{host}:{port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
