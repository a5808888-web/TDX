Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Find-Python {
    $candidates = @("py", "python")
    foreach ($cmd in $candidates) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($null -ne $found) {
            if ($cmd -eq "py") {
                return @{ Exe = "py"; Args = @("-3") }
            }
            return @{ Exe = "python"; Args = @() }
        }
    }
    throw "未找到 Python。请安装 Python 3.10/3.11 并加入 PATH。"
}

function Load-DotEnv {
    $envFile = Join-Path $Root ".env"
    if (-not (Test-Path $envFile)) {
        Write-Host "未找到 .env，将使用当前环境变量。" -ForegroundColor Yellow
        return
    }
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line.Length -eq 0 -or $line.StartsWith("#")) { return }
        if ($line.StartsWith("export ")) { $line = $line.Substring(7).Trim() }
        $parts = $line.Split("=", 2)
        if ($parts.Count -eq 2) {
            $name = $parts[0].Trim().Trim([char]0xFEFF)
            $value = $parts[1].Trim().Trim('"').Trim("'")
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

function Require-Env($Name) {
    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "缺少环境变量 $Name。请检查 .env。"
    }
}

Write-Step "检查 Python"
$Python = Find-Python
& $Python.Exe @($Python.Args + @("--version"))

Write-Step "检查虚拟环境"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    & $Python.Exe @($Python.Args + @("-m", "venv", ".venv"))
}

Write-Step "安装依赖"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

Write-Step "读取环境变量"
Load-DotEnv
Require-Env "DEEPSEEK_API_KEY"
Require-Env "ARK_API_KEY"
if (-not [Environment]::GetEnvironmentVariable("DOUBAO_BASE_URL", "Process")) { $env:DOUBAO_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/responses" }
if (-not [Environment]::GetEnvironmentVariable("DOUBAO_MODEL", "Process")) { $env:DOUBAO_MODEL = "doubao-seed-2-0-pro-260215" }
if (-not [Environment]::GetEnvironmentVariable("FUTU_HOST", "Process")) { $env:FUTU_HOST = "127.0.0.1" }
if (-not [Environment]::GetEnvironmentVariable("FUTU_PORT", "Process")) { $env:FUTU_PORT = "11111" }

Write-Step "检查 DeepSeek / 豆包连接"
& $VenvPython test_llm_connection.py

Write-Step "检查富途 OpenD"
& $VenvPython test_futu_connection.py

Write-Step "检查 AKShare A股数据"
& $VenvPython test_a_stock_data.py

Write-Step "执行健康检查"
& $VenvPython health_check.py --skip-llm --skip-futu --skip-a-stock

Write-Step "启动本地驾驶舱服务"
$backendHost = if ($env:LOCUST_BACKEND_HOST) { $env:LOCUST_BACKEND_HOST } else { "127.0.0.1" }
$backendPort = if ($env:LOCUST_BACKEND_PORT) { $env:LOCUST_BACKEND_PORT } else { "8000" }
$publicHost = if ($env:LOCUST_PUBLIC_HOST) { $env:LOCUST_PUBLIC_HOST } else { "127.0.0.1" }
if ($publicHost -eq "0.0.0.0" -or $publicHost -eq "::") { $publicHost = "127.0.0.1" }
$env:LOCUST_BACKEND_URL = "http://${publicHost}:${backendPort}/trading_cockpit.html"
$backend = Start-Process -FilePath $VenvPython -ArgumentList "app.py" -WorkingDirectory $Root -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 2

Write-Step "启动 Streamlit"
$streamlitAddress = if ($env:STREAMLIT_SERVER_ADDRESS) { $env:STREAMLIT_SERVER_ADDRESS } else { "0.0.0.0" }
$streamlitPort = if ($env:STREAMLIT_SERVER_PORT) { $env:STREAMLIT_SERVER_PORT } else { "8501" }
Write-Host "Streamlit: http://127.0.0.1:$streamlitPort"
Write-Host "原生驾驶舱: $env:LOCUST_BACKEND_URL"
$lanIps = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Select-Object -ExpandProperty IPAddress
foreach ($ip in $lanIps) {
    Write-Host "局域网入口: http://${ip}:$streamlitPort"
}
& $VenvPython -m streamlit run streamlit_app.py --server.address $streamlitAddress --server.port $streamlitPort

if ($null -ne $backend -and -not $backend.HasExited) {
    Stop-Process -Id $backend.Id -Force
}
