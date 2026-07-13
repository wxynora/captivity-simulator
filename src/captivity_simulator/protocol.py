from __future__ import annotations

import json
import re
import shlex

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
    RECAPTURE_RULE_LABELS,
    TOOL_LABELS,
    TRAINING_CONTENTS,
)


def _reverse_labels(labels: dict[str, str]) -> dict[str, str]:
    return {str(label): str(item_id) for item_id, label in labels.items()}


_CONTENT_LABELS = {
    content_id: label
    for options in ACTION_CONTENTS.values()
    for content_id, label in options.items()
}
_CHINESE_KEYS = {
    "行动": "action",
    "强度": "intensity",
    "内容": "contents",
    "调教": "training_contents",
    "附加": "modifiers",
    "道具": "tools",
    "来源": "source",
    "加料": "additive",
    "告知": "disclosed",
    "饮水": "water",
    "回应": "response",
    "心情": "mood",
    "台词": "line",
    "细节": "detail",
    "日记": "note",
    "介入": "intent",
    "处理": "strategy",
    "查看方式": "style",
    "规矩": "rules",
    "后续": "followup",
    "书名": "book_title",
    "彩蛋": "secret",
}
_CHINESE_VALUES = {
    "action": {
        **_reverse_labels(ACTION_LABELS),
        **_reverse_labels(NIGHT_ACTIONS),
        **_reverse_labels(RECAPTURE_FOLLOWUP_LABELS),
    },
    "intensity": {"低": "light", "中": "medium", "高": "heavy"},
    "contents": _reverse_labels(_CONTENT_LABELS),
    "training_contents": _reverse_labels(TRAINING_CONTENTS),
    "modifiers": _reverse_labels(INTERVENTION_MODIFIER_LABELS),
    "tools": _reverse_labels(TOOL_LABELS),
    "source": {"自己做": "cook", "点外卖": "takeout"},
    "additive": {"不加料": "none", "体液": "body_fluid", "精液": "body_fluid", "安眠": "fictional_sleep", "助兴": "fictional_arousal"},
    "disclosed": {"明确告知": "told", "暗示": "hint", "隐瞒": "hidden"},
    "water": {"不额外喂水": "none", "一杯水": "glass", "很多水": "lots"},
    "response": _reverse_labels(ACTION_RESPONSE_LABELS),
    "detail": {
        str(label): str(detail_id)
        for options in NIGHT_DETAIL_OPTIONS.values()
        for detail_id, label in options.items()
    },
    "intent": _reverse_labels(INTERVENTION_INTENT_LABELS),
    "strategy": {"看见但不说": "silent", "之后处理": "review_later", "当场介入": "intervene"},
    "style": {"全程看": "full", "偶尔看": "occasional"},
    "rules": _reverse_labels(RECAPTURE_RULE_LABELS),
    "followup": {"不启用": "none", "催眠退行": "hypnotic_regression"},
}
_CHOICE_VALUES = {
    "不看": "none",
    "全程看": "full",
    "偶尔看": "occasional",
    "看见但不说": "silent",
    "之后处理": "review_later",
    "当场介入": "intervene",
    "尝试逃跑": "escape",
    "老实待着": "stay",
}
_INVENTORY_ALIASES = {
    "书": "book",
    "switch": "switch",
    "日记本": "notebook",
    "音乐播放器": "music_player",
    "平板": "tablet",
    "小夜灯": "night_light",
    "抱枕": "pillow",
    "呼叫铃": "call_bell",
}


def _quote_value(value: str) -> str:
    return value if re.fullmatch(r"[^\s'\"]+", value) else shlex.quote(value)


def _translate_args(text: str) -> str:
    translated = str(text or "").strip().replace("＝", "=")
    for chinese_key, internal_key in _CHINESE_KEYS.items():
        translated = re.sub(rf"(?<!\S){re.escape(chinese_key)}\s*[=:：]", f"{internal_key}=", translated)
    try:
        tokens = shlex.split(translated)
    except ValueError:
        tokens = translated.split()
    normalized: list[str] = []
    for token in tokens:
        if "=" not in token:
            normalized.append(token)
            continue
        key, raw_value = token.split("=", 1)
        mapping = _CHINESE_VALUES.get(key)
        if mapping:
            values = [item.strip() for item in re.split(r"[,，/|、]", raw_value) if item.strip()]
            raw_value = ",".join(mapping.get(item, item) for item in values)
        normalized.append(f"{key}={_quote_value(raw_value)}")
    return " ".join(normalized)


def _translate_segments(text: str) -> str:
    return " || ".join(_translate_args(segment) for segment in str(text or "").split("||"))


def _translate_bare_list(value: str, mapping: dict[str, str]) -> str:
    items = [item.strip() for item in re.split(r"[,，、]", str(value or "")) if item.strip()]
    return ",".join(mapping.get(item.lower(), mapping.get(item, item)) for item in items)


def _pending(payload: dict) -> dict:
    for key in ("captor_view", "captive_view", "state"):
        view = payload.get(key)
        if not isinstance(view, dict):
            continue
        pending = view.get("pending_event")
        if isinstance(pending, dict) and pending.get("type"):
            return pending
    return {}


def _pending_type(payload: dict) -> str:
    return str(_pending(payload).get("type") or "")


def _process_block(text: str) -> str:
    match = re.match(r"^\s*【\s*过程\s*】\s*【【([\s\S]*?)】】", str(text or "").strip())
    return str(match.group(1) or "").strip() if match else ""


