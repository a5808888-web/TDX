#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

step() {
  printf '\n==> %s\n' "$1"
}

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    printf 'python3'
    return
  fi
  if command -v python >/dev/null 2>&1; then
    printf 'python'
    return
  fi
  printf '未找到 Python。请先安装 Python 3.10 或 3.11。\n' >&2
  exit 1
}

require_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    printf '缺少环境变量 %s。请检查 .env。\n' "$name" >&2
    exit 1
  fi
}

load_dotenv() {
  if [ ! -f "$ROOT/.env" ]; then
    printf '未找到 .env，将使用当前系统环境变量。\n'
    return
  fi

  mkdir -p "$ROOT/.venv"
  sed $'1s/^\xef\xbb\xbf//' "$ROOT/.env" > "$ROOT/.venv/.env.runtime"
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/.venv/.env.runtime"
  set +a
}

cleanup() {
  if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

step "检查 Python"
PYTHON="$(find_python)"
"$PYTHON" --version

step "检查虚拟环境"
if [ ! -x "$ROOT/.venv/bin/python" ]; then
  "$PYTHON" -m venv "$ROOT/.venv"
fi
VENV_PYTHON="$ROOT/.venv/bin/python"

step "安装依赖"
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements.txt

step "读取环境变量"
load_dotenv
require_env "DEEPSEEK_API_KEY"
require_env "ARK_API_KEY"
export DOUBAO_BASE_URL="${DOUBAO_BASE_URL:-https://ark.cn-beijing.volces.com/api/v3/responses}"
export DOUBAO_MODEL="${DOUBAO_MODEL:-doubao-seed-2-0-pro-260215}"
export FUTU_HOST="${FUTU_HOST:-127.0.0.1}"
export FUTU_PORT="${FUTU_PORT:-11111}"

step "检查 DeepSeek / 豆包连接"
"$VENV_PYTHON" test_llm_connection.py

step "检查富途 OpenD"
"$VENV_PYTHON" test_futu_connection.py

step "检查 AKShare A股数据"
"$VENV_PYTHON" test_a_stock_data.py

step "执行健康检查"
"$VENV_PYTHON" health_check.py --skip-llm --skip-futu --skip-a-stock

step "启动本地驾驶舱服务"
BACKEND_PORT="${LOCUST_BACKEND_PORT:-8000}"
PUBLIC_HOST="${LOCUST_PUBLIC_HOST:-127.0.0.1}"
if [ "$PUBLIC_HOST" = "0.0.0.0" ] || [ "$PUBLIC_HOST" = "::" ]; then
  PUBLIC_HOST="127.0.0.1"
fi
export LOCUST_BACKEND_URL="http://${PUBLIC_HOST}:${BACKEND_PORT}/trading_cockpit.html"
"$VENV_PYTHON" app.py &
BACKEND_PID="$!"
sleep 2

step "启动 Streamlit"
STREAMLIT_ADDRESS="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}"
STREAMLIT_PORT="${STREAMLIT_SERVER_PORT:-8501}"
printf 'Streamlit: http://127.0.0.1:%s\n' "$STREAMLIT_PORT"
printf '原生驾驶舱: %s\n' "$LOCUST_BACKEND_URL"
if command -v ipconfig >/dev/null 2>&1; then
  ipconfig getifaddr en0 2>/dev/null | awk -v port="$STREAMLIT_PORT" 'NF { print "局域网入口: http://" $0 ":" port }'
fi
"$VENV_PYTHON" -m streamlit run streamlit_app.py --server.address "$STREAMLIT_ADDRESS" --server.port "$STREAMLIT_PORT"
