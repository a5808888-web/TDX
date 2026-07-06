import unittest
from unittest.mock import patch

from ai_consensus_layer import (
    AIAnalysisRequest,
    AIConsensusError,
    DualAIAnalysisLayer,
    OpenAICompatibleProvider,
    build_default_dual_ai_layer,
    load_ai_api_key,
)


class AIConsensusLayerTest(unittest.TestCase):
    def test_requires_two_successful_ai_responses(self):
        calls = []

        def transport(url, headers, body, timeout):
            calls.append((url, headers, body, timeout))
            return {"choices": [{"message": {"content": f"ok from {body['model']}"}}]}

        layer = DualAIAnalysisLayer(
            providers=(
                OpenAICompatibleProvider("DeepSeek", "https://deepseek.test", "deepseek-chat", "deepseek-redacted", transport),
                OpenAICompatibleProvider("Doubao", "https://doubao.test", "doubao", "doubao-redacted", transport),
            )
        )
        result = layer.analyze(AIAnalysisRequest(task="复盘", payload={"symbol": "NVDA"}))

        self.assertEqual(len(result.responses), 2)
        self.assertIn("DeepSeek", result.consensus)
        self.assertIn("Doubao", result.consensus)
        self.assertEqual(calls[0][1]["Authorization"], "Bearer deepseek-redacted")
        self.assertEqual(calls[1][1]["Authorization"], "Bearer doubao-redacted")

    def test_rejects_single_model_result_when_one_provider_fails(self):
        def ok_transport(url, headers, body, timeout):
            if "doubao" in url:
                raise RuntimeError("down")
            return {"choices": [{"message": {"content": "ok"}}]}

        layer = DualAIAnalysisLayer(
            providers=(
                OpenAICompatibleProvider("DeepSeek", "https://deepseek.test", "deepseek-chat", "deepseek-redacted", ok_transport),
                OpenAICompatibleProvider("Doubao", "https://doubao.test", "doubao", "doubao-redacted", ok_transport),
            )
        )

        with self.assertRaisesRegex(AIConsensusError, "双 AI 分析未完成"):
            layer.analyze(AIAnalysisRequest(task="复盘", payload={}))

    def test_provider_supports_responses_endpoint_shape(self):
        calls = []

        def transport(url, headers, body, timeout):
            calls.append(body)
            return {"output_text": "OK"}

        provider = OpenAICompatibleProvider(
            "Doubao",
            "https://ark.cn-beijing.volces.com/api/v3/responses",
            "doubao-seed-2-0-pro-260215",
            "doubao-redacted",
            transport,
            api_format="responses",
        )
        result = provider.analyze(AIAnalysisRequest(task="检查", payload={"symbol": "601138.SH"}))

        self.assertEqual(result.content, "OK")
        self.assertIn("input", calls[0])
        self.assertNotIn("messages", calls[0])

    def test_default_layer_loads_provider_specific_keys(self):
        with patch.dict(
            "os.environ",
            {"DEEPSEEK_API_KEY": "deepseek-test-key", "ARK_API_KEY": "doubao-test-key"},
            clear=True,
        ):
            self.assertEqual(load_ai_api_key("deepseek"), "deepseek-test-key")
            self.assertEqual(load_ai_api_key("doubao"), "doubao-test-key")

            layer = build_default_dual_ai_layer(
                transport=lambda url, headers, body, timeout: {"choices": [{"message": {"content": "ok"}}]}
            )
            result = layer.analyze(AIAnalysisRequest(task="检查", payload={"score": 80}))

        self.assertEqual(len(result.responses), 2)

    def test_default_layer_rejects_missing_environment_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(AIConsensusError, "未找到 deepseek API key"):
                load_ai_api_key("deepseek")


if __name__ == "__main__":
    unittest.main()
