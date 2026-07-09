from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any, Callable


@dataclass(frozen=True)
class AIAnalysisRequest:
    task: str
    payload: dict[str, Any]
    locale: str = "zh-CN"


@dataclass(frozen=True)
class AIProviderResponse:
    provider: str
    content: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class AIConsensusResult:
    task: str
    responses: tuple[AIProviderResponse, ...]
    consensus: str


Transport = Callable[[str, dict[str, str], dict[str, Any], int], dict[str, Any]]


class AIConsensusError(RuntimeError):
    pass


class OpenAICompatibleProvider:
    def __init__(
        self,
        name: str,
        endpoint: str,
        model: str,
        api_key: str,
        transport: Transport | None = None,
        api_format: str = "chat",
    ) -> None:
        self.name = name
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key
        self.api_format = api_format
        self.transport = transport or _post_json

    def analyze(self, request: AIAnalysisRequest, timeout: int = 60) -> AIProviderResponse:
        body = _build_request_body(self.model, request, self.api_format)
        raw = self.transport(
            self.endpoint,
            {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            body,
            timeout,
        )
        content = _extract_model_content(raw)
        return AIProviderResponse(provider=self.name, content=content, raw=raw)


class DualAIAnalysisLayer:
    def __init__(self, providers: tuple[OpenAICompatibleProvider, ...], require_all: bool = True) -> None:
        if len(providers) < 2:
            raise ValueError("必须至少配置两个 AI 分析提供方。")
        self.providers = providers
        self.require_all = require_all

    def analyze(self, request: AIAnalysisRequest) -> AIConsensusResult:
        responses: list[AIProviderResponse] = []
        failures: list[str] = []
        for provider in self.providers:
            try:
                responses.append(provider.analyze(request))
            except Exception as exc:
                failures.append(f"{provider.name}: {type(exc).__name__}")

        if failures and self.require_all:
            raise AIConsensusError("双 AI 分析未完成：" + "；".join(failures))
        if len(responses) < 2:
            raise AIConsensusError("有效 AI 响应不足两个，拒绝输出单模型分析。")

        return AIConsensusResult(
            task=request.task,
            responses=tuple(responses),
            consensus=_build_consensus_summary(responses),
        )


def _build_request_body(model: str, request: AIAnalysisRequest, api_format: str) -> dict[str, Any]:
    system_text = (
        "你是蝗虫计划的交易分析审查员。只基于输入数据判断结构、资金、风险与执行条件；"
        "不要编造行情，不要替代真实数据源，不构成投资建议。"
    )
    user_text = json.dumps(
        {"task": request.task, "locale": request.locale, "payload": _json_safe(request.payload)},
        ensure_ascii=False,
    )
    if api_format == "responses":
        return {
            "model": model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": f"{system_text}\n\n{user_text}"},
                    ],
                }
            ],
            "temperature": 0.2,
            "max_output_tokens": 1024,
        }
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_text,
            },
            {
                "role": "user",
                "content": user_text,
            },
        ],
        "temperature": 0.2,
    }


def build_default_dual_ai_layer(transport: Transport | None = None) -> DualAIAnalysisLayer:
    deepseek_key = load_ai_api_key("deepseek")
    doubao_key = load_ai_api_key("doubao")
    doubao_endpoint = os.environ.get("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/responses")
    return DualAIAnalysisLayer(
        providers=(
            OpenAICompatibleProvider(
                name="DeepSeek",
                endpoint=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions"),
                model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                api_key=deepseek_key,
                transport=transport,
            ),
            OpenAICompatibleProvider(
                name="Doubao",
                endpoint=doubao_endpoint,
                model=os.environ.get("DOUBAO_MODEL", "doubao-seed-2-0-pro-260215"),
                api_key=doubao_key,
                api_format=_infer_api_format(doubao_endpoint),
                transport=transport,
            ),
        ),
        require_all=True,
    )


def analyze_with_required_consensus(task: str, payload: dict[str, Any], locale: str = "zh-CN") -> AIConsensusResult:
    layer = build_default_dual_ai_layer()
    return layer.analyze(AIAnalysisRequest(task=task, payload=payload, locale=locale))


def load_ai_api_key(provider: str) -> str:
    normalized = provider.lower()
    env_names = {
        "deepseek": ("DEEPSEEK_API_KEY",),
        "doubao": ("DOUBAO_API_KEY", "ARK_API_KEY"),
    }.get(normalized)
    if env_names is None:
        raise AIConsensusError(f"未知 AI 提供方：{provider}")

    for name in env_names:
        value = os.environ.get(name)
        if value:
            return value

    raise AIConsensusError(f"未找到 {provider} API key。")


def _post_json(url: str, headers: dict[str, str], body: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise AIConsensusError(f"AI 服务返回 HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise AIConsensusError("AI 服务网络连接失败。") from exc


def _infer_api_format(endpoint: str) -> str:
    return "responses" if endpoint.rstrip("/").endswith("/responses") else "chat"


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _extract_model_content(raw: dict[str, Any]) -> str:
    output_text = raw.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    choices = raw.get("choices")
    if not isinstance(choices, list) or not choices:
        output = raw.get("output")
        if isinstance(output, list):
            text = _extract_responses_output_text(output)
            if text:
                return text
        raise AIConsensusError("AI 响应缺少 choices 或 output。")

    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    raise AIConsensusError("AI 响应内容为空。")


def _extract_responses_output_text(output: list[Any]) -> str | None:
    chunks: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        summary = item.get("summary")
        if isinstance(summary, list):
            for part in summary:
                if not isinstance(part, dict):
                    continue
                text = part.get("text") or part.get("content")
                if isinstance(text, str) and text.strip():
                    chunks.append(text.strip())
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            text = part.get("text") or part.get("content")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
    return "\n".join(chunks) if chunks else None


def _build_consensus_summary(responses: list[AIProviderResponse]) -> str:
    return "\n\n".join(f"{item.provider}:\n{item.content}" for item in responses)
