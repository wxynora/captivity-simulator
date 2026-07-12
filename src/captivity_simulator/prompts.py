from __future__ import annotations

import json
from typing import Any

from .configuration import render_placeholders


PENDING_RULES = {
    "day_plan_choice": "一次安排三个白天行动。第一行使用【今日安排：...】，三段用 || 分隔。",
    "action_response": "回应当前行动并选择心情。第一行使用【反应：response=accept mood=害羞 line=可选台词】。",
    "process_write": "写下当前事件的完整经过。第一行使用【过程：完整经过】。",
    "process_reaction_write": "一次提交自己的回应、心情和完整经过。第一行使用【过程心情：response=accept mood=害羞 line=可选台词 process=完整经过】。",
    "reaction_choice": "选择过程结束后的心情。第一行使用【心情：害羞 可选台词】。",
    "advance_action": "当前行动已经保存，等待另一方推进。",
    "night_action_choice": "选择夜间行动。第一行使用【夜间行动：sleep】。",
    "bell_response_choice": "语音铃已经响起；当前事件 bell_voice.line 是本次实际播放的预录台词，每次按铃都会随事件提供。第一行使用【不过去】或【过去：完整经过】。",
    "bell_voice_reveal": "当前事件 bell_voice.line 是本次实际播放的预录台词。确认听清后，第一行使用【确认铃声】。",
    "item_secret_reveal": "确认看完本次发现的物品痕迹。第一行使用【确认彩蛋】。",
    "monitor_gate": "选择是否查看监控。第一行使用【选择：none】或【查看监控：full】。",
    "monitor_handle": "处理监控记录。第一行使用【选择：silent】、【选择：review_later】或【选择：intervene intent=catch】。",
    "escape_choice": "在逃跑机会中作出选择。第一行使用【选择：escape】或【选择：stay】。",
    "return_action_choice": "选择回来后发生的一个行为。第一行使用【行动：action=reward intensity=light】。",
    "recapture_rules_choice": "选择一至三条抓回后新规矩。第一行使用【重新立规矩：double_lock,key_isolation】。",
    "recapture_followup_choice": "选择抓回后的后续处理。第一行使用【后续处理：action=punishment intensity=medium】。",
}


def _assistant_view(payload: dict[str, Any]) -> dict[str, Any]:
    captor = payload.get("captor_view") if isinstance(payload.get("captor_view"), dict) else {}
    captive = payload.get("captive_view") if isinstance(payload.get("captive_view"), dict) else {}
    return captor if str(captor.get("captor") or "") == "assistant" else captive


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
    parts = [opening, "", "【游戏状态】", json.dumps(view, ensure_ascii=False, indent=2)]
    if message.strip():
        parts.extend(["", "【{user}刚刚在游戏里说】", message.strip()])
    if pending:
        parts.extend(["", "【当前事件】", json.dumps(pending, ensure_ascii=False, indent=2)])
    rule = PENDING_RULES.get(pending_type)
    if rule:
        parts.extend(["", "【menu】", rule])
    if pending_type in {"process_write", "process_reaction_write"} and process_style:
        parts.extend(["", process_style])
    if extra_rules:
        parts.extend(["", *[str(item) for item in extra_rules if str(item).strip()]])
    return str(render_placeholders("\n".join(parts).strip(), config))