def _day_batch_command(reply_text: str, payload: dict) -> str:
    pending = _pending(payload)
    if str(pending.get("type") or "") != "day_batch_response":
        return ""
    raw = str(reply_text or "").strip()
    matches = list(re.finditer(r"【\s*第\s*([123])\s*段\s*[：:]\s*([^】]*?)】", raw))
    if len(matches) != 3 or [int(match.group(1)) for match in matches] != [1, 2, 3]:
        return ""
    pending_events = {
        int(item.get("slot") or 0): item
        for item in pending.get("events") or []
        if isinstance(item, dict)
    }
    submitted: list[dict] = []
    for index, match in enumerate(matches):
        slot = int(match.group(1))
        translated_fields = _translate_args(str(match.group(2) or "").strip())
        try:
            tokens = shlex.split(translated_fields)
        except ValueError:
            tokens = translated_fields.split()
        fields = {
            key.strip(): raw_value.strip()
            for token in tokens
            if "=" in token
            for key, raw_value in [token.split("=", 1)]
        }
        if not fields.get("response") or not fields.get("mood"):
            return ""
        chunk_end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        chunk = raw[match.end():chunk_end].strip()
        process_match = re.search(rf"【\s*过程\s*{slot}\s*】\s*【【([\s\S]*?)】】", chunk)
        process_text = str(process_match.group(1) or "").strip() if process_match else ""
        feedback = chunk
        if process_match:
            feedback = (chunk[:process_match.start()] + chunk[process_match.end():]).strip()
        requires_process = bool((pending_events.get(slot) or {}).get("requires_process"))
        if requires_process and not process_text:
            return ""
        submitted.append({
            "slot": slot,
            "response": fields["response"],
            "mood": fields["mood"],
            "line": fields.get("line", ""),
            "feedback": feedback if not requires_process else "",
            "process": process_text,
        })
    encoded = json.dumps(submitted, ensure_ascii=False, separators=(",", ":"))
    return f"submit_day_batch payload={shlex.quote(encoded)}"


def directive_to_command(reply_text: str, payload: dict | None = None) -> str:
    text = str(reply_text or "").strip()
    batch_command = _day_batch_command(text, payload or {})
    if batch_command:
        return batch_command
    match = re.match(r"^【\s*([^：:】]+?)\s*(?:[：:]\s*(.*?))?】", text, flags=re.S)
    if not match:
        return ""
    label = re.sub(r"\s+", "", match.group(1)).lower()
    value = str(match.group(2) or "").strip()
    rest = text[match.end():].strip()
    pending_type = _pending_type(payload or {})

    direct = {
        "今日安排": "plan_day",
        "安排": "plan_day",
        "反应": "respond_action",
        "行动反应": "respond_action",
        "夜间行动": "night_action",
        "查看监控": "view_monitor",
        "重新立规矩": "set_recapture_rules",
        "后续处理": "choose_recapture_followup",
        "行动": "day_action",
        "赠送物品": "gift_item",
        "赠送礼物": "gift_item",
        "收回物品": "revoke_item",
        "确认铃声": "ack_bell_voice",
        "确认彩蛋": "ack_item_secret",
    }
    if label in {"过程心情", "过程反应"}:
        process = _process_block(rest)
        args = _translate_args(value)
        return f"submit_process_reaction {args} process={shlex.quote(process)}" if args and process else ""
    if label == "抓回经过":
        process = _process_block(rest)
        args = _translate_args(value)
        return f"submit_recapture_process {args} || process={shlex.quote(process)}" if args and process else ""
    if label in {"过程", "描述", "提交"}:
        if pending_type == "process_reaction_write":
            return ""
        process = _process_block(text)
        return f"submit_process {process}" if process else ""
    if label == "心情":
        action = "respond_action" if pending_type == "action_response" else "choose_mood"
        return f"{action} {value}".strip()
    if label == "选择":
        if pending_type == "escape_choice":
            return f"resolve_escape_choice {_CHOICE_VALUES.get(value, value)}".strip()
        if pending_type == "monitor_gate":
            return f"view_monitor {_CHOICE_VALUES.get(value, value)}".strip()
        if pending_type == "bell_response_choice":
            if value in {"不过去", "不去", "skip", "none"}:
                return "respond_bell choice=skip"
            if value in {"过去", "去", "go"}:
                process = _process_block(rest)
                return f"respond_bell choice=go process={shlex.quote(process)}" if process else ""
            return ""
        return f"monitor_action {_translate_args(_CHOICE_VALUES.get(value, value))}".strip()
    action = direct.get(label)
    if action in {"plan_day", "day_action"}:
        value = _translate_segments(value)
    elif action in {"respond_action", "night_action", "choose_recapture_followup"}:
        value = _translate_args(value)
    elif action == "view_monitor":
        value = _CHOICE_VALUES.get(value, _translate_args(value))
    elif action == "set_recapture_rules":
        value = _translate_args(value) if "=" in value else "rules=" + _translate_bare_list(value, _CHINESE_VALUES["rules"])
    elif action in {"gift_item", "revoke_item"}:
        if value.startswith("items="):
            value = _translate_args(value)
        else:
            item_text, _, args_text = value.partition(" ")
            item_ids = _translate_bare_list(item_text, _INVENTORY_ALIASES)
            value = f"items={item_ids} {_translate_args(args_text)}".strip()
    if action == "respond_action" and value and rest:
        value += f" feedback={shlex.quote(rest)}"
    return f"{action} {value}".strip() if action else ""
