from __future__ import annotations

from pathlib import Path


def load_local_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(Path(__file__).resolve().parent / ".env", override=False, encoding="utf-8-sig")
