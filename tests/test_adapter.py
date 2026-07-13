from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from captivity_simulator.adapter import request_assistant


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


class AdapterTest(unittest.TestCase):
    def test_uses_labeled_user_envelope_and_resolves_reference_tool(self) -> None:
        requests: list[dict] = []
        responses = iter([
            {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "captivity_simulator_reference",
                                "arguments": '{"分类":"喂食"}',
                            },
                        }],
                    }
                }]
            },
            {"choices": [{"message": {"role": "assistant", "content": "【今日安排：...】"}}]},
        ])

        def fake_urlopen(req, timeout=0):
            requests.append(json.loads(req.data.decode("utf-8")))
            return _Response(next(responses))

        config = {
            "ai": {
                "enabled": True,
                "base_url": "https://example.invalid/v1",
                "api_key_env": "TEST_CAPTIVITY_KEY",
                "model": "test-model",
            }
        }
        with patch.dict("os.environ", {"TEST_CAPTIVITY_KEY": "secret"}), patch(
            "captivity_simulator.adapter.request.urlopen", side_effect=fake_urlopen
        ):
            reply = request_assistant("当前事件", config, player_message="我想说的话")

        self.assertEqual(reply, "【今日安排：...】")
        system_message, player_message = requests[0]["messages"]
        self.assertEqual(system_message, {"role": "system", "content": "当前事件"})
        self.assertEqual(player_message["role"], "user")
        self.assertEqual(player_message["content"], "（囚禁模拟器频道）\n{user}：我想说的话")
        self.assertEqual(requests[0]["tools"][0]["function"]["name"], "captivity_simulator_reference")
        self.assertEqual(requests[1]["messages"][-1]["role"], "tool")
        self.assertIn("始终包含一份正常食物", requests[1]["messages"][-1]["content"])

    def test_no_player_text_uses_explicit_channel_system_notice(self) -> None:
        captured: dict = {}

        def fake_urlopen(req, timeout=0):
            captured.update(json.loads(req.data.decode("utf-8")))
            return _Response({"choices": [{"message": {"role": "assistant", "content": "ok"}}]})

        config = {
            "actors": {"user": "Player", "assistant": "Partner"},
            "ai": {
                "enabled": True,
                "base_url": "https://example.invalid/v1",
                "api_key_env": "TEST_CAPTIVITY_KEY",
                "model": "test-model",
            },
        }
        with patch.dict("os.environ", {"TEST_CAPTIVITY_KEY": "secret"}), patch(
            "captivity_simulator.adapter.request.urlopen", side_effect=fake_urlopen
        ):
            self.assertEqual(request_assistant("当前事件", config), "ok")

        self.assertEqual(
            captured["messages"][-1]["content"],
            "（囚禁模拟器频道系统提示）Player没有发文字消息给你",
        )


if __name__ == "__main__":
    unittest.main()
