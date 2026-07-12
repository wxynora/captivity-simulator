from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from captivity_simulator.server import create_app


class ServerTest(unittest.TestCase):
    def test_command_endpoint_uses_local_save(self) -> None:
        app = create_app()
        with tempfile.TemporaryDirectory() as directory, patch(
            "captivity_simulator.server._save_path",
            side_effect=lambda save_id: Path(directory) / f"{save_id}.json",
        ):
            with app.test_client() as client:
                response = client.post("/api/game/command", json={"command": "new_game route=captured_by_assistant"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])

    def test_disabled_adapter_returns_prompt_without_network(self) -> None:
        app = create_app()
        with tempfile.TemporaryDirectory() as directory, patch(
            "captivity_simulator.server._save_path",
            side_effect=lambda save_id: Path(directory) / f"{save_id}.json",
        ):
            with app.test_client() as client:
                client.post("/api/game/command", json={"command": "new_game route=captured_by_assistant"})
                response = client.post("/api/game/sync-assistant", json={"save_id": "default"})
        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        self.assertEqual(payload["sync_result"], "adapter_required")
        self.assertIn("【游戏状态】", payload["prompt"])


if __name__ == "__main__":
    unittest.main()
