from __future__ import annotations

from typing import Any

from .configuration import render_placeholders
from .engine import (
    ACTION_CONTENTS,
    ACTION_LABELS,
    ACTION_RESPONSE_LABELS,
    ESCAPE_CHOICE_LABELS,
    INTERVENTION_INTENT_LABELS,
    INTERVENTION_MODIFIER_LABELS,
    NIGHT_ACTIONS,
    NIGHT_DETAIL_OPTIONS,
    RECAPTURE_FOLLOWUP_LABELS,
    TOOL_LABELS,
    TRAINING_CONTENTS,
)


PENDING_RULES = {
    "day_plan_choice": "一次安排三个白天行动。决定后写「【今日安排：行动=喂食 强度=中 || 行动=奖励取悦 强度=低 内容=抚摸奖励 || 行动=服从调教 强度=中 调教=口令服从 附加=性行为 道具=项圈】」。",
    "day_batch_response": "今天的三个白天行动已经一次性交给你。你要在同一条回复里按顺序完成三段，系统会先展示第一段，后两段只保存等待对方推进，不会再次询问你。",
    "action_response": "按照你当下的感受选择回应和心情。决定后写「【反应：回应=接受 心情=害羞 台词=可选台词】」。",
    "process_write": "当前事件已经进入具体经过。回复格式固定为「【过程】」换行「【【完整正文】】」。",
    "process_reaction_write": "按照你当下的感受回应。先写「【过程心情：回应=接受 心情=害羞 台词=可选台词】」，再写「【过程】」换行「【【完整正文】】」。",
    "reaction_choice": "过程已经结束。按照你当下的感受写「【心情：害羞 可选台词】」。",
    "advance_action": "当前行动已经保存，等待另一方推进。",
    "night_action_choice": "夜晚已经开始，现在轮到你决定接下来做什么。",
    "bell_response_choice": "语音铃已经响起。若不过去写「【选择：不过去】」；若过去，先写「【选择：过去】」，再写「【过程】」换行「【【完整正文】】」。",
    "bell_voice_reveal": "按照你当下的感受回应；听清后写「【确认铃声】」。",
    "item_secret_reveal": "按照你当下的感受回应；看完本次发现后写「【确认彩蛋】」。",
    "monitor_gate": "不看就写「【选择：不看】」；打开监控就写「【查看监控：全程看】」或「【查看监控：偶尔看】」。",
    "monitor_handle": "看见但不说写「【选择：看见但不说】」，留到之后写「【选择：之后处理】」；当场介入写「【选择：处理=当场介入 介入=抓现行 附加=调教、性行为 调教=口令服从 道具=项圈 台词=可选台词】」。",
    "escape_choice": "决定后写「【选择：尝试逃跑】」或「【选择：老实待着】」。",
    "return_action_choice": "这里只选一个行为，不是三个今日安排。决定后写「【行动：行动=奖励取悦 强度=低 内容=抚摸奖励】」。",
    "recapture_rules_choice": "选择一至三条抓回后新规矩。决定后写「【重新立规矩：加装双重门锁、禁止接触钥匙和门锁】」。",
    "recapture_followup_choice": "选择抓回后的后续处理。决定后写「【后续处理：行动=惩戒 强度=中 附加=调教、性行为 调教=拍打调教 道具=软鞭】」。",
}

BODY_STATE_DISCLAIMER = "这只是游戏里的状态，只影响游戏结局的达成，与你现实状态无关。"
_INTENSITY_LABELS = {"light": "低", "medium": "中", "heavy": "高"}
_CONTENT_LABELS = {
    content_id: label
    for options in ACTION_CONTENTS.values()
    for content_id, label in options.items()
}
_FEEDING_LABELS = {
    "source": {"cook": "自己做", "takeout": "点外卖"},
    "method": {"normal": "正常喂食"},
    "additive": {"none": "不加料", "body_fluid": "体液", "semen": "精液", "fictional_sleep": "安眠", "fictional_arousal": "助兴"},
    "disclosed": {"told": "明确告知", "hint": "暗示", "hidden": "隐瞒"},
    "water": {"none": "不额外喂水", "glass": "一杯水", "lots": "很多水"},
}


