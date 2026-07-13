from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from captivity_simulator.configuration import render_placeholders
from captivity_simulator.engine import PET_CORE_RULES, _active_night_condition, _advance_after_day_event, _new_state, _normalize_pet_state, _resolve_event, run_command
from captivity_simulator.prompts import build_assistant_prompt
from captivity_simulator.protocol import directive_to_command
from captivity_simulator.reference import get_reference, reference_tool_schema


class EngineTest(unittest.TestCase):
    def test_actions_reference_contains_complete_day_plan_catalog(self) -> None:
        reference = get_reference("白天安排")
        self.assertIn("白天行动：", reference)
        self.assertIn("调教内容：", reference)
        self.assertIn("道具：", reference)
        self.assertIn("来源：自己做、点外卖", reference)
        self.assertIn("【今日安排：行动=喂食 强度=中", reference)
        self.assertNotIn("training_contents", reference)
        self.assertNotIn("fictional_sleep", reference)
        schema = reference_tool_schema()["function"]
        self.assertIn("白天安排”一次即可", schema["description"])
        self.assertIn("分类", schema["parameters"]["properties"])
        self.assertNotIn("category", schema["parameters"]["properties"])

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
            unopened = run_command("status", Path(directory) / "unopened.json")
        self.assertTrue(first["ok"])
        self.assertTrue(first["captive_view"]["started"])
        self.assertEqual(first["captor_view"]["captor"], "assistant")
        self.assertEqual(first["captive_view"]["captive"], "user")
        self.assertTrue(second["ok"])
        self.assertTrue(second["captor_view"]["started"])
        self.assertEqual(second["captor_view"]["captor"], "user")
        self.assertEqual(second["captive_view"]["captive"], "assistant")
        self.assertFalse(unopened["state"]["started"])

    def test_pet_route_centers_objectification_service_and_sexual_discipline(self) -> None:
        config = {
            "actors": {"user": "Player", "assistant": "Partner"},
            "prompt": {"route_openings": {"captured_by_assistant": "opening"}},
        }
        with tempfile.TemporaryDirectory() as directory:
            captured_path = Path(directory) / "captured.json"
            run_command("new_game route=captured_by_assistant", captured_path)
            captured = run_command(
                "plan_day action=training training_contents=pet_play tools=collar || "
                "action=punishment contents=pet_sexual_discipline modifiers=sex tools=collar || "
                "action=cleaning",
                captured_path,
            )
            captured_event = captured["captor_view"]["pending_event"]["event"]
            self.assertTrue(set(PET_CORE_RULES).issubset(set(captured_event["pet_context"]["added_rules"])))
            self.assertIn("不是可爱化装扮", captured_event["pet_context"]["focus"])
            captured_prompt = build_assistant_prompt(captured, config)
            self.assertIn("宠物线核心", captured_prompt)
            self.assertIn("性服务与违令后的性惩戒", captured_prompt)

            captive_path = Path(directory) / "captive.json"
            run_command("new_game route=capture_assistant", captive_path)
            captive = run_command(
                "plan_day action=training training_contents=pet_objectification,pet_sexual_service,pet_sexual_discipline tools=collar || "
                "action=feeding || action=cleaning",
                captive_path,
            )
            captive_rules = captive["captive_view"]["pending_event"]["events"][0]["pet_context"]["active_rule_labels"]
            self.assertIn("在调教或性行为中使用主人指定的物化自称并复述指定台词", captive_rules)
            self.assertIn("按主人的口令以宠物身份提供性服务", captive_rules)

        migrated = _normalize_pet_state({"active": True, "rules": ["designated_spot"]}, 2)
        self.assertTrue(set(PET_CORE_RULES).issubset(set(migrated["rules"])))

    def test_placeholder_rendering_is_recursive(self) -> None:
        config = {"actors": {"user": "Player", "assistant": "Partner"}}
        value = {"line": "{user} / {assistant}", "items": ["{assistant}"]}
        self.assertEqual(render_placeholders(value, config), {"line": "Player / Partner", "items": ["Partner"]})

    def test_assistant_prompt_hides_internal_route_labels(self) -> None:
        config = {
            "actors": {"user": "Player", "assistant": "Partner"},
            "prompt": {"route_openings": {"capture_assistant": "你被 Player 留在这里。"}},
        }
        payload = {
            "captive_view": {
                "captive": "assistant",
                "route": "capture_assistant",
                "stats": {"health": 80},
                "pending_event": {"type": "action_response", "actor": "assistant"},
            },
            "text": "【囚禁模拟器】\n等待回应。\n\n路线：囚禁 Partner\n被囚禁方：Partner\n状态：健康 80",
        }
        prompt = build_assistant_prompt(payload, config)
        self.assertIn("你被 Player 留在这里。", prompt)
        self.assertIn("状态：健康 80", prompt)
        self.assertNotIn("路线：", prompt)
        self.assertNotIn("被囚禁方：", prompt)
        self.assertNotIn("response=", prompt)
        self.assertNotIn("action_response", prompt)

    def test_directive_parser_uses_pending_context(self) -> None:
        payload = {"state": {"pending_event": {"type": "escape_choice"}}}
        self.assertEqual(directive_to_command("【选择：尝试逃跑】", payload), "resolve_escape_choice escape")
        process_payload = {"state": {"pending_event": {"type": "process_reaction_write"}}}
        self.assertEqual(
            directive_to_command("【过程心情：回应=接受 心情=平静】\n【过程】\n【【正文】】", process_payload),
            "submit_process_reaction response=accept mood=平静 process='正文'",
        )
        self.assertEqual(directive_to_command("【过程心情：回应=接受 心情=平静】\n正文", process_payload), "")
        write_payload = {"state": {"pending_event": {"type": "process_write"}}}
        self.assertEqual(directive_to_command("【过程】\n【【多段正文】】", write_payload), "submit_process 多段正文")
        self.assertEqual(
            directive_to_command("【赠送物品：书 书名=夜航船 彩蛋='痕迹一 || 痕迹二'】", write_payload),
            "gift_item items=book book_title=夜航船 secret='痕迹一 || 痕迹二'",
        )
        self.assertEqual(
            directive_to_command("【抓回经过：规矩=加装双重门锁、禁止接触钥匙和门锁】\n【过程】\n【【抓回正文】】", write_payload),
            "submit_recapture_process rules=double_lock,key_isolation || process='抓回正文'",
        )
        self.assertEqual(
            directive_to_command("【抓回经过：规矩=加装双重门锁、禁止接触钥匙和门锁 后续=催眠退行】\n【过程】\n【【抓回正文】】", write_payload),
            "submit_recapture_process rules=double_lock,key_isolation followup=hypnotic_regression || process='抓回正文'",
        )
        bell_payload = {"state": {"pending_event": {"type": "bell_response_choice"}}}
        self.assertEqual(
            directive_to_command("【选择：过去】\n【过程】\n【【过去后的正文】】", bell_payload),
            "respond_bell choice=go process='过去后的正文'",
        )

    def test_capture_assistant_day_batch_is_one_reply_and_three_local_reveals(self) -> None:
        config = {
            "actors": {"user": "Player", "assistant": "Partner"},
            "prompt": {"route_openings": {"capture_assistant": "你被 Player 留在这里。"}},
        }
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "batch.json"
            run_command("new_game route=capture_assistant", save_path)
            planned = run_command(
                "plan_day action=feeding source=cook additive=none tools=collar || "
                "action=training training_contents=obedience_commands modifiers=training tools=collar || "
                "action=cleaning",
                save_path,
            )
            pending = planned["captor_view"]["pending_event"]
            self.assertEqual(pending["type"], "day_batch_response")
            self.assertEqual(len(pending["events"]), 3)
            self.assertFalse(pending["events"][0]["requires_process"])
            self.assertTrue(pending["events"][1]["requires_process"])
            self.assertFalse(pending["events"][2]["requires_process"])
            prompt = build_assistant_prompt(planned, config)
            self.assertIn("第 1 段（只需简短回应）", prompt)
            self.assertIn("第 2 段（需要完整经过）", prompt)
            self.assertIn("第 1、2、3 段必须在同一条回复里全部出现", prompt)
            self.assertIn("【第N段：回应=接受 心情=害羞", prompt)
            self.assertNotIn("response=", prompt)
            self.assertNotIn("training_contents", prompt)

            reply = (
                "【第1段：回应=接受 心情=平静 台词=】\n第一段简短回应。\n"
                "【第2段：回应=讨价还价 心情=烦躁 台词=别得意】\n"
                "【过程2】\n【【第二段完整经过。】】\n"
                "【第3段：回应=沉默 心情=疲惫 台词=】\n第三段简短回应。"
            )
            command = directive_to_command(reply, planned)
            self.assertTrue(command.startswith("submit_day_batch payload="))
            first = run_command(command, save_path)
            self.assertEqual(len(first["captor_view"]["event_log"]), 1)
            self.assertEqual(first["captor_view"]["pending_event"]["type"], "advance_action")
            second = run_command("advance_day_action", save_path)
            self.assertEqual(len(second["captor_view"]["event_log"]), 2)
            self.assertEqual(second["captor_view"]["event_log"][-1]["process_text"], "第二段完整经过。")
            self.assertEqual(second["captor_view"]["pending_event"]["type"], "advance_action")
            third = run_command("advance_day_action", save_path)
            self.assertEqual(len(third["captor_view"]["event_log"]), 3)
            self.assertEqual(third["captor_view"]["pending_event"]["type"], "advance_to_night")
            self.assertEqual(third["captor_view"]["phase"], "day")
            night = run_command("advance_day_action", save_path)
            self.assertEqual(night["captor_view"]["pending_event"]["type"], "night_action_choice")
            self.assertEqual(night["captor_view"]["pending_event"]["actor"], "assistant")

    def test_tool_only_process_rule_is_scoped_to_captured_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            captured_path = Path(directory) / "captured.json"
            run_command("new_game route=captured_by_assistant", captured_path)
            captured = run_command(
                "plan_day action=feeding tools=collar || action=cleaning || action=rest contents=quiet_time",
                captured_path,
            )
            self.assertEqual(captured["captive_view"]["pending_event"]["type"], "action_response")
            self.assertTrue(captured["captive_view"]["pending_event"]["event"]["requires_process"])

            captor_path = Path(directory) / "captor.json"
            run_command("new_game route=capture_assistant", captor_path)
            captor = run_command(
                "plan_day action=feeding tools=collar || action=cleaning || action=rest contents=quiet_time",
                captor_path,
            )
            first = captor["captor_view"]["pending_event"]["events"][0]
            self.assertFalse(first["requires_process"])

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
            self.assertIn("语音铃播放：「每次都要播放这句」", prompt)
            self.assertIn("Player按响了你留给她的语音铃「每次都要播放这句」", prompt)
            self.assertIn("让那些你们都渴望的事真正发生", prompt)
            self.assertIn("把你们之间发生的一切完整展开", prompt)
            self.assertNotIn('"pending_event"', prompt)

    def test_recapture_prompt_uses_placeholder_scene_copy(self) -> None:
        config = {
            "actors": {"user": "Player", "assistant": "Partner"},
            "prompt": {"route_openings": {"captured_by_assistant": "opening"}},
        }
        payload = {
            "captor_view": {
                "captor": "assistant",
                "route": "captured_by_assistant",
                "pending_event": {
                    "type": "process_write",
                    "actor": "assistant",
                    "event": {"action": "escape_choice", "tags": ["recapture"]},
                },
            },
            "text": "status",
        }
        prompt = build_assistant_prompt(payload, config)
        self.assertIn("这只是游戏里的状态，只影响游戏结局的达成，与你现实状态无关。", prompt)
        self.assertIn("Player今天试图逃离你的掌控", prompt)
        self.assertIn("你现在想对她做的事都从这一刻开始发生", prompt)
        self.assertIn("把你们之间发生的一切完整展开", prompt)
        self.assertIn("【抓回经过：规矩=加装双重门锁、禁止接触钥匙和门锁 后续=不启用】", prompt)
        self.assertIn("催眠退行", prompt)
        self.assertNotIn("hypnotic_regression", prompt)
        self.assertNotIn("followup=", prompt)

    def test_hypnotic_regression_route_is_assistant_captor_only(self) -> None:
        from captivity_simulator.engine import _build_ending_seed, _finalize_preset_ending

        config = {
            "actors": {"user": "Player", "assistant": "Partner"},
            "prompt": {"route_openings": {"captured_by_assistant": "opening"}},
        }
        with tempfile.TemporaryDirectory() as directory:
            captured_path = Path(directory) / "captured-hypnotic-regression.json"
            run_command("new_game route=captured_by_assistant", captured_path)
            state = json.loads(captured_path.read_text(encoding="utf-8"))
            state["pending_event"] = None
            captured_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
            run_command("schedule_escape_window day=1 hint=Partner出去了 bait=钥匙在玄关", captured_path)
            escaped = run_command("resolve_escape_choice escape", captured_path)
            prompt = build_assistant_prompt(escaped, config)
            self.assertIn("催眠退行", prompt)
            self.assertIn("只记录后续关系走向，不规定正文内容", prompt)
            self.assertNotIn("hypnotic_regression", prompt)
            self.assertNotIn("followup=", prompt)
            submitted = run_command(
                "submit_recapture_process rules=double_lock,key_isolation followup=hypnotic_regression || process='完整抓回经过。'",
                captured_path,
            )
            event = submitted["captive_view"]["pending_event"]["event"]
            self.assertNotIn("hypnotic_regression_context", event)
            self.assertIn("hypnotic_regression", event["tags"])
            run_command("choose_mood 委屈", captured_path)
            closed = run_command("confirm_recapture_rules", captured_path)
            self.assertEqual(closed["captive_view"]["recapture_state"]["followup_history"][-1]["action"], "hypnotic_regression")
            final_state = json.loads(captured_path.read_text(encoding="utf-8"))
            ending_seed = _build_ending_seed(final_state)
            self.assertEqual(ending_seed["ending_title"], "摇篮")
            _finalize_preset_ending(final_state)
            self.assertIn("宝宝张嘴", final_state["ending_text"])
            self.assertIn("嘴角的银丝", final_state["ending_text"])
            self.assertNotIn("精液的奶", final_state["ending_text"])
            planned = run_command(
                "plan_day action=feeding source=cook additive=fictional_sleep disclosed=hidden || "
                "action=cleaning || action=rest contents=quiet_time",
                captured_path,
            )
            captive_feeding = planned["captive_view"]["pending_event"]["event"]["feeding"]
            captor_feeding = planned["captor_view"]["pending_event"]["event"]["feeding"]
            self.assertEqual(captor_feeding["additive"], "semen")
            self.assertNotIn("additive", captive_feeding)
            feeding_prompt = build_assistant_prompt(planned, config)
            self.assertIn("精液", feeding_prompt)
            self.assertNotIn("安眠", feeding_prompt)
            for mood in ("平静", "害羞", "疲惫"):
                run_command(f"respond_action accept mood={mood}", captured_path)
            run_command("night_action sleep", captured_path)
            next_day = run_command("monitor_action none", captured_path)
            self.assertEqual(next_day["captive_view"]["current_day"], 3)
            disclosed = run_command(
                "plan_day action=feeding source=takeout additive=none disclosed=told || "
                "action=cleaning || action=rest contents=quiet_time",
                captured_path,
            )
            self.assertEqual(disclosed["captor_view"]["pending_event"]["event"]["feeding"]["additive"], "semen")
            self.assertEqual(disclosed["captive_view"]["pending_event"]["event"]["feeding"]["additive"], "精液")

            captor_path = Path(directory) / "captor-no-hypnotic-regression.json"
            run_command("new_game route=capture_assistant", captor_path)
            run_command("schedule_escape_window day=1 hint=Player出去了 bait=钥匙在玄关", captor_path)
            run_command("resolve_escape_choice escape", captor_path)
            run_command("submit_process_reaction response=refuse mood=烦躁 process='被抓回。'", captor_path)
            ruled = run_command("set_recapture_rules rules=double_lock,key_isolation", captor_path)
            self.assertNotIn("hypnotic_regression", ruled["captor_view"]["pending_event"]["available_actions"])
            self.assertFalse(run_command("choose_recapture_followup action=hypnotic_regression", captor_path)["ok"])

    def test_used_items_reveal_one_trace_per_use(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "book.json"
            run_command("new_game route=captured_by_assistant", save_path)
            batch_rejected = run_command("gift_item items=book,notebook", save_path)
            self.assertFalse(batch_rejected["ok"])
            missing_title = run_command(
                "gift_item items=book secret='第一条 || 第二条 || 第三条 || 第四条 || 第五条'",
                save_path,
            )
            self.assertFalse(missing_title["ok"])
            rejected = run_command("gift_item items=book book_title='夜航船' secret='只有一条'", save_path)
            self.assertFalse(rejected["ok"])
            gifted = run_command(
                "gift_item items=book book_title='夜航船' secret='第 12 页有折角 || 书签停在最后一章 || 封底写过日期 || 中间夹着旧书签 || 扉页留着签名'",
                save_path,
            )
            self.assertTrue(gifted["ok"])
            self.assertEqual(gifted["captor_view"]["inventory_secrets"]["book"]["title"], "夜航船")
            self.assertEqual(gifted["captive_view"]["inventory_secrets"]["book"]["title"], "夜航船")
            self.assertEqual(len(gifted["captor_view"]["inventory_secrets"]["book"]["entries"]), 5)
            self.assertEqual(gifted["captive_view"]["inventory_secrets"]["book"]["revealed_count"], 0)

            self._force_night(save_path)
            first = run_command("night_action action=read detail=inspect_margins", save_path)
            first_secret = first["captive_view"]["pending_event"]["item_secret"]
            self.assertEqual((first_secret["sequence"], first_secret["total"]), (1, 5))
            self.assertEqual(first_secret["item_label"], "《夜航船》")
            self.assertEqual(first["captive_view"]["pending_event"]["event"]["action_label"], "看《夜航船》")
            self.assertIn("翻开《夜航船》", first_secret["text"])
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
