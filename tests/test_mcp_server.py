from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from captivity_simulator.mcp_server import RESOURCE_URI, TOOL_NAME, handle_request


class McpServerTest(unittest.TestCase):
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
        self.assertEqual(result["structuredContent"]["state"]["route"], "captured_by_assistant")
        self.assertEqual(result["structuredContent"]["state"]["viewer"], "captor")
        self.assertIn("captor_view", result["structuredContent"])
        self.assertNotIn("captive_view", result["structuredContent"])
        self.assertTrue(result["content"][0]["text"])

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
        self.assertEqual(payload["state"]["viewer"], "captive")
        self.assertIn("captive_view", payload)
        self.assertNotIn("captor_view", payload)

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


if __name__ == "__main__":
    unittest.main()
