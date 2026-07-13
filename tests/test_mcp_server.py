from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from captivity_simulator.mcp_server import REFERENCE_TOOL_NAME, RESOURCE_URI, TOOL_NAME, handle_request


class McpServerTest(unittest.TestCase):
    def test_lists_and_calls_read_only_reference_tool(self) -> None:
        listed = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = [item["name"] for item in listed["result"]["tools"]]
        self.assertIn(REFERENCE_TOOL_NAME, names)

        called = handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": REFERENCE_TOOL_NAME, "arguments": {"分类": "喂食"}},
        })
        self.assertIn("来源：自己做、点外卖", called["result"]["structuredContent"]["text"])
        self.assertEqual(called["result"]["content"][0]["text"], called["result"]["structuredContent"]["text"])

    def test_lists_simulator_tool(self) -> None:
        response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        self.assertIsNotNone(response)
        tool = response["result"]["tools"][0]
        self.assertEqual(tool["name"], TOOL_NAME)
        self.assertEqual(tool["inputSchema"]["required"], ["command"])

    def test_calls_engine_with_structured_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch(
            "captivity_simulator.mcp_server._save_path",
            side_effect=lambda save_id: Path(directory) / f"{save_id}.json",
        ):
            response = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": TOOL_NAME,
                        "arguments": {
                            "command": "new_game route=captured_by_assistant",
                            "save_id": "mcp-test",
                        },
                    },
                }
            )
        self.assertIsNotNone(response)
        result = response["result"]
        self.assertTrue(result["structuredContent"]["ok"])
        visible = result["content"][0]["text"]
        self.assertEqual(visible, result["structuredContent"]["text"])
        self.assertIn("【今日安排：行动=", visible)
        self.assertNotIn("action=", visible)
        self.assertNotIn("day_plan_choice", visible)
        self.assertNotIn("required_directive", visible)

    def test_mcp_projects_assistant_captive_view_on_captor_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch(
            "captivity_simulator.mcp_server._save_path",
            side_effect=lambda save_id: Path(directory) / f"{save_id}.json",
        ):
            response = handle_request({
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": TOOL_NAME,
                    "arguments": {"command": "new_game route=capture_assistant", "save_id": "captor-route"},
                },
            })
        payload = response["result"]["structuredContent"]
        self.assertTrue(payload["ok"])
        self.assertIn("你被", payload["text"])
        self.assertNotIn("capture_assistant", payload["text"])

    def test_mcp_accepts_current_chinese_directive(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch(
            "captivity_simulator.mcp_server._save_path",
            side_effect=lambda save_id: Path(directory) / f"{save_id}.json",
        ):
            handle_request({
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": TOOL_NAME,
                    "arguments": {"command": "new_game route=captured_by_assistant", "save_id": "zh-directive"},
                },
            })
            response = handle_request({
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {
                    "name": TOOL_NAME,
                    "arguments": {
                        "command": "【今日安排：行动=喂食 强度=中 || 行动=清洗 强度=低 || 行动=服从调教 强度=中 调教=口令服从】",
                        "save_id": "zh-directive",
                    },
                },
            })
        self.assertTrue(response["result"]["structuredContent"]["ok"])
        self.assertNotIn("action=", response["result"]["content"][0]["text"])

    def test_reads_default_save_resource(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch(
            "captivity_simulator.mcp_server._save_path",
            side_effect=lambda save_id: Path(directory) / f"{save_id}.json",
        ):
            response = handle_request(
                {"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": RESOURCE_URI}}
            )
        self.assertIsNotNone(response)
        payload = json.loads(response["result"]["contents"][0]["text"])
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["game_id"], "captivity_simulator")
        self.assertNotIn("required_directive", json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
