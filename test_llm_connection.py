from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from local_env import load_local_env


def main() -> int:
    load_local_env()
    checks = [
        (
            "DeepSeek",
            os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions"),
            os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            os.environ.get("DEEPSEEK_API_KEY"),
        ),
        (
            "豆包/火山方舟",
            os.environ.get("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/responses"),
            os.environ.get("DOUBAO_MODEL", "doubao-seed-2-0-pro-260215"),
            os.environ.get("ARK_API_KEY") or os.environ.get("DOUBAO_API_KEY"),
        ),
    ]
    failed = False
    for name, endpoint, model, api_key in checks:
        if not api_key:
            print(f"[FAIL] {name}: 缺少环境变量 API Key")
            failed = True
            continue
        try:
            content = call_openai_compatible(endpoint, model, api_key)
        except Exception as exc:
            print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
            failed = True
        else:
            print(f"[OK] {name}: 模型 {model} 连接成功，返回 {len(content)} 个字符")
    return 1 if failed else 0


def call_openai_compatible(endpoint: str, model: str, api_key: str) -> str:
    body = build_test_body(endpoint, model)
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:200]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    choices = payload.get("choices")
    if not choices:
        content = extract_responses_content(payload)
        if content:
            return content
        raise RuntimeError("响应缺少 choices 或 output")
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("响应内容为空")
    return content


def build_test_body(endpoint: str, model: str) -> dict[str, object]:
    if endpoint.rstrip("/").endswith("/responses"):
        return {
            "model": model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "连接测试，只返回 OK。"},
                    ],
                }
            ],
            "temperature": 0,
            "max_output_tokens": 256,
        }
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "只返回 OK。"},
            {"role": "user", "content": "连接测试"},
        ],
        "temperature": 0,
        "max_tokens": 16,
    }


def extract_responses_content(payload: dict[str, object]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    output = payload.get("output")
    if not isinstance(output, list):
        return ""
    chunks: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            text = part.get("text") or part.get("content")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
    return "\n".join(chunks)


if __name__ == "__main__":
    raise SystemExit(main())