def _assistant_view(payload: dict[str, Any]) -> dict[str, Any]:
    captor = payload.get("captor_view") if isinstance(payload.get("captor_view"), dict) else {}
    captive = payload.get("captive_view") if isinstance(payload.get("captive_view"), dict) else {}
    return captor if str(captor.get("captor") or "") == "assistant" else captive


def _status_text(view: dict[str, Any]) -> str:
    day = int(view.get("current_day") or 1)
    completed = int(view.get("day_action_count") or 0)
    phase = str(view.get("phase") or "day")
    if phase == "day":
        return f"第 {day} 天，白天三段行动已完成 {completed} 段。"
    if phase == "night":
        return f"第 {day} 天，已经入夜。"
    if phase == "ending":
        title = str(view.get("ending_title") or "").strip()
        return f"本局达成结局「{title}」。" if title else "本局已经结束。"
    return f"第 {day} 天。"


def _stats_text(view: dict[str, Any]) -> str:
    stats = view.get("stats") if isinstance(view.get("stats"), dict) else {}
    labels = {
        "health": "健康",
        "stamina": "体力",
        "cleanliness": "清洁",
        "shame": "羞耻",
        "intimacy": "依赖",
        "mood": "心情",
    }
    bits = [f"{label} {stats[key]}" for key, label in labels.items() if key in stats]
    return "状态：" + " / ".join(bits) if bits else ""


def _current_event_lines(pending: dict[str, Any]) -> list[str]:
    if str(pending.get("type") or "") == "monitor_gate":
        return ["夜间监控记录已封存；在打开监控前，不提供被囚禁方的夜间行动内容。"]
    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    lines: list[str] = []
    action = str(event.get("action") or "").strip()
    action_label = str(
        event.get("action_label")
        or ACTION_LABELS.get(action)
        or NIGHT_ACTIONS.get(action)
        or RECAPTURE_FOLLOWUP_LABELS.get(action)
        or ""
    ).strip()
    if action_label:
        lines.append("行动：" + action_label)
    intensity = str(event.get("intensity") or "").strip()
    if intensity:
        lines.append("强度：" + _INTENSITY_LABELS.get(intensity, intensity))
    contents = [str(item) for item in event.get("contents") or [] if str(item).strip()]
    if contents:
        lines.append("具体内容：" + " / ".join(_CONTENT_LABELS.get(item, item) for item in contents))
    training = [str(item) for item in event.get("training_contents") or [] if str(item).strip()]
    if training:
        lines.append("调教内容：" + " / ".join(TRAINING_CONTENTS.get(item, item) for item in training))
    modifiers = [
        str(item)
        for item in event.get("modifiers") or []
        if str(item).strip() and str(item) in INTERVENTION_MODIFIER_LABELS
    ]
    if modifiers:
        lines.append("附加玩法：" + " / ".join(INTERVENTION_MODIFIER_LABELS.get(item, item) for item in modifiers))
    tools = [str(item) for item in event.get("tools") or [] if str(item).strip()]
    if tools:
        lines.append("道具：" + " / ".join(TOOL_LABELS.get(item, item) for item in tools))
    feeding = event.get("feeding") if isinstance(event.get("feeding"), dict) else {}
    if feeding:
        feeding_bits = [
            _FEEDING_LABELS.get(key, {}).get(str(value), str(value))
            for key, value in feeding.items()
            if str(value or "").strip() and str(value or "") != "none"
        ]
        if feeding_bits:
            lines.append("喂食设置：" + " / ".join(feeding_bits))
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
        response_id = str(action_response.get("response") or "").strip()
        response_bits = [
            str(action_response.get("response_label") or ACTION_RESPONSE_LABELS.get(response_id) or response_id).strip(),
            str(action_response.get("mood") or "").strip(),
            str(action_response.get("line") or "").strip(),
        ]
        lines.append("已记录回应：" + " / ".join(item for item in response_bits if item))
    intervention = event.get("intervention") if isinstance(event.get("intervention"), dict) else {}
    if intervention:
        intent_id = str(intervention.get("intent") or "").strip()
        intent = str(intervention.get("intent_label") or INTERVENTION_INTENT_LABELS.get(intent_id) or intent_id).strip()
        if intent:
            lines.append("当场介入：" + intent)
    escape = event.get("escape") if isinstance(event.get("escape"), dict) else {}
    choice = str(escape.get("choice") or "").strip()
    if choice:
        lines.append("逃跑选择：" + ESCAPE_CHOICE_LABELS.get(choice, choice))
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


