# Locust Plan 新电脑运行说明

本说明用于在新电脑恢复蝗虫计划运行环境。当前阶段只恢复运行，不重构业务模块、不改交易逻辑、不改 UI。

## 不要迁移或写入代码的内容

- 不要迁移 `.venv`
- 不要把真实 API Key 写进 Python、JavaScript、HTML、脚本或 README
- 不要提交 `.env`
- 所有密钥只从本机 `.env` 或系统环境变量读取

## 必需文件

项目根目录需要包含：

- `app.py`
- `streamlit_app.py`
- `requirements.txt`
- `.env.example`
- `README_DEPLOY.md`
- `health_check.py`
- `test_a_stock_data.py`
- `test_llm_connection.py`
- `test_futu_connection.py`
- `scripts/start_windows.ps1`
- `scripts/start_mac.sh`

`main.py`、`package.json`、`pyproject.toml` 不是当前运行链路必需文件；本项目以 Python + Streamlit + 静态驾驶舱页面启动。

## .env 配置

复制模板：

Windows:

```powershell
Copy-Item .env.example .env
notepad .env
```

Mac:

```bash
cp .env.example .env
nano .env
```

在 `.env` 中填写真实值：

```text
DEEPSEEK_API_KEY=
ARK_API_KEY=
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/responses
DOUBAO_MODEL=
FUTU_HOST=127.0.0.1
FUTU_PORT=11111
LOCUST_BACKEND_HOST=127.0.0.1
LOCUST_BACKEND_PORT=8000
LOCUST_PUBLIC_HOST=127.0.0.1
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_PORT=8501
```

豆包默认使用火山方舟 `responses` 接口。`DOUBAO_MODEL` 可填写 `doubao-seed-2-0-pro-260215`，或火山方舟控制台已开通的可用模型名 / 推理接入点 ID。

## Windows 一键启动

在项目根目录打开 PowerShell：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\start_windows.ps1
```

脚本会依次完成：

1. 检查 Python
2. 创建或复用 `.venv`
3. 安装 `requirements.txt`
4. 检查 `.env` 或系统环境变量
5. 检查 DeepSeek
6. 检查豆包
7. 检查 AKShare A股数据
8. 检查 Futu OpenD
9. 启动本地驾驶舱服务
10. 启动 Streamlit

## Mac 一键启动

在项目根目录打开 Terminal：

```bash
chmod +x scripts/start_mac.sh
./scripts/start_mac.sh
```

脚本会执行与 Windows 相同的检查和启动流程。

## 手动单项检查

Windows:

```powershell
.\.venv\Scripts\python.exe health_check.py
.\.venv\Scripts\python.exe test_llm_connection.py
.\.venv\Scripts\python.exe test_a_stock_data.py
.\.venv\Scripts\python.exe test_futu_connection.py
```

Mac:

```bash
.venv/bin/python health_check.py
.venv/bin/python test_llm_connection.py
.venv/bin/python test_a_stock_data.py
.venv/bin/python test_futu_connection.py
```

## 访问地址

本机访问：

- Streamlit 首页：`http://127.0.0.1:8501`
- 原生驾驶舱：`http://127.0.0.1:8000/trading_cockpit.html`

如果要让同一局域网的手机或其他电脑访问，把 `.env` 里的 `LOCUST_PUBLIC_HOST` 改成新电脑的局域网 IP，并确认系统防火墙允许 Python / Streamlit 使用 `8501` 和 `8000` 端口。
