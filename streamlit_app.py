from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from local_env import load_local_env

load_local_env()
ROOT = Path(__file__).resolve().parent
BACKEND_HOST = os.environ.get("LOCUST_BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.environ.get("LOCUST_BACKEND_PORT", "8000")
PUBLIC_HOST = os.environ.get("LOCUST_PUBLIC_HOST", "127.0.0.1")
if PUBLIC_HOST in {"0.0.0.0", "::"}:
    PUBLIC_HOST = "127.0.0.1"
BACKEND_URL = os.environ.get("LOCUST_BACKEND_URL", f"http://{PUBLIC_HOST}:{BACKEND_PORT}/trading_cockpit.html")

st.set_page_config(page_title="蝗虫计划 Locust Plan", page_icon="LP", layout="wide")


def backend_is_ready() -> bool:
    try:
        with urllib.request.urlopen(BACKEND_URL, timeout=2) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


@st.cache_resource
def ensure_backend() -> subprocess.Popen[str] | None:
    if backend_is_ready():
        return None

    env = os.environ.copy()
    env.setdefault("LOCUST_BACKEND_HOST", BACKEND_HOST)
    env.setdefault("LOCUST_BACKEND_PORT", BACKEND_PORT)
    process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    for _ in range(20):
        if backend_is_ready():
            return process
        time.sleep(0.5)
    return process


ensure_backend()

st.title("蝗虫计划 Locust Plan")
st.caption("Streamlit 迁移入口。核心交易驾驶舱仍由本地 Locust Plan 服务动态刷新。")

st.info(
    "请确认后台服务已经启动。Windows 启动脚本会先启动 `python app.py`，"
    "然后启动本 Streamlit 页面。"
)

st.link_button("打开交易驾驶舱", BACKEND_URL, use_container_width=True)

components.iframe(BACKEND_URL, height=900, scrolling=True)
