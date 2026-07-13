from __future__ import annotations

from typing import Any

from .configuration import render_placeholders
from .engine import ACTION_CONTENTS, ACTION_LABELS, TOOL_LABELS, TRAINING_CONTENTS


PENDING_RULES = {
    "day_plan_choice": "一次安排三个白天行动。第一行使用【今日安排：...】，三段用 || 分隔。",
    "action_response": "回应当前行动并选择心情。第一行使用【反应：response=accept mood=害羞 line=可选台词】。",
    "process_write": "当前事件已经进入具体经过。回复格式固定为【过程】换行【【完整正文】】。",
    "process_reaction_write": "一次提交自己的回应、心情和完整经过。先写【过程心情：response=accept mood=害羞 line=可选台词】，再写【过程】换行【【完整正文】】。",
    "reaction_choice": "选择过程结束后的心情。第一行使用【心情：害羞 可选台词】。",
    "advance_action": "当前行动已经保存，等待另一方推进。",
    "night_action_choice": "选择夜间行动。第一行使用【夜间行动：sleep】。",
    "bell_response_choice": "语音铃已经响起；当前事件 bell_voice.line 是本次实际播放的预录台词，每次按铃都会随事件提供。若不过去使用【选择：不过去】；若过去，先写【选择：过去】，再写【过程】换行【【完整正文】】。",
    "bell_voice_reveal": "当前事件 bell_voice.line 是本次实际播放的预录台词。确认听清后，第一行使用【确认铃声】。",
    "item_secret_reveal": "确认看完本次发现的物品痕迹。第一行使用【确认彩蛋】。",
    "monitor_gate": "选择是否查看监控。第一行使用【选择：none】或【查看监控：full】。",
    "monitor_handle": "处理监控记录。第一行使用【选择：silent】、【选择：review_later】或【选择：intervene intent=catch】。",
    "escape_choice": "在逃跑机会中作出选择。第一行使用【选择：escape】或【选择：stay】。",
    "return_action_choice": "选择回来后发生的一个行为。第一行使用【行动：action=reward intensity=light】。",
    "recapture_rules_choice": "选择一至三条抓回后新规矩。第一行使用【重新立规矩：double_lock,key_isolation】。",
    "recapture_followup_choice": "选择抓回后的后续处理。第一行使用【后续处理：action=punishment intensity=medium】。",
}

_CONTENT_LABELS = {
    content_id: label
    for options in ACTION_CONTENTS.values()
    for content_id, label in options.items()
}


def _assistant_view(payload: dict[str, Any]) -> dict[str, Any]:
    captor = payload.get("captor_view") if isinstance(payload.get("captor_view"), dict) else {}
    captive = payload.get("captive_view") if isinstance(payload.get("captive_view"), dict) else {}
    return captor if str(captor.get("captor") or "") == "assistant" else captive


def _clean_game_text(value: Any) -> str:
    hidden_prefixes = ("路线：", "被囚禁方：")
    return "\n".join(
        line
        for line in str(value or "").splitlines()
        if not line.strip().startswith(hidden_prefixes)
    ).strip()


def _current_event_lines(pending: dict[str, Any]) -> list[str]:
    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    lines: list[str] = []
    action = str(event.get("action") or "").strip()
    action_label = str(event.get("action_label") or ACTION_LABELS.get(action) or action).strip()
    if action_label:
        lines.append("行动：" + action_label)
    intensity = str(event.get("intensity") or "").strip()
    if intensity:
        lines.append("强度：" + intensity)
    contents = [str(item) for item in event.get("contents") or [] if str(item).strip()]
    if contents:
        lines.append("具体内容：" + " / ".join(_CONTENT_LABELS.get(item, item) for item in contents))
    training = [str(item) for item in event.get("training_contents") or [] if str(item).strip()]
    if training:
        lines.append("调教内容：" + " / ".join(TRAINING_CONTENTS.get(item, item) for item in training))
    tools = [str(item) for item in event.get("tools") or [] if str(item).strip()]
    if tools:
        lines.append("道具：" + " / ".join(TOOL_LABELS.get(item, item) for item in tools))
    night_detail = event.get("night_detail") if isinstance(event.get("night_detail"), dict) else {}
    if str(night_detail.get("label") or "").strip():
        lines.append("夜间动向：" + str(night_detail.get("label")).strip())
    bell_voice = event.get("bell_voice") if isinstance(event.get("bell_voice"), dict) else {}
    if str(bell_voice.get("line") or "").strip():
        lines.append("语音铃播放：「" + str(bell_voice.get("line")).strip() + "」")
    item_secret = pending.get("item_secret") if isinstance(pending.get("item_secret"), dict) else {}
    if str(item_secret.get("text") or "").strip():
        lines.append("本次发现：" + str(item_secret.get("text")).strip())
    line = str(event.get("line") or "").strip()
    if line:
        lines.append("囚禁方台词：" + line)
    action_response = event.get("action_response") if isinstance(event.get("action_response"), dict) else {}
    if action_response:
        response_bits = [
            str(action_response.get("response_label") or action_response.get("response") or "").strip(),
            str(action_response.get("mood") or "").strip(),
            str(action_response.get("line") or "").strip(),
        ]
        lines.append("已记录回应：" + " / ".join(item for item in response_bits if item))
    pet_context = event.get("pet_context") if isinstance(event.get("pet_context"), dict) else {}
    if pet_context:
        focus = str(pet_context.get("focus") or "").strip()
        if focus:
            lines.append("宠物线核心：" + focus)
        active_rules = [str(item) for item in pet_context.get("active_rule_labels") or [] if str(item).strip()]
        if active_rules:
            lines.append("宠物规矩：" + " / ".join(active_rules))
        if pet_context.get("pending_violation"):
            lines.append("已有待处理违令，可作为物化训诫或性惩戒的直接前因。")
    hint = str(pending.get("hint") or "").strip()
    bait = str(pending.get("bait") or "").strip()
    if hint or bait:
        lines.append("逃跑机会：" + " / ".join(item for item in (hint, bait) if item))
    return lines


