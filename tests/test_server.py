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

    def test_capture_assistant_day_batch_uses_one_assistant_sync(self) -> None:
        app = create_app()
        assistant_calls: list[str] = []

        def fake_assistant(prompt: str, _config: dict, player_message: str = "") -> str:
            assistant_calls.append(prompt)
            return (
                "【第1段：response=accept mood=平静 line=】\n第一段简短回应。\n"
                "【第2段：response=bargain mood=烦躁 line=别得意】\n"
                "【过程2】\n【【第二段完整经过。】】\n"
                "【第3段：response=silent mood=疲惫 line=】\n第三段简短回应。"
            )

        with tempfile.TemporaryDirectory() as directory, patch(
            "captivity_simulator.server._save_path",
            side_effect=lambda save_id: Path(directory) / f"{save_id}.json",
        ), patch("captivity_simulator.server.request_assistant", side_effect=fake_assistant):
            with app.test_client() as client:
                client.post("/api/game/command", json={"save_id": "batch", "command": "new_game route=capture_assistant"})
                planned = client.post(
                    "/api/game/command",
                    json={
                        "save_id": "batch",
                        "command": (
                            "plan_day action=feeding source=cook additive=none || "
                            "action=training training_contents=obedience_commands modifiers=training tools=collar || "
                            "action=cleaning"
                        ),
                    },
                ).get_json()
                self.assertEqual(planned["state"]["pending_event"]["type"], "day_batch_response")
                first = client.post("/api/game/sync-assistant", json={"save_id": "batch"}).get_json()
                self.assertEqual(len(assistant_calls), 1)
                self.assertEqual(first["state"]["pending_event"]["type"], "advance_action")
                second = client.post(
                    "/api/game/command",
                    json={"save_id": "batch", "command": "advance_day_action"},
                ).get_json()
                self.assertEqual(len(assistant_calls), 1)
                self.assertEqual(second["state"]["pending_event"]["type"], "advance_action")
                third = client.post(
                    "/api/game/command",
                    json={"save_id": "batch", "command": "advance_day_action"},
                ).get_json()
                self.assertEqual(len(assistant_calls), 1)
                self.assertEqual(third["state"]["pending_event"]["type"], "advance_to_night")
                self.assertEqual(third["state"]["phase"], "day")
                night = client.post(
                    "/api/game/command",
                    json={"save_id": "batch", "command": "advance_day_action"},
                ).get_json()
                self.assertEqual(len(assistant_calls), 1)
                self.assertEqual(night["state"]["pending_event"]["type"], "night_action_choice")


if __name__ == "__main__":
    unittest.main()