def _day_batch_event_lines(pending: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for index, event in enumerate(pending.get("events") or [], start=1):
        if not isinstance(event, dict):
            continue
        process_label = "需要完整经过" if bool(event.get("requires_process")) else "只需简短回应"
        lines.append(f"第 {index} 段（{process_label}）：")
        lines.extend(_current_event_lines({"event": event}))
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


def _night_detail_rule(pending: dict[str, Any]) -> str:
    raw = pending.get("detail_options") if isinstance(pending.get("detail_options"), dict) else NIGHT_DETAIL_OPTIONS
    available = {str(item) for item in pending.get("available_actions") or [] if str(item).strip()}
    return "；".join(
        f"{NIGHT_ACTIONS.get(action, action)}=" + "/".join(str(label) for label in options.values())
        for action, options in raw.items()
        if isinstance(options, dict) and options and (not available or action in available)
    )


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
    parts = [opening, "", "【当前进度】", _status_text(view)]
    stats_text = _stats_text(view)
    if stats_text:
        parts.append(stats_text)
    if BODY_STATE_DISCLAIMER not in opening:
        parts.append(BODY_STATE_DISCLAIMER)
    event_lines = _day_batch_event_lines(pending) if pending_type == "day_batch_response" else _current_event_lines(pending)
    if message.strip():
        message_excerpt = message.strip()[:220]
        event_lines = [line for line in event_lines if message_excerpt not in line]
    if event_lines:
        parts.extend(["", "【眼前发生的事】", *event_lines])
    if message.strip():
        parts.extend(["", "【{user}刚刚说】", message.strip()[:220]])
    scene_lines = _scene_lines(pending, route)
    if scene_lines:
        parts.extend(["", "---", "", *scene_lines])
    rule = PENDING_RULES.get(pending_type, "")
    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    if pending_type == "process_write" and str(event.get("action") or "") == "escape_choice" and "recapture" in (event.get("tags") or []):
        rule = (
            "同时选择一至三条新规矩；过程正文不要写成规矩清单。"
            "如果要让抓回后转入催眠退行路线，把“后续=不启用”改成“后续=催眠退行”；这只记录后续关系走向，不规定正文内容。"
            "决定后先写「【抓回经过：规矩=加装双重门锁、禁止接触钥匙和门锁 后续=不启用】」，再写「【过程】」换行「【【完整抓回经过】】」。"
        )
    if rule:
        parts.extend(["", "---", "", "【现在轮到你】", rule])
    if pending_type == "day_batch_response":
        parts.extend([
            "每段先写「【第N段：回应=接受 心情=害羞 台词=可选台词】」。",
            "标记为“需要完整经过”的段落，紧接着写「【过程N】」换行「【【完整正文】】」。",
            "标记为“只需简短回应”的段落不要写过程块，只在该段指令后写一至三句自然回应，不要扩写完整事件经过。",
            "第 1、2、3 段必须在同一条回复里全部出现。不要写夜间安排。",
        ])
    available_actions = [str(item).strip() for item in pending.get("available_actions") or [] if str(item).strip()]
    if pending_type == "night_action_choice" and available_actions:
        parts.append("今晚能做的事：" + " / ".join(NIGHT_ACTIONS.get(item, item) for item in available_actions) + "。")
        detail_rule = _night_detail_rule(pending)
        if detail_rule:
            parts.append("需要补充具体动向时，可选：" + detail_rule + "。")
        example_action = available_actions[0]
        parts.append(f"决定后写「【夜间行动：行动={NIGHT_ACTIONS.get(example_action, example_action)} 台词=可选台词】」。")
    condition_prompt = str(pending.get("condition_prompt") or "").strip()
    if condition_prompt:
        parts.append(condition_prompt)
    if pending_type in {"process_write", "process_reaction_write"} and process_style:
        parts.extend(["", process_style])
    if extra_rules:
        parts.extend(["", *[str(item) for item in extra_rules if str(item).strip()]])
    return str(render_placeholders("\n".join(parts).strip(), config))
