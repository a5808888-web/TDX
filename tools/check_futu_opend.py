from __future__ import annotations

import socket


def main() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect(("127.0.0.1", 11111))
    except OSError as exc:
        raise SystemExit(f"Futu OpenD 未连接：{type(exc).__name__}")
    finally:
        sock.close()
    print("Futu OpenD 已连接：127.0.0.1:11111")


if __name__ == "__main__":
    main()
