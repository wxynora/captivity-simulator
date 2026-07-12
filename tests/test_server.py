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

    def test_disabled_adapter_keeps_assistant_prompt_out_of_player_response(self) -> None:
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
        self.assertNotIn("prompt", payload)
        self.assertNotIn("reply_text", payload)
        self.assertNotIn("reply_preview", payload)
        self.assertEqual(payload["state"]["viewer"], "captive")
        self.assertNotIn("captor_view", payload)

    def test_http_projects_only_the_player_route_view(self) -> None:
        app = create_app()
        with tempfile.TemporaryDirectory() as directory, patch(
            "captivity_simulator.server._save_path",
            side_effect=lambda save_id: Path(directory) / f"{save_id}.json",
        ):
            with app.test_client() as client:
                captive = client.post("/api/game/command", json={"command": "new_game route=captured_by_assistant"}).get_json()
                captor = client.post("/api/game/command", json={"save_id": "captor", "command": "new_game route=capture_assistant"}).get_json()
        self.assertEqual(captive["state"]["viewer"], "captive")
        self.assertIn("captive_view", captive)
        self.assertNotIn("captor_view", captive)
        self.assertEqual(captor["state"]["viewer"], "captor")
        self.assertIn("captor_view", captor)
        self.assertNotIn("captive_view", captor)


if __name__ == "__main__":
    unittest.main()
