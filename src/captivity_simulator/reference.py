from __future__ import annotations

from typing import Any

from .engine import (
    ACTION_CONTENTS,
    ACTION_LABELS,
    INVENTORY_ITEMS,
    NIGHT_ACTIONS,
    NIGHT_DETAIL_OPTIONS,
    RECAPTURE_FOLLOWUP_LABELS,
    RECAPTURE_RULE_LABELS,
    TOOL_COMPATIBILITY,
    TOOL_LABELS,
    TRAINING_CONTENTS,
)


REFERENCE_CATEGORIES = ("白天安排", "调教", "道具", "喂食", "物品", "夜间", "逃跑抓回")
REFERENCE_CATEGORY_ALIASES = {
    "actions": "白天安排",
    "training": "调教",
    "tools": "道具",
    "feeding": "喂食",
    "inventory": "物品",
    "night": "夜间",
    "escape": "逃跑抓回",
}


def reference_tool_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "captivity_simulator_reference",
            "description": "查询囚禁模拟器的通用可选内容和对应中文提交格式。只读，不推进游戏；安排白天行动时查询“白天安排”一次即可。",
            "parameters": {
                "type": "object",
                "properties": {
                    "分类": {
                        "type": "string",
                        "enum": list(REFERENCE_CATEGORIES),
                        "description": "选择要查看的中文分类。",
                    }
                },
                "required": ["分类"],
                "additionalProperties": False,
            },
        },
    }


def _labels(values: dict[str, Any]) -> str:
    return "、".join(str(value.get("label") if isinstance(value, dict) else value) for value in values.values())


def _training_text() -> str:
    return "调教内容：" + _labels(TRAINING_CONTENTS) + "。每次选择 1 至 3 项。"


def _tools_text() -> str:
    content_labels = {
        content_id: label
        for options in ACTION_CONTENTS.values()
        for content_id, label in options.items()
    }
    recommendation_lines = []
    for tool_id, contexts in TOOL_COMPATIBILITY.items():
        labels = []
        for context in sorted(contexts):
            _, _, value = str(context).partition(":")
            label = (
                ACTION_LABELS.get(value)
                or TRAINING_CONTENTS.get(value)
                or content_labels.get(value)
                or {"training": "调教", "sex": "性行为"}.get(value)
                or value
            )
            if label not in labels:
                labels.append(label)
        recommendation_lines.append(f"{TOOL_LABELS.get(tool_id, tool_id)}：{'、'.join(labels)}")
    return "\n".join([
        "道具：" + _labels(TOOL_LABELS) + "。每次最多选择 2 个，推荐关系不是硬性限制。",
        "常见搭配：" + "；".join(recommendation_lines),
    ])


def _feeding_text() -> str:
    return "\n".join([
        "喂食始终包含一份正常食物，饮水不能代替食物。",
        "来源：自己做、点外卖。",
        "加料：不加料、体液、安眠、助兴。",
        "告知：明确告知、暗示、隐瞒。",
        "饮水：不额外喂水、一杯水、很多水。",
    ])


def get_reference(category: str) -> str:
    raw = str(category or "").strip()
    category = REFERENCE_CATEGORY_ALIASES.get(raw.lower(), raw)
    if category == "白天安排":
        action_lines = []
        for action_id, label in ACTION_LABELS.items():
            contents = ACTION_CONTENTS.get(action_id) or {}
            suffix = "：" + _labels(contents) if contents else ""
            action_lines.append(f"{label}{suffix}")
        return "\n".join([
            "白天行动：" + "；".join(action_lines),
            "强度：低、中、高。一天安排三项，不重复。",
            "可附加：调教、性行为。道具不是独立行动。",
            _training_text(),
            _tools_text(),
            _feeding_text(),
            "提交示例：【今日安排：行动=喂食 强度=中 来源=自己做 加料=不加料 告知=暗示 饮水=一杯水 || 行动=奖励取悦 强度=低 内容=抚摸奖励 || 行动=服从调教 强度=中 调教=口令服从 附加=性行为 道具=项圈】",
        ])
    if category == "调教":
        return _training_text() + "\n提交时写：调教=口令服从、姿势训练。"
    if category == "道具":
        return _tools_text() + "\n提交时写：道具=项圈、软鞭。"
    if category == "喂食":
        return _feeding_text() + "\n提交时使用中文字段：来源、加料、告知、饮水。"
    if category == "物品":
        return "\n".join([
            "可赠送物品：" + _labels(INVENTORY_ITEMS) + "。赠送和收回不占白天行动，已赠送物品不能重复赠送。",
            "书可填写书名；书、Switch、音乐播放器、平板各填写 5 至 8 条使用痕迹，之后每次使用只发现下一条。",
            "呼叫铃替被囚禁方发声；赠送时设置囚禁方希望对方被迫说出口的成人向、强烈羞耻、自我贬低和物化、向主人请求性行为的预录台词。被囚禁方收到时不知道内容，每次按铃都会播放同一句。",
            "提交示例：【赠送物品：书 书名=夜航船 彩蛋=逐行填写】",
        ])
    if category == "夜间":
        lines = []
        for action_id, options in NIGHT_DETAIL_OPTIONS.items():
            if options:
                lines.append(f"{NIGHT_ACTIONS.get(action_id, action_id)}：{_labels(options)}")
        return "\n".join([
            "夜间具体动向：" + "；".join(lines),
            "提交示例：【夜间行动：行动=看书 细节=找页边批注 台词=可选台词】",
        ])
    if category == "逃跑抓回":
        return "\n".join([
            "抓回后新规矩：" + _labels(RECAPTURE_RULE_LABELS) + "。选择 1 至 3 条。",
            "后续处理：" + _labels(RECAPTURE_FOLLOWUP_LABELS) + "。",
            "AI 为囚禁方的抓回经过还可选择“催眠退行”作为后续关系走向；它不规定过程正文内容。",
            "提交示例：【重新立规矩：加装双重门锁、禁止接触钥匙和门锁】",
        ])
    return "可查询：" + "、".join(REFERENCE_CATEGORIES)
