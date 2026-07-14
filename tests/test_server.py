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

    def test_initial_captive_plan_persists_and_plain_refresh_recovers_first_action(self) -> None:
        app = create_app()

        def fake_assistant(_prompt: str, _config: dict, player_message: str = "") -> str:
            return "【今日安排：行动=喂食 强度=低 || 行动=清洗 强度=低 || 行动=看管休息 强度=低 内容=安静待着】"

        with tempfile.TemporaryDirectory() as directory, patch(
            "captivity_simulator.server._save_path",
            side_effect=lambda save_id: Path(directory) / f"{save_id}.json",
        ), patch("captivity_simulator.server.request_assistant", side_effect=fake_assistant):
            with app.test_client() as client:
                client.post(
                    "/api/game/command",
                    json={"save_id": "initial", "command": "new_game route=captured_by_assistant"},
                )
                synced = client.post("/api/game/sync-assistant", json={"save_id": "initial"})
                refreshed = client.post(
                    "/api/game/command",
                    json={"save_id": "initial", "command": "status"},
                )
        self.assertEqual(synced.status_code, 200)
        self.assertEqual(synced.get_json()["state"]["pending_event"]["type"], "action_response")
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(refreshed.get_json()["state"]["pending_event"]["type"], "action_response")
        self.assertEqual(refreshed.get_json()["state"]["pending_event"]["event"]["action"], "feeding")

    def test_rejected_initial_plan_returns_error_and_stays_pending(self) -> None:
        app = create_app()

        def fake_assistant(_prompt: str, _config: dict, player_message: str = "") -> str:
            return "【今日安排：行动=喂食 强度=低 || 行动=清洗 强度=低 || 行动=看管休息 强度=低 内容=安静独处】"

        with tempfile.TemporaryDirectory() as directory, patch(
            "captivity_simulator.server._save_path",
            side_effect=lambda save_id: Path(directory) / f"{save_id}.json",
        ), patch("captivity_simulator.server.request_assistant", side_effect=fake_assistant):
            with app.test_client() as client:
                client.post(
                    "/api/game/command",
                    json={"save_id": "rejected", "command": "new_game route=captured_by_assistant"},
                )
                synced = client.post("/api/game/sync-assistant", json={"save_id": "rejected"})
                refreshed = client.post(
                    "/api/game/command",
                    json={"save_id": "rejected", "command": "status"},
                )
        self.assertEqual(synced.status_code, 400)
        self.assertFalse(synced.get_json()["ok"])
        self.assertEqual(refreshed.get_json()["state"]["pending_event"]["type"], "day_plan_choice")

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

    def test_scheduled_escape_is_delivered_as_a_bounded_followup_chain(self) -> None:
        app = create_app()

        def payload(pending: dict) -> dict:
            state = {
                "route": "capture_assistant",
                "captor": "user",
                "captive": "assistant",
                "current_day": 2,
                "total_days": 30,
                "day_action_count": 0,
                "phase": "day",
                "stats": {"health": 80, "stamina": 70, "cleanliness": 70, "shame": 20, "intimacy": 20},
                "pending_event": pending,
                "event_log": [],
            }
            return {
                "ok": True,
                "state": state,
                "captor_view": {**state, "viewer": "captor"},
                "captive_view": {**state, "viewer": "captive"},
            }

        night_event = {
            "id": "night-process",
            "day": 1,
            "slot": 0,
            "phase": "night",
            "action": "training",
            "action_label": "夜间介入",
            "tags": ["night"],
        }
        escape_event = {
            "id": "escape-process",
            "day": 2,
            "slot": 0,
            "phase": "day",
            "action": "escape_choice",
            "action_label": "逃跑诱导：尝试逃跑",
            "tags": ["escape", "recapture"],
        }
        payloads = [
            payload({"type": "process_reaction_write", "actor": "assistant", "event": night_event}),
            payload({"type": "escape_choice", "actor": "assistant", "hint": "今天出去了", "bait": "钥匙在玄关"}),
            payload({"type": "process_reaction_write", "actor": "assistant", "event": escape_event}),
            payload({"type": "recapture_rules_choice", "actor": "user", "event": escape_event}),
        ]
        commands: list[str] = []
        replies = iter([
            "【过程心情：回应=接受 心情=平静】\n【过程】\n【【昨晚的经过。】】",
            "【选择：尝试逃跑】",
            "【过程心情：回应=拒绝 心情=烦躁】\n【过程】\n【【抓回经过。】】",
        ])

        def fake_run(command: str, save_path: Path) -> dict:
            if command == "status":
                return payloads[0]
            commands.append(command)
            return payloads[len(commands)]

        with patch("captivity_simulator.server.run_command", side_effect=fake_run), patch(
            "captivity_simulator.server.request_assistant",
            side_effect=lambda *args, **kwargs: next(replies),
        ):
            with app.test_client() as client:
                response = client.post("/api/game/sync-assistant", json={"save_id": "escape"})

        result = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(commands), 3)
        self.assertTrue(commands[0].startswith("submit_process_reaction "))
        self.assertEqual(commands[1], "resolve_escape_choice escape")
        self.assertTrue(commands[2].startswith("submit_process_reaction "))
        self.assertEqual(result["state"]["pending_event"]["type"], "recapture_rules_choice")

    def test_high_risk_night_followups_finish_without_manual_retry(self) -> None:
        def payload(pending_type: str, actor: str, *, route: str) -> dict:
            pending = {"type": pending_type, "actor": actor} if pending_type else None
            state = {
                "route": route,
                "captor": "assistant" if route == "captured_by_assistant" else "user",
                "captive": "user" if route == "captured_by_assistant" else "assistant",
                "current_day": 2,
                "total_days": 30,
                "day_action_count": 0,
                "phase": "night" if pending_type in {"monitor_gate", "monitor_handle", "bell_response_choice", "night_action_choice", "item_secret_reveal"} else "day",
                "stats": {"health": 80, "stamina": 70, "cleanliness": 70, "shame": 20, "intimacy": 20},
                "pending_event": pending,
                "event_log": [],
            }
            return {
                "ok": True,
                "state": state,
                "captor_view": {**state, "viewer": "captor"},
                "captive_view": {**state, "viewer": "captive"},
            }

        scenarios = [
            {
                "name": "monitor_skip_to_next_plan",
                "route": "captured_by_assistant",
                "types": [("monitor_gate", "assistant"), ("day_plan_choice", "assistant"), ("action_response", "user")],
                "replies": [
                    "【选择：不看】",
                    "【今日安排：action=feeding || action=cleaning || action=rest contents=quiet_time】",
                ],
            },
            {
                "name": "opened_monitor_to_next_plan",
                "route": "captured_by_assistant",
                "types": [("monitor_gate", "assistant"), ("monitor_handle", "assistant"), ("day_plan_choice", "assistant"), ("action_response", "user")],
                "replies": [
                    "【查看监控：全程看】",
                    "【选择：看见但不说】",
                    "【今日安排：action=feeding || action=cleaning || action=rest contents=quiet_time】",
                ],
            },
            {
                "name": "bell_skip_to_next_plan",
                "route": "captured_by_assistant",
                "types": [("bell_response_choice", "assistant"), ("day_plan_choice", "assistant"), ("action_response", "user")],
                "replies": [
                    "【选择：不过去】",
                    "【今日安排：action=feeding || action=cleaning || action=rest contents=quiet_time】",
                ],
            },
            {
                "name": "two_item_discoveries",
                "route": "capture_assistant",
                "types": [("night_action_choice", "assistant"), ("item_secret_reveal", "assistant"), ("item_secret_reveal", "assistant"), ("monitor_gate", "user")],
                "replies": ["【夜间行动：action=sleep】", "【确认彩蛋】", "【确认彩蛋】"],
            },
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                payloads = [payload(item_type, actor, route=scenario["route"]) for item_type, actor in scenario["types"]]
                commands: list[str] = []
                replies = iter(scenario["replies"])

                def fake_run(command: str, save_path: Path) -> dict:
                    if command == "status":
                        return payloads[0]
                    commands.append(command)
                    return payloads[len(commands)]

                with patch("captivity_simulator.server.run_command", side_effect=fake_run), patch(
                    "captivity_simulator.server.request_assistant",
                    side_effect=lambda *args, **kwargs: next(replies),
                ):
                    with create_app().test_client() as client:
                        response = client.post("/api/game/sync-assistant", json={"save_id": scenario["name"]})

                result = response.get_json()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(commands), len(scenario["replies"]))
                self.assertEqual(result["state"]["pending_event"]["type"], scenario["types"][-1][0])

    def test_gifting_does_not_force_an_unrelated_assistant_sync(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "web" / "src" / "CaptivitySimulator.tsx").read_text(encoding="utf-8")
        gift_block = source.split("function applyInventoryItem", 1)[1].split("function closeSubpage", 1)[0]
        self.assertIn("gift_item", gift_block)
        self.assertNotIn("continueAutomaticSync", gift_block)
        self.assertIn("note=${quoteArg(note)}", gift_block)

    def test_route_startup_keeps_captive_loading_and_never_syncs_captor(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "web" / "src" / "CaptivitySimulator.tsx").read_text(encoding="utf-8")
        start_block = source.split("function startRoute", 1)[1].split("function returnToSelector", 1)[0]
        self.assertIn('if (nextRoute === "captured_by_assistant")', start_block)
        self.assertIn("startCapturedRoute", start_block)
        self.assertIn('syncCaptivityToAssistant("state_update", "", true)', start_block)
        self.assertNotIn("syncInitialAssistantDayPlan", source)
        self.assertIn('executeCaptivityCommand("new_game route=capture_assistant")', start_block)
        captor_start = start_block.split('executeCaptivityCommand("new_game route=capture_assistant")', 1)[1]
        self.assertNotIn("syncCaptivityToAssistant", captor_start)
        self.assertIn("isWaitingForAssistantDayPlan(next)", source)
        self.assertIn("STATUS: WAITING_FOR_DAY_PLAN", source)

    def test_assistant_reply_cannot_advance_a_user_owned_pending(self) -> None:
        def payload(route: str, pending_type: str, actor: str, *, inventory: dict | None = None) -> dict:
            state = {
                "route": route,
                "captor": "assistant" if route == "captured_by_assistant" else "user",
                "captive": "user" if route == "captured_by_assistant" else "assistant",
                "current_day": 2,
                "total_days": 30,
                "day_action_count": 1,
                "phase": "night" if pending_type == "monitor_gate" else "day",
                "stats": {"health": 80, "stamina": 70, "cleanliness": 70, "shame": 20, "intimacy": 20},
                "inventory": inventory or {},
                "pending_event": {"type": pending_type, "actor": actor},
                "event_log": [],
            }
            return {
                "ok": True,
                "state": state,
                "captor_view": {**state, "viewer": "captor"},
                "captive_view": {**state, "viewer": "captive"},
            }

        monitor_payload = payload("capture_assistant", "monitor_gate", "user")
        monitor_commands: list[str] = []

        def monitor_run(command: str, save_path: Path) -> dict:
            if command == "status":
                return monitor_payload
            monitor_commands.append(command)
            raise AssertionError(f"user-owned monitor should not execute assistant command: {command}")

        with patch("captivity_simulator.server.run_command", side_effect=monitor_run), patch(
            "captivity_simulator.server.request_assistant",
            return_value="【查看监控：全程看】",
        ):
            with create_app().test_client() as client:
                monitor_response = client.post("/api/game/sync-assistant", json={"save_id": "local-monitor", "message": "我还没选择"})
        self.assertEqual(monitor_response.status_code, 200)
        self.assertEqual(monitor_commands, [])
        self.assertEqual(monitor_response.get_json()["state"]["pending_event"]["type"], "monitor_gate")

        before_gift = payload("captured_by_assistant", "action_response", "user")
        after_gift = payload("captured_by_assistant", "action_response", "user", inventory={"notebook": True})
        gift_commands: list[str] = []

        def gift_run(command: str, save_path: Path) -> dict:
            if command == "status":
                return before_gift
            gift_commands.append(command)
            return after_gift

        with patch("captivity_simulator.server.run_command", side_effect=gift_run), patch(
            "captivity_simulator.server.request_assistant",
            return_value="【赠送物品：notebook】",
        ):
            with create_app().test_client() as client:
                gift_response = client.post("/api/game/sync-assistant", json={"save_id": "out-of-band-gift", "message": "局内附言"})
        self.assertEqual(gift_response.status_code, 200)
        self.assertEqual(gift_commands, ["gift_item items=notebook"])
        self.assertEqual(gift_response.get_json()["state"]["pending_event"]["type"], "action_response")


if __name__ == "__main__":
    unittest.main()
