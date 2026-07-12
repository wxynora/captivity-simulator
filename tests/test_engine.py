from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from captivity_simulator.configuration import render_placeholders
from captivity_simulator.engine import _active_night_condition, _advance_after_day_event, _new_state, _resolve_event, run_command
from captivity_simulator.prompts import build_assistant_prompt
from captivity_simulator.protocol import directive_to_command


class EngineTest(unittest.TestCase):
    @staticmethod
    def _force_night(save_path: Path) -> None:
        state = json.loads(save_path.read_text(encoding="utf-8"))
        state["phase"] = "night"
        state["day_action_count"] = 3
        state["pending_event"] = None
        save_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    def test_both_routes_start_with_generic_actor_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = run_command("new_game route=captured_by_assistant", Path(directory) / "first.json")
            second = run_command("new_game route=capture_assistant", Path(directory) / "second.json")
        self.assertTrue(first["ok"])
        self.assertEqual(first["captor_view"]["captor"], "assistant")
        self.assertEqual(first["captive_view"]["captive"], "user")
        self.assertTrue(second["ok"])
        self.assertEqual(second["captor_view"]["captor"], "user")
        self.assertEqual(second["captive_view"]["captive"], "assistant")

    def test_placeholder_rendering_is_recursive(self) -> None:
        config = {"actors": {"user": "Player", "assistant": "Partner"}}
        value = {"line": "{user} / {assistant}", "items": ["{assistant}"]}
        self.assertEqual(render_placeholders(value, config), {"line": "Player / Partner", "items": ["Partner"]})

    def test_directive_parser_uses_pending_context(self) -> None:
        payload = {"state": {"pending_event": {"type": "escape_choice"}}}
        self.assertEqual(directive_to_command("【选择：escape】", payload), "resolve_escape_choice escape")
        process_payload = {"state": {"pending_event": {"type": "process_reaction_write"}}}
        self.assertEqual(
            directive_to_command("【过程：response=accept mood=平静 process=正文】", process_payload),
            "submit_process_reaction response=accept mood=平静 process=正文",
        )

    def test_voice_bell_replays_line_and_keeps_it_in_assistant_context(self) -> None:
        config = {
            "actors": {"user": "Player", "assistant": "Partner"},
            "prompt": {"route_openings": {"captured_by_assistant": "opening"}},
        }
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "bell.json"
            run_command("new_game route=captured_by_assistant", save_path)
            gifted = run_command("gift_item items=call_bell voice_line='每次都要播放这句'", save_path)
            self.assertTrue(gifted["ok"])

            self._force_night(save_path)
            first = run_command("night_action action=ring_bell", save_path)
            self.assertEqual(first["captive_view"]["pending_event"]["type"], "bell_voice_reveal")
            self.assertEqual(first["captive_view"]["pending_event"]["event"]["bell_voice"]["line"], "每次都要播放这句")
            run_command("ack_bell_voice", save_path)
            run_command("respond_bell choice=skip", save_path)

            self._force_night(save_path)
            second = run_command("night_action action=ring_bell", save_path)
            second_pending = second["captive_view"]["pending_event"]
            self.assertEqual(second_pending["type"], "bell_voice_reveal")
            self.assertFalse(second_pending["event"]["bell_voice"]["first_reveal"])
            self.assertEqual(second_pending["event"]["bell_voice"]["line"], "每次都要播放这句")

            acknowledged = run_command("ack_bell_voice", save_path)
            assistant_pending = acknowledged["captor_view"]["pending_event"]
            self.assertEqual(assistant_pending["type"], "bell_response_choice")
            self.assertEqual(assistant_pending["event"]["bell_voice"]["line"], "每次都要播放这句")
            prompt = build_assistant_prompt(acknowledged, config)
            self.assertIn('"line": "每次都要播放这句"', prompt)

    def test_used_items_reveal_one_trace_per_use(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "book.json"
            run_command("new_game route=captured_by_assistant", save_path)
            rejected = run_command("gift_item items=book secret='只有一条'", save_path)
            self.assertFalse(rejected["ok"])
            gifted = run_command(
                "gift_item items=book secret='第 12 页有折角\n书签停在最后一章\n封底写过日期\n中间夹着旧书签\n扉页留着签名'",
                save_path,
            )
            self.assertTrue(gifted["ok"])
            self.assertEqual(len(gifted["captor_view"]["inventory_secrets"]["book"]["entries"]), 5)
            self.assertEqual(gifted["captive_view"]["inventory_secrets"]["book"]["revealed_count"], 0)

            self._force_night(save_path)
            first = run_command("night_action action=read detail=inspect_margins", save_path)
            first_secret = first["captive_view"]["pending_event"]["item_secret"]
            self.assertEqual((first_secret["sequence"], first_secret["total"]), (1, 5))
            self.assertIn("第 12 页有折角", first_secret["text"])
            run_command("ack_item_secret", save_path)

            self._force_night(save_path)
            second = run_command("night_action action=read detail=inspect_margins", save_path)
            second_secret = second["captive_view"]["pending_event"]["item_secret"]
            self.assertEqual((second_secret["sequence"], second_secret["total"]), (2, 5))
            self.assertIn("书签停在最后一章", second_secret["text"])
            self.assertNotIn("第 12 页有折角", second_secret["text"])

    def test_water_pressure_advances_with_later_actions_and_night(self) -> None:
        def event(action: str = "care", water: str = "none") -> dict:
            return {
                "id": action,
                "day": 1,
                "slot": 1,
                "phase": "day",
                "action": action,
                "mood": "",
                "modifiers": [],
                "tools": [],
                "contents": [],
                "training_contents": [],
                "feeding": {"water": water} if action == "feeding" else {},
                "effects": {},
                "tags": [],
            }

        state = _new_state("captured_by_assistant")
        _resolve_event(state, event("feeding", "glass"))
        _advance_after_day_event(state)
        self.assertEqual(state["bladder"]["pressure"], 1)
        _resolve_event(state, event())
        _advance_after_day_event(state)
        self.assertEqual(state["bladder"]["pressure"], 2)
        _resolve_event(state, event())
        _advance_after_day_event(state)
        self.assertEqual(state["bladder"]["pressure"], 3)
        self.assertEqual(state["phase"], "night")
        self.assertEqual(_active_night_condition(state)["label"], "快忍不住了")

        late_water = _new_state("captured_by_assistant")
        late_water["day_action_count"] = 2
        _resolve_event(late_water, event("feeding", "glass"))
        _advance_after_day_event(late_water)
        self.assertEqual(late_water["phase"], "night")
        self.assertEqual(late_water["bladder"]["pressure"], 2)


if __name__ == "__main__":
    unittest.main()
