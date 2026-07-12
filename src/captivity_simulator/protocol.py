from __future__ import annotations

import re
import shlex


def _pending_type(payload: dict) -> str:
    for key in ("captor_view", "captive_view", "state"):
        view = payload.get(key)
        if not isinstance(view, dict):
            continue
        pending = view.get("pending_event")
        if isinstance(pending, dict) and pending.get("type"):
            return str(pending["type"])
    return ""


def _process_block(text: str) -> str:
    match = re.match(r"^\s*【\s*过程\s*】\s*【【([\s\S]*?)】】", str(text or "").strip())
    return str(match.group(1) or "").strip() if match else ""


def directive_to_command(reply_text: str, payload: dict | None = None) -> str:
    text = str(reply_text or "").strip()
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
        return f"submit_process_reaction {value} process={shlex.quote(process)}" if value and process else ""
    if label == "抓回经过":
        process = _process_block(rest)
        return f"submit_recapture_process {value} || process={shlex.quote(process)}" if value and process else ""
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
            return f"resolve_escape_choice {value}".strip()
        if pending_type == "monitor_gate":
            return f"view_monitor {value}".strip()
        if pending_type == "bell_response_choice":
            if value in {"不过去", "不去", "skip", "none"}:
                return "respond_bell choice=skip"
            if value in {"过去", "去", "go"}:
                process = _process_block(rest)
                return f"respond_bell choice=go process={shlex.quote(process)}" if process else ""
            return ""
        return f"monitor_action {value}".strip()
    action = direct.get(label)
    return f"{action} {value}".strip() if action else ""
