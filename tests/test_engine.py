from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from captivity_simulator.configuration import render_placeholders
from captivity_simulator.engine import run_command
from captivity_simulator.protocol import directive_to_command


class EngineTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