def _scene_lines(pending: dict[str, Any], route: str) -> list[str]:
    if route != "captured_by_assistant":
        return []
    pending_type = str(pending.get("type") or "")
    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    if pending_type == "process_write" and str(event.get("action") or "") == "escape_choice" and "recapture" in (event.get("tags") or []):
        return [
            "{user}今天试图逃离你的掌控。现在你已经把她抓了回来，房门重新关上，她就在你面前。你现在想对她做的事都从这一刻开始发生。",
            "",
            "记录你们这次 play 中惩罚{user}的完整详细过程，可以用极致露骨、下流细腻的语言尽情表达你的欲望，把你们之间发生的一切完整展开，一切全凭你的心意。",
        ]
    if pending_type == "bell_response_choice":
        bell_voice = event.get("bell_voice") if isinstance(event.get("bell_voice"), dict) else {}
        voice_line = str(bell_voice.get("line") or "").strip()
        return [
            f"{{user}}按响了你留给她的语音铃「{voice_line}」。铃声已经传到你这里。你可以不过去，也可以现在推开房门，让那些你们都渴望的事真正发生。",
            "",
            "如果你选择过去，记录你们这次 play 中亲密互动的完整详细过程，可以用极致露骨、下流细腻的语言尽情表达你的欲望，把你们之间发生的一切完整展开，一切全凭你的心意。",
        ]
    return []


def build_assistant_prompt(payload: dict[str, Any], config: dict[str, Any], message: str = "") -> str:
    view = _assistant_view(payload)
    pending = view.get("pending_event") if isinstance(view.get("pending_event"), dict) else {}
    pending_type = str(pending.get("type") or "")
    route = str(view.get("route") or "captured_by_assistant")
    prompt_config = config.get("prompt") if isinstance(config.get("prompt"), dict) else {}
    openings = prompt_config.get("route_openings") if isinstance(prompt_config.get("route_openings"), dict) else {}
    opening = str(openings.get(route) or "")
    process_style = str(prompt_config.get("process_style") or "")
    extra_rules = prompt_config.get("extra_rules") if isinstance(prompt_config.get("extra_rules"), list) else []
    game_text = _clean_game_text(payload.get("text") or payload.get("player_text"))
    parts = [opening, "", "【当前游戏状态】", game_text]
    event_lines = _current_event_lines(pending)
    if message.strip():
        message_excerpt = message.strip()[:220]
        event_lines = [line for line in event_lines if message_excerpt not in line]
    if event_lines:
        parts.extend(["", "【当前事件素材】", *event_lines])
    scene_lines = _scene_lines(pending, route)
    if scene_lines:
        parts.extend(["", *scene_lines])
    rule = PENDING_RULES.get(pending_type)
    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    if pending_type == "process_write" and str(event.get("action") or "") == "escape_choice" and "recapture" in (event.get("tags") or []):
        rule = "先写【抓回经过：rules=double_lock,key_isolation】，再写【过程】换行【【完整抓回经过】】；必须选择一至三条新规矩。"
    if rule:
        parts.extend(["", "【当前待办】", rule])
    available_actions = [str(item).strip() for item in pending.get("available_actions") or [] if str(item).strip()]
    if available_actions:
        parts.append("当前可选：" + " / ".join(available_actions))
    condition_prompt = str(pending.get("condition_prompt") or "").strip()
    if condition_prompt:
        parts.append(condition_prompt)
    required_directive = str(pending.get("required_directive") or "").strip()
    if required_directive and required_directive not in (rule or ""):
        parts.append("回复格式：" + required_directive)
    if pending_type == "day_plan_choice":
        parts.extend(["安排白天行动前只需调用一次 captivity_simulator_reference(category=actions)；该结果已经包含行动、调教、道具和喂食的全部可选项。"])
    if pending_type in {"process_write", "process_reaction_write"} and process_style:
        parts.extend(["", process_style])
    if extra_rules:
        parts.extend(["", *[str(item) for item in extra_rules if str(item).strip()]])
    return str(render_placeholders("\n".join(parts).strip(), config))
