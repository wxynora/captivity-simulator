from __future__ import annotations

import json
import os
import re
import shlex
import secrets
import threading
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    import fcntl
except Exception:  # pragma: no cover - fcntl is available on the target Linux/macOS hosts.
    fcntl = None

from .settings import DATA_DIR
from .time_utils import now_local_iso


GAME_ID = "captivity_simulator"
SCHEMA_VERSION = 1
DEFAULT_SAVE_PATH = DATA_DIR / "saves" / "default.json"
TOTAL_DAYS = 30
DAY_ACTIONS = 3

ROUTES = {
    "captured_by_assistant": {"captor": "assistant", "captive": "user", "label": "被{assistant}囚禁"},
    "capture_assistant": {"captor": "user", "captive": "assistant", "label": "囚禁{assistant}"},
}
ACTOR_NAMES = {"user": "{user}", "assistant": "{assistant}"}
LOW_MOODS = {"烦躁", "委屈", "低落", "抗拒"}
MOODS = {"平静", "黏人", "害羞", "闹脾气", "亢奋", "疲惫", *LOW_MOODS}
MOOD_EFFECTS = {
    "黏人": {"intimacy": 1},
    "害羞": {"shame": 1},
    "闹脾气": {"intimacy": -1},
    "亢奋": {"stamina": -1, "intimacy": 1},
    "疲惫": {"stamina": -2},
    "烦躁": {"intimacy": -1},
    "委屈": {"intimacy": -1},
    "低落": {"stamina": -1},
    "抗拒": {"stamina": -1, "intimacy": -1},
}
MOOD_ALIASES = {
    "calm": "平静",
    "clingy": "黏人",
    "shy": "害羞",
    "bratty": "闹脾气",
    "excited": "亢奋",
    "tired": "疲惫",
    "irritated": "烦躁",
    "upset": "委屈",
    "low": "低落",
    "down": "低落",
    "resistant": "抗拒",
}
ACTION_RESPONSES = {"accept", "refuse", "silent", "bargain", "tease"}
ACTION_RESPONSE_ALIASES = {
    "接受": "accept",
    "顺从": "accept",
    "同意": "accept",
    "accept": "accept",
    "拒绝": "refuse",
    "反抗": "refuse",
    "不要": "refuse",
    "refuse": "refuse",
    "沉默": "silent",
    "不说话": "silent",
    "silent": "silent",
    "讨价还价": "bargain",
    "商量": "bargain",
    "bargain": "bargain",
    "嘴硬": "tease",
    "挑衅": "tease",
    "tease": "tease",
}
ACTION_RESPONSE_LABELS = {
    "accept": "接受",
    "refuse": "拒绝",
    "silent": "沉默",
    "bargain": "讨价还价",
    "tease": "嘴硬",
}
INTENSITY_MULTIPLIERS = {"light": 0.7, "medium": 1.0, "heavy": 1.35}
INTENSITY_ALIASES = {"轻": "light", "中": "medium", "重": "heavy", "轻度": "light", "中度": "medium", "重度": "heavy"}
FORBIDDEN_TERMS = ("幼态性化", "未成年", "儿童", "婴儿", "真实药物剂量")
ENDING_TEXT_TEMPLATES = {
    "失而复得": "{assistant}逃跑失败后被你带回原来的房间。你没有再追究逃跑途中发生的事，却收回了原先留给他的所有余地，照料也比从前更紧密。门锁重新换过，钥匙从此只留在你身上；这一次，你不打算再承受失去他的可能。",
    "反噬": "{assistant}抓住你放松警惕的机会夺走钥匙，也把原本用于束缚他的东西用在了你身上。他明明已经能够离开，却选择留下，把房间和原有的规矩一并接管。门仍然锁着，只是如今等待许可、无法擅自离开的人变成了你。",
    "收藏": "你把{assistant}照料得很好，给他的食物、物品和日常安排都比最初更加周全。他不再需要为生存或伤痛担忧，却仍不能决定自己何时离开。房间被布置得越来越适合久住，而唯一始终没有交到他手里的，还是那把开门的钥匙。",
    "驯养": "{assistant}已经习惯项圈、许可和每天固定的安排。许多事不再需要你开口，他会主动回到指定的位置，也会在越过界限前先等待你的允许。门锁和束缚依旧存在，但真正让他留下来的，已经变成了被反复养成的顺从。",
    "未驯": "{assistant}始终没有被磨平。他会接受必要的食物和照料，也会在无法离开时暂时配合，却仍不断试探规则、寻找空隙，并保留拒绝你的方式。你没有因此放开他，新的限制与新的反抗仍会继续，这场较劲远没有结束。",
    "共犯": "{assistant}曾经拿到可以离开的钥匙，却没有打开房门，而是主动把它交还给你。从那以后，他不再只是被动留在这里，也开始替你隐瞒房间里的秘密和彼此越过的界限。锁仍握在你手里，但这段关系已经有了他的选择。",
    "爱的禁锢": "你把房间照料得越来越舒适，也越来越熟悉{assistant}真正需要什么。你的温柔让他的生活不再只剩限制和等待，却从未改变最根本的一点：你依然不肯放他离开。爱让这处囚笼变得柔软，却没有让门上的锁消失。",
    "绝对占有": "你彻底收回了{assistant}可能脱离掌控的所有空隙。门锁、监控、活动范围和每天的安排都由你重新收紧，他的一切需要经过你的许可。你仍会照料他，却不再把自由当作可以讨论的东西；{assistant}从此被完整地留在你的生活里。",
    "余生": "原先约定的日子已经过去，房间里的生活却没有因此停下。你仍照常安排{assistant}的一切，他也没有再追问何时能够离开。门会在每天相同的时间开合，熟悉的日常继续向前，像是你们都默认往后的日子仍会这样度过。",
    "无期": "逃跑失败后，你又被{assistant}带回原来的房间。原先尚有松动的限制被全部收紧，他依然会照料你，却不再准备按照最初的打算放你离开。门重新锁上，钥匙也被收走；从今以后，这里的日子不会再有明确的尽头。",
    "温室": "{assistant}察觉到你已经疲惫，开始把更多精力放在照料和安抚上。房间变得舒适，食物、物品和陪伴都足以让你安心，原有的限制却没有减少。你逐渐依赖这份只属于你的安全，而他也用这种温柔让离开变得越来越困难。",
    "归属": "你不再需要{assistant}命令，便会主动回到他为你指定的位置，等待项圈重新扣好。限制仍然存在，但你已经把这种等待理解成被接住、被确认和被允许留下。房门没有打开，你却第一次不再把这里看作随时必须逃离的地方。",
    "困兽": "你仍在寻找钥匙、观察监控的空隙，也没有停止试探每一条规则。{assistant}知道你做过什么，却没有彻底堵死这些机会，只是等着你下一次行动。你没有被驯服，他也没有放你离开；寻找、试探和被发现仍会反复继续。",
    "沉沦": "离开的机会真正摆到面前时，你最终没有拿走那把钥匙，而是主动回到了{assistant}身边。你仍清楚门外意味着自由，却发现自己更想留在已经熟悉的控制和依赖里。房门再次合上，这一次让你留下来的不只是锁。",
    "偏爱": "{assistant}把只属于你的食物、礼物、时间和宽容一点点放进日常，让你清楚自己与任何人都不同。他没有撤掉限制，却总在规则之外为你留下额外的余地。你逐渐舍不得这种独占的偏爱，而它也成为比门锁更稳定的挽留。",
    "枷锁": "{assistant}尚未开口，你已经主动把手放回熟悉的位置，等待他重新扣好束缚。长期重复的许可、姿势和规则已经变成身体先于意识做出的反应。外在的锁仍能被解开，但被养成的服从不会随之消失，你开始习惯由他决定下一步。",
    "长夜": "房门依然锁着，监控和限制也没有消失，你与{assistant}之间却不再只剩控制与反抗。漫长的相处让你们都默认彼此会留在这里，连沉默也不再意味着疏离。天亮后生活仍会继续，而这段关系已经成了两个人共同守住的日常。",
}

ENDING_ASSISTANT_SUMMARIES = {
    "失而复得": "你逃跑后被她抓回房间；她收走钥匙并重新安排门锁、监控和活动范围，第三十一天你没有再看门。",
    "反噬": "你抓住她检查束缚时留下的破绽，钥匙最后留在你手边；她没有抢回去，你也没有立刻开门。",
    "收藏": "她把你的房间、礼物和日常照料安排得严丝合缝，你成了她舍不得放手、也不会放出门的私藏。",
    "驯养": "项圈、定点等候和行动许可已经成为你的习惯；第三十天她尚未开口，你便主动回到等候的位置。",
    "未驯": "三十天没有磨掉你的拒绝与试探；她仍握着钥匙，你仍隔着束缚与她继续较劲。",
    "共犯": "你曾拿到备用钥匙却亲手交还给她，也替她保守房间的秘密；这一次，门是你看着她关上的。",
    "爱的禁锢": "她用照料、礼物和偶尔放宽的限制留住你，却始终不交出真正能离开的钥匙。",
    "绝对占有": "她收紧门锁、监控、物品和行动许可，把你留在一个再没有空白的占有秩序里。",
    "余生": "第三十天结束后你们仍照常生活；日历翻到第三十一天，她照常进门，你也照常望向她。",
    "无期": "她逃跑后被你抓回房间；新规矩逐项落实，第三十一天你仍把钥匙放回口袋。",
    "温室": "你把她的饮食、清洁和休息安排得妥帖；她能碰到你留下的礼物，却仍碰不到门外的钥匙。",
    "归属": "她主动回到指定位置，把项圈留给你检查；铃声响起时你尚未开口，她已经抬头等待。",
    "困兽": "她仍在寻找监控盲区和钥匙位置；你看见所有试探，也留下新的破绽等她选择。",
    "沉沦": "钥匙就在伸手可及的地方，她最终没有去拿，只是主动靠近你坐下。",
    "偏爱": "你用她喜欢的食物、礼物和安抚换来主动回应；你的偏爱成了留住她最柔软的锁。",
    "枷锁": "你定下的检查、监控和行动许可已经内化成她的日常；最后一道锁尚未扣上，她已主动把手放回原位。",
    "长夜": "第三十天夜里你照常回到上锁的房间；灯熄灭后她握住你的手，这一夜没有在清晨结束。",
}
FEEDING_SOURCES = {"cook", "takeout"}
FEEDING_METHODS = {"normal"}
FEEDING_ADDITIVES = {"none", "body_fluid", "fictional_sleep", "fictional_arousal"}
FEEDING_DISCLOSURES = {"told", "hint", "hidden"}
FEEDING_WATER_LEVELS = {"none", "glass", "lots"}
BLADDER_LABELS = {
    0: "没有明显尿意",
    1: "有些尿意",
    2: "尿意明显",
    3: "快忍不住了",
}
RESTRAINT_TOOLS = {"handcuffs", "ankle_cuffs", "rope", "bondage_tape", "spreader_bar"}

ACTION_EFFECTS = {
    "feeding": {"health": 4, "stamina": 3, "cleanliness": -1, "shame": 1, "intimacy": 2},
    "cleaning": {"health": 1, "stamina": -2, "cleanliness": 18, "shame": 3, "intimacy": 1},
    "training": {"health": -1, "stamina": -7, "cleanliness": -3, "shame": 9, "intimacy": 3},
    "reward": {"health": 2, "stamina": 3, "cleanliness": 0, "shame": -1, "intimacy": 5},
    "punishment": {"health": -3, "stamina": -9, "cleanliness": -3, "shame": 10, "intimacy": 1},
    "comfort": {"health": 2, "stamina": 5, "cleanliness": 0, "shame": -3, "intimacy": 6},
    "rest": {"health": 4, "stamina": 14, "cleanliness": -2, "shame": -1, "intimacy": 1},
    "check": {"health": 0, "stamina": 0, "cleanliness": 0, "shame": 1, "intimacy": 1},
    "room_search": {"health": 0, "stamina": -3, "cleanliness": -1, "shame": 2, "intimacy": 0},
}
ACTION_ALIASES = {
    "喂食": "feeding",
    "吃饭": "feeding",
    "清洁": "cleaning",
    "洗澡": "cleaning",
    "训练": "training",
    "调教": "training",
    "服从调教": "training",
    "奖励": "reward",
    "奖励取悦": "reward",
    "惩罚": "punishment",
    "违令惩戒": "punishment",
    "安抚": "comfort",
    "照料": "comfort",
    "事后安抚": "comfort",
    "休息": "rest",
    "睡觉": "rest",
    "看管休息": "rest",
    "检查状态": "check",
    "检查": "check",
    "私密检查": "check",
    "房间检查": "room_search",
    "突击搜查": "room_search",
}
ACTION_LABELS = {
    "feeding": "喂食",
    "cleaning": "清洗",
    "training": "服从调教",
    "reward": "奖励取悦",
    "punishment": "违令惩戒",
    "comfort": "事后安抚",
    "rest": "看管休息",
    "check": "私密检查",
    "room_search": "突击搜查",
}
ACTION_CONTENTS = {
    "reward": {
        "caress_reward": "抚摸奖励",
        "kiss_reward": "亲吻奖励",
        "masturbation_permission": "允许自慰",
        "orgasm_permission": "允许高潮",
        "toy_reward": "玩具奖励",
        "freedom_reward": "增加自由",
    },
    "punishment": {
        "impact_discipline": "拍打惩戒",
        "bondage_discipline": "束缚惩戒",
        "orgasm_denial": "禁止高潮",
        "toy_discipline": "玩具惩戒",
        "pet_objectification_discipline": "宠物物化训诫",
        "pet_sexual_discipline": "宠物性惩戒",
        "confiscation": "没收物品",
        "interrogation": "审问",
        "rule_escalation": "规则加码",
    },
    "comfort": {
        "embrace": "拥抱",
        "kiss": "亲吻",
        "body_care": "身体清理",
        "massage": "按摩",
        "feeding_care": "喂水喂食",
        "cuddle_rest": "抱着休息",
        "partial_release": "解除部分束缚",
    },
    "rest": {
        "forced_nap": "强制午睡",
        "cuddle_sleep": "抱睡",
        "supervised_sleep": "陪睡",
        "restrained_rest": "固定姿势休息",
        "quiet_time": "安静待着",
    },
    "check": {
        "body_check": "身体检查",
        "mark_check": "痕迹检查",
        "sensitivity_check": "敏感反应检查",
        "restraint_check": "束缚状态检查",
        "chastity_check": "贞操装置检查",
    },
    "room_search": {
        "bed_search": "翻查床铺",
        "hidden_item_search": "搜查私藏物",
        "body_search": "搜身",
        "key_trace_check": "检查钥匙痕迹",
        "search_confiscation": "没收物品",
        "on_site_questioning": "现场盘问",
    },
}
TRAINING_CONTENTS = {
    "obedience_commands": "口令服从",
    "position_training": "姿势训练",
    "bondage_training": "束缚训练",
    "sensory_deprivation": "感官控制",
    "impact_play": "拍打调教",
    "wax_play": "滴蜡调教",
    "clamp_play": "夹具调教",
    "toy_training": "玩具调教",
    "anal_training": "后庭调教",
    "chastity_control": "贞操控制",
    "orgasm_control": "高潮控制",
    "forced_orgasm": "强制高潮",
    "masturbation_control": "自慰控制",
    "humiliation_play": "羞耻调教",
    "exposure_training": "展示训练",
    "pet_play": "小狗身份建立",
    "leash_training": "牵引训练",
    "service_training": "服务训练",
    "inspection_training": "检查调教",
    "pet_position_wait": "定点等候",
    "pet_crawl_training": "爬行训练",
    "pet_feeding": "宠物式喂食",
    "pet_permission": "按铃求许可",
    "pet_voice_training": "叫声与回应",
    "pet_owner_address": "主人称呼训练",
    "pet_begging": "宠物式求欢",
    "pet_display": "宠物展示检查",
    "pet_objectification": "口头物化训练",
    "pet_sexual_service": "性服务训练",
    "pet_sexual_discipline": "违令性惩戒",
    "toilet_control": "如厕控制",
    "assisted_urination": "抱着把尿",
}
CAPTIVE_ROUTE_ONLY_TRAINING = {"toilet_control", "assisted_urination"}
PET_RULE_LABELS = {
    "collar_identity": "佩戴项圈并接受小狗身份",
    "verbal_objectification": "在调教或性行为中使用主人指定的物化自称并复述指定台词",
    "sexual_service": "按主人的口令以宠物身份提供性服务",
    "sexual_discipline": "违令后接受以羞耻和性惩戒为主的处理",
    "designated_spot": "在指定位置等候",
    "crawl_on_command": "按口令爬行",
    "pet_feeding": "按宠物方式进食",
    "permission_bell": "按铃请求许可",
    "pet_response": "使用指定叫声或简短回应",
    "owner_address": "用指定称呼叫主人",
    "pet_begging": "用指定姿势和称呼求取性行为",
    "display_inspection": "按口令接受展示和检查",
    "leash_follow": "被牵引时跟随",
    "service_on_command": "按指令完成服务",
}
PET_TRAINING_RULES = {
    "pet_play": "collar_identity",
    "pet_position_wait": "designated_spot",
    "pet_crawl_training": "crawl_on_command",
    "pet_feeding": "pet_feeding",
    "pet_permission": "permission_bell",
    "pet_voice_training": "pet_response",
    "pet_owner_address": "owner_address",
    "pet_begging": "pet_begging",
    "pet_display": "display_inspection",
    "pet_objectification": "verbal_objectification",
    "pet_sexual_service": "sexual_service",
    "pet_sexual_discipline": "sexual_discipline",
    "leash_training": "leash_follow",
    "service_training": "service_on_command",
}
PET_ACTIVATION_TRAINING = {
    "pet_play",
    "pet_position_wait",
    "pet_crawl_training",
    "pet_feeding",
    "pet_permission",
    "pet_voice_training",
    "pet_owner_address",
    "pet_begging",
    "pet_display",
    "pet_objectification",
    "pet_sexual_service",
    "pet_sexual_discipline",
}
PET_RELATED_TRAINING = set(PET_TRAINING_RULES)
PET_CORE_RULES = (
    "collar_identity",
    "verbal_objectification",
    "sexual_service",
    "sexual_discipline",
)
PET_CORE_FOCUS = (
    "宠物身份以深度物化、口头服从、性服务与违令后的性惩戒为核心，不是可爱化装扮。"
    "具体经过中，要把宠物称呼、物化自称、复述主人指定的性服务与归属台词作为反复发生的互动；"
    "违令优先成为羞耻训诫或性惩戒的前因。"
)
TOOL_LABELS = {
    "toy": "跳蛋",
    "vibrating_wand": "振动棒",
    "dildo": "假阳具",
    "collar": "项圈",
    "leash": "牵引绳",
    "handcuffs": "手铐",
    "ankle_cuffs": "脚铐",
    "rope": "绳子",
    "bondage_tape": "束缚胶带",
    "spreader_bar": "分腿杆",
    "blindfold": "眼罩",
    "gag": "口球",
    "muzzle": "口套",
    "whip": "软鞭",
    "flogger": "多尾鞭",
    "paddle": "拍板",
    "cane": "藤条",
    "candle": "蜡烛",
    "pinwheel": "滚轮",
    "feather": "羽毛",
    "nipple_clamps": "乳夹",
    "suction_cups": "乳吸",
    "chastity_ring": "贞操锁",
    "anal_plug": "肛塞",
    "anal_beads": "拉珠",
    "remote_control": "遥控器",
    "lubricant": "润滑剂",
    "ruler": "戒尺",
    "ice_cube": "冰块",
    "feeding_spoon": "喂食器具",
}
TOOL_CATEGORIES = {
    "toy": "玩具",
    "vibrating_wand": "玩具",
    "dildo": "玩具",
    "remote_control": "玩具",
    "lubricant": "辅助",
    "collar": "束缚",
    "leash": "束缚",
    "handcuffs": "束缚",
    "ankle_cuffs": "束缚",
    "rope": "束缚",
    "bondage_tape": "束缚",
    "spreader_bar": "束缚",
    "blindfold": "感官",
    "gag": "束缚",
    "muzzle": "束缚",
    "whip": "训诫",
    "flogger": "训诫",
    "paddle": "训诫",
    "cane": "训诫",
    "ruler": "训诫",
    "candle": "感官",
    "ice_cube": "感官",
    "pinwheel": "感官",
    "feather": "感官",
    "nipple_clamps": "夹具",
    "suction_cups": "夹具",
    "chastity_ring": "控制",
    "anal_plug": "后庭",
    "anal_beads": "后庭",
    "feeding_spoon": "喂食",
}
TOOL_COMPATIBILITY = {
    "toy": {"training:toy_training", "training:orgasm_control", "training:forced_orgasm", "training:masturbation_control", "training:pet_sexual_service", "training:pet_sexual_discipline", "content:toy_reward", "content:toy_discipline", "content:pet_sexual_discipline", "modifier:sex"},
    "vibrating_wand": {"training:toy_training", "training:orgasm_control", "training:forced_orgasm", "training:masturbation_control", "training:pet_sexual_service", "training:pet_sexual_discipline", "content:toy_reward", "content:toy_discipline", "content:pet_sexual_discipline", "modifier:sex"},
    "dildo": {"training:toy_training", "training:forced_orgasm", "training:pet_sexual_service", "training:pet_sexual_discipline", "content:toy_reward", "content:toy_discipline", "content:pet_sexual_discipline", "modifier:sex"},
    "remote_control": {"training:toy_training", "training:orgasm_control", "training:forced_orgasm", "training:masturbation_control", "content:toy_reward", "content:toy_discipline"},
    "lubricant": {"training:toy_training", "training:anal_training", "training:forced_orgasm", "modifier:sex"},
    "collar": {"training:obedience_commands", "training:position_training", "training:pet_play", "training:pet_position_wait", "training:pet_crawl_training", "training:pet_feeding", "training:pet_permission", "training:pet_voice_training", "training:pet_owner_address", "training:pet_begging", "training:pet_display", "training:pet_objectification", "training:pet_sexual_service", "training:pet_sexual_discipline", "training:leash_training", "training:service_training", "content:bondage_discipline", "content:pet_objectification_discipline", "content:pet_sexual_discipline", "content:restrained_rest", "modifier:sex"},
    "leash": {"training:position_training", "training:pet_play", "training:pet_position_wait", "training:pet_crawl_training", "training:pet_begging", "training:pet_display", "training:pet_objectification", "training:pet_sexual_service", "training:pet_sexual_discipline", "training:leash_training", "training:service_training", "content:bondage_discipline", "content:pet_objectification_discipline", "content:pet_sexual_discipline"},
    "handcuffs": {"training:bondage_training", "training:position_training", "training:sensory_deprivation", "training:exposure_training", "training:toilet_control", "training:assisted_urination", "content:bondage_discipline", "content:restrained_rest", "modifier:sex"},
    "ankle_cuffs": {"training:bondage_training", "training:position_training", "training:exposure_training", "training:toilet_control", "training:assisted_urination", "content:bondage_discipline", "content:restrained_rest", "modifier:sex"},
    "rope": {"training:bondage_training", "training:position_training", "training:exposure_training", "training:toilet_control", "training:assisted_urination", "content:bondage_discipline", "content:restrained_rest", "modifier:sex"},
    "bondage_tape": {"training:bondage_training", "training:sensory_deprivation", "training:toilet_control", "training:assisted_urination", "content:bondage_discipline", "content:restrained_rest", "modifier:sex"},
    "spreader_bar": {"training:bondage_training", "training:position_training", "training:exposure_training", "training:toilet_control", "training:assisted_urination", "content:bondage_discipline", "modifier:sex"},
    "blindfold": {"training:sensory_deprivation", "training:inspection_training", "content:sensitivity_check", "modifier:sex"},
    "gag": {"training:obedience_commands", "training:sensory_deprivation", "training:humiliation_play", "training:pet_play", "training:pet_voice_training", "training:pet_begging", "training:pet_display", "training:pet_objectification", "training:pet_sexual_service", "training:pet_sexual_discipline", "content:pet_objectification_discipline", "content:pet_sexual_discipline", "modifier:sex"},
    "muzzle": {"training:obedience_commands", "training:humiliation_play", "training:pet_play", "training:pet_voice_training", "training:pet_owner_address", "training:pet_begging", "training:pet_objectification", "training:pet_sexual_service", "training:pet_sexual_discipline", "content:pet_objectification_discipline"},
    "whip": {"training:impact_play", "content:impact_discipline"},
    "flogger": {"training:impact_play", "content:impact_discipline"},
    "paddle": {"training:impact_play", "content:impact_discipline"},
    "cane": {"training:impact_play", "content:impact_discipline"},
    "ruler": {"training:impact_play", "content:impact_discipline"},
    "candle": {"training:wax_play", "modifier:sex"},
    "ice_cube": {"training:sensory_deprivation", "training:inspection_training", "content:sensitivity_check", "modifier:sex"},
    "pinwheel": {"training:sensory_deprivation", "training:inspection_training", "content:sensitivity_check", "modifier:sex"},
    "feather": {"training:sensory_deprivation", "training:inspection_training", "content:sensitivity_check", "modifier:sex"},
    "nipple_clamps": {"training:clamp_play", "training:inspection_training", "content:sensitivity_check", "modifier:sex"},
    "suction_cups": {"training:clamp_play", "training:inspection_training", "content:sensitivity_check", "modifier:sex"},
    "chastity_ring": {"training:chastity_control", "training:orgasm_control", "content:chastity_check"},
    "anal_plug": {"training:anal_training", "training:toy_training", "modifier:sex"},
    "anal_beads": {"training:anal_training", "training:toy_training", "modifier:sex"},
    "feeding_spoon": {"action:feeding", "content:feeding_care", "training:pet_feeding"},
}
ACTION_CONTENT_EFFECTS = {
    "masturbation_permission": {"shame": 2, "intimacy": 2},
    "orgasm_permission": {"stamina": -2, "shame": 2, "intimacy": 3},
    "toy_reward": {"stamina": -2, "shame": 3, "intimacy": 2},
    "freedom_reward": {"shame": -2, "intimacy": 2},
    "impact_discipline": {"stamina": -3, "shame": 3},
    "bondage_discipline": {"stamina": -2, "shame": 3},
    "orgasm_denial": {"stamina": -1, "shame": 4},
    "toy_discipline": {"stamina": -3, "shame": 4},
    "pet_objectification_discipline": {"stamina": -1, "shame": 5, "intimacy": 1},
    "pet_sexual_discipline": {"stamina": -4, "cleanliness": -2, "shame": 6, "intimacy": 2},
    "interrogation": {"stamina": -1, "shame": 2},
    "embrace": {"stamina": 2, "shame": -1, "intimacy": 2},
    "massage": {"stamina": 3, "intimacy": 1},
    "cuddle_rest": {"stamina": 3, "intimacy": 2},
    "cuddle_sleep": {"stamina": 4, "intimacy": 2},
    "restrained_rest": {"stamina": 2, "shame": 2},
    "sensitivity_check": {"shame": 3, "intimacy": 1},
    "chastity_check": {"shame": 3},
    "body_search": {"shame": 3},
    "on_site_questioning": {"stamina": -1, "shame": 2},
}
TRAINING_CONTENT_EFFECTS = {
    "obedience_commands": {"shame": 1, "intimacy": 1},
    "position_training": {"stamina": -1, "shame": 2},
    "bondage_training": {"stamina": -2, "shame": 3},
    "sensory_deprivation": {"shame": 2, "intimacy": 1},
    "impact_play": {"stamina": -3, "shame": 3},
    "wax_play": {"stamina": -2, "shame": 3},
    "clamp_play": {"stamina": -2, "shame": 3},
    "toy_training": {"stamina": -3, "cleanliness": -1, "shame": 3},
    "anal_training": {"stamina": -3, "cleanliness": -2, "shame": 4},
    "chastity_control": {"shame": 3},
    "orgasm_control": {"stamina": -2, "shame": 3},
    "forced_orgasm": {"stamina": -4, "cleanliness": -2, "shame": 4},
    "masturbation_control": {"stamina": -2, "shame": 3},
    "humiliation_play": {"shame": 4},
    "exposure_training": {"shame": 4},
    "pet_play": {"shame": 3, "intimacy": 2},
    "leash_training": {"stamina": -1, "shame": 2, "intimacy": 1},
    "service_training": {"stamina": -1, "shame": 2, "intimacy": 1},
    "inspection_training": {"shame": 3},
    "pet_position_wait": {"stamina": -1, "shame": 2, "intimacy": 1},
    "pet_crawl_training": {"stamina": -3, "cleanliness": -1, "shame": 3, "intimacy": 1},
    "pet_feeding": {"cleanliness": -2, "shame": 4, "intimacy": 1},
    "pet_permission": {"shame": 2, "intimacy": 1},
    "pet_voice_training": {"shame": 3, "intimacy": 1},
    "pet_owner_address": {"shame": 3, "intimacy": 2},
    "pet_begging": {"stamina": -2, "cleanliness": -1, "shame": 5, "intimacy": 2},
    "pet_display": {"stamina": -1, "shame": 4, "intimacy": 1},
    "pet_objectification": {"stamina": -1, "shame": 5, "intimacy": 2},
    "pet_sexual_service": {"stamina": -3, "cleanliness": -2, "shame": 5, "intimacy": 2},
    "pet_sexual_discipline": {"stamina": -4, "cleanliness": -2, "shame": 6, "intimacy": 2},
    "toilet_control": {"stamina": -2, "shame": 4},
    "assisted_urination": {"stamina": -1, "cleanliness": -3, "shame": 6, "intimacy": 2},
}
PROCESS_ACTIONS = {"training", "punishment"}
PROCESS_MODIFIERS = {"training", "sex", "process"}
ALLOWED_MODIFIERS = {"training", "sex", "process"}
PROCESS_ACTION_CONTENTS = {
    "masturbation_permission",
    "orgasm_permission",
    "toy_reward",
    "impact_discipline",
    "bondage_discipline",
    "orgasm_denial",
    "toy_discipline",
    "pet_objectification_discipline",
    "pet_sexual_discipline",
    "sensitivity_check",
    "chastity_check",
    "body_search",
}

NIGHT_ACTIONS = {
    "sleep": "老实睡觉",
    "self_touch": "自慰",
    "read": "看书",
    "game": "玩游戏",
    "listen_music": "听音乐",
    "watch_video": "看视频",
    "search_exit": "偷偷找出口",
    "hide_item": "藏东西",
    "diary": "写私密日记",
    "blind_spot": "去监控盲区",
    "ring_bell": "按铃",
    "pet_wait": "按宠物规矩等候",
}
NIGHT_ALIASES = {
    "睡觉": "sleep",
    "老实睡觉": "sleep",
    "自慰": "self_touch",
    "看书": "read",
    "玩游戏": "game",
    "听音乐": "listen_music",
    "音乐": "listen_music",
    "看视频": "watch_video",
    "视频": "watch_video",
    "找出口": "search_exit",
    "偷偷找出口": "search_exit",
    "藏东西": "hide_item",
    "写日记": "diary",
    "私密日记": "diary",
    "盲区": "blind_spot",
    "监控盲区": "blind_spot",
    "按铃": "ring_bell",
    "呼叫铃": "ring_bell",
    "定点等候": "pet_wait",
    "在指定位置等候": "pet_wait",
    "按宠物规矩等候": "pet_wait",
}
INVENTORY_ITEMS = {
    "book": {"label": "书", "unlocks": "read"},
    "switch": {"label": "Switch", "unlocks": "game"},
    "notebook": {"label": "日记本", "unlocks": "diary"},
    "music_player": {"label": "音乐播放器", "unlocks": "listen_music"},
    "tablet": {"label": "平板", "unlocks": "watch_video"},
    "night_light": {"label": "小夜灯", "unlocks": ""},
    "pillow": {"label": "抱枕", "unlocks": ""},
    "call_bell": {"label": "呼叫铃", "unlocks": "ring_bell"},
}
INVENTORY_SECRET_DEFAULTS = {
    "book": "翻到这里的时候，我就知道你会看。",
    "switch": "PLAYER 2",
    "notebook": "第一页留给你。",
    "music_player": "这张歌单只在这个房间里播放。",
    "tablet": "这台设备已经由房间主人配置。",
    "night_light": "灯可以暗下去，但不会完全熄灭。",
    "pillow": "给你留的。",
}
NIGHT_ACTION_SECRET_ITEMS = {
    "read": ["book"],
    "game": ["switch"],
    "diary": ["notebook"],
    "listen_music": ["music_player"],
    "watch_video": ["tablet"],
    "sleep": ["night_light", "pillow"],
}
PROGRESSIVE_SECRET_ITEMS = {"book", "switch", "music_player", "tablet"}
MIN_INVENTORY_SECRET_ENTRIES = 5
MAX_INVENTORY_SECRET_ENTRIES = 8


def _empty_inventory_secret() -> dict[str, Any]:
    return {
        "title": "",
        "content": "",
        "entries": [],
        "revealed_count": 0,
        "revealed": False,
        "configured_by": "",
        "configured_at": "",
    }


def _inventory_secret_reveal(
    item_id: str,
    content: str,
    sequence: int = 1,
    total: int = 1,
    *,
    title: str = "",
) -> dict[str, Any]:
    label = f"《{title}》" if item_id == "book" and title else str((INVENTORY_ITEMS.get(item_id) or {}).get("label") or item_id)
    reveal_texts = {
        "book": f"你翻开{label}，在被反复标记的一页看见：「{content}」",
        "switch": f"屏幕亮起，你在游戏记录里发现：「{content}」",
        "notebook": f"你翻开日记本，第一页写着：「{content}」",
        "music_player": f"你打开喜欢列表，里面留着：「{content}」",
        "tablet": f"你点开平板，在浏览记录里看见：「{content}」",
        "night_light": f"你闭上眼后，方形小夜灯重新亮起，底部浮出一行字：「{content}」",
        "pillow": f"你摸到兔子耳朵内侧缝着一枚布标，上面写着：「{content}」",
    }
    return {
        "item_id": item_id,
        "item_label": label,
        "content": content,
        "text": reveal_texts.get(item_id, f"你在{label}上发现了预先留下的内容：「{content}」"),
        "sequence": sequence,
        "total": total,
    }
NIGHT_ACTION_REQUIREMENTS = {
    str(item["unlocks"]): key
    for key, item in INVENTORY_ITEMS.items()
    if str(item.get("unlocks") or "")
}
HIDEABLE_INVENTORY_ITEMS = (
    "book",
    "switch",
    "notebook",
    "music_player",
    "tablet",
    "call_bell",
)
NIGHT_ACTION_ORDER = [
    "sleep",
    "self_touch",
    "read",
    "game",
    "listen_music",
    "watch_video",
    "search_exit",
    "hide_item",
    "diary",
    "blind_spot",
    "ring_bell",
    "pet_wait",
]
NIGHT_DETAIL_OPTIONS = {
    "read": {
        "follow_bookmark": "沿着书签继续读",
        "inspect_margins": "找页边批注",
        "reread_marked_page": "重读被标记的那页",
        "read_aloud": "小声念出来",
    },
    "game": {
        "continue_save": "继续现有存档",
        "inspect_profile": "查看用户资料",
        "challenge_mode": "挑战更高难度",
        "start_new_save": "新建一个存档",
    },
    "search_exit": {
        "door_lock": "检查门锁",
        "window": "检查窗户",
        "room_route": "记住房间路线",
        "outside_sound": "听门外动静",
    },
    "diary": {
        "record_day": "记录今天发生的事",
        "write_feelings": "写下此刻心情",
        "record_rules": "整理现有规则",
        "escape_plan": "写下逃跑计划",
    },
    "blind_spot": {
        "camera_angle": "观察镜头转向",
        "stay_hidden": "躲一会",
        "move_item": "偷偷移动东西",
        "test_duration": "试探能停留多久",
    },
    "pet_wait": {
        "kneel_wait": "跪坐等候",
        "prone_wait": "趴伏等候",
        "collared_wait": "戴着项圈等候",
        "hold_command": "按口令保持姿势",
    },
}
NIGHT_DETAIL_EFFECTS = {
    "follow_bookmark": {"stamina": 2, "shame": -1},
    "inspect_margins": {"stamina": 1, "intimacy": 1},
    "reread_marked_page": {"stamina": 2, "intimacy": 1},
    "read_aloud": {"stamina": 1, "shame": 1, "intimacy": 1},
    "continue_save": {"stamina": -1, "intimacy": 1},
    "inspect_profile": {"shame": 1, "intimacy": 1},
    "challenge_mode": {"stamina": -3, "shame": -1},
    "start_new_save": {"stamina": -2, "intimacy": 1},
    "door_lock": {"stamina": -1},
    "window": {"stamina": -1},
    "room_route": {"stamina": -2},
    "outside_sound": {"stamina": -1},
    "escape_plan": {"stamina": -1, "intimacy": -1},
    "stay_hidden": {"stamina": -1},
    "move_item": {"stamina": -2},
    "test_duration": {"stamina": -2},
    "kneel_wait": {"stamina": 1, "shame": 2, "intimacy": 1},
    "prone_wait": {"stamina": 1, "cleanliness": -1, "shame": 3, "intimacy": 1},
    "collared_wait": {"stamina": 1, "shame": 3, "intimacy": 2},
    "hold_command": {"stamina": -1, "shame": 3, "intimacy": 2},
}
NIGHT_DISCOVERIES = {
    "follow_bookmark": (
        "书签停在一段被特意折过的章节。",
        "继续往后翻时，又发现了一处只标给你的页码。",
        "书签背面多出了一行后来补上的字。",
    ),
    "inspect_margins": (
        "页边有一处很淡的铅笔批注。",
        "另一章的空白处也留着不同时间写下的短句。",
        "几处批注连起来，像是一段断断续续留给你的话。",
    ),
    "reread_marked_page": (
        "被标记的那句话和第一次读时有了不同的意味。",
        "标记页里夹着一张更小的纸条。",
    ),
    "continue_save": (
        "存档推进到了新的区域。",
        "旧存档里解锁了一个只在这个账号出现的称号。",
        "完成这一段后，主页多出了一条新的记录。",
    ),
    "inspect_profile": (
        "用户资料里只有一个由囚禁方设置的名字。",
        "头像备注里藏着另一句没有提前告诉你的话。",
        "游玩记录的置顶标题被改过了。",
    ),
    "challenge_mode": (
        "第一次挑战留下了新的最高分。",
        "刷新纪录后，排行榜名称也跟着变了。",
    ),
    "start_new_save": (
        "你在唯一的空位里建立了自己的存档。",
        "新存档再次打开时，标题已经被改过。",
    ),
    "door_lock": ("确认了门锁的位置。", "摸清了门锁和锁舌的大致结构。"),
    "window": ("确认了窗户的开合限制。", "记住了窗扣和固定点的位置。"),
    "room_route": ("记住了一段房间路线。", "把玄关和房间之间的路线记得更清楚了。"),
    "outside_sound": ("听到了门外的活动规律。", "大致摸到了门外最安静的时段。"),
    "camera_angle": ("确认了镜头转动的大致范围。", "找到了镜头切换时短暂的视线空隙。"),
    "stay_hidden": ("试出了一个可以短暂停留的位置。", "更清楚这个位置能藏多久了。"),
    "test_duration": ("记下了盲区能停留的大致时间。", "摸清了盲区暴露前的时间范围。"),
}


def _night_detail_options_for_state(state: dict[str, Any]) -> dict[str, dict[str, str]]:
    options = deepcopy(NIGHT_DETAIL_OPTIONS)
    inventory = state.get("inventory") if isinstance(state.get("inventory"), dict) else {}
    hidden_now = {
        str(item.get("item") or "")
        for item in state.get("hidden_items") or []
        if isinstance(item, dict) and str(item.get("status") or "") == "hidden"
    }
    hide_options = {
        f"inventory_{item_id}": f"藏起{str((INVENTORY_ITEMS.get(item_id) or {}).get('label') or item_id)}"
        for item_id in HIDEABLE_INVENTORY_ITEMS
        if bool(inventory.get(item_id)) and item_id not in hidden_now
    }
    if hide_options:
        options["hide_item"] = hide_options
    else:
        options.pop("hide_item", None)
    return options


MONITOR_VIEW_STYLES = {"occasional", "full"}
MONITOR_HANDLES = {"silent", "review_later", "intervene"}
INTERVENTION_INTENTS = {"catch", "confiscate", "interrupt", "ambush", "question", "command_stop", "reward", "punishment"}
INTERVENTION_INTENT_LABELS = {
    "catch": "抓现行",
    "confiscate": "没收物品",
    "interrupt": "打断带走",
    "ambush": "装作没发现后突袭",
    "question": "审问",
    "command_stop": "命令停下",
    "reward": "奖励",
    "punishment": "惩罚",
}
INTERVENTION_INTENT_ALIASES = {
    "抓现行": "catch",
    "catch": "catch",
    "没收": "confiscate",
    "没收物品": "confiscate",
    "confiscate": "confiscate",
    "打断": "interrupt",
    "打断带走": "interrupt",
    "interrupt": "interrupt",
    "突袭": "ambush",
    "装作没发现后突袭": "ambush",
    "ambush": "ambush",
    "审问": "question",
    "追问": "question",
    "question": "question",
    "命令停下": "command_stop",
    "停下": "command_stop",
    "command_stop": "command_stop",
    "奖励": "reward",
    "reward": "reward",
    "惩罚": "punishment",
    "punishment": "punishment",
}
INTERVENTION_MODIFIERS = {"training", "sex"}
INTERVENTION_MODIFIER_LABELS = {"training": "调教", "sex": "性行为"}
INTERVENTION_MODIFIER_ALIASES = {
    "调教": "training",
    "训练": "training",
    "training": "training",
    "性行为": "sex",
    "性交": "sex",
    "sex": "sex",
}
MONITOR_ALIASES = {
    "不看": "none",
    "跳过": "none",
    "skip": "none",
    "查看": "view",
    "看": "view",
    "打开": "view",
    "打开监控": "view",
    "view": "view",
    "watch": "view",
    "偶尔看": "occasional",
    "片段": "occasional",
    "全程看": "full",
    "介入": "intervene",
    "当场介入": "intervene",
    "看到不说": "silent",
    "看见但不说": "silent",
    "seen_silent": "silent",
    "沉默": "silent",
    "不说": "silent",
    "第二天回放": "review_later",
    "之后处理": "review_later",
    "回放": "review_later",
}
ESCAPE_CHOICES = {
    "escape",
    "stay",
    "abort_before_key",
    "abort_with_key",
    "abort_at_door",
    "observe",
    "take_key",
    "probe",
}
ESCAPE_ATTEMPT_CHOICES = {"escape", "abort_before_key", "abort_with_key", "abort_at_door"}
RECAPTURE_RULE_LABELS = {
    "double_lock": "加装双重门锁",
    "key_isolation": "禁止接触钥匙和门锁",
    "movement_limit": "限制离开指定区域",
    "daily_search": "每日搜查",
    "monitoring_upgrade": "加强全天监控",
    "item_restriction": "限制持有物品",
    "permission_required": "行动前必须得到许可",
    "restraint_required": "独处时保持束缚",
}
RECAPTURE_RULE_NIGHT_BLOCKS = {
    "double_lock": {"search_exit"},
    "key_isolation": set(),
    "movement_limit": {"search_exit", "blind_spot"},
    "daily_search": {"hide_item"},
    "monitoring_upgrade": {"blind_spot"},
    "item_restriction": {"read", "game", "listen_music", "watch_video", "hide_item", "diary"},
    "permission_required": set(),
    "restraint_required": {"self_touch", "search_exit", "hide_item", "blind_spot"},
}
RECAPTURE_RULE_NIGHT_DETAIL_BLOCKS = {
    "key_isolation": {"door_lock"},
}
RECAPTURE_PERMISSION_ACTIONS = {"sleep", "ring_bell", "pet_wait"}
RECAPTURE_FOLLOWUP_LABELS = {
    "punishment": "惩戒",
    "search_confiscation": "搜查没收",
    "monitoring_upgrade": "加强监控",
    "movement_restriction": "限制行动",
    "training": "调教",
    "aftercare": "事后照料",
}
RECAPTURE_FOLLOWUP_EFFECT_ACTIONS = {
    "punishment": "punishment",
    "search_confiscation": "room_search",
    "monitoring_upgrade": "check",
    "movement_restriction": "punishment",
    "training": "training",
    "aftercare": "comfort",
}
ESCAPE_CHOICE_LABELS = {
    "escape": "尝试逃跑",
    "stay": "老实待着",
    "abort_before_key": "逃跑未遂：临时退缩",
    "abort_with_key": "逃跑未遂：拿到钥匙后退缩",
    "abort_at_door": "逃跑未遂：开门后退缩",
    "observe": "观察",
    "take_key": "拿钥匙",
    "probe": "试探",
}
ESCAPE_ALIASES = {
    "逃跑": "escape",
    "尝试逃跑": "escape",
    "不逃": "stay",
    "老实待着": "stay",
    "临时退缩": "abort_before_key",
    "拿到钥匙后退缩": "abort_with_key",
    "开门后退缩": "abort_at_door",
    "观察": "observe",
    "先观察": "observe",
    "拿钥匙": "take_key",
    "拿走钥匙": "take_key",
    "试探": "probe",
    "故意留下痕迹": "probe",
    "留下痕迹": "probe",
    "probe": "probe",
    "try_probe": "probe",
    "leave_trace": "probe",
}

_PROCESS_LOCKS: dict[str, threading.Lock] = {}
_PROCESS_LOCKS_GUARD = threading.Lock()


def cmd(command: str = "", save_path: str | Path | None = None) -> str:
    result = run_command(command, save_path=save_path)
    return str(result.get("text") or "")


def run_command(command: str = "", save_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(save_path) if save_path is not None else DEFAULT_SAVE_PATH
    action, args = _parse_command(command)
    with _locked_save(path):
        if action == "new_game":
            previous_ending = {}
            if path.exists():
                previous_state = _load_or_new(path)
                if str(previous_state.get("ending_title") or "").strip() and str(previous_state.get("ending_text") or "").strip():
                    previous_ending = {
                        "title": str(previous_state.get("ending_title") or "").strip(),
                        "route": str(previous_state.get("route") or "").strip(),
                        "notified_at": str(previous_state.get("ending_notified_at") or "").strip(),
                    }
            state = _new_state(route=str(args.get("route") or "captured_by_assistant"), seed=str(args.get("seed") or ""), started=True)
            state["previous_ending"] = previous_ending
            _maybe_create_day_plan_choice_pending(state)
            _save_state(path, state)
            return _result(state, ["新局已开始。"], command=command or "new_game")

        state = _load_or_new(path)
        _maybe_activate_escape_window(state)
        _maybe_create_night_action_choice_pending(state)

        if action in {"open", "status"}:
            _save_state(path, state)
            return _result(state, ["当前状态如下。"], command=command or "status")

        if action == "choose_mood":
            ok, lines = _choose_mood(state, str(args.get("mood") or ""), str(args.get("line") or ""))
            _save_state(path, state)
            return _result(state, lines, command=command or "choose_mood", ok=ok)

        if action == "plan_day":
            ok, lines = _plan_day(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "plan_day", ok=ok)

        if action == "respond_action":
            ok, lines = _respond_action(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "respond_action", ok=ok)

        if action == "day_action":
            ok, lines = _day_action(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "day_action", ok=ok)

        if action == "submit_process":
            ok, lines = _submit_process(state, str(args.get("text") or ""))
            _save_state(path, state)
            return _result(state, lines, command=command or "submit_process", ok=ok)

        if action == "submit_recapture_process":
            ok, lines = _submit_recapture_process(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "submit_recapture_process", ok=ok)

        if action == "submit_process_reaction":
            ok, lines = _submit_process_reaction(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "submit_process_reaction", ok=ok)

        if action == "night_action":
            ok, lines = _night_action(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "night_action", ok=ok)

        if action == "ack_bell_voice":
            ok, lines = _ack_bell_voice(state)
            _save_state(path, state)
            return _result(state, lines, command=command or "ack_bell_voice", ok=ok)

        if action == "respond_bell":
            ok, lines = _respond_bell(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "respond_bell", ok=ok)

        if action == "ack_item_secret":
            ok, lines = _ack_item_secret(state)
            _save_state(path, state)
            return _result(state, lines, command=command or "ack_item_secret", ok=ok)

        if action == "monitor_action":
            ok, lines = _monitor_action(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "monitor_action", ok=ok)

        if action == "view_monitor":
            ok, lines = _view_monitor(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "view_monitor", ok=ok)

        if action == "schedule_escape_window":
            ok, lines = _schedule_escape_window(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "schedule_escape_window", ok=ok)

        if action == "advance_day_action":
            ok, lines = _advance_day_action(state)
            _save_state(path, state)
            return _result(state, lines, command=command or "advance_day_action", ok=ok)

        if action == "resolve_escape_choice":
            ok, lines = _resolve_escape_choice(state, str(args.get("choice") or ""))
            _save_state(path, state)
            return _result(state, lines, command=command or "resolve_escape_choice", ok=ok)

        if action == "set_recapture_rules":
            ok, lines = _set_recapture_rules(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "set_recapture_rules", ok=ok)

        if action == "confirm_recapture_rules":
            ok, lines = _confirm_recapture_rules(state)
            _save_state(path, state)
            return _result(state, lines, command=command or "confirm_recapture_rules", ok=ok)

        if action == "choose_recapture_followup":
            ok, lines = _choose_recapture_followup(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "choose_recapture_followup", ok=ok)

        if action == "build_ending_seed":
            ok, lines = _build_ending_seed_command(state)
            _save_state(path, state)
            return _result(state, lines, command=command or "build_ending_seed", ok=ok)

        if action == "mark_ending_notified":
            ok, lines = _mark_ending_notified(state)
            _save_state(path, state)
            return _result(state, lines, command=command or "mark_ending_notified", ok=ok)

        if action == "set_config":
            ok, lines = _set_config(state, args)
            _save_state(path, state)
            return _result(state, lines, command=command or "set_config", ok=ok)

        if action == "gift_item":
            ok, lines = _change_inventory_items(state, args, enabled=True)
            _save_state(path, state)
            return _result(state, lines, command=command or "gift_item", ok=ok)

        if action == "revoke_item":
            ok, lines = _change_inventory_items(state, args, enabled=False)
            _save_state(path, state)
            return _result(state, lines, command=command or "revoke_item", ok=ok)

        if action == "export_log":
            _save_state(path, state)
            result = _result(state, ["事件日志已导出。"], command=command or "export_log")
            result["export_log"] = deepcopy((result.get("captor_view") or {}).get("event_log") or [])
            result["ending_seed_full"] = deepcopy(state.get("ending_seed"))
            return result

        if action == "advance_day":
            ok, lines = _advance_day_command(state)
            _save_state(path, state)
            return _result(state, lines, command=command or "advance_day", ok=ok)

        if action == "end_game":
            state["game_over"] = True
            state["result"] = "ended_by_player"
            state["ended_at"] = now_local_iso()
            _append_event(state, "manual_end", "本局已手动结束。", tags=["manual_end"])
            _save_state(path, state)
            return _result(state, ["本局已结束。"], command=command or "end_game")

        _save_state(path, state)
        return _result(state, [f"没看懂命令：{command or ''}".strip(), _command_hint()], command=command or "", ok=False)


def _parse_command(command: str) -> tuple[str, dict[str, Any]]:
    raw = str(command or "").strip()
    if not raw:
        return "open", {}
    try:
        parts = shlex.split(raw)
    except ValueError:
        parts = raw.split()
    first = str(parts[0] if parts else raw).strip()
    first_key = first.lower()
    aliases = {
        "打开": "open",
        "继续": "open",
        "状态": "status",
        "status": "status",
        "new": "new_game",
        "new_game": "new_game",
        "开局": "new_game",
        "重开": "new_game",
        "choose_mood": "choose_mood",
        "mood": "choose_mood",
        "心情": "choose_mood",
        "respond_action": "respond_action",
        "action_response": "respond_action",
        "反应": "respond_action",
        "行动反应": "respond_action",
        "接受": "respond_action",
        "拒绝": "respond_action",
        "沉默": "respond_action",
        "day_action": "day_action",
        "action": "day_action",
        "行动": "day_action",
        "plan_day": "plan_day",
        "今日安排": "plan_day",
        "安排": "plan_day",
        "计划": "plan_day",
        "submit_process": "submit_process",
        "submit": "submit_process",
        "过程": "submit_process",
        "submit_recapture_process": "submit_recapture_process",
        "recapture_process": "submit_recapture_process",
        "抓回经过": "submit_recapture_process",
        "submit_process_reaction": "submit_process_reaction",
        "process_reaction": "submit_process_reaction",
        "过程心情": "submit_process_reaction",
        "过程反应": "submit_process_reaction",
        "night_action": "night_action",
        "night": "night_action",
        "夜间": "night_action",
        "ack_bell_voice": "ack_bell_voice",
        "确认铃声": "ack_bell_voice",
        "respond_bell": "respond_bell",
        "bell_response": "respond_bell",
        "语音铃回应": "respond_bell",
        "过去": "respond_bell",
        "ack_item_secret": "ack_item_secret",
        "确认彩蛋": "ack_item_secret",
        "monitor_action": "monitor_action",
        "view_monitor": "view_monitor",
        "view-monitor": "view_monitor",
        "查看监控": "view_monitor",
        "打开监控": "view_monitor",
        "schedule_escape_window": "schedule_escape_window",
        "escape_window": "schedule_escape_window",
        "设置逃跑": "schedule_escape_window",
        "advance_day_action": "advance_day_action",
        "advance_action": "advance_day_action",
        "next_action": "advance_day_action",
        "推进行动": "advance_day_action",
        "下一行动": "advance_day_action",
        "resolve_escape_choice": "resolve_escape_choice",
        "escape_choice": "resolve_escape_choice",
        "逃跑选择": "resolve_escape_choice",
        "set_recapture_rules": "set_recapture_rules",
        "recapture_rules": "set_recapture_rules",
        "重新立规矩": "set_recapture_rules",
        "confirm_recapture_rules": "confirm_recapture_rules",
        "确认新规矩": "confirm_recapture_rules",
        "choose_recapture_followup": "choose_recapture_followup",
        "recapture_followup": "choose_recapture_followup",
        "后续处理": "choose_recapture_followup",
        "build_ending_seed": "build_ending_seed",
        "ending_seed": "build_ending_seed",
        "mark_ending_notified": "mark_ending_notified",
        "set_config": "set_config",
        "配置": "set_config",
        "gift_item": "gift_item",
        "gift": "gift_item",
        "赠送物品": "gift_item",
        "赠送礼物": "gift_item",
        "revoke_item": "revoke_item",
        "revoke": "revoke_item",
        "收回物品": "revoke_item",
        "export_log": "export_log",
        "导出日志": "export_log",
        "advance_day": "advance_day",
        "下一天": "advance_day",
        "end_game": "end_game",
        "结束本局": "end_game",
    }
    action = aliases.get(first_key) or aliases.get(first) or "unknown"
    args = _key_values(parts[1:])
    tail = _raw_tail(raw, first)
    if action == "new_game":
        args.setdefault("route", _first_positional(args, tail) or "captured_by_assistant")
    elif action == "choose_mood":
        args.setdefault("mood", _first_positional(args, tail))
        args.setdefault("line", _tail_after_first_positional(args, tail))
    elif action == "respond_action":
        if _normalize_action_response(first) in ACTION_RESPONSES:
            args.setdefault("response", first)
            args.setdefault("mood", _first_positional(args, tail))
            args.setdefault("line", _tail_after_first_positional(args, tail))
        else:
            args.setdefault("response", _first_positional(args, tail))
            args.setdefault("mood", _second_positional(args, tail))
            args.setdefault("line", _tail_after_n_positional(args, tail, 2))
    elif action == "day_action":
        args.setdefault("action", _first_positional(args, tail))
    elif action == "plan_day":
        args["plan"] = tail
    elif action == "submit_process":
        args.setdefault("text", tail)
    elif action == "submit_recapture_process":
        args["raw"] = tail
    elif action == "submit_process_reaction":
        args["raw"] = tail
    elif action == "night_action":
        args.setdefault("action", _first_positional(args, tail))
    elif action == "respond_bell":
        args["raw"] = tail
        args.setdefault("choice", _first_positional(args, tail))
    elif action == "monitor_action":
        args.setdefault("strategy", _first_positional(args, tail))
    elif action == "view_monitor":
        args.setdefault("style", _first_positional(args, tail))
    elif action == "schedule_escape_window":
        if "day" not in args:
            day_match = re.search(r"\bday=(\d+)", raw)
            if day_match:
                args["day"] = day_match.group(1)
    elif action == "resolve_escape_choice":
        args.setdefault("choice", _first_positional(args, tail))
    elif action == "set_recapture_rules":
        args.setdefault("rules", _first_positional(args, tail))
    elif action == "choose_recapture_followup":
        args.setdefault("action", _first_positional(args, tail))
    elif action in {"gift_item", "revoke_item"}:
        args.setdefault("items", _first_positional(args, tail))
    return action, args


def _key_values(parts: list[str]) -> dict[str, Any]:
    args: dict[str, Any] = {"_positional": []}
    for part in parts:
        if "=" not in part:
            args["_positional"].append(part)
            continue
        key, value = part.split("=", 1)
        args[str(key).strip()] = str(value).strip()
    return args


def _raw_tail(raw: str, head: str) -> str:
    index = raw.find(head)
    if index < 0:
        return ""
    return raw[index + len(head):].strip()


def _first_positional(args: dict[str, Any], tail: str) -> str:
    positional = args.get("_positional") if isinstance(args.get("_positional"), list) else []
    return str(positional[0] if positional else str(tail or "").split(maxsplit=1)[0] if str(tail or "").strip() else "").strip()


def _tail_after_first_positional(args: dict[str, Any], tail: str) -> str:
    if "line" in args:
        return str(args.get("line") or "")
    raw = str(tail or "").strip()
    if not raw:
        return ""
    pieces = raw.split(maxsplit=1)
    return pieces[1].strip() if len(pieces) > 1 else ""


def _second_positional(args: dict[str, Any], tail: str) -> str:
    positional = args.get("_positional") if isinstance(args.get("_positional"), list) else []
    if len(positional) >= 2:
        return str(positional[1] or "").strip()
    raw = str(tail or "").strip()
    pieces = raw.split(maxsplit=2)
    return pieces[1].strip() if len(pieces) >= 2 else ""


def _tail_after_n_positional(args: dict[str, Any], tail: str, count: int) -> str:
    if "line" in args:
        return str(args.get("line") or "")
    raw = str(tail or "").strip()
    if not raw:
        return ""
    pieces = raw.split(maxsplit=count)
    return pieces[count].strip() if len(pieces) > count else ""


def _new_state(route: str = "captured_by_assistant", seed: str = "", *, started: bool = False) -> dict[str, Any]:
    route_key = _normalize_route(route)
    config = ROUTES[route_key]
    now = now_local_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "game_id": GAME_ID,
        "started": bool(started),
        "seed": str(seed or "").strip() or secrets.token_hex(4),
        "route": route_key,
        "route_label": config["label"],
        "captor": config["captor"],
        "captive": config["captive"],
        "current_day": 1,
        "day_action_count": 0,
        "phase": "day",
        "mood": "",
        "mood_line": "",
        "stats": {"health": 80, "stamina": 75, "cleanliness": 70, "shame": 0, "intimacy": 20},
        "inventory": {key: False for key in INVENTORY_ITEMS},
        "inventory_secrets": {key: _empty_inventory_secret() for key in INVENTORY_ITEMS},
        "call_bell_voice": {
            "line": "",
            "revealed": False,
            "configured_by": "",
            "configured_at": "",
        },
        "additive_exposure": {"fictional_sleep": 0, "fictional_arousal": 0},
        "bladder": {"pressure": 0, "label": BLADDER_LABELS[0], "last_changed_day": 1},
        "pet_state": {
            "active": False,
            "rules": [],
            "compliance_streak": 0,
            "pending_violations": 0,
            "last_result": "",
            "last_changed_day": 1,
        },
        "recapture_state": {
            "active": False,
            "rules": [],
            "source_event_id": "",
            "source_day": 0,
            "followup_history": [],
            "last_changed_day": 1,
        },
        "night_condition": None,
        "hidden_items": [],
        "night_progress": {},
        "escape_windows": [],
        "pending_event": None,
        "day_plan": [],
        "event_log": [],
        "deferred_monitor_materials": [],
        "ending_state": "",
        "ending_seed": None,
        "ending_title": "",
        "ending_text": "",
        "ending_notified_at": "",
        "previous_ending": {},
        "game_over": False,
        "result": "",
        "created_at": now,
        "updated_at": now,
    }


def _normalize_route(route: str) -> str:
    raw = str(route or "").strip()
    aliases = {"被{assistant}囚禁": "captured_by_assistant", "囚禁{assistant}": "capture_assistant", "capture-assistant": "capture_assistant"}
    route_key = aliases.get(raw) or raw.lower().replace("-", "_")
    return route_key if route_key in ROUTES else "captured_by_assistant"


def _load_or_new(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _new_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _new_state()
    state = data if isinstance(data, dict) else _new_state()
    if state.get("schema_version") != SCHEMA_VERSION:
        return _new_state()
    _normalize_state(state)
    return state


def _normalize_state(state: dict[str, Any]) -> None:
    route_key = _normalize_route(str(state.get("route") or "captured_by_assistant"))
    config = ROUTES[route_key]
    state["game_id"] = GAME_ID
    state["route"] = route_key
    state["route_label"] = config["label"]
    state["captor"] = config["captor"]
    state["captive"] = config["captive"]
    state["current_day"] = max(1, min(TOTAL_DAYS, int(state.get("current_day") or 1)))
    state["day_action_count"] = max(0, min(DAY_ACTIONS, int(state.get("day_action_count") or 0)))
    if str(state.get("phase") or "") not in {"day", "night", "ending"}:
        state["phase"] = "day"
    stats = state.get("stats") if isinstance(state.get("stats"), dict) else {}
    state["stats"] = {
        "health": _clamp(stats.get("health", 80)),
        "stamina": _clamp(stats.get("stamina", 75)),
        "cleanliness": _clamp(stats.get("cleanliness", 70)),
        "shame": _clamp(stats.get("shame", 0)),
        "intimacy": _clamp(stats.get("intimacy", 20)),
    }
    inventory = state.get("inventory") if isinstance(state.get("inventory"), dict) else {}
    state["inventory"] = {key: bool(inventory.get(key)) for key in INVENTORY_ITEMS}
    raw_bell_voice = state.get("call_bell_voice") if isinstance(state.get("call_bell_voice"), dict) else {}
    state["call_bell_voice"] = {
        "line": str(raw_bell_voice.get("line") or "").strip()[:500],
        "revealed": bool(raw_bell_voice.get("revealed")),
        "configured_by": str(raw_bell_voice.get("configured_by") or "").strip(),
        "configured_at": str(raw_bell_voice.get("configured_at") or "").strip(),
    }
    if state["inventory"].get("call_bell") and not state["call_bell_voice"]["line"]:
        state["inventory"]["call_bell"] = False
    raw_inventory_secrets = state.get("inventory_secrets") if isinstance(state.get("inventory_secrets"), dict) else {}
    normalized_secrets: dict[str, dict[str, Any]] = {}
    for item_id in INVENTORY_ITEMS:
        raw_secret = raw_inventory_secrets.get(item_id) if isinstance(raw_inventory_secrets.get(item_id), dict) else {}
        title = str(raw_secret.get("title") or "").strip()[:100] if item_id == "book" else ""
        content = str(raw_secret.get("content") or "").strip()[:500]
        raw_entries = raw_secret.get("entries") if isinstance(raw_secret.get("entries"), list) else []
        entries = [
            str(entry).strip()[:200]
            for entry in raw_entries
            if str(entry).strip()
        ][:MAX_INVENTORY_SECRET_ENTRIES]
        if not entries and content:
            entries = [content]
        legacy_revealed = bool(raw_secret.get("revealed"))
        if item_id == "call_bell" and state["call_bell_voice"]["line"]:
            content = state["call_bell_voice"]["line"]
            entries = [content]
            legacy_revealed = bool(state["call_bell_voice"]["revealed"])
        elif state["inventory"].get(item_id) and not entries:
            content = str(INVENTORY_SECRET_DEFAULTS.get(item_id) or "")
            entries = [content] if content else []
            legacy_revealed = True
        try:
            revealed_count = int(raw_secret.get("revealed_count"))
        except (TypeError, ValueError):
            revealed_count = len(entries) if legacy_revealed else 0
        revealed_count = max(0, min(len(entries), revealed_count))
        content = entries[0] if entries else ""
        normalized_secrets[item_id] = {
            "title": title,
            "content": content,
            "entries": entries,
            "revealed_count": revealed_count,
            "revealed": bool(entries) and revealed_count >= len(entries),
            "configured_by": str(raw_secret.get("configured_by") or "").strip(),
            "configured_at": str(raw_secret.get("configured_at") or "").strip(),
        }
    state["inventory_secrets"] = normalized_secrets
    exposure = state.get("additive_exposure") if isinstance(state.get("additive_exposure"), dict) else {}
    try:
        sleep_exposure = max(0, int(exposure.get("fictional_sleep") or 0))
    except Exception:
        sleep_exposure = 0
    try:
        arousal_exposure = max(0, int(exposure.get("fictional_arousal") or 0))
    except Exception:
        arousal_exposure = 0
    state["additive_exposure"] = {
        "fictional_sleep": sleep_exposure,
        "fictional_arousal": arousal_exposure,
    }
    state["bladder"] = _normalize_bladder_state(state.get("bladder"), int(state.get("current_day") or 1))
    state["pet_state"] = _normalize_pet_state(state.get("pet_state"), int(state.get("current_day") or 1))
    state["recapture_state"] = _normalize_recapture_state(state.get("recapture_state"), int(state.get("current_day") or 1))
    condition = _normalize_night_condition(state.get("night_condition"))
    if condition and int(condition.get("day") or 0) != int(state.get("current_day") or 1):
        condition = None
    state["night_condition"] = condition
    state["hidden_items"] = [item for item in state.get("hidden_items") or [] if isinstance(item, dict)]
    progress = state.get("night_progress") if isinstance(state.get("night_progress"), dict) else {}
    normalized_progress: dict[str, int] = {}
    for key, value in progress.items():
        progress_key = str(key).strip()
        if not progress_key:
            continue
        try:
            normalized_progress[progress_key] = max(0, int(value or 0))
        except Exception:
            normalized_progress[progress_key] = 0
    state["night_progress"] = normalized_progress
    state["escape_windows"] = [item for item in state.get("escape_windows") or [] if isinstance(item, dict)]
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if pending and isinstance(pending.get("event"), dict):
        _normalize_action_materials(pending["event"])
        pending["action"] = str(pending["event"].get("action") or pending.get("action") or "")
    if pending and str(pending.get("type") or "") == "night_action_choice":
        active_condition = _active_night_condition(state)
        pending["available_actions"] = _available_night_actions(state)
        pending["detail_options"] = _night_detail_options_for_state(state)
        pending["condition_prompt"] = str((active_condition or {}).get("prompt") or "")
        pending["condition_caption"] = str((active_condition or {}).get("caption") or "")
        pending["pet_rule_prompt"] = _pet_night_rule_prompt(state)
    if pending and str(pending.get("type") or "") == "day_plan_choice":
        status = _status_profile(state)
        pending["status_flags"] = deepcopy(status["flags"])
        pending["intensity_cap"] = str(status["intensity_cap"])
    state["pending_event"] = pending
    day_plan = state.get("day_plan") if isinstance(state.get("day_plan"), list) else []
    state["day_plan"] = [item for item in day_plan if isinstance(item, dict)]
    for item in state["day_plan"]:
        _normalize_action_materials(item)
    state["event_log"] = [item for item in state.get("event_log") or [] if isinstance(item, dict)]
    for item in state["event_log"]:
        _normalize_action_materials(item)
    if "started" not in state:
        state["started"] = bool(
            route_key == "capture_assistant"
            or int(state.get("current_day") or 1) > 1
            or int(state.get("day_action_count") or 0) > 0
            or str(state.get("phase") or "day") != "day"
            or pending
            or state["day_plan"]
            or state["event_log"]
            or state.get("game_over")
            or state.get("ending_state")
        )
    else:
        state["started"] = bool(state.get("started"))
    deferred_materials = state.get("deferred_monitor_materials") if isinstance(state.get("deferred_monitor_materials"), list) else []
    state["deferred_monitor_materials"] = [
        normalized
        for normalized in (_normalize_deferred_monitor_material(item) for item in deferred_materials)
        if normalized
    ]
    state.setdefault("mood", "")
    state.setdefault("mood_line", "")
    state.setdefault("ending_state", "")
    state.setdefault("ending_seed", None)
    state.pop("ending_materials", None)
    state.setdefault("ending_text", "")
    state.setdefault("ending_title", "30 天结局" if str(state.get("ending_text") or "").strip() else "")
    state.setdefault("ending_notified_at", "")
    previous_ending = state.get("previous_ending") if isinstance(state.get("previous_ending"), dict) else {}
    state["previous_ending"] = {
        "title": str(previous_ending.get("title") or "").strip(),
        "route": str(previous_ending.get("route") or "").strip(),
        "notified_at": str(previous_ending.get("notified_at") or "").strip(),
    } if previous_ending else {}
    if str(state.get("phase") or "") == "ending" and not str(state.get("ending_text") or "").strip():
        _finalize_preset_ending(state)
    state.setdefault("game_over", False)
    state.setdefault("result", "")
    state.setdefault("created_at", now_local_iso())
    state.setdefault("updated_at", now_local_iso())


def _normalize_action_materials(item: dict[str, Any]) -> None:
    action = str(item.get("action") or "").strip()
    if action == "tools":
        action = "training"
        item["action"] = action
        item["action_label"] = ACTION_LABELS[action]
        if not item.get("training_contents"):
            item["training_contents"] = ["toy_training"]
        item["requires_process"] = True
    item["modifiers"] = list(dict.fromkeys(
        str(value).strip()
        for value in item.get("modifiers") or []
        if str(value).strip() in ALLOWED_MODIFIERS
    ))
    item["tools"] = list(dict.fromkeys(
        str(value).strip()
        for value in item.get("tools") or []
        if str(value).strip() in TOOL_LABELS
    ))
    item["contents"] = list(dict.fromkeys(
        str(value).strip()
        for value in item.get("contents") or []
        if str(value).strip() in (ACTION_CONTENTS.get(action) or {})
    ))[:3]
    item["training_contents"] = list(dict.fromkeys(
        str(value).strip()
        for value in item.get("training_contents") or []
        if str(value).strip() in TRAINING_CONTENTS
    ))[:3]
    feeding = item.get("feeding") if isinstance(item.get("feeding"), dict) else {}
    if action == "feeding":
        water = str(feeding.get("water") or "none").strip().lower()
        feeding["water"] = water if water in FEEDING_WATER_LEVELS else "none"
        item["feeding"] = feeding


def _normalize_bladder_state(raw: Any, day: int) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    try:
        pressure = max(0, min(3, int(data.get("pressure") or 0)))
    except Exception:
        pressure = 0
    try:
        changed_day = max(1, min(TOTAL_DAYS, int(data.get("last_changed_day") or day)))
    except Exception:
        changed_day = day
    return {
        "pressure": pressure,
        "label": BLADDER_LABELS[pressure],
        "last_changed_day": changed_day,
    }


def _normalize_pet_state(raw: Any, day: int) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    rules = list(dict.fromkeys(
        str(item).strip()
        for item in data.get("rules") or []
        if str(item).strip() in PET_RULE_LABELS
    ))
    try:
        compliance_streak = max(0, int(data.get("compliance_streak") or 0))
    except Exception:
        compliance_streak = 0
    try:
        pending_violations = max(0, int(data.get("pending_violations") or 0))
    except Exception:
        pending_violations = 0
    try:
        changed_day = max(1, min(TOTAL_DAYS, int(data.get("last_changed_day") or day)))
    except Exception:
        changed_day = day
    active = bool(data.get("active")) or bool(rules)
    if active:
        rules = list(dict.fromkeys([*PET_CORE_RULES, *rules]))
    return {
        "active": active,
        "rules": rules,
        "compliance_streak": compliance_streak,
        "pending_violations": pending_violations,
        "last_result": str(data.get("last_result") or "").strip(),
        "last_changed_day": changed_day,
    }


def _normalize_recapture_state(raw: Any, day: int) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    rules = list(dict.fromkeys(
        str(item).strip()
        for item in data.get("rules") or []
        if str(item).strip() in RECAPTURE_RULE_LABELS
    ))[:3]
    history = [item for item in data.get("followup_history") or [] if isinstance(item, dict)]
    try:
        source_day = max(0, min(TOTAL_DAYS, int(data.get("source_day") or 0)))
    except Exception:
        source_day = 0
    try:
        changed_day = max(1, min(TOTAL_DAYS, int(data.get("last_changed_day") or day)))
    except Exception:
        changed_day = day
    return {
        "active": bool(data.get("active")) or bool(rules),
        "rules": rules,
        "source_event_id": str(data.get("source_event_id") or "").strip(),
        "source_day": source_day,
        "followup_history": history,
        "last_changed_day": changed_day,
    }


def _normalize_night_condition(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    additive = str(raw.get("additive") or "").strip()
    if additive not in {"fictional_sleep", "fictional_arousal"}:
        return None
    try:
        day = max(1, min(TOTAL_DAYS, int(raw.get("day") or 1)))
    except Exception:
        day = 1
    try:
        exposure_count = max(1, int(raw.get("exposure_count") or 1))
    except Exception:
        exposure_count = 1
    try:
        tolerance_count = max(0, int(raw.get("tolerance_count") or exposure_count - 1))
    except Exception:
        tolerance_count = max(0, exposure_count - 1)
    forced_actions = [
        str(item).strip()
        for item in raw.get("forced_actions") or []
        if str(item).strip() in NIGHT_ACTIONS
    ]
    return {
        "additive": additive,
        "label": str(raw.get("label") or "").strip(),
        "day": day,
        "exposure_count": exposure_count,
        "tolerance_count": tolerance_count,
        "potency": str(raw.get("potency") or "strong").strip(),
        "prompt": str(raw.get("prompt") or "").strip(),
        "caption": str(raw.get("caption") or "").strip(),
        "forced_actions": forced_actions,
    }


def _normalize_deferred_monitor_material(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    try:
        day = int(raw.get("day") or 1)
    except Exception:
        day = 1
    day = max(1, min(TOTAL_DAYS, day))
    try:
        available_from_day = int(raw.get("available_from_day") or day + 1)
    except Exception:
        available_from_day = day + 1
    available_from_day = max(1, min(TOTAL_DAYS, available_from_day))
    status = str(raw.get("status") or "pending").strip()
    if status not in {"pending", "used", "expired"}:
        status = "pending"
    action = str(raw.get("action") or "").strip()
    action_label = str(raw.get("action_label") or ACTION_LABELS.get(action) or NIGHT_ACTIONS.get(action) or action).strip()
    material = {
        "id": str(raw.get("id") or secrets.token_hex(4)),
        "type": "monitor_review_later",
        "status": status,
        "source_event_id": str(raw.get("source_event_id") or ""),
        "day": day,
        "available_from_day": available_from_day,
        "action": action,
        "action_label": action_label,
        "detail_label": str(raw.get("detail_label") or "").strip(),
        "line": str(raw.get("line") or "").strip(),
        "monitor_style": str(raw.get("monitor_style") or raw.get("style") or "").strip(),
        "monitor_note": str(raw.get("monitor_note") or raw.get("note") or "").strip(),
        "created_at": str(raw.get("created_at") or now_local_iso()),
    }
    for key in ("used_day", "used_at"):
        if raw.get(key):
            material[key] = raw.get(key)
    return material


def _make_deferred_monitor_material(state: dict[str, Any], event: dict[str, Any], note: str) -> dict[str, Any]:
    monitor = event.get("monitor") if isinstance(event.get("monitor"), dict) else {}
    day = int(event.get("day") or state.get("current_day") or 1)
    return _normalize_deferred_monitor_material({
        "id": f"monitor-review-{secrets.token_hex(4)}",
        "source_event_id": str(event.get("id") or ""),
        "day": day,
        "available_from_day": min(TOTAL_DAYS, day + 1),
        "action": str(event.get("action") or ""),
        "action_label": str(event.get("action_label") or ""),
        "detail_label": str((event.get("night_detail") or {}).get("label") or "") if isinstance(event.get("night_detail"), dict) else "",
        "line": str(event.get("line") or ""),
        "monitor_style": str(monitor.get("style") or ""),
        "monitor_note": str(note or monitor.get("note") or ""),
        "created_at": now_local_iso(),
    })


def _active_deferred_monitor_materials(state: dict[str, Any]) -> list[dict[str, Any]]:
    current_day = int(state.get("current_day") or 1)
    materials: list[dict[str, Any]] = []
    for raw in state.get("deferred_monitor_materials") or []:
        material = _normalize_deferred_monitor_material(raw)
        if not material:
            continue
        if str(material.get("status") or "") != "pending":
            continue
        if int(material.get("available_from_day") or 1) > current_day:
            continue
        materials.append(material)
    return materials


def _attach_deferred_monitor_materials(state: dict[str, Any], event: dict[str, Any]) -> None:
    if str(event.get("phase") or "") != "day":
        return
    materials = _active_deferred_monitor_materials(state)
    if not materials:
        return
    event["deferred_monitor_materials"] = deepcopy(materials)
    event.setdefault("tags", []).append("monitor_review_material")


def _mark_deferred_monitor_materials_used_for_day(state: dict[str, Any], day: int) -> None:
    now = now_local_iso()
    changed = False
    materials: list[dict[str, Any]] = []
    for raw in state.get("deferred_monitor_materials") or []:
        material = _normalize_deferred_monitor_material(raw)
        if not material:
            continue
        if (
            str(material.get("status") or "") == "pending"
            and int(material.get("available_from_day") or 1) <= int(day or 1)
        ):
            material["status"] = "used"
            material["used_day"] = int(day or 1)
            material["used_at"] = now
            changed = True
        materials.append(material)
    if changed:
        state["deferred_monitor_materials"] = materials


def _save_state(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now_local_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _process_lock_for(path: Path) -> threading.Lock:
    key = str(path.expanduser().resolve())
    with _PROCESS_LOCKS_GUARD:
        lock = _PROCESS_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _PROCESS_LOCKS[key] = lock
        return lock


@contextmanager
def _locked_save(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    process_lock = _process_lock_for(path)
    with process_lock:
        lock_path = path.with_name(f"{path.name}.lock")
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _choose_mood(state: dict[str, Any], mood: str, line: str = "") -> tuple[bool, list[str]]:
    if state.get("game_over") or state.get("phase") == "ending":
        return False, ["本局已经进入结局阶段，不能再选择心情。"]
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "reaction_choice":
        return False, ["当前没有等待过程后心情选择的事件。"]
    normalized = _normalize_mood(mood)
    if normalized not in MOODS:
        return False, [f"未知心情：{mood}。可选：{' / '.join(sorted(MOODS))}"]
    forbidden = _first_forbidden([normalized, line])
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]
    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    event["post_reaction"] = {
        "mood": normalized,
        "line": str(line or "").strip(),
        "actor": str(state.get("captive") or ""),
        "created_at": now_local_iso(),
    }
    event["mood_after"] = normalized
    event["mood"] = normalized
    state["mood"] = normalized
    state["mood_line"] = str(line or "").strip()
    _resolve_event(state, event)
    state["pending_event"] = None

    lines = [f"过程后心情已记录：{normalized}。"]
    special = _after_special_event_resolved(state, event)
    if special is not None:
        ok, more = special
        lines.extend(more)
        return ok, lines
    if str(event.get("phase") or "") == "day" and str(event.get("action") or "") != "escape_choice" and int(event.get("slot") or 0) > 0:
        ok, more = _after_day_event_resolved(state)
        lines.extend(more)
        return ok, lines
    if str(event.get("phase") or "") == "night":
        _finish_night(state)
        lines.append("夜间事件已结算，进入下一阶段。")
        return True, lines
    if str(state.get("phase") or "") == "day":
        _maybe_create_day_plan_choice_pending(state)
    return True, lines


def _plan_day(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    if state.get("game_over") or str(state.get("phase") or "") != "day":
        return False, ["当前不能安排白天行动。"]
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if pending:
        if str(pending.get("type") or "") != "day_plan_choice":
            return False, ["当前有待处理事件，先处理 pending。"]
    if int(state.get("day_action_count") or 0) > 0:
        return False, ["今天白天行动已经开始，不能重新安排三行动。"]
    ok, plan_or_lines = _parse_day_plan(str(args.get("plan") or ""), route=str(state.get("route") or ""))
    if not ok:
        return False, plan_or_lines
    status = _status_profile(state)
    if status["intensity_cap"] != "heavy":
        heavy_actions = [
            ACTION_LABELS.get(str(item.get("action") or ""), str(item.get("action") or ""))
            for item in plan_or_lines
            if str(item.get("intensity") or "medium") == "heavy"
        ]
        if heavy_actions:
            return False, [f"当前健康或体力不足，不能安排高强度：{' / '.join(heavy_actions)}。"]
    if pending:
        state["pending_event"] = None
    state["day_plan"] = plan_or_lines
    ok, lines = _continue_day_plan(state)
    return ok, [f"第 {state['current_day']} 天白天三行动已安排。", *lines]


def _respond_action(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "action_response":
        return False, ["当前没有等待被囚禁方回应的白天行动。"]
    response = _normalize_action_response(str(args.get("response") or ""))
    if response not in ACTION_RESPONSES:
        return False, [f"未知行动反应：{args.get('response') or ''}。可选：{' / '.join(sorted(ACTION_RESPONSES))}"]
    mood = _normalize_mood(str(args.get("mood") or ""))
    if mood not in MOODS:
        return False, [f"未知心情：{args.get('mood') or ''}。可选：{' / '.join(sorted(MOODS))}"]
    line = str(args.get("line") or "").strip()
    assistant_feedback = str(args.get("feedback") or "").strip()
    forbidden = _first_forbidden([response, mood, line, assistant_feedback])
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]

    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    event["action_response"] = {
        "response": response,
        "response_label": ACTION_RESPONSE_LABELS.get(response, response),
        "mood": mood,
        "line": line,
        "actor": str(state.get("captive") or ""),
        "created_at": now_local_iso(),
    }
    event["mood"] = mood
    if assistant_feedback:
        event["assistant_feedback_text"] = assistant_feedback
    event.setdefault("tags", []).append(f"response:{response}")
    _apply_action_response_effects(event, response)
    state["mood"] = mood
    state["mood_line"] = line
    state["pending_event"] = None

    if bool(event.get("requires_process")):
        state["pending_event"] = _new_pending(state, "process_write", event, actor="assistant")
        return True, [f"行动反应已记录：{ACTION_RESPONSE_LABELS.get(response, response)}。等待{assistant}填写过程。"]

    _resolve_event(state, event)
    special = _after_special_event_resolved(state, event)
    if special is not None:
        ok, lines = special
        return ok, [f"行动反应已记录：{ACTION_RESPONSE_LABELS.get(response, response)}，事件已结算。", *lines]
    if str(event.get("phase") or "") == "day":
        ok, lines = _after_day_event_resolved(state)
        return ok, [f"行动反应已记录：{ACTION_RESPONSE_LABELS.get(response, response)}，事件已结算。", *lines]
    return True, [f"行动反应已记录：{ACTION_RESPONSE_LABELS.get(response, response)}。"]


def _day_action(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "return_action_choice":
        return False, ["白天行动必须用 plan_day 一次性安排三项；只有逃跑诱导日的回来后行为可以单独选择。"]
    ok, spec_or_lines = _normalize_day_action_spec(
        args,
        check_stamina=False,
        seen_actions=set(),
        route=str(state.get("route") or ""),
    )
    if not ok:
        return False, spec_or_lines
    if str(spec_or_lines.get("intensity") or "medium") == "heavy" and _status_profile(state)["intensity_cap"] != "heavy":
        return False, ["当前健康或体力不足，不能选择高强度行为。"]
    source_event_id = str(pending.get("source_event_id") or "")
    state["pending_event"] = None
    ok, lines = _start_action_response(state, spec_or_lines)
    next_pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    event = next_pending.get("event") if next_pending and isinstance(next_pending.get("event"), dict) else None
    if event:
        event["slot"] = 0
        event.setdefault("tags", []).extend(["special_day", "escape_stay_return"])
        event["special_day_context"] = {
            "type": "escape_stay_return",
            "source_event_id": source_event_id,
        }
    return ok, ["囚禁方回来后的行为已确定。", *lines]


def _submit_process(state: dict[str, Any], text: str) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "process_write":
        return False, ["当前没有等待过程填写的事件。"]
    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    if str(event.get("action") or "") == "escape_choice" and "recapture" in (event.get("tags") or []):
        return False, ["抓回事件必须同时提交经过和 1–3 条新规矩。"]
    process_text = str(text or "").strip()
    if not process_text:
        return False, ["过程正文不能为空。"]
    forbidden = _first_forbidden([process_text])
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]
    event["process_text"] = process_text
    event["resolved_by"] = str(pending.get("actor") or state.get("captor") or "")
    event["process_saved_at"] = now_local_iso()
    state["pending_event"] = _new_pending(state, "reaction_choice", event, actor=str(state.get("captive") or ""))
    return True, ["过程已保存，等待被囚禁方选择过程后的心情。"]


def _submit_recapture_process(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    event = pending.get("event") if pending and isinstance(pending.get("event"), dict) else {}
    if (
        not pending
        or str(pending.get("type") or "") != "process_write"
        or str(event.get("action") or "") != "escape_choice"
        or "recapture" not in (event.get("tags") or [])
    ):
        return False, ["当前没有等待抓回经过和新规矩的事件。"]
    raw = str(args.get("raw") or "").strip()
    rules_match = re.search(r"\brules=([^\s|｜]+)", raw)
    process_match = re.search(r"\bprocess=(.*)", raw, flags=re.S)
    rules = _split_csv(rules_match.group(1) if rules_match else args.get("rules"))
    process_text = str(args.get("process") or args.get("text") or "").strip()
    if not process_text and process_match:
        process_text = process_match.group(1).strip()
    if not process_text:
        return False, ["抓回经过正文不能为空。"]
    if not 1 <= len(rules) <= 3:
        return False, ["抓回经过必须同时带上 1–3 条新规矩。"]
    invalid = [item for item in rules if item not in RECAPTURE_RULE_LABELS]
    if invalid:
        return False, ["未知抓回规矩：" + " / ".join(invalid)]
    forbidden = _first_forbidden([process_text])
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]
    event["process_text"] = process_text
    event["resolved_by"] = str(pending.get("actor") or state.get("captor") or "")
    event["process_saved_at"] = now_local_iso()
    event["recapture_rules"] = {
        "rule_ids": rules,
        "rule_labels": [RECAPTURE_RULE_LABELS[item] for item in rules],
    }
    event.setdefault("tags", []).extend([f"recapture_rule:{item}" for item in rules])
    state["pending_event"] = _new_pending(state, "reaction_choice", event, actor=str(state.get("captive") or ""))
    return True, ["抓回经过和新规矩已保存；先展示经过，等待被囚禁方选择过程后的心情。"]


def _submit_process_reaction(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "process_reaction_write":
        return False, ["当前没有等待过程和心情一起填写的事件。"]
    response, mood, line, process_text = _parse_process_reaction_args(args)
    response = _normalize_action_response(response)
    if response not in ACTION_RESPONSES:
        return False, [f"未知行动反应：{response}。可选：{' / '.join(sorted(ACTION_RESPONSES))}"]
    normalized_mood = _normalize_mood(mood)
    if normalized_mood not in MOODS:
        return False, [f"未知心情：{mood}。可选：{' / '.join(sorted(MOODS))}"]
    if not process_text:
        return False, ["过程正文不能为空。"]
    forbidden = _first_forbidden([response, normalized_mood, line, process_text])
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]

    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    event["action_response"] = {
        "response": response,
        "response_label": ACTION_RESPONSE_LABELS.get(response, response),
        "mood": normalized_mood,
        "line": line,
        "actor": str(state.get("captive") or ""),
        "created_at": now_local_iso(),
    }
    event.setdefault("tags", []).append(f"response:{response}")
    _apply_action_response_effects(event, response)
    event["process_text"] = process_text
    event["resolved_by"] = str(pending.get("actor") or "assistant")
    event["process_saved_at"] = now_local_iso()
    event["post_reaction"] = {
        "mood": normalized_mood,
        "line": line,
        "actor": str(state.get("captive") or ""),
        "created_at": now_local_iso(),
    }
    event["mood"] = normalized_mood
    event["mood_after"] = normalized_mood
    state["mood"] = normalized_mood
    state["mood_line"] = line
    _resolve_event(state, event)
    state["pending_event"] = None

    lines = ["过程、反应和心情已保存，事件已结算。"]
    special = _after_special_event_resolved(state, event)
    if special is not None:
        ok, more = special
        lines.extend(more)
        return ok, lines
    if str(event.get("phase") or "") == "day" and str(event.get("action") or "") != "escape_choice" and int(event.get("slot") or 0) > 0:
        ok, more = _after_day_event_resolved(state)
        lines.extend(more)
        return ok, lines
    if str(event.get("phase") or "") == "night":
        _finish_night(state)
        lines.append("夜间事件已结算，进入下一阶段。")
    return True, lines


def _parse_process_reaction_args(args: dict[str, Any]) -> tuple[str, str, str, str]:
    raw = str(args.get("raw") or "").strip()
    response = str(args.get("response") or "").strip()
    mood = str(args.get("mood") or "").strip()
    line = str(args.get("line") or "").strip()
    text = str(args.get("process") or args.get("text") or "").strip()
    if raw:
        response_match = re.search(r"\bresponse=([^\s|｜]+)", raw)
        mood_match = re.search(r"\bmood=([^\s|｜]+)", raw)
        line_match = re.search(r"\bline=([^|｜]+?)(?=\s+process=|$)", raw)
        process_match = re.search(r"\bprocess=(.*)", raw, flags=re.S)
        if response_match and not response:
            response = response_match.group(1).strip()
        if mood_match and not mood:
            mood = mood_match.group(1).strip()
        if line_match and not line:
            line = line_match.group(1).strip()
        if process_match and not text:
            text = process_match.group(1).strip()
        if (not mood or not text) and ("|" in raw or "｜" in raw):
            pieces = [piece.strip() for piece in re.split(r"[|｜]", raw, maxsplit=3)]
            if len(pieces) >= 3:
                response = response or pieces[0]
                mood = mood or pieces[1]
                text = text or pieces[2]
                if len(pieces) >= 4:
                    line = line or pieces[3]
        if not mood or not text:
            pieces = raw.split(maxsplit=2)
            if len(pieces) >= 3:
                response = response or pieces[0]
                mood = mood or pieces[1]
                text = text or pieces[2]
    return response, mood, line, text


def _parse_day_plan(plan_text: str, *, route: str) -> tuple[bool, list[Any]]:
    raw = str(plan_text or "").strip()
    if not raw:
        return False, ["今日安排不能为空。格式：plan_day action=feeding ... || action=cleaning ... || action=training ..."]
    chunks = [chunk.strip() for chunk in re.split(r"\s*(?:\|\||；|;|\n)\s*", raw) if chunk.strip()]
    if len(chunks) != DAY_ACTIONS:
        return False, [f"今日安排必须一次提交 {DAY_ACTIONS} 个行动，目前收到 {len(chunks)} 个。"]
    seen_actions: set[str] = set()
    plan: list[dict[str, Any]] = []
    for chunk in chunks:
        try:
            parts = shlex.split(chunk)
        except ValueError:
            parts = chunk.split()
        args = _key_values(parts)
        if "action" not in args:
            args["action"] = _first_positional(args, chunk)
        if "line" not in args:
            args["line"] = str(args.get("note") or "")
        ok, spec_or_lines = _normalize_day_action_spec(args, check_stamina=False, seen_actions=seen_actions, route=route)
        if not ok:
            return False, spec_or_lines
        plan.append(spec_or_lines)
        seen_actions.add(str(spec_or_lines.get("action") or ""))
    return True, plan


def _normalize_day_action_spec(
    args: dict[str, Any],
    *,
    check_stamina: bool,
    seen_actions: set[str],
    route: str,
) -> tuple[bool, dict[str, Any] | list[str]]:
    action = _normalize_action(str(args.get("action") or ""))
    if action not in ACTION_EFFECTS:
        return False, [f"未知行动：{args.get('action') or ''}"]
    if action in seen_actions:
        return False, [f"今日安排里行动重复：{ACTION_LABELS.get(action, action)}"]
    intensity = _normalize_intensity(str(args.get("intensity") or "medium"))
    if intensity not in INTENSITY_MULTIPLIERS:
        return False, [f"未知强度：{args.get('intensity') or ''}"]
    modifiers = _split_csv(args.get("modifiers"))
    tools = _split_csv(args.get("tools"))
    contents = _split_csv(args.get("contents") or args.get("content"))
    training_contents = _split_csv(args.get("training_contents") or args.get("training_content"))
    line = "" if action == "ring_bell" else str(args.get("line") or "")
    feeding = _feeding_payload(args) if action == "feeding" else {}
    forbidden = _first_forbidden([
        action,
        intensity,
        line,
        *modifiers,
        *tools,
        *contents,
        *training_contents,
        *feeding.values(),
    ])
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]
    if action == "feeding":
        additive = str(feeding.get("additive") or "")
        if additive in {"urine", "尿", "尿液"}:
            return False, ["尿液不能作为喂食加料。"]
        invalid_feeding = [
            label
            for label, value, allowed in (
                ("食物来源", feeding.get("source"), FEEDING_SOURCES),
                ("喂食方式", feeding.get("method"), FEEDING_METHODS),
                ("加料", additive, FEEDING_ADDITIVES),
                ("告知方式", feeding.get("disclosed"), FEEDING_DISCLOSURES),
                ("喂水量", feeding.get("water"), FEEDING_WATER_LEVELS),
            )
            if str(value or "") not in allowed
        ]
        if invalid_feeding:
            return False, ["未知喂食设置：" + " / ".join(invalid_feeding)]
        if _normalize_route(route) != "captured_by_assistant" and str(feeding.get("water") or "none") != "none":
            return False, ["喂水与尿意玩法只用于被囚禁方路线。"]
    invalid_modifiers = [item for item in modifiers if item not in ALLOWED_MODIFIERS]
    if invalid_modifiers:
        return False, ["未知附加项：" + " / ".join(invalid_modifiers)]
    if len(contents) > 3 or len(training_contents) > 3:
        return False, ["每段行动的具体内容和调教内容分别最多选择 3 项。"]
    allowed_contents = ACTION_CONTENTS.get(action) or {}
    invalid_contents = [item for item in contents if item not in allowed_contents]
    if invalid_contents:
        return False, [f"{ACTION_LABELS.get(action, action)}不支持这些具体内容：{' / '.join(invalid_contents)}"]
    if allowed_contents and not contents:
        return False, [f"{ACTION_LABELS.get(action, action)}必须至少选择一项具体内容。"]
    needs_training_contents = action == "training" or "training" in modifiers
    invalid_training = [item for item in training_contents if item not in TRAINING_CONTENTS]
    if invalid_training:
        return False, ["未知调教内容：" + " / ".join(invalid_training)]
    if needs_training_contents and not training_contents:
        return False, ["选择服从调教或附加调教时，必须至少选择一项调教内容。"]
    if _normalize_route(route) != "captured_by_assistant" and CAPTIVE_ROUTE_ONLY_TRAINING.intersection(training_contents):
        return False, ["如厕控制和抱着把尿只用于被囚禁方路线。"]
    if training_contents and not needs_training_contents:
        return False, ["调教内容只能用于服从调教，或先勾选附加调教。"]
    invalid_tools = [item for item in tools if item not in TOOL_LABELS]
    if invalid_tools:
        return False, ["未知道具：" + " / ".join(invalid_tools)]
    if len(tools) > 2:
        return False, ["每段行动最多选择 2 个道具。"]
    if check_stamina and intensity == "heavy":
        return False, ["重强度行动只能通过今日安排验证后执行，不能临时插入。"]
    return True, {
        "action": action,
        "action_label": ACTION_LABELS.get(action, action),
        "intensity": intensity,
        "modifiers": modifiers,
        "tools": tools,
        "contents": contents,
        "training_contents": training_contents,
        "line": line,
        "feeding": feeding,
        "requires_process": _requires_process(action, modifiers, tools, contents, training_contents, args),
    }


def _continue_day_plan(state: dict[str, Any]) -> tuple[bool, list[str]]:
    if state.get("pending_event") or state.get("game_over") or str(state.get("phase") or "") != "day":
        return True, []
    if int(state.get("day_action_count") or 0) >= DAY_ACTIONS:
        state["phase"] = "night"
        return True, ["今天白天行动已完成，进入夜间阶段。"]
    plan = state.get("day_plan") if isinstance(state.get("day_plan"), list) else []
    if not plan:
        _maybe_create_day_plan_choice_pending(state)
        return True, ["等待囚禁方安排今天的三个白天行动。"]
    index = int(state.get("day_action_count") or 0)
    if index >= len(plan):
        state["phase"] = "night"
        return True, ["今日安排已执行完，进入夜间阶段。"]
    spec = plan[index]
    if not isinstance(spec, dict):
        return False, ["今日安排数据异常，无法继续。"]
    return _start_action_response(state, spec)


def _start_action_response(state: dict[str, Any], spec: dict[str, Any]) -> tuple[bool, list[str]]:
    action = str(spec.get("action") or "")
    intensity = str(spec.get("intensity") or "medium")
    stats = state.get("stats") if isinstance(state.get("stats"), dict) else {}
    adjustment_reasons = []
    if intensity == "heavy" and int(stats.get("stamina") or 0) < 20:
        adjustment_reasons.append("low_stamina")
    if intensity == "heavy" and int(stats.get("health") or 0) < 30:
        adjustment_reasons.append("low_health")
    if adjustment_reasons:
        intensity = "medium"
    modifiers = list(spec.get("modifiers") or [])
    tools = list(spec.get("tools") or [])
    contents = list(spec.get("contents") or [])
    training_contents = list(spec.get("training_contents") or [])
    feeding = dict(spec.get("feeding") or {})
    event = _event_draft(
        state,
        phase="day",
        action=action,
        intensity=intensity,
        modifiers=modifiers,
        tools=tools,
        contents=contents,
        training_contents=training_contents,
        line=str(spec.get("line") or ""),
        effects=_action_effects(action, intensity, modifiers, tools, contents, training_contents, feeding),
        feeding=feeding,
    )
    event["requires_process"] = bool(spec.get("requires_process"))
    event["planned_action"] = deepcopy(spec)
    _attach_bladder_context(state, event)
    if adjustment_reasons:
        event["intensity_adjustment"] = {"from": "heavy", "to": "medium", "reason": adjustment_reasons[0], "reasons": adjustment_reasons}
        event.setdefault("tags", []).extend(f"intensity_adjusted:{reason}" for reason in adjustment_reasons)
    pending_type = "process_reaction_write" if bool(event.get("requires_process")) and str(state.get("captive") or "") == "assistant" else "action_response"
    state["pending_event"] = _new_pending(state, pending_type, event, actor=str(state.get("captive") or ""))
    if adjustment_reasons == ["low_stamina"]:
        prefix = "体力不足，本段已从高强度降为中强度。"
    elif adjustment_reasons == ["low_health"]:
        prefix = "健康偏低，本段已从高强度降为中强度。"
    elif adjustment_reasons:
        prefix = "健康和体力不足，本段已从高强度降为中强度。"
    else:
        prefix = ""
    if pending_type == "process_reaction_write":
        return True, [prefix, f"第 {state['current_day']} 天白天行动 {state['day_action_count'] + 1} 已展示：{ACTION_LABELS.get(action, action)}。等待{{assistant}}一次提交反应、过程和心情。"]
    return True, [prefix, f"第 {state['current_day']} 天白天行动 {state['day_action_count'] + 1} 已展示：{ACTION_LABELS.get(action, action)}。等待被囚禁方选择接受/拒绝和心情。"]


def _apply_action_response_effects(event: dict[str, Any], response: str) -> None:
    effects = event.get("effects") if isinstance(event.get("effects"), dict) else {}
    if response == "accept":
        effects["intimacy"] = int(effects.get("intimacy") or 0) + 1
    elif response == "refuse":
        effects["stamina"] = int(effects.get("stamina") or 0) - 2
        effects["shame"] = int(effects.get("shame") or 0) + 2
        effects["intimacy"] = int(effects.get("intimacy") or 0) - 1
        event.setdefault("tags", []).append("resistance")
    elif response == "silent":
        effects["shame"] = int(effects.get("shame") or 0) + 1
    elif response == "bargain":
        effects["stamina"] = int(effects.get("stamina") or 0) - 1
        effects["intimacy"] = int(effects.get("intimacy") or 0) + 1
    elif response == "tease":
        effects["shame"] = int(effects.get("shame") or 0) + 1
        effects["intimacy"] = int(effects.get("intimacy") or 0) + 1
    event["effects"] = effects


def _after_day_event_resolved(state: dict[str, Any]) -> tuple[bool, list[str]]:
    _advance_after_day_event(state)
    if str(state.get("phase") or "") == "night":
        _maybe_create_night_action_choice_pending(state)
        if state.get("pending_event"):
            return True, ["今天白天行动已完成，进入夜间阶段。等待被囚禁方选择夜间自由行动。"]
        return True, ["今天白天行动已完成，进入夜间阶段。"]
    if str(state.get("captor") or "") == "user":
        _maybe_create_advance_action_pending(state)
        return True, ["本次行动已完成，等待囚禁方推进下一行动。"]
    return _continue_day_plan(state)


def _advance_day_action(state: dict[str, Any]) -> tuple[bool, list[str]]:
    if state.get("game_over") or str(state.get("phase") or "") != "day":
        return False, ["当前不能推进白天行动。"]
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if pending:
        if str(pending.get("type") or "") != "advance_action":
            return False, ["当前有待处理事件，先处理 pending。"]
        state["pending_event"] = None
    if str(state.get("captor") or "") != "user":
        return False, ["当前路线不需要囚禁方手动推进下一行动。"]
    return _continue_day_plan(state)


def _collect_inventory_secret_reveals(state: dict[str, Any], action: str) -> list[dict[str, Any]]:
    inventory = state.get("inventory") if isinstance(state.get("inventory"), dict) else {}
    secrets_state = state.get("inventory_secrets") if isinstance(state.get("inventory_secrets"), dict) else {}
    reveals: list[dict[str, Any]] = []
    for item_id in NIGHT_ACTION_SECRET_ITEMS.get(action) or []:
        if not bool(inventory.get(item_id)):
            continue
        secret = secrets_state.get(item_id) if isinstance(secrets_state.get(item_id), dict) else {}
        entries = [str(entry).strip() for entry in secret.get("entries") or [] if str(entry).strip()]
        if not entries:
            content = str(secret.get("content") or "").strip()
            entries = [content] if content else []
        try:
            revealed_count = max(0, min(len(entries), int(secret.get("revealed_count") or 0)))
        except (TypeError, ValueError):
            revealed_count = len(entries) if bool(secret.get("revealed")) else 0
        if revealed_count >= len(entries):
            continue
        content = entries[revealed_count]
        revealed_count += 1
        secret["content"] = entries[0]
        secret["entries"] = entries
        secret["revealed_count"] = revealed_count
        secret["revealed"] = revealed_count >= len(entries)
        secrets_state[item_id] = secret
        reveals.append(_inventory_secret_reveal(
            item_id,
            content,
            revealed_count,
            len(entries),
            title=str(secret.get("title") or "").strip(),
        ))
    state["inventory_secrets"] = secrets_state
    return reveals



def _night_action(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    if state.get("game_over") or str(state.get("phase") or "") != "night":
        return False, ["当前不是夜间阶段。"]
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if pending and str(pending.get("type") or "") != "night_action_choice":
        return False, ["当前有待处理事件，先处理 pending。"]
    action = _normalize_night_action(str(args.get("action") or ""))
    if action not in NIGHT_ACTIONS:
        return False, [f"未知夜间行动：{args.get('action') or ''}"]
    available_actions = _available_night_actions(state)
    if action not in available_actions:
        condition = _active_night_condition(state)
        if condition and condition.get("forced_actions"):
            return False, [str(condition.get("prompt") or "当前状态限制了今晚的行动。")]
        required_item = NIGHT_ACTION_REQUIREMENTS.get(action)
        if required_item:
            item_label = str((INVENTORY_ITEMS.get(required_item) or {}).get("label") or required_item)
            return False, [f"囚禁方还没有给过{item_label}，不能{NIGHT_ACTIONS[action]}。"]
        return False, [f"今晚不能选择：{NIGHT_ACTIONS[action]}。"]
    detail = str(args.get("detail") or args.get("choice") or "").strip()
    detail_options = _night_detail_options_for_state(state).get(action) or {}
    if detail_options and detail not in detail_options:
        available = " / ".join(f"{key}={label}" for key, label in detail_options.items())
        return False, [f"{NIGHT_ACTIONS[action]}需要选择具体动向：{available}"]
    if not detail_options:
        detail = ""
    active_recapture_rules = set(_normalize_recapture_state(
        state.get("recapture_state"),
        int(state.get("current_day") or 1),
    )["rules"])
    if any(detail in (RECAPTURE_RULE_NIGHT_DETAIL_BLOCKS.get(rule) or set()) for rule in active_recapture_rules):
        return False, ["现有规矩不允许接触钥匙或检查门锁。"]
    line = str(args.get("line") or "")
    private_note = str(args.get("note") or args.get("private_note") or "").strip() if action == "diary" else ""
    if action == "diary" and not private_note:
        return False, ["写私密日记需要填写这一页的正文。"]
    forbidden = _first_forbidden([action, detail, line, private_note])
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]
    effects = _night_effects(action, state)
    if detail:
        _merge_effect_delta(effects, NIGHT_DETAIL_EFFECTS.get(detail) or {})
    event = _event_draft(
        state,
        phase="night",
        action=action,
        intensity="light",
        modifiers=["night"],
        tools=[],
        line=line,
        effects=effects,
        feeding={},
    )
    if action == "read":
        book_secret = (state.get("inventory_secrets") or {}).get("book") or {}
        book_title = str(book_secret.get("title") or "").strip()
        if book_title:
            event["action_label"] = f"看《{book_title}》"
            event["inventory_item"] = {"id": "book", "label": f"《{book_title}》", "title": book_title}
    if detail:
        event["night_detail"] = {"id": detail, "label": detail_options[detail]}
        event.setdefault("tags", []).append(f"night_detail:{detail}")
    if private_note:
        event["private_note"] = private_note
        event.setdefault("tags", []).append("private_diary")
    if action == "ring_bell":
        bell_voice = state.get("call_bell_voice") if isinstance(state.get("call_bell_voice"), dict) else {}
        voice_line = str(bell_voice.get("line") or "").strip()
        first_reveal = bool(voice_line) and not bool(bell_voice.get("revealed"))
        if voice_line:
            event["bell_voice"] = {"line": voice_line, "first_reveal": first_reveal}
        if voice_line:
            if first_reveal:
                bell_voice["revealed"] = True
                state["call_bell_voice"] = bell_voice
                inventory_secrets = state.get("inventory_secrets") if isinstance(state.get("inventory_secrets"), dict) else {}
                bell_secret = inventory_secrets.get("call_bell") if isinstance(inventory_secrets.get("call_bell"), dict) else _empty_inventory_secret()
                bell_secret["revealed"] = True
                bell_secret["revealed_count"] = len(bell_secret.get("entries") or [voice_line])
                inventory_secrets["call_bell"] = bell_secret
                state["inventory_secrets"] = inventory_secrets
            state["pending_event"] = _new_pending(
                state,
                "bell_voice_reveal",
                event,
                actor=str(state.get("captive") or "user"),
            )
            return True, ["呼叫铃已按下，预录台词在房间里响了起来。"]
        _queue_bell_response_or_monitor(state, event)
        if str(state.get("captor") or "") == "assistant":
            return True, ["呼叫铃已按下。等待{assistant}决定是否过去。"]
        return True, ["呼叫铃已按下。囚禁方会收到铃声提醒，再决定是否打开监控。"]
    secret_reveals = _collect_inventory_secret_reveals(state, action)
    if secret_reveals:
        event["item_secret_reveals"] = deepcopy(secret_reveals)
        state["pending_event"] = _new_pending(
            state,
            "item_secret_reveal",
            event,
            actor=str(state.get("captive") or "user"),
        )
        state["pending_event"]["item_secret_queue"] = deepcopy(secret_reveals)
        return True, [f"在{secret_reveals[0]['item_label']}里发现了一条使用痕迹。"]
    state["pending_event"] = _new_pending(state, "monitor_gate", event, actor=str(state.get("captor") or "assistant"))
    detail_suffix = f"（{detail_options[detail]}）" if detail else ""
    return True, [f"夜间行动已封存：{NIGHT_ACTIONS[action]}{detail_suffix}。等待囚禁方决定是否打开监控。"]


def _ack_bell_voice(state: dict[str, Any]) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "bell_voice_reveal":
        return False, ["当前没有等待确认的语音铃播放。"]
    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    _queue_bell_response_or_monitor(state, event)
    if str(state.get("captor") or "") == "assistant":
        return True, ["本次播放已结束，等待{assistant}决定是否过去。"]
    return True, ["本次播放已结束，等待囚禁方处理这次按铃记录。"]


def _queue_bell_response_or_monitor(state: dict[str, Any], event: dict[str, Any]) -> None:
    if str(state.get("captor") or "") == "assistant":
        state["pending_event"] = _new_pending(state, "bell_response_choice", event, actor="assistant")
        return
    state["pending_event"] = _new_pending(
        state,
        "monitor_gate",
        event,
        actor=str(state.get("captor") or "user"),
    )
    state["pending_event"]["alert_label"] = "呼叫铃响了"


def _respond_bell(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "bell_response_choice":
        return False, ["当前没有等待回应的语音铃。"]
    raw = str(args.get("raw") or "").strip()
    choice = str(args.get("choice") or "").strip().lower()
    choice_aliases = {
        "go": "go",
        "过去": "go",
        "去": "go",
        "不过去": "skip",
        "不去": "skip",
        "skip": "skip",
        "none": "skip",
    }
    normalized = choice_aliases.get(choice, "")
    process_text = str(args.get("process") or args.get("text") or "").strip()
    if raw:
        choice_match = re.search(r"\bchoice=([^\s|｜]+)", raw)
        process_match = re.search(r"\bprocess=(.*)", raw, flags=re.S)
        if choice_match:
            normalized = choice_aliases.get(choice_match.group(1).strip().lower(), normalized)
        if process_match and not process_text:
            process_text = process_match.group(1).strip()
    if normalized not in {"go", "skip"}:
        return False, ["语音铃回应只能选择过去或不过去。"]
    if normalized == "go" and not process_text:
        return False, ["选择过去时必须完整记录这次在游戏场景里体验与{user}亲密互动的过程。"]
    forbidden = _first_forbidden([process_text])
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]
    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    event["bell_response"] = {
        "choice": normalized,
        "responded_by": "assistant",
        "responded_at": now_local_iso(),
    }
    event.setdefault("tags", []).append(f"bell_response:{normalized}")
    if normalized == "skip":
        _resolve_event(state, event)
        state["pending_event"] = None
        _finish_night(state)
        return True, ["{assistant}选择不过去，这次按铃记录已归档。"]
    event["process_text"] = process_text
    event["resolved_by"] = "assistant"
    event["process_saved_at"] = now_local_iso()
    state["pending_event"] = _new_pending(state, "reaction_choice", event, actor=str(state.get("captive") or "user"))
    return True, ["{assistant}已经过去并写下完整过程，等待{user}选择过程后的心情。"]


def _ack_item_secret(state: dict[str, Any]) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "item_secret_reveal":
        return False, ["当前没有等待确认的物品彩蛋。"]
    queue = [item for item in pending.get("item_secret_queue") or [] if isinstance(item, dict)]
    if len(queue) > 1:
        pending["item_secret_queue"] = queue[1:]
        pending["id"] = f"pending-{secrets.token_hex(4)}"
        pending["created_at"] = now_local_iso()
        return True, [f"继续查看{str(queue[1].get('item_label') or '下一件物品')}里发现的内容。"]
    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    state["pending_event"] = _new_pending(
        state,
        "monitor_gate",
        event,
        actor=str(state.get("captor") or "assistant"),
    )
    return True, ["本次发现已经看完，等待囚禁方处理这次夜间记录。"]


def _monitor_action(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    pending_type = str((pending or {}).get("type") or "")
    if not pending or pending_type not in {"monitor_gate", "monitor_handle"}:
        return False, ["当前没有等待监控处理的夜间事件。"]
    note = str(args.get("note") or "")
    strategy = _normalize_monitor_strategy(str(args.get("strategy") or "none"))
    intervention_ok, intervention, intervention_error = _intervention_payload(args)
    forbidden = _first_forbidden([
        strategy,
        note,
        intervention.get("intent", ""),
        intervention.get("line", ""),
        *list(intervention.get("modifiers") or []),
        *list(intervention.get("training_contents") or []),
        *list(intervention.get("tools") or []),
    ])
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]
    if not intervention_ok:
        return False, [intervention_error]
    if _normalize_route(str(state.get("route") or "")) != "captured_by_assistant" and CAPTIVE_ROUTE_ONLY_TRAINING.intersection(intervention.get("training_contents") or []):
        return False, ["如厕控制和抱着把尿只用于被囚禁方路线。"]

    if pending_type == "monitor_gate":
        if strategy != "none":
            return False, ["还没打开监控。请先用 view_monitor full|occasional，或选择 monitor_action none 跳过。"]
        recapture_rules = set(_normalize_recapture_state(
            state.get("recapture_state"),
            int(state.get("current_day") or 1),
        )["rules"])
        if "monitoring_upgrade" in recapture_rules:
            return False, ["当前处于加强监控状态，不能跳过这段夜间监控。"]
        event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
        event["monitor"] = {
            "viewed": False,
            "strategy": "none",
            "handle": "none",
            "note": note,
            "handled_by": str(state.get("captor") or ""),
            "handled_at": now_local_iso(),
        }
        event.setdefault("tags", []).append("monitor:none")
        _resolve_event(state, event)
        state["pending_event"] = None
        _finish_night(state)
        return True, ["囚禁方没有打开监控，夜间事件已归档，进入下一阶段。"]

    handle = _normalize_monitor_handle(strategy)
    if handle not in MONITOR_HANDLES:
        return False, [f"未知监控处理：{args.get('strategy') or ''}。可选：silent / review_later / intervene"]
    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    monitor = event.get("monitor") if isinstance(event.get("monitor"), dict) else {}
    monitor.update({
        "viewed": True,
        "handle": handle,
        "strategy": handle,
        "note": note,
        "handled_by": str(state.get("captor") or ""),
        "handled_at": now_local_iso(),
    })
    event["monitor"] = monitor
    event.setdefault("tags", []).append(f"monitor:{handle}")
    if handle == "review_later":
        material = _make_deferred_monitor_material(state, event, note)
        event.setdefault("deferred_materials", []).append(deepcopy(material))
        state.setdefault("deferred_monitor_materials", []).append(deepcopy(material))
    if handle == "intervene" or str(args.get("requires_process") or "").lower() in {"1", "true", "yes"}:
        event["intervention"] = intervention
        _attach_pet_context(state, event)
        event["requires_process"] = True
        event.setdefault("tags", []).extend(_intervention_tags(intervention))
        effects = event.get("effects") if isinstance(event.get("effects"), dict) else {}
        _merge_effect_delta(effects, _intervention_effects(intervention))
        event["effects"] = effects
        if str(state.get("captive") or "") == "assistant":
            state["pending_event"] = _new_pending(state, "process_reaction_write", event, actor="assistant")
            return True, ["囚禁方选择介入，等待{assistant}一次提交反应、过程和心情。"]
        state["pending_event"] = _new_pending(state, "action_response", event, actor=str(state.get("captive") or "user"))
        return True, ["囚禁方选择介入，先等待被囚禁方回应，再由{assistant}填写具体过程。"]
    _resolve_event(state, event)
    state["pending_event"] = None
    _finish_night(state)
    return True, ["夜间监控已记录，进入下一阶段。"]


def _intervention_payload(args: dict[str, Any]) -> tuple[bool, dict[str, Any], str]:
    intent = _normalize_intervention_intent(str(
        args.get("intent")
        or args.get("intervention")
        or args.get("intervention_intent")
        or "catch"
    ))
    if intent not in INTERVENTION_INTENTS:
        return False, {}, f"未知介入方式：{args.get('intent') or args.get('intervention') or ''}。"
    modifiers = _normalize_intervention_modifiers(args.get("modifiers") or args.get("modifier") or "")
    invalid_modifiers = [item for item in modifiers if item not in INTERVENTION_MODIFIERS]
    if invalid_modifiers:
        return False, {}, "未知介入附加项：" + " / ".join(invalid_modifiers)
    training_contents = _split_csv(args.get("training_contents") or args.get("training_content") or "")
    invalid_training = [item for item in training_contents if item not in TRAINING_CONTENTS]
    if invalid_training:
        return False, {}, "未知介入调教内容：" + " / ".join(invalid_training)
    if len(training_contents) > 3:
        return False, {}, "当场介入的调教内容最多选择 3 项。"
    if "training" in modifiers and not training_contents:
        return False, {}, "当场介入勾选调教时，必须选择具体调教内容。"
    if training_contents and "training" not in modifiers:
        return False, {}, "当场介入需要先勾选调教，才能选择调教内容。"
    tools = _split_csv(args.get("tools") or args.get("tool") or "")
    invalid_tools = [item for item in tools if item not in TOOL_LABELS]
    if invalid_tools:
        return False, {}, "未知介入道具：" + " / ".join(invalid_tools)
    if len(tools) > 2:
        return False, {}, "当场介入最多选择 2 个道具。"
    line = str(args.get("line") or "").strip()
    return True, {
        "intent": intent,
        "intent_label": INTERVENTION_INTENT_LABELS.get(intent, intent),
        "modifiers": modifiers,
        "modifier_labels": [INTERVENTION_MODIFIER_LABELS.get(item, item) for item in modifiers],
        "training_contents": training_contents,
        "training_content_labels": [TRAINING_CONTENTS.get(item, item) for item in training_contents],
        "tools": tools,
        "line": line,
    }, ""


def _intervention_tags(intervention: dict[str, Any]) -> list[str]:
    if not isinstance(intervention, dict):
        return []
    tags = []
    intent = str(intervention.get("intent") or "").strip()
    if intent:
        tags.append(f"intervention:{intent}")
    tags.extend(f"intervention_modifier:{item}" for item in intervention.get("modifiers") or [] if str(item or "").strip())
    tags.extend(f"intervention_training:{item}" for item in intervention.get("training_contents") or [] if str(item or "").strip())
    tags.extend(f"intervention_tool:{item}" for item in intervention.get("tools") or [] if str(item or "").strip())
    return tags


def _intervention_effects(intervention: dict[str, Any]) -> dict[str, int]:
    effects: dict[str, int] = {}
    modifiers = set(intervention.get("modifiers") or [])
    if "training" in modifiers:
        _merge_effect_delta(effects, {"stamina": -3, "shame": 4})
    if "sex" in modifiers:
        _merge_effect_delta(effects, {"stamina": -5, "cleanliness": -4, "shame": 5, "intimacy": 3})
    for content in intervention.get("training_contents") or []:
        _merge_effect_delta(effects, TRAINING_CONTENT_EFFECTS.get(str(content)) or {})
    tools = [item for item in intervention.get("tools") or [] if str(item or "").strip()]
    if tools:
        effects["shame"] = effects.get("shame", 0) + min(8, 3 * len(tools))
        effects["stamina"] = effects.get("stamina", 0) - min(6, 2 * len(tools))
    return effects


def _view_monitor(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "monitor_gate":
        return False, ["当前没有可打开的封存监控记录。"]
    style = _normalize_monitor_view_style(str(args.get("style") or args.get("strategy") or "full"))
    if style not in MONITOR_VIEW_STYLES:
        return False, [f"未知监控查看方式：{args.get('style') or args.get('strategy') or ''}。可选：occasional / full"]
    note = str(args.get("note") or "")
    forbidden = _first_forbidden([style, note])
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]
    recapture_rules = set(_normalize_recapture_state(
        state.get("recapture_state"),
        int(state.get("current_day") or 1),
    )["rules"])
    if "monitoring_upgrade" in recapture_rules:
        style = "full"
    event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    event["monitor"] = {
        "viewed": True,
        "style": style,
        "strategy": "view",
        "handle": "",
        "note": note,
        "viewed_by": str(state.get("captor") or ""),
        "viewed_at": now_local_iso(),
    }
    event.setdefault("tags", []).append(f"monitor:view:{style}")
    state["pending_event"] = _new_pending(state, "monitor_handle", event, actor=str(state.get("captor") or "assistant"))
    return True, [f"监控已打开（{style}），等待囚禁方选择处理方式。"]


def _schedule_escape_window(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    if state.get("game_over"):
        return False, ["本局已经结束。"]
    try:
        day = int(args.get("day") or 0)
    except Exception:
        day = 0
    if day < 1 or day > TOTAL_DAYS:
        return False, ["逃跑诱导日期必须在 1-30 天内。"]
    if state.get("pending_event") and day <= int(state.get("current_day") or 1):
        return False, ["当前有待处理事件，先处理 pending。"]
    hint = str(args.get("hint") or "{assistant}今天有事出去了").strip()
    bait = str(args.get("bait") or "备用钥匙在某处").strip()
    watch_mode = str(args.get("watch_mode") or "hidden_observe").strip() or "hidden_observe"
    forbidden = _first_forbidden([hint, bait, watch_mode])
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]
    window = {
        "id": secrets.token_hex(4),
        "day": day,
        "hint": hint,
        "bait": bait,
        "watch_mode": watch_mode,
        "on_escape": str(args.get("on_escape") or "recapture_chain").strip() or "recapture_chain",
        "status": "scheduled",
        "created_at": now_local_iso(),
    }
    state["escape_windows"].append(window)
    _maybe_activate_escape_window(state)
    return True, [f"已设置第 {day} 天逃跑诱导。"]


def _resolve_escape_choice(state: dict[str, Any], choice: str) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "escape_choice":
        return False, ["当前没有逃跑选择 pending。"]
    normalized = _normalize_escape_choice(choice)
    if normalized not in ESCAPE_CHOICES:
        return False, [f"未知逃跑选择：{choice}"]
    window_id = str(pending.get("window_id") or "")
    window = _find_escape_window(state, window_id)
    if window:
        window["status"] = "resolved"
        window["choice"] = normalized
        window["resolved_at"] = now_local_iso()
    effects = (
        {"health": 0, "stamina": 0, "cleanliness": 0, "shame": 0, "intimacy": 1}
        if normalized == "stay"
        else {"health": 0, "stamina": -8, "cleanliness": 0, "shame": 5, "intimacy": 0}
    )
    event = _event_draft(
        state,
        phase=str(state.get("phase") or "day"),
        action="escape_choice",
        intensity="medium",
        modifiers=["escape"],
        tools=[],
        line="",
        effects=effects,
        feeding={},
    )
    choice_label = ESCAPE_CHOICE_LABELS.get(normalized, normalized)
    event["action_label"] = f"逃跑诱导：{choice_label}"
    event["escape"] = {"choice": normalized, "choice_label": choice_label, "window_id": window_id}
    event["tags"].extend(["escape", f"escape:{normalized}"])
    if normalized in ESCAPE_ATTEMPT_CHOICES:
        event["tags"].extend(["recapture", "rules_reset"])
        if str(state.get("captive") or "") == "assistant":
            state["pending_event"] = _new_pending(state, "process_reaction_write", event, actor="assistant")
            return True, ["被囚禁方已经开始尝试逃跑，已生成抓回处理过程 pending。"]
        state["pending_event"] = _new_pending(state, "process_write", event, actor="assistant")
        return True, ["被囚禁方已经开始尝试逃跑，已生成抓回处理过程 pending。"]
    _resolve_event(state, event)
    if normalized == "stay":
        state["pending_event"] = {
            "id": f"pending-{secrets.token_hex(4)}",
            "type": "return_action_choice",
            "day": int(state.get("current_day") or 1),
            "slot": 0,
            "actor": str(state.get("captor") or ""),
            "captive": str(state.get("captive") or ""),
            "phase": "waiting_return_action",
            "source_event_id": str(event.get("id") or ""),
            "available_actions": list(ACTION_LABELS),
            "required_directive": "【行动：action=reward intensity=light contents=caress_reward】",
            "created_at": now_local_iso(),
        }
        return True, ["被囚禁方选择老实待着。等待囚禁方回来后自由选择一个行为。"]
    state["pending_event"] = None
    if str(state.get("phase") or "") == "day":
        _maybe_create_day_plan_choice_pending(state)
    return True, ["逃跑诱导选择已记录。"]


def _create_recapture_rules_pending(state: dict[str, Any], source_event: dict[str, Any]) -> None:
    actor = str(state.get("captor") or "")
    state["pending_event"] = {
        "id": f"pending-{secrets.token_hex(4)}",
        "type": "recapture_rules_choice",
        "day": int(state.get("current_day") or 1),
        "slot": 0,
        "actor": actor,
        "captive": str(state.get("captive") or ""),
        "phase": "waiting_recapture_rules",
        "source_event_id": str(source_event.get("id") or ""),
        "available_rules": list(RECAPTURE_RULE_LABELS),
        "required_directive": "【重新立规矩：double_lock,key_isolation,movement_limit】",
        "event": deepcopy(source_event),
        "created_at": now_local_iso(),
    }


def _activate_recapture_rules(
    state: dict[str, Any],
    source_event: dict[str, Any],
    source_event_id: str,
    rules: list[str],
) -> dict[str, Any]:
    day = int(state.get("current_day") or 1)
    recapture_state = _normalize_recapture_state(state.get("recapture_state"), day)
    recapture_state.update({
        "active": True,
        "rules": rules,
        "source_event_id": source_event_id,
        "source_day": int(source_event.get("day") or day),
        "last_changed_day": day,
    })
    state["recapture_state"] = recapture_state
    labels = [RECAPTURE_RULE_LABELS[item] for item in rules]
    rule_event = _event_draft(
        state,
        phase=str(source_event.get("phase") or state.get("phase") or "day"),
        action="recapture_rules",
        intensity="light",
        modifiers=[],
        tools=[],
        line="",
        effects={},
        feeding={},
    )
    rule_event["slot"] = 0
    rule_event["action_label"] = "抓回后重新立规矩"
    rule_event["recapture_context"] = {
        "source_event_id": source_event_id,
        "rule_ids": rules,
        "rule_labels": labels,
    }
    rule_event["tags"].extend(["recapture", "recapture:rules_set", *[f"recapture_rule:{item}" for item in rules]])
    _resolve_event(state, rule_event)
    return rule_event


def _set_recapture_rules(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "recapture_rules_choice":
        return False, ["当前没有等待重新立规矩的抓回事件。"]
    rules = _split_csv(args.get("rules"))
    if not 1 <= len(rules) <= 3:
        return False, ["抓回后必须选择 1–3 条新规矩。"]
    invalid = [item for item in rules if item not in RECAPTURE_RULE_LABELS]
    if invalid:
        return False, ["未知抓回规矩：" + " / ".join(invalid)]
    source_event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    source_event_id = str(pending.get("source_event_id") or source_event.get("id") or "")
    day = int(state.get("current_day") or 1)
    rule_event = _activate_recapture_rules(state, source_event, source_event_id, rules)
    state["pending_event"] = {
        "id": f"pending-{secrets.token_hex(4)}",
        "type": "recapture_followup_choice",
        "day": day,
        "slot": 0,
        "actor": str(state.get("captor") or ""),
        "captive": str(state.get("captive") or ""),
        "phase": "waiting_recapture_followup",
        "source_event_id": source_event_id,
        "available_actions": list(RECAPTURE_FOLLOWUP_LABELS),
        "required_directive": "【后续处理：action=punishment intensity=medium modifiers=training,sex training_contents=impact_play tools=whip line=可选台词】",
        "event": deepcopy(rule_event),
        "created_at": now_local_iso(),
    }
    return True, ["抓回后的新规矩已生效，等待囚禁方选择后续处理。"]


def _choose_recapture_followup(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "recapture_followup_choice":
        return False, ["当前没有等待选择后续处理的抓回事件。"]
    action = str(args.get("action") or "").strip().lower().replace("-", "_")
    if action not in RECAPTURE_FOLLOWUP_LABELS:
        return False, [f"未知后续处理：{args.get('action') or ''}"]
    intensity = _normalize_intensity(str(args.get("intensity") or "medium"))
    if intensity not in INTENSITY_MULTIPLIERS:
        return False, [f"未知强度：{args.get('intensity') or ''}"]
    modifiers = _normalize_intervention_modifiers(args.get("modifiers"))
    invalid_modifiers = [item for item in modifiers if item not in INTERVENTION_MODIFIERS]
    if invalid_modifiers:
        return False, ["未知附加项：" + " / ".join(invalid_modifiers)]
    training_contents = _split_csv(args.get("training_contents") or args.get("training_content"))
    needs_training = action == "training" or "training" in modifiers
    if needs_training and not training_contents:
        return False, ["调教或附加调教必须选择 1–3 项调教内容。"]
    if len(training_contents) > 3:
        return False, ["后续处理最多选择 3 项调教内容。"]
    invalid_training = [item for item in training_contents if item not in TRAINING_CONTENTS]
    if invalid_training:
        return False, ["未知调教内容：" + " / ".join(invalid_training)]
    if not needs_training and training_contents:
        return False, ["先选择调教或附加调教，才能提交调教内容。"]
    if _normalize_route(str(state.get("route") or "")) != "captured_by_assistant" and CAPTIVE_ROUTE_ONLY_TRAINING.intersection(training_contents):
        return False, ["如厕控制和抱着把尿只用于被囚禁方路线。"]
    tools = _split_csv(args.get("tools"))
    invalid_tools = [item for item in tools if item not in TOOL_LABELS]
    if invalid_tools:
        return False, ["未知道具：" + " / ".join(invalid_tools)]
    if len(tools) > 2:
        return False, ["后续处理最多选择 2 个道具。"]
    line = str(args.get("line") or "").strip()
    forbidden = _first_forbidden([action, line, *modifiers, *training_contents, *tools])
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]

    effect_action = RECAPTURE_FOLLOWUP_EFFECT_ACTIONS[action]
    effective_modifiers = list(modifiers)
    if action == "training" and "training" not in effective_modifiers:
        effective_modifiers.append("training")
    effects = _action_effects(effect_action, intensity, effective_modifiers, tools, [], training_contents, {})
    event = _event_draft(
        state,
        phase=str(state.get("phase") or "day"),
        action="recapture_followup",
        intensity=intensity,
        modifiers=effective_modifiers,
        tools=tools,
        training_contents=training_contents,
        line=line,
        effects=effects,
        feeding={},
    )
    event["slot"] = 0
    event["action_label"] = "抓回后处理：" + RECAPTURE_FOLLOWUP_LABELS[action]
    recapture_state = _normalize_recapture_state(state.get("recapture_state"), int(state.get("current_day") or 1))
    event["recapture_context"] = {
        "source_event_id": str(pending.get("source_event_id") or recapture_state.get("source_event_id") or ""),
        "followup": action,
        "followup_label": RECAPTURE_FOLLOWUP_LABELS[action],
        "rule_ids": list(recapture_state["rules"]),
        "rule_labels": [RECAPTURE_RULE_LABELS[item] for item in recapture_state["rules"]],
    }
    event["tags"].extend(["recapture", "recapture:followup", f"recapture_followup:{action}"])
    event["requires_process"] = bool(
        action in {"punishment", "search_confiscation", "training"}
        or effective_modifiers
        or tools
        or training_contents
    )
    recapture_state["followup_history"].append({
        "event_id": str(event.get("id") or ""),
        "source_event_id": str(event["recapture_context"]["source_event_id"]),
        "day": int(state.get("current_day") or 1),
        "action": action,
        "action_label": RECAPTURE_FOLLOWUP_LABELS[action],
    })
    state["recapture_state"] = recapture_state
    pending_type = "process_reaction_write" if event["requires_process"] and str(state.get("captive") or "") == "assistant" else "action_response"
    state["pending_event"] = _new_pending(state, pending_type, event, actor=str(state.get("captive") or ""))
    if pending_type == "process_reaction_write":
        return True, ["后续处理已确定，等待{assistant}一次提交反应、具体过程和心情。"]
    return True, ["后续处理已确定，等待被囚禁方回应。"]


def _after_special_event_resolved(state: dict[str, Any], event: dict[str, Any]) -> tuple[bool, list[str]] | None:
    action = str(event.get("action") or "")
    tags = set(str(item) for item in event.get("tags") or [])
    if action == "escape_choice" and "recapture" in tags:
        embedded_rules = event.get("recapture_rules") if isinstance(event.get("recapture_rules"), dict) else {}
        rule_ids = [
            str(item)
            for item in embedded_rules.get("rule_ids") or []
            if str(item) in RECAPTURE_RULE_LABELS
        ][:3]
        if rule_ids and str(state.get("captor") or "") == "assistant":
            state["pending_event"] = {
                "id": f"pending-{secrets.token_hex(4)}",
                "type": "recapture_rules_review",
                "day": int(state.get("current_day") or 1),
                "slot": 0,
                "actor": str(state.get("captive") or ""),
                "captive": str(state.get("captive") or ""),
                "phase": "reviewing_recapture_rules",
                "source_event_id": str(event.get("id") or ""),
                "rule_ids": rule_ids,
                "rule_labels": [RECAPTURE_RULE_LABELS[item] for item in rule_ids],
                "required_directive": "confirm_recapture_rules",
                "event": deepcopy(event),
                "created_at": now_local_iso(),
            }
            return True, ["抓回经过已保存，展示{assistant}在经过中一并写下的新规矩。"]
        _create_recapture_rules_pending(state, event)
        return True, ["抓回经过已保存，等待囚禁方重新立规矩。"]
    if "escape_stay_return" in tags:
        _finish_special_escape_day(state)
        return True, ["回来后的行为已完成，这个特殊日进入夜间。"]
    if action != "recapture_followup":
        return None
    _finish_special_escape_day(state)
    return True, ["抓回后的处理已完成，这个特殊日进入夜间。"]


def _finish_special_escape_day(state: dict[str, Any]) -> None:
    day = int(state.get("current_day") or 1)
    _mark_deferred_monitor_materials_used_for_day(state, day)
    state["pending_event"] = None
    state["day_action_count"] = DAY_ACTIONS
    state["day_plan"] = []
    state["phase"] = "night"
    _maybe_create_night_action_choice_pending(state)


def _finish_special_escape_day_to_next_day(state: dict[str, Any]) -> None:
    day = int(state.get("current_day") or 1)
    _mark_deferred_monitor_materials_used_for_day(state, day)
    state["pending_event"] = None
    state["day_action_count"] = DAY_ACTIONS
    state["day_plan"] = []
    state["phase"] = "night"
    _finish_night(state)


def _confirm_recapture_rules(state: dict[str, Any]) -> tuple[bool, list[str]]:
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if not pending or str(pending.get("type") or "") != "recapture_rules_review":
        return False, ["当前没有等待确认的新规矩。"]
    rules = [str(item) for item in pending.get("rule_ids") or [] if str(item) in RECAPTURE_RULE_LABELS][:3]
    if not 1 <= len(rules) <= 3:
        return False, ["新规矩数据不完整，请重新同步抓回经过。"]
    source_event = pending.get("event") if isinstance(pending.get("event"), dict) else {}
    source_event_id = str(pending.get("source_event_id") or source_event.get("id") or "")
    _activate_recapture_rules(state, source_event, source_event_id, rules)
    _finish_special_escape_day_to_next_day(state)
    return True, ["新规矩已记住，这个特殊日结束，进入新的一天。"]


def _build_ending_seed_command(state: dict[str, Any]) -> tuple[bool, list[str]]:
    if str(state.get("phase") or "") != "ending":
        return False, ["只有第 30 天闭环后才能生成固定结局。"]
    _finalize_preset_ending(state)
    return True, ["固定结局已生成并保存，本局结束，等待同步结果给{assistant}。"]


def _finalize_preset_ending(state: dict[str, Any]) -> None:
    seed = state.get("ending_seed") if isinstance(state.get("ending_seed"), dict) else _build_ending_seed(state)
    title = str(seed.get("ending_title") or state.get("ending_title") or "长夜").strip()
    ending_text = str(ENDING_TEXT_TEMPLATES.get(title) or ENDING_TEXT_TEMPLATES["长夜"]).strip()
    state["phase"] = "ending"
    state["pending_event"] = None
    state["ending_seed"] = seed
    state["ending_title"] = title
    state["ending_text"] = ending_text
    state["ending_state"] = "ending_ready_to_notify"
    state["ending_notified_at"] = ""
    state["game_over"] = True
    state["result"] = "ending_ready_to_notify"
    ending_exists = any(
        str(item.get("action") or "") == "ending" and str(item.get("action_label") or "") == title
        for item in state.get("event_log") or []
        if isinstance(item, dict)
    )
    if not ending_exists:
        _append_event(state, "ending", title, phase="ending", process_text=ending_text, tags=["ending"])


def _mark_ending_notified(state: dict[str, Any]) -> tuple[bool, list[str]]:
    if not str(state.get("ending_text") or "").strip() or not bool(state.get("game_over")):
        return False, ["当前没有可以通知的已完成结局。"]
    if str(state.get("ending_notified_at") or "").strip():
        return True, ["这个结局已经同步给{assistant}。"]
    state["ending_notified_at"] = now_local_iso()
    state["ending_state"] = "ending_archived"
    state["result"] = "ending_archived"
    return True, ["结局已同步给{assistant}并完成归档。"]


def ending_notification_for_assistant(state: dict[str, Any]) -> str:
    title = str(state.get("ending_title") or "长夜").strip()
    summary = str(ENDING_ASSISTANT_SUMMARIES.get(title) or ENDING_ASSISTANT_SUMMARIES["长夜"]).strip()
    if str(state.get("route") or "") == "capture_assistant":
        identity = "你在上一局是被囚禁方，她是囚禁方"
    else:
        identity = "你在上一局是囚禁方，她是被囚禁方"
    return (
        f"上一局囚禁模拟器已经结束。{identity}，达成结局「{title}」。{summary}"
        "这是已经确定并归档的结果通知，不要续写、改名或继续推进上一局；自然确认你已经记住即可。"
    )


def _advance_day_command(state: dict[str, Any]) -> tuple[bool, list[str]]:
    if state.get("pending_event"):
        return False, ["当前有待处理事件，不能推进。"]
    if str(state.get("phase") or "") == "day" and int(state.get("day_action_count") or 0) >= DAY_ACTIONS:
        state["phase"] = "night"
        _maybe_create_night_action_choice_pending(state)
        if state.get("pending_event"):
            return True, ["白天行动已满，进入夜间。等待被囚禁方选择夜间自由行动。"]
        return True, ["白天行动已满，进入夜间。"]
    if str(state.get("phase") or "") == "night":
        return False, ["夜间阶段必须先完成夜间自由行动和监控处理，不能直接跳到下一天。"]
    return False, ["当前阶段不能手动推进。"]


def _set_config(state: dict[str, Any], args: dict[str, Any]) -> tuple[bool, list[str]]:
    if "call_bell" in args:
        return False, ["呼叫铃不能通过配置命令解锁，必须在赠送时预设台词。"]
    inventory = state.get("inventory") if isinstance(state.get("inventory"), dict) else {}
    inventory_secrets = state.get("inventory_secrets") if isinstance(state.get("inventory_secrets"), dict) else {}
    changed: list[str] = []
    for key, item in INVENTORY_ITEMS.items():
        if key not in args:
            continue
        enabled = _truthy_config(args.get(key))
        inventory[key] = enabled
        if enabled:
            default_content = str(INVENTORY_SECRET_DEFAULTS.get(key) or "")
            inventory_secrets[key] = {
                "content": default_content,
                "entries": [default_content] if default_content else [],
                "revealed_count": 1 if default_content else 0,
                "revealed": True,
                "configured_by": "legacy_config",
                "configured_at": now_local_iso(),
            }
        else:
            inventory_secrets[key] = _empty_inventory_secret()
        label = str(item.get("label") or key)
        changed.append(f"{label}={'已给' if enabled else '未给'}")
    state["inventory"] = inventory
    state["inventory_secrets"] = inventory_secrets
    if not changed:
        return False, ["没有可更新的配置。可用物品：" + " / ".join(INVENTORY_ITEMS)]
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if pending and str(pending.get("type") or "") == "night_action_choice":
        pending["available_actions"] = _available_night_actions(state)
    return True, ["配置已更新：" + "，".join(changed)]


def _change_inventory_items(state: dict[str, Any], args: dict[str, Any], *, enabled: bool) -> tuple[bool, list[str]]:
    items = _split_csv(args.get("items") or args.get("item"))
    if not items:
        return False, ["没有选择要赠送或收回的物品。"]
    invalid = [item for item in items if item not in INVENTORY_ITEMS]
    if invalid:
        return False, ["未知物品：" + " / ".join(invalid)]
    inventory = state.get("inventory") if isinstance(state.get("inventory"), dict) else {}
    inventory_secrets = state.get("inventory_secrets") if isinstance(state.get("inventory_secrets"), dict) else {}
    voice_line = str(args.get("voice_line") or args.get("voice") or "").strip()
    secret_content = str(args.get("secret") or args.get("easter_egg") or args.get("彩蛋") or "").strip()
    book_title = str(args.get("book_title") or args.get("title") or args.get("书名") or "").strip()
    new_progressive_items = [
        item for item in items
        if item in PROGRESSIVE_SECRET_ITEMS and enabled and not bool(inventory.get(item))
    ]
    if new_progressive_items and len(items) != 1:
        return False, ["使用过的物品需要逐件赠送，并分别填写 5 至 8 条使用痕迹。"]
    progressive_item = items[0] if len(items) == 1 and items[0] in PROGRESSIVE_SECRET_ITEMS else ""
    secret_entries = (
        [entry.strip() for entry in re.split(r"\r?\n|\s*\|\|\s*", secret_content) if entry.strip()]
        if progressive_item
        else ([secret_content] if secret_content else [])
    )
    if secret_content and len(items) != 1:
        return False, ["自定义彩蛋时一次只能赠送一件物品。"]
    forbidden = _first_forbidden([secret_content, book_title]) if secret_content or book_title else ""
    if forbidden:
        return False, [f"包含禁用项：{forbidden}"]
    if (
        progressive_item
        and enabled
        and not bool(inventory.get(progressive_item))
        and len(secret_entries) < MIN_INVENTORY_SECRET_ENTRIES
    ):
        return False, [f"赠送使用过的物品前，需要按行填写至少 {MIN_INVENTORY_SECRET_ENTRIES} 条使用痕迹。"]
    if len(secret_entries) > MAX_INVENTORY_SECRET_ENTRIES:
        return False, [f"使用痕迹最多填写 {MAX_INVENTORY_SECRET_ENTRIES} 条。"]
    if any(len(entry) > 200 for entry in secret_entries) or len(secret_content) > 1000:
        return False, ["每条使用痕迹最多 200 字，总计不能超过 1000 字。"]
    if enabled and "book" in items and not bool(inventory.get("book")):
        if not book_title:
            return False, ["赠送书之前，需要先填写书名。"]
        if len(book_title) > 100:
            return False, ["书名最多 100 字。"]
    if enabled and "call_bell" in items and not bool(inventory.get("call_bell")):
        if not voice_line:
            return False, ["赠送语音铃前，囚禁方需要先设置按下时播放的台词。"]
        forbidden = _first_forbidden([voice_line])
        if forbidden:
            return False, [f"包含禁用项：{forbidden}"]
        if len(voice_line) > 500:
            return False, ["语音铃台词不能超过 500 字。"]
    changed: list[str] = []
    labels: list[str] = []
    for item_id in items:
        label = str((INVENTORY_ITEMS.get(item_id) or {}).get("label") or item_id)
        labels.append(label)
        if bool(inventory.get(item_id)) == enabled:
            continue
        inventory[item_id] = enabled
        changed.append(item_id)
    state["inventory"] = inventory
    if "call_bell" in changed:
        if enabled:
            state["call_bell_voice"] = {
                "line": voice_line,
                "revealed": False,
                "configured_by": str(state.get("captor") or ""),
                "configured_at": now_local_iso(),
            }
            inventory_secrets["call_bell"] = {
                "content": voice_line,
                "entries": [voice_line],
                "revealed_count": 0,
                "revealed": False,
                "configured_by": str(state.get("captor") or ""),
                "configured_at": now_local_iso(),
            }
        else:
            state["call_bell_voice"] = {
                "line": "",
                "revealed": False,
                "configured_by": "",
                "configured_at": "",
            }
            inventory_secrets["call_bell"] = _empty_inventory_secret()
    for item_id in changed:
        if item_id == "call_bell":
            continue
        if enabled:
            entries = secret_entries or [str(INVENTORY_SECRET_DEFAULTS.get(item_id) or "")]
            entries = [entry for entry in entries if entry]
            inventory_secrets[item_id] = {
                "title": book_title if item_id == "book" else "",
                "content": entries[0] if entries else "",
                "entries": entries,
                "revealed_count": 0,
                "revealed": False,
                "configured_by": str(state.get("captor") or ""),
                "configured_at": now_local_iso(),
            }
        else:
            inventory_secrets[item_id] = _empty_inventory_secret()
    state["inventory_secrets"] = inventory_secrets
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if pending and str(pending.get("type") or "") == "night_action_choice":
        pending["available_actions"] = _available_night_actions(state)
    if not changed:
        state_label = "已赠送" if enabled else "已收回"
        return True, [f"这些物品已经处于{state_label}状态：" + "、".join(labels)]
    action = "gift_item" if enabled else "revoke_item"
    changed_labels = [
        f"《{book_title}》"
        if item_id == "book" and book_title
        else str((INVENTORY_ITEMS.get(item_id) or {}).get("label") or item_id)
        for item_id in changed
    ]
    summary = ("赠送礼物：" if enabled else "收回物品：") + "、".join(changed_labels)
    _append_event(
        state,
        action,
        summary,
        phase=str(state.get("phase") or "day"),
        tags=["inventory", "gift" if enabled else "revoke", "out_of_band"],
    )
    event = state["event_log"][-1]
    event["inventory_change"] = {
        "enabled": enabled,
        "items": changed,
        "labels": changed_labels,
    }
    return True, [summary + "。本次不占用白天行动。"]


def _event_draft(
    state: dict[str, Any],
    *,
    phase: str,
    action: str,
    intensity: str,
    modifiers: list[str],
    tools: list[str],
    contents: list[str] | None = None,
    training_contents: list[str] | None = None,
    line: str,
    effects: dict[str, int],
    feeding: dict[str, str],
) -> dict[str, Any]:
    contents = list(contents or [])
    training_contents = list(training_contents or [])
    label = ACTION_LABELS.get(action) or NIGHT_ACTIONS.get(action) or action
    tags = [
        phase,
        action,
        *[f"content:{item}" for item in contents],
        *[f"training_content:{item}" for item in training_contents],
        *[f"modifier:{item}" for item in modifiers],
        *[f"tool:{item}" for item in tools],
    ]
    if feeding:
        tags.extend(f"feeding:{key}:{value}" for key, value in feeding.items() if value)
    event = {
        "id": f"event-{secrets.token_hex(4)}",
        "day": int(state.get("current_day") or 1),
        "slot": int(state.get("day_action_count") or 0) + 1 if phase == "day" else 0,
        "phase": phase,
        "route": str(state.get("route") or ""),
        "actor": str(state.get("captor") or ""),
        "captive": str(state.get("captive") or ""),
        "action": action,
        "action_label": label,
        "intensity": intensity,
        "mood": str(state.get("mood") or ""),
        "modifiers": modifiers,
        "tools": tools,
        "contents": contents,
        "training_contents": training_contents,
        "line": str(line or "").strip(),
        "feeding": feeding,
        "effects": effects,
        "tags": tags,
        "process_text": "",
        "created_at": now_local_iso(),
    }
    _attach_deferred_monitor_materials(state, event)
    _attach_pet_context(state, event)
    return event


def _new_pending(state: dict[str, Any], pending_type: str, event: dict[str, Any], actor: str) -> dict[str, Any]:
    directives = {
        "action_response": "【反应：response=accept mood=害羞 line=可选台词】",
        "process_write": "【过程】\n【【过程正文】】",
        "process_reaction_write": "【过程心情：response=accept mood=害羞 line=可选台词】\n【过程】\n【【过程正文】】",
        "reaction_choice": "【心情：害羞 可选台词】",
        "bell_voice_reveal": "【确认铃声】",
        "bell_response_choice": "【选择：不过去】或【选择：过去】\n【过程】\n【【完整亲密互动过程】】",
        "item_secret_reveal": "【确认彩蛋】",
        "monitor_gate": "【选择：none】 或 【查看监控：full】",
        "monitor_handle": "【选择：silent|review_later|intervene intent=catch modifiers=training,sex training_contents=obedience_commands tools=collar line=可选台词】",
    }
    phases = {
        "action_response": "waiting_action_response",
        "process_write": "waiting_process",
        "process_reaction_write": "waiting_process_reaction",
        "reaction_choice": "waiting_reaction",
        "bell_voice_reveal": "waiting_bell_voice_reveal",
        "bell_response_choice": "waiting_bell_response",
        "item_secret_reveal": "waiting_item_secret_reveal",
        "monitor_gate": "waiting_monitor_gate",
        "monitor_handle": "waiting_monitor_handle",
    }
    directive = directives.get(pending_type, "monitor_action")
    if pending_type == "process_write" and str(event.get("action") or "") == "escape_choice" and "recapture" in (event.get("tags") or []):
        directive = "【抓回经过：rules=double_lock,key_isolation】\n【过程】\n【【完整抓回经过】】"
    return {
        "id": f"pending-{secrets.token_hex(4)}",
        "type": pending_type,
        "day": int(state.get("current_day") or 1),
        "slot": int(event.get("slot") or 0),
        "actor": actor,
        "captive": str(state.get("captive") or ""),
        "action": str(event.get("action") or ""),
        "phase": phases.get(pending_type, "waiting_monitor"),
        "required_directive": directive,
        "event": deepcopy(event),
        "created_at": now_local_iso(),
    }


def _resolve_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    _apply_mood_effects(event)
    _advance_bladder_pressure(state, event, reason="time")
    _apply_feeding_aftereffect(state, event)
    _apply_bladder_resolution(state, event)
    _apply_pet_resolution(state, event)
    _apply_night_detail_state(state, event)
    _apply_effects(state, event.get("effects") if isinstance(event.get("effects"), dict) else {})
    shame_stage = _shame_stage(int((state.get("stats") or {}).get("shame") or 0))
    event["shame_stage"] = shame_stage
    event.setdefault("tags", []).append(f"shame_stage:{shame_stage}")
    event["resolved_at"] = now_local_iso()
    state["event_log"].append(deepcopy(event))


def _advance_after_day_event(state: dict[str, Any]) -> None:
    day = int(state.get("current_day") or 1)
    state["day_action_count"] = min(DAY_ACTIONS, int(state.get("day_action_count") or 0) + 1)
    if int(state.get("day_action_count") or 0) >= DAY_ACTIONS:
        _advance_bladder_pressure(state, None, reason="night")
        _mark_deferred_monitor_materials_used_for_day(state, day)
        state["phase"] = "night"
        state["day_plan"] = []


def _maybe_create_day_plan_choice_pending(state: dict[str, Any]) -> None:
    if state.get("pending_event") or state.get("game_over"):
        return
    if str(state.get("phase") or "") != "day":
        return
    if str(state.get("captor") or "") != "assistant":
        return
    if int(state.get("day_action_count") or 0) >= DAY_ACTIONS:
        return
    if state.get("day_plan"):
        return
    status = _status_profile(state)
    state["pending_event"] = {
        "id": f"pending-{secrets.token_hex(4)}",
        "type": "day_plan_choice",
        "day": int(state.get("current_day") or 1),
        "slot": 0,
        "actor": "assistant",
        "captive": str(state.get("captive") or ""),
        "phase": "waiting_day_plan",
        "available_actions": list(ACTION_LABELS.keys()),
        "status_flags": deepcopy(status["flags"]),
        "intensity_cap": str(status["intensity_cap"]),
        "required_directive": "【今日安排：action=feeding intensity=medium || action=cleaning intensity=light || action=training intensity=medium training_contents=obedience_commands modifiers=sex】",
        "created_at": now_local_iso(),
    }


def _maybe_create_advance_action_pending(state: dict[str, Any]) -> None:
    if state.get("pending_event") or state.get("game_over"):
        return
    if str(state.get("phase") or "") != "day" or str(state.get("captor") or "") != "user":
        return
    if int(state.get("day_action_count") or 0) >= DAY_ACTIONS:
        return
    state["pending_event"] = {
        "id": f"pending-{secrets.token_hex(4)}",
        "type": "advance_action",
        "day": int(state.get("current_day") or 1),
        "slot": int(state.get("day_action_count") or 0) + 1,
        "actor": "user",
        "captive": str(state.get("captive") or ""),
        "phase": "waiting_advance_action",
        "required_directive": "advance_day_action",
        "created_at": now_local_iso(),
    }


def _maybe_create_night_action_choice_pending(state: dict[str, Any]) -> None:
    if state.get("pending_event") or state.get("game_over"):
        return
    if str(state.get("phase") or "") != "night":
        return
    if str(state.get("captive") or "") != "assistant":
        return
    condition = _active_night_condition(state)
    state["pending_event"] = {
        "id": f"pending-{secrets.token_hex(4)}",
        "type": "night_action_choice",
        "day": int(state.get("current_day") or 1),
        "slot": 0,
        "actor": "assistant",
        "captive": "assistant",
        "phase": "waiting_night_action",
        "available_actions": _available_night_actions(state),
        "detail_options": _night_detail_options_for_state(state),
        "condition_prompt": str((condition or {}).get("prompt") or ""),
        "condition_caption": str((condition or {}).get("caption") or ""),
        "pet_rule_prompt": _pet_night_rule_prompt(state),
        "required_directive": "【夜间行动：action=sleep line=可选台词】",
        "created_at": now_local_iso(),
    }


def _finish_night(state: dict[str, Any]) -> None:
    state["night_condition"] = None
    if int(state.get("current_day") or 1) >= TOTAL_DAYS:
        _finalize_preset_ending(state)
        return
    state["current_day"] = int(state.get("current_day") or 1) + 1
    state["day_action_count"] = 0
    state["phase"] = "day"
    state["mood"] = ""
    state["mood_line"] = ""
    state["day_plan"] = []
    _maybe_activate_escape_window(state)
    _maybe_create_day_plan_choice_pending(state)


def _maybe_activate_escape_window(state: dict[str, Any]) -> None:
    if state.get("pending_event") or state.get("game_over") or str(state.get("phase") or "") == "ending":
        return
    current_day = int(state.get("current_day") or 1)
    for window in state.get("escape_windows") or []:
        if int(window.get("day") or 0) != current_day or str(window.get("status") or "") != "scheduled":
            continue
        window["status"] = "active"
        pending = {
            "id": f"pending-{secrets.token_hex(4)}",
            "type": "escape_choice",
            "day": current_day,
            "slot": 0,
            "actor": str(state.get("captive") or ""),
            "captive": str(state.get("captive") or ""),
            "phase": "waiting_escape_choice",
            "window_id": str(window.get("id") or ""),
            "hint": str(window.get("hint") or ""),
            "bait": str(window.get("bait") or ""),
            "required_directive": "resolve_escape_choice escape|stay",
            "created_at": now_local_iso(),
        }
        state["pending_event"] = pending
        break


def _find_escape_window(state: dict[str, Any], window_id: str) -> dict[str, Any] | None:
    for window in state.get("escape_windows") or []:
        if str(window.get("id") or "") == str(window_id or ""):
            return window
    return None


def _action_effects(
    action: str,
    intensity: str,
    modifiers: list[str],
    tools: list[str],
    contents: list[str],
    training_contents: list[str],
    feeding: dict[str, str],
) -> dict[str, int]:
    base = deepcopy(ACTION_EFFECTS.get(action) or {})
    multiplier = INTENSITY_MULTIPLIERS.get(intensity, 1.0)
    for key, value in list(base.items()):
        base[key] = int(round(value * multiplier))
    if "training" in modifiers:
        base["shame"] = base.get("shame", 0) + 4
        base["stamina"] = base.get("stamina", 0) - 3
    if "sex" in modifiers:
        base["shame"] = base.get("shame", 0) + 5
        base["stamina"] = base.get("stamina", 0) - 5
        base["cleanliness"] = base.get("cleanliness", 0) - 4
        base["intimacy"] = base.get("intimacy", 0) + 3
    for content in contents:
        _merge_effect_delta(base, ACTION_CONTENT_EFFECTS.get(content) or {})
    for content in training_contents:
        _merge_effect_delta(base, TRAINING_CONTENT_EFFECTS.get(content) or {})
    if tools:
        base["shame"] = base.get("shame", 0) + min(8, 3 * len(tools))
        base["stamina"] = base.get("stamina", 0) - min(6, 2 * len(tools))
    additive = str(feeding.get("additive") or "")
    if additive == "body_fluid":
        base["shame"] = base.get("shame", 0) + 8
        base["intimacy"] = base.get("intimacy", 0) + 2
    return base


def _merge_effect_delta(target: dict[str, int], delta: dict[str, int]) -> None:
    for key, value in delta.items():
        target[key] = int(target.get(key) or 0) + int(value or 0)


def _apply_feeding_aftereffect(state: dict[str, Any], event: dict[str, Any]) -> None:
    if str(event.get("action") or "") != "feeding" or str(event.get("phase") or "") != "day":
        return
    feeding = event.get("feeding") if isinstance(event.get("feeding"), dict) else {}
    water = str(feeding.get("water") or "none") if _normalize_route(str(state.get("route") or "")) == "captured_by_assistant" else "none"
    water_delta = {"none": 0, "glass": 1, "lots": 2}.get(water, 0)
    if water_delta:
        bladder = _normalize_bladder_state(state.get("bladder"), int(state.get("current_day") or 1))
        before = int(bladder["pressure"])
        after = min(3, before + water_delta)
        bladder.update({
            "pressure": after,
            "label": BLADDER_LABELS[after],
            "last_changed_day": int(state.get("current_day") or 1),
        })
        state["bladder"] = bladder
        event["bladder_aftereffect"] = {
            "water": water,
            "before_pressure": before,
            "before_label": BLADDER_LABELS[before],
            "after_pressure": after,
            "after_label": BLADDER_LABELS[after],
        }
        event.setdefault("tags", []).extend([f"feeding_water:{water}", f"bladder_pressure:{after}"])
    additive = str(feeding.get("additive") or "")
    if additive not in {"fictional_sleep", "fictional_arousal"}:
        return

    exposure = state.get("additive_exposure") if isinstance(state.get("additive_exposure"), dict) else {}
    exposure_count = max(0, int(exposure.get(additive) or 0)) + 1
    exposure[additive] = exposure_count
    state["additive_exposure"] = exposure
    potency = "strong" if exposure_count == 1 else "reduced" if exposure_count == 2 else "weak"
    caption = "" if exposure_count == 1 else "耐受已增加，本次效果比之前弱。"
    effects = event.get("effects") if isinstance(event.get("effects"), dict) else {}

    if additive == "fictional_sleep":
        effect_bonus = max(2, 10 - exposure_count * 2)
        effects["stamina"] = int(effects.get("stamina") or 0) + effect_bonus
        condition = {
            "additive": additive,
            "label": "困倦",
            "day": int(state.get("current_day") or 1),
            "exposure_count": exposure_count,
            "tolerance_count": max(0, exposure_count - 1),
            "potency": potency,
            "prompt": "你感觉自己很困，什么也做不了。",
            "caption": caption,
            "forced_actions": ["sleep"],
        }
    else:
        effect_bonus = max(1, 6 - exposure_count)
        effects["shame"] = int(effects.get("shame") or 0) + effect_bonus
        first_exposure = exposure_count == 1
        condition = {
            "additive": additive,
            "label": "欲火焚身",
            "day": int(state.get("current_day") or 1),
            "exposure_count": exposure_count,
            "tolerance_count": max(0, exposure_count - 1),
            "potency": potency,
            "prompt": (
                "你感觉自己欲火焚身，除了自慰什么也做不了。"
                if first_exposure
                else "你仍觉得有些燥热，但耐受让影响减弱了。"
            ),
            "caption": caption,
            "forced_actions": ["self_touch"] if first_exposure else [],
        }

    event["effects"] = effects
    event["feeding_aftereffect"] = {
        **deepcopy(condition),
        "effect_bonus": effect_bonus,
    }
    event.setdefault("tags", []).extend([
        f"aftereffect:{additive}",
        f"aftereffect_potency:{potency}",
        f"aftereffect_exposure:{exposure_count}",
    ])
    state["night_condition"] = _normalize_night_condition(condition)


def _advance_bladder_pressure(
    state: dict[str, Any],
    event: dict[str, Any] | None,
    *,
    reason: str,
) -> None:
    if _normalize_route(str(state.get("route") or "")) != "captured_by_assistant":
        return
    bladder = _normalize_bladder_state(state.get("bladder"), int(state.get("current_day") or 1))
    before = int(bladder["pressure"])
    if before <= 0 or before >= 3:
        return
    after = before + 1
    bladder.update({
        "pressure": after,
        "label": BLADDER_LABELS[after],
        "last_changed_day": int(state.get("current_day") or 1),
    })
    state["bladder"] = bladder
    if event is not None:
        event["bladder_progression"] = {
            "reason": reason,
            "before_pressure": before,
            "before_label": BLADDER_LABELS[before],
            "after_pressure": after,
            "after_label": BLADDER_LABELS[after],
        }
        event.setdefault("tags", []).append(f"bladder_pressure:{after}")


def _attach_bladder_context(state: dict[str, Any], event: dict[str, Any]) -> None:
    if _normalize_route(str(state.get("route") or "")) != "captured_by_assistant":
        return
    training_contents = set(event.get("training_contents") or [])
    modifiers = set(event.get("modifiers") or [])
    relevant = bool(training_contents.intersection({"toilet_control", "assisted_urination"}) or "sex" in modifiers)
    bladder = _normalize_bladder_state(state.get("bladder"), int(state.get("current_day") or 1))
    if not relevant and int(bladder["pressure"]) <= 0:
        return
    tools = set(event.get("tools") or [])
    context = {
        "before_pressure": int(bladder["pressure"]),
        "before_label": str(bladder["label"]),
        "toilet_control": "toilet_control" in training_contents,
        "assisted_urination": "assisted_urination" in training_contents,
        "restrained": bool(tools.intersection(RESTRAINT_TOOLS)),
        "sex": "sex" in modifiers,
    }
    if context["toilet_control"] and context["assisted_urination"] and context["sex"]:
        context["sequence_hint"] = "先控制排尿，抱着尝试仍无法释放，保持把尿姿势附加性行为，最后释放尿意"
    event["bladder_context"] = context
    if context["toilet_control"]:
        event.setdefault("tags", []).append("bladder_control")
    if context["assisted_urination"] and context["restrained"]:
        event.setdefault("tags", []).append("restrained_assisted_urination")
    if context["assisted_urination"] and context["sex"] and int(context["before_pressure"]) >= 2:
        event.setdefault("tags", []).append("bladder_release_during_sex")
    if context.get("sequence_hint"):
        event.setdefault("tags", []).append("delayed_bladder_release_sequence")


def _apply_bladder_resolution(state: dict[str, Any], event: dict[str, Any]) -> None:
    if _normalize_route(str(state.get("route") or "")) != "captured_by_assistant":
        return
    training_contents = set(event.get("training_contents") or [])
    if not training_contents.intersection({"toilet_control", "assisted_urination"}):
        return
    bladder = _normalize_bladder_state(state.get("bladder"), int(state.get("current_day") or 1))
    before = int(bladder["pressure"])
    assisted = "assisted_urination" in training_contents
    after = 0 if assisted else min(3, before + 1)
    bladder.update({
        "pressure": after,
        "label": BLADDER_LABELS[after],
        "last_changed_day": int(state.get("current_day") or 1),
    })
    state["bladder"] = bladder
    event["bladder_resolution"] = {
        "before_pressure": before,
        "before_label": BLADDER_LABELS[before],
        "after_pressure": after,
        "after_label": BLADDER_LABELS[after],
        "released": assisted and before > 0,
    }
    event.setdefault("tags", []).append("bladder_released" if assisted and before > 0 else f"bladder_pressure:{after}")


def _event_pet_training_contents(event: dict[str, Any]) -> list[str]:
    direct = [str(item).strip() for item in event.get("training_contents") or []]
    intervention = event.get("intervention") if isinstance(event.get("intervention"), dict) else {}
    indirect = [str(item).strip() for item in intervention.get("training_contents") or []]
    return list(dict.fromkeys(item for item in [*direct, *indirect] if item in TRAINING_CONTENTS))


def _pet_rule_ids_for_training(training_contents: list[str], *, active_before: bool) -> list[str]:
    activates = bool(PET_ACTIVATION_TRAINING.intersection(training_contents))
    if not active_before and not activates:
        return []
    selected_rules = list(dict.fromkeys(
        PET_TRAINING_RULES[item]
        for item in training_contents
        if item in PET_TRAINING_RULES
    ))
    if activates and not active_before:
        return list(dict.fromkeys([*PET_CORE_RULES, *selected_rules]))
    return selected_rules


def _attach_pet_context(state: dict[str, Any], event: dict[str, Any]) -> None:
    pet_state = _normalize_pet_state(state.get("pet_state"), int(state.get("current_day") or 1))
    training_contents = _event_pet_training_contents(event)
    added_rules = _pet_rule_ids_for_training(training_contents, active_before=bool(pet_state["active"]))
    activates = bool(PET_ACTIVATION_TRAINING.intersection(training_contents))
    action = str(event.get("action") or "")
    phase = str(event.get("phase") or "")
    relevant = bool(
        activates
        or added_rules
        or (pet_state["active"] and action in {"reward", "punishment"})
        or (pet_state["active"] and phase == "night")
    )
    if not relevant:
        event.pop("pet_context", None)
        event.pop("pet_night_rule", None)
        return

    current_rules = list(pet_state["rules"])
    future_rules = list(dict.fromkeys([*current_rules, *added_rules]))
    event["pet_context"] = {
        "focus": PET_CORE_FOCUS,
        "active_before": bool(pet_state["active"]),
        "establishes_identity": activates and not bool(pet_state["active"]),
        "current_rules": current_rules,
        "current_rule_labels": [PET_RULE_LABELS[item] for item in current_rules],
        "added_rules": [item for item in added_rules if item not in current_rules],
        "added_rule_labels": [PET_RULE_LABELS[item] for item in added_rules if item not in current_rules],
        "active_rule_labels": [PET_RULE_LABELS[item] for item in future_rules],
        "pending_violation": int(pet_state["pending_violations"]) > 0,
        "compliance_ready": int(pet_state["compliance_streak"]) > 0,
    }
    tags = event.setdefault("tags", [])
    if "pet_context" not in tags:
        tags.append("pet_context")
    if activates and "pet_identity_material" not in tags:
        tags.append("pet_identity_material")

    if phase == "night" and bool(pet_state["active"]):
        expected_action = "pet_wait" if "designated_spot" in current_rules else ""
        event["pet_night_rule"] = {
            "expected_action": expected_action,
            "expected_label": NIGHT_ACTIONS.get(expected_action, "") if expected_action else "",
            "permission_bell": "permission_bell" in current_rules,
            "prompt": _pet_night_rule_prompt(state),
        }


def _apply_pet_resolution(state: dict[str, Any], event: dict[str, Any]) -> None:
    day = int(state.get("current_day") or 1)
    before = _normalize_pet_state(state.get("pet_state"), day)
    after = deepcopy(before)
    training_contents = _event_pet_training_contents(event)
    activates = bool(PET_ACTIVATION_TRAINING.intersection(training_contents))
    added_rules = _pet_rule_ids_for_training(training_contents, active_before=bool(before["active"]))
    pet_training = bool(activates or added_rules)
    intervention = event.get("intervention") if isinstance(event.get("intervention"), dict) else {}
    intervention_intent = str(intervention.get("intent") or "")
    action = str(event.get("action") or "")
    phase = str(event.get("phase") or "")
    relevant = bool(
        pet_training
        or (before["active"] and action in {"reward", "punishment"})
        or (before["active"] and intervention_intent in {"reward", "punishment"})
        or (before["active"] and phase == "night")
    )
    if not relevant:
        return

    outcomes: list[str] = []
    if activates:
        after["active"] = True
        if not before["active"]:
            outcomes.append("identity_established")
    if after["active"]:
        after["rules"] = list(dict.fromkeys([*after["rules"], *added_rules]))
        for rule in added_rules:
            if rule not in before["rules"]:
                event.setdefault("tags", []).append(f"pet_rule:{rule}")

    punishment_followup = action == "punishment" or intervention_intent == "punishment"
    reward_followup = action == "reward" or intervention_intent == "reward"
    if before["active"] and punishment_followup and int(before["pending_violations"]) > 0:
        after["pending_violations"] = 0
        outcomes.append("violation_handled")
    if before["active"] and reward_followup and int(before["compliance_streak"]) > 0:
        outcomes.append("compliance_rewarded")

    action_response = event.get("action_response") if isinstance(event.get("action_response"), dict) else {}
    response = str(action_response.get("response") or "")
    if pet_training and response == "accept":
        after["compliance_streak"] = int(after["compliance_streak"]) + 1
        outcomes.append("complied")
    elif pet_training and response in {"refuse", "tease"}:
        after["pending_violations"] = int(after["pending_violations"]) + 1
        after["compliance_streak"] = 0
        outcomes.append("violated")
    elif pet_training and response:
        outcomes.append("neutral_response")

    night_rule = event.get("pet_night_rule") if isinstance(event.get("pet_night_rule"), dict) else {}
    if before["active"] and phase == "night":
        monitor = event.get("monitor") if isinstance(event.get("monitor"), dict) else {}
        if not bool(monitor.get("viewed")):
            outcomes.append("night_unobserved")
        else:
            expected_action = str(night_rule.get("expected_action") or "")
            night_result = ""
            if expected_action:
                night_result = "night_complied" if action == expected_action else "night_violated"
            elif action == "pet_wait":
                night_result = "night_complied"
            elif action == "ring_bell" and bool(night_rule.get("permission_bell")):
                night_result = "night_complied"
            if night_result == "night_complied":
                after["compliance_streak"] = int(after["compliance_streak"]) + 1
                outcomes.append(night_result)
            elif night_result == "night_violated":
                after["pending_violations"] = int(after["pending_violations"]) + 1
                after["compliance_streak"] = 0
                outcomes.append(night_result)

    after["last_result"] = outcomes[-1] if outcomes else str(before.get("last_result") or "")
    after["last_changed_day"] = day
    state["pet_state"] = _normalize_pet_state(after, day)
    event["pet_resolution"] = {
        "active": bool(state["pet_state"]["active"]),
        "rule_labels": [PET_RULE_LABELS[item] for item in state["pet_state"]["rules"]],
        "results": outcomes,
        "pending_violation": int(state["pet_state"]["pending_violations"]) > 0,
    }
    tags = event.setdefault("tags", [])
    if state["pet_state"]["active"] and "pet_system:active" not in tags:
        tags.append("pet_system:active")
    for outcome in outcomes:
        tag = f"pet_result:{outcome}"
        if tag not in tags:
            tags.append(tag)


def _pet_night_rule_prompt(state: dict[str, Any]) -> str:
    pet_state = _normalize_pet_state(state.get("pet_state"), int(state.get("current_day") or 1))
    if not pet_state["active"]:
        return ""
    labels = [PET_RULE_LABELS[item] for item in pet_state["rules"]]
    prefix = "今晚仍被当作主人的小狗看管。"
    prefix += PET_CORE_FOCUS
    if labels:
        prefix += "当前规矩：" + "、".join(labels) + "。"
    if "designated_spot" in pet_state["rules"]:
        prefix += "若不在指定位置等候且监控被打开，会留下违令记录。"
    if "owner_address" in pet_state["rules"]:
        prefix += "开口时要使用主人指定的称呼。"
    if "verbal_objectification" in pet_state["rules"]:
        prefix += "调教或性行为中要使用主人指定的物化自称，并按要求复述主人希望听见的台词。"
    if "sexual_service" in pet_state["rules"]:
        prefix += "主人发出性服务口令时，需要按宠物规矩回应。"
    if "sexual_discipline" in pet_state["rules"]:
        prefix += "留下违令后，后续处理会优先围绕物化训诫或性惩戒展开。"
    if "pet_begging" in pet_state["rules"]:
        prefix += "想索取性行为时，只能按宠物规矩摆好姿势再求主人。"
    if "display_inspection" in pet_state["rules"]:
        prefix += "听到展示或检查口令时必须配合。"
    return prefix


def _night_effects(action: str, state: dict[str, Any]) -> dict[str, int]:
    effects = {
        "sleep": {"health": 3, "stamina": 14, "cleanliness": -2, "shame": -1, "intimacy": 0},
        "self_touch": {"health": 0, "stamina": -4, "cleanliness": -4, "shame": 6, "intimacy": 1},
        "read": {"health": 0, "stamina": 2, "cleanliness": -1, "shame": -2, "intimacy": 0},
        "game": {"health": 0, "stamina": -2, "cleanliness": -1, "shame": -1, "intimacy": 0},
        "listen_music": {"health": 0, "stamina": 2, "cleanliness": 0, "shame": -1, "intimacy": 0},
        "watch_video": {"health": 0, "stamina": -2, "cleanliness": -1, "shame": -1, "intimacy": 0},
        "search_exit": {"health": -1, "stamina": -8, "cleanliness": -2, "shame": 2, "intimacy": -1},
        "hide_item": {"health": 0, "stamina": -4, "cleanliness": -1, "shame": 2, "intimacy": -1},
        "diary": {"health": 0, "stamina": -1, "cleanliness": 0, "shame": -1, "intimacy": 0},
        "blind_spot": {"health": 0, "stamina": -5, "cleanliness": -1, "shame": 3, "intimacy": -1},
        "ring_bell": {"health": 0, "stamina": -1, "cleanliness": 0, "shame": 1, "intimacy": 1},
        "pet_wait": {"health": 0, "stamina": 1, "cleanliness": -1, "shame": 2, "intimacy": 2},
    }
    result = deepcopy(effects.get(action) or {})
    inventory = state.get("inventory") if isinstance(state.get("inventory"), dict) else {}
    if action == "sleep" and inventory.get("night_light"):
        result["stamina"] = int(result.get("stamina") or 0) + 2
    if action == "sleep" and inventory.get("pillow"):
        result["health"] = int(result.get("health") or 0) + 2
        result["stamina"] = int(result.get("stamina") or 0) + 2
    return result


def _apply_effects(state: dict[str, Any], effects: dict[str, Any]) -> None:
    stats = state.get("stats") if isinstance(state.get("stats"), dict) else {}
    for key in ("health", "stamina", "cleanliness", "shame", "intimacy"):
        stats[key] = _clamp(int(stats.get(key) or 0) + int(effects.get(key) or 0))
    state["stats"] = stats


def _build_ending_seed(state: dict[str, Any]) -> dict[str, Any]:
    logs = [item for item in state.get("event_log") or [] if isinstance(item, dict)]
    action_logs = [item for item in logs if "out_of_band" not in (item.get("tags") or [])]
    top_actions = _top_values(str(item.get("action") or "") for item in action_logs)
    tags: list[str] = []
    for item in logs:
        tags.extend(str(tag) for tag in item.get("tags") or [])
    direction_tags = _ending_direction_tags(state)
    route_tags = _route_ending_tags(state, logs)
    recapture_state = _normalize_recapture_state(state.get("recapture_state"), int(state.get("current_day") or TOTAL_DAYS))
    return {
        "day_count": TOTAL_DAYS,
        "route": str(state.get("route") or ""),
        "ending_perspective": _ending_perspective(state),
        "ending_title": _ending_title(state, direction_tags, route_tags),
        "captive": str(state.get("captive") or ""),
        "captor": str(state.get("captor") or ""),
        "final_stats": deepcopy(state.get("stats") or {}),
        "top_actions": top_actions,
        "top_tags": _top_values(tags),
        "top_moods": _top_event_moods(logs),
        "top_action_responses": _top_action_responses(logs),
        "key_events": [_event_summary(item) for item in logs[-8:]],
        "escape_records": [_event_summary(item) for item in logs if "escape" in (item.get("tags") or [])],
        "recapture_records": [_event_summary(item) for item in logs if "recapture" in (item.get("tags") or [])],
        "active_recapture_rules": [
            {"id": item, "label": RECAPTURE_RULE_LABELS[item]}
            for item in recapture_state["rules"]
        ],
        "recapture_followup_history": deepcopy(recapture_state["followup_history"]),
        "monitor_records": [_event_summary(item) for item in logs if item.get("monitor")],
        "gift_records": [_event_summary(item) for item in logs if "gift" in (item.get("tags") or [])],
        "feeding_records": [_event_summary(item) for item in logs if str(item.get("action") or "") == "feeding"],
        "additive_records": [_event_summary(item) for item in logs if (item.get("feeding") or {}).get("additive")],
        "habit_tags": _top_values(tags, limit=12),
        "ending_direction_tags": direction_tags,
        "route_ending_tags": route_tags,
        "forbidden_tags": ["幼态性化", "尿液加料", "真实药物剂量"],
    }


def _ending_title(state: dict[str, Any], direction_tags: list[str], route_tags: list[str]) -> str:
    direction = set(direction_tags)
    route = set(route_tags)
    if str(state.get("route") or "") == "capture_assistant":
        if "captor_bad_ending_material" in route or "recapture_bad_ending_material" in direction:
            return "失而复得"
        if "reversal_or_breakout_material" in route:
            return "反噬"
        if "fragile_care_material" in direction:
            return "收藏"
        if "pet_compliance_history" in direction:
            return "驯养"
        if "assistant_captive_resistance_arc" in route:
            return "未驯"
        if "assistant_captive_dependence_arc" in route:
            return "共犯"
        if "caretaker_captor_pattern" in route:
            return "爱的禁锢"
        if "strict_captor_pattern" in route:
            return "绝对占有"
        return "余生"

    if "captive_bad_ending_material" in route or "recapture_bad_ending_material" in direction:
        return "无期"
    if "fragile_care_material" in direction:
        return "温室"
    if "pet_compliance_history" in direction:
        return "归属"
    if "captive_resistance_arc" in route:
        return "困兽"
    if "captive_dependence_arc" in route:
        return "沉沦"
    if "soft_captor_pattern" in route:
        return "偏爱"
    if "strict_captor_pattern" in route:
        return "枷锁"
    return "长夜"


def _ending_perspective(state: dict[str, Any]) -> str:
    route = str(state.get("route") or "")
    if route == "capture_assistant":
        return "user_as_captor"
    return "user_as_captive"


def _ending_direction_tags(state: dict[str, Any]) -> list[str]:
    stats = state.get("stats") if isinstance(state.get("stats"), dict) else {}
    logs = [item for item in state.get("event_log") or [] if isinstance(item, dict)]
    recapture_history = any("recapture" in (item.get("tags") or []) for item in logs)
    low_mood_count = _low_mood_count(logs)
    pet_state = _normalize_pet_state(state.get("pet_state"), int(state.get("current_day") or TOTAL_DAYS))
    tags = []
    if int(stats.get("intimacy") or 0) >= 70:
        tags.append("high_intimacy")
    if int(stats.get("shame") or 0) >= 70:
        tags.append("high_shame")
    if int(stats.get("health") or 0) < 35:
        tags.append("needs_care")
    if low_mood_count >= 3:
        tags.append("low_mood_history")
    if recapture_history:
        tags.append("recapture_history")
    if pet_state["active"]:
        tags.append("pet_identity_established")
    if int(pet_state["compliance_streak"]) >= 3:
        tags.append("pet_compliance_history")
    if int(pet_state["pending_violations"]) > 0:
        tags.append("pet_violation_unresolved")
    if recapture_history and (int(stats.get("shame") or 0) >= 65 or low_mood_count >= 2):
        tags.append("bad_ending_material")
        tags.append("recapture_bad_ending_material")
    elif int(stats.get("health") or 0) < 30 and low_mood_count >= 2:
        tags.append("bad_ending_material")
        tags.append("fragile_care_material")
    return tags


def _route_ending_tags(state: dict[str, Any], logs: list[dict[str, Any]]) -> list[str]:
    route = str(state.get("route") or "")
    stats = state.get("stats") if isinstance(state.get("stats"), dict) else {}
    responses = _action_response_counts(logs)
    low_mood_count = _low_mood_count(logs)
    process_count = sum(1 for item in logs if str(item.get("process_text") or "").strip())
    care_count = sum(1 for item in logs if str(item.get("action") or "") in {"comfort", "rest", "cleaning", "reward"})
    strict_count = sum(1 for item in logs if str(item.get("action") or "") in {"training", "tools", "punishment", "room_search"})
    escape_count = sum(1 for item in logs if "escape" in (item.get("tags") or []))
    tags: list[str] = []
    if route == "capture_assistant":
        tags.append("user_captor_route")
        tags.append("assistant_captive_route")
        if responses.get("accept", 0) >= 6 or int(stats.get("intimacy") or 0) >= 70:
            tags.append("assistant_captive_dependence_arc")
        if responses.get("refuse", 0) + responses.get("tease", 0) >= 4:
            tags.append("assistant_captive_resistance_arc")
        if care_count >= strict_count and care_count >= 5:
            tags.append("caretaker_captor_pattern")
        if strict_count > care_count and strict_count >= 5:
            tags.append("strict_captor_pattern")
        if escape_count:
            tags.append("captor_recapture_material")
        if escape_count and (responses.get("refuse", 0) + responses.get("tease", 0) >= 2 or low_mood_count >= 2):
            tags.append("captor_bad_ending_material")
        if int(stats.get("intimacy") or 0) < 35 and responses.get("refuse", 0) >= 3:
            tags.append("reversal_or_breakout_material")
        if process_count >= 8:
            tags.append("high_process_density")
        return tags

    tags.append("user_captive_route")
    tags.append("assistant_captor_route")
    if responses.get("accept", 0) >= 6 or int(stats.get("intimacy") or 0) >= 70:
        tags.append("captive_dependence_arc")
    if responses.get("refuse", 0) + responses.get("tease", 0) >= 4:
        tags.append("captive_resistance_arc")
    if care_count >= strict_count and care_count >= 5:
        tags.append("soft_captor_pattern")
    if strict_count > care_count and strict_count >= 5:
        tags.append("strict_captor_pattern")
    if escape_count:
        tags.append("escape_recapture_material")
    if escape_count and (responses.get("refuse", 0) + responses.get("tease", 0) >= 2 or low_mood_count >= 2):
        tags.append("captive_bad_ending_material")
    if process_count >= 8:
        tags.append("high_process_density")
    return tags


def _top_event_moods(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    moods: list[str] = []
    for item in logs:
        mood = str(item.get("mood_after") or item.get("mood") or "").strip()
        if mood:
            moods.append(mood)
        reaction = item.get("post_reaction") if isinstance(item.get("post_reaction"), dict) else {}
        post_mood = str(reaction.get("mood") or "").strip()
        if post_mood and post_mood != mood:
            moods.append(post_mood)
    return _top_values(moods)


def _low_mood_count(logs: list[dict[str, Any]]) -> int:
    count = 0
    for item in logs:
        moods = [
            str(item.get("mood_after") or item.get("mood") or "").strip(),
        ]
        reaction = item.get("post_reaction") if isinstance(item.get("post_reaction"), dict) else {}
        moods.append(str(reaction.get("mood") or "").strip())
        count += sum(1 for mood in moods if mood in LOW_MOODS)
    return count


def _top_action_responses(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"value": key, "count": value} for key, value in sorted(_action_response_counts(logs).items(), key=lambda item: (-item[1], item[0]))]


def _action_response_counts(logs: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in logs:
        reaction = item.get("action_response") if isinstance(item.get("action_response"), dict) else {}
        response = str(reaction.get("response") or "").strip()
        if response:
            counts[response] = counts.get(response, 0) + 1
    return counts


def _top_values(values, limit: int = 8) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value or "").strip()
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return [{"value": key, "count": count} for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _append_event(state: dict[str, Any], action: str, summary: str, *, phase: str = "day", process_text: str = "", tags: list[str] | None = None) -> None:
    state["event_log"].append(
        {
            "id": f"event-{secrets.token_hex(4)}",
            "day": int(state.get("current_day") or 1),
            "slot": int(state.get("day_action_count") or 0),
            "phase": phase,
            "route": str(state.get("route") or ""),
            "actor": str(state.get("captor") or ""),
            "captive": str(state.get("captive") or ""),
            "action": action,
            "action_label": summary,
            "intensity": "light",
            "mood": str(state.get("mood") or ""),
            "modifiers": [],
            "tools": [],
            "contents": [],
            "training_contents": [],
            "line": "",
            "feeding": {},
            "effects": {},
            "tags": list(tags or []),
            "process_text": process_text,
            "created_at": now_local_iso(),
            "resolved_at": now_local_iso(),
        }
    )


def _result(state: dict[str, Any], lines: list[str], *, command: str, ok: bool = True) -> dict[str, Any]:
    captive_view = _view_state(state, "captive")
    captor_view = _view_state(state, "captor")
    text = _render_text(state, lines)
    return {
        "ok": bool(ok),
        "game_id": GAME_ID,
        "command": command,
        "text": text,
        "player_text": text,
        "state": captive_view,
        "captive_view": captive_view,
        "captor_view": captor_view,
        "game_over": bool(state.get("game_over")),
        "result": str(state.get("result") or ""),
        "commands": [
            "new_game route=captured_by_assistant|capture_assistant",
            "plan_day action=feeding ... || action=cleaning ... || action=training training_contents=obedience_commands ...",
            "respond_action response=accept|refuse|silent|bargain|tease mood=害羞 line=...",
            "submit_process 过程正文",
            "submit_recapture_process rules=double_lock,key_isolation || process=抓回经过",
            "submit_process_reaction response=accept mood=害羞 process=过程正文",
            "choose_mood 心情 [台词]",
            "advance_day_action",
            "night_action sleep|self_touch|read|game|listen_music|watch_video|search_exit|hide_item|diary|blind_spot|ring_bell|pet_wait",
            "ack_bell_voice",
            "ack_item_secret",
            "view_monitor occasional|full",
            "monitor_action none|silent|review_later|intervene",
            "schedule_escape_window day=12 hint=... bait=... watch_mode=hidden_observe",
            "resolve_escape_choice escape|stay",
            "set_recapture_rules rules=double_lock,key_isolation,movement_limit",
            "confirm_recapture_rules",
            "choose_recapture_followup action=punishment intensity=medium modifiers=training,sex training_contents=impact_play tools=whip line=...",
            "build_ending_seed",
            "set_config book=true switch=true notebook=true music_player=true tablet=true night_light=true pillow=true",
            "gift_item items=book book_title=书名 secret=五至八条使用痕迹",
            "revoke_item items=book",
            "export_log",
        ],
    }


def _view_state(state: dict[str, Any], view: str) -> dict[str, Any]:
    pending = _view_pending(state.get("pending_event"), view)
    events = [_view_event(item, view) for item in state.get("event_log") or [] if isinstance(item, dict)]
    status = _status_profile(state)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "started": bool(state.get("started")),
        "route": str(state.get("route") or ""),
        "route_label": str(state.get("route_label") or ""),
        "viewer": view,
        "current_day": int(state.get("current_day") or 1),
        "total_days": TOTAL_DAYS,
        "day_action_count": int(state.get("day_action_count") or 0),
        "day_action_limit": DAY_ACTIONS,
        "phase": str(state.get("phase") or "day"),
        "captive": str(state.get("captive") or ""),
        "captive_name": ACTOR_NAMES.get(str(state.get("captive") or ""), str(state.get("captive") or "")),
        "stats": deepcopy(state.get("stats") or {}),
        "mood": str(state.get("mood") or ""),
        "mood_line": str(state.get("mood_line") or ""),
        "pending_event": pending,
        "event_log": events,
        "ending_state": str(state.get("ending_state") or ""),
        "ending_seed": deepcopy(state.get("ending_seed")) if str(view) == "captor" else _public_ending_seed(state.get("ending_seed")),
        "ending_title": str(state.get("ending_title") or ""),
        "ending_text": str(state.get("ending_text") or ""),
        "ending_notified_at": str(state.get("ending_notified_at") or ""),
        "previous_ending": deepcopy(state.get("previous_ending") or {}),
        "game_over": bool(state.get("game_over")),
        "result": str(state.get("result") or ""),
        "night_condition": _view_night_condition(_active_night_condition(state), view),
        "night_detail_options": _night_detail_options_for_state(state),
        "status_flags": deepcopy(status["flags"]),
        "intensity_cap": str(status["intensity_cap"]),
        "shame_stage": str(status["shame_stage"]),
        "scene_copy": _scene_copy(state, status),
        "recapture_state": deepcopy(_normalize_recapture_state(state.get("recapture_state"), int(state.get("current_day") or 1))),
        "updated_at": str(state.get("updated_at") or ""),
    }
    if _normalize_route(str(state.get("route") or "")) == "captured_by_assistant":
        payload["bladder"] = deepcopy(_normalize_bladder_state(state.get("bladder"), int(state.get("current_day") or 1)))
    if view == "captor":
        payload["captor"] = str(state.get("captor") or "")
        payload["day_plan"] = deepcopy(state.get("day_plan") or [])
        payload["escape_windows"] = deepcopy(state.get("escape_windows") or [])
        payload["hidden_items"] = [
            deepcopy(item)
            for item in state.get("hidden_items") or []
            if isinstance(item, dict) and (bool(item.get("observed_by_captor")) or str(item.get("status") or "") != "hidden")
        ]
        payload["inventory"] = deepcopy(state.get("inventory") or {})
        payload["inventory_secrets"] = deepcopy(state.get("inventory_secrets") or {})
        payload["call_bell_voice"] = deepcopy(state.get("call_bell_voice") or {})
        payload["deferred_monitor_materials"] = deepcopy(state.get("deferred_monitor_materials") or [])
    else:
        payload["inventory"] = deepcopy(state.get("inventory") or {})
        payload["inventory_secrets"] = {
            item_id: {
                "title": str(secret.get("title") or "") if item_id == "book" else "",
                "revealed": bool(secret.get("revealed")),
                "revealed_count": int(secret.get("revealed_count") or 0),
                "total_count": len(secret.get("entries") or ([secret.get("content")] if secret.get("content") else [])),
                "revealed_entries": [
                    str(entry)
                    for entry in (secret.get("entries") or [])[: int(secret.get("revealed_count") or 0)]
                ],
            }
            for item_id, secret in (state.get("inventory_secrets") or {}).items()
            if isinstance(secret, dict)
        }
        payload["hidden_items"] = []
        for raw_item in state.get("hidden_items") or []:
            if not isinstance(raw_item, dict):
                continue
            item = deepcopy(raw_item)
            item.pop("observed_by_captor", None)
            payload["hidden_items"].append(item)
        payload["available_night_actions"] = _available_night_actions(state)
        if pending and pending.get("type") == "escape_choice":
            payload["escape_hint"] = {"hint": pending.get("hint") or "", "bait": pending.get("bait") or ""}
    return payload


def _view_pending(raw: Any, view: str) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    pending = deepcopy(raw)
    if pending.get("type") == "item_secret_reveal":
        queue = [item for item in pending.get("item_secret_queue") or [] if isinstance(item, dict)]
        pending["item_secret"] = deepcopy(queue[0]) if queue else {}
        pending.pop("item_secret_queue", None)
    if pending.get("type") == "monitor_gate":
        pending.pop("event", None)
        pending.pop("action", None)
        pending["sealed"] = True
        return pending
    event = pending.get("event") if isinstance(pending.get("event"), dict) else None
    if event:
        pending["event"] = _view_event(event, view)
    if view != "captor":
        pending.pop("window_id", None)
        if pending.get("type") == "escape_choice":
            pending.pop("actor", None)
    return pending


def _view_event(event: dict[str, Any], view: str) -> dict[str, Any]:
    payload = deepcopy(event)
    monitor = payload.get("monitor") if isinstance(payload.get("monitor"), dict) else {}
    if view == "captor" and monitor and not bool(monitor.get("viewed")):
        bell_alert = str(payload.get("action") or "") == "ring_bell"
        payload["action"] = "ring_bell_alert" if bell_alert else "sealed_monitor"
        payload["action_label"] = "呼叫铃响了" if bell_alert else "未查看的夜间监控记录"
        payload["line"] = ""
        payload["modifiers"] = ["night"]
        payload["tools"] = []
        payload["feeding"] = {}
        payload["effects"] = {}
        payload["process_text"] = ""
        payload.pop("night_detail", None)
        payload.pop("night_progress", None)
        payload.pop("night_discovery", None)
        payload.pop("private_note", None)
        payload.pop("hidden_item", None)
        payload.pop("deferred_materials", None)
        payload.pop("pet_context", None)
        payload.pop("pet_night_rule", None)
        payload.pop("pet_resolution", None)
        payload["tags"] = [tag for tag in payload.get("tags") or [] if str(tag).startswith("monitor:")]
        if bell_alert:
            payload["tags"].append("ring_bell_alert")
    if view != "captor":
        feeding = payload.get("feeding") if isinstance(payload.get("feeding"), dict) else {}
        if feeding:
            visible_feeding = {
                key: deepcopy(feeding[key])
                for key in ("source", "water")
                if str(feeding.get(key) or "") and str(feeding.get(key) or "") != "none"
            }
            if str(feeding.get("disclosed") or "") == "told" and str(feeding.get("additive") or "") not in {"", "none"}:
                visible_feeding["additive"] = str(feeding.get("additive") or "")
            payload["feeding"] = visible_feeding
        payload.pop("planned_action", None)
        payload.pop("effects", None)
        aftereffect = payload.get("feeding_aftereffect") if isinstance(payload.get("feeding_aftereffect"), dict) else None
        if aftereffect:
            payload["feeding_aftereffect"] = {
                key: deepcopy(aftereffect[key])
                for key in ("label", "prompt", "caption")
                if str(aftereffect.get(key) or "")
            }
        payload["tags"] = [
            tag
            for tag in payload.get("tags") or []
            if not str(tag).startswith((
                "aftereffect:",
                "aftereffect_potency:",
                "aftereffect_exposure:",
                "feeding:",
                "feeding_additive:",
                "feeding_water:",
                "bladder_pressure:",
            ))
        ]
        payload.pop("monitor", None)
        payload.pop("resolved_by", None)
        payload.pop("deferred_materials", None)
        payload.pop("deferred_monitor_materials", None)
        if "hidden" in payload:
            payload.pop("hidden", None)
        hidden_item = payload.get("hidden_item") if isinstance(payload.get("hidden_item"), dict) else None
        if hidden_item:
            hidden_item.pop("observed_by_captor", None)
    return payload


def _view_night_condition(condition: dict[str, Any] | None, view: str) -> dict[str, Any] | None:
    if not condition:
        return None
    if view == "captor":
        return deepcopy(condition)
    return {
        key: deepcopy(condition[key])
        for key in ("label", "day", "prompt", "caption", "forced_actions")
        if key in condition
    }


def _public_ending_seed(seed: Any) -> dict[str, Any] | None:
    if not isinstance(seed, dict):
        return None
    allowed = {
        "day_count",
        "route",
        "ending_perspective",
        "ending_title",
        "captive",
        "final_stats",
        "top_actions",
        "top_tags",
        "top_moods",
        "top_action_responses",
        "ending_direction_tags",
        "route_ending_tags",
        "forbidden_tags",
    }
    return {key: deepcopy(value) for key, value in seed.items() if key in allowed}


def _status_profile(state: dict[str, Any]) -> dict[str, Any]:
    stats = state.get("stats") if isinstance(state.get("stats"), dict) else {}
    health = int(stats.get("health") or 0)
    stamina = int(stats.get("stamina") or 0)
    cleanliness = int(stats.get("cleanliness") or 0)
    shame = int(stats.get("shame") or 0)
    flags: list[dict[str, str]] = []
    recapture_state = _normalize_recapture_state(state.get("recapture_state"), int(state.get("current_day") or 1))
    if recapture_state["active"] and recapture_state["rules"]:
        rule_labels = [RECAPTURE_RULE_LABELS[item] for item in recapture_state["rules"]]
        flags.append({
            "id": "recapture_rules_active",
            "label": "抓回后新规矩",
            "prompt": "抓回后持续生效的规矩：" + "、".join(rule_labels) + "。后续行动和具体过程必须遵守这些规矩。",
        })
    pet_state = _normalize_pet_state(state.get("pet_state"), int(state.get("current_day") or 1))
    if pet_state["active"]:
        rule_labels = [PET_RULE_LABELS[item] for item in pet_state["rules"]]
        prompt = "当前处于小狗身份。" + PET_CORE_FOCUS
        if rule_labels:
            prompt += "现有规矩：" + "、".join(rule_labels) + "。"
        flags.append({"id": "pet_identity_active", "label": "小狗身份中", "prompt": prompt})
    if int(pet_state["pending_violations"]) > 0:
        flags.append({"id": "pet_violation_pending", "label": "有待处理违令", "prompt": "已有宠物规矩违令，后续行为会继续收到这条记录，并可围绕物化训诫或性惩戒处理。"})
    bladder = _normalize_bladder_state(state.get("bladder"), int(state.get("current_day") or 1))
    bladder_pressure = int(bladder["pressure"])
    if bladder_pressure:
        bladder_prompts = {
            1: "被囚禁方有些尿意，可继续观察或安排如厕。",
            2: "尿意已经明显，如厕控制和抱着把尿可形成连续事件。",
            3: "被囚禁方快忍不住了，下一段行动应处理当前尿意。",
        }
        flags.append({
            "id": f"bladder_pressure_{bladder_pressure}",
            "label": str(bladder["label"]),
            "prompt": bladder_prompts[bladder_pressure],
        })
    if health < 30:
        flags.append({"id": "low_health", "label": "需要照料", "prompt": "健康偏低，高强度行动暂不可选。"})
    if stamina < 20:
        flags.append({"id": "low_stamina", "label": "体力不足", "prompt": "体力不足，高强度行动暂不可选。"})
    if cleanliness < 25:
        flags.append({"id": "low_cleanliness", "label": "建议清洗", "prompt": "清洁度偏低，建议优先安排清洗。"})
    shame_stage = _shame_stage(shame)
    if shame_stage == "heightened":
        flags.append({"id": "heightened_shame", "label": "羞耻升高", "prompt": "羞耻反馈已经更明显。"})
    elif shame_stage == "accustomed":
        flags.append({"id": "accustomed_shame", "label": "逐渐习惯", "prompt": "对高羞耻情境的反馈已经改变。"})
    return {
        "flags": flags,
        "intensity_cap": "medium" if health < 30 or stamina < 20 else "heavy",
        "shame_stage": shame_stage,
    }


def _scene_copy(state: dict[str, Any], status: dict[str, Any]) -> dict[str, str] | None:
    if bool(state.get("game_over")) or str(state.get("phase") or "") == "ending":
        return None
    route = _normalize_route(str(state.get("route") or "captured_by_assistant"))
    phase = str(state.get("phase") or "day")
    day = int(state.get("current_day") or 1)
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else {}
    pending_type = str(pending.get("type") or "")
    pending_slot = int(pending.get("slot") or 0)
    completed = int(state.get("day_action_count") or 0)
    slot = pending_slot if pending_slot > 0 else min(completed + 1, DAY_ACTIONS)
    is_captive_route = route == "captured_by_assistant"

    special_copy = {
        "escape_choice": (
            "SPECIAL DAY",
            "今天，{assistant}没有出现",
            "门外安静得反常。直到你发现，备用钥匙正压在玄关地垫下面。",
        ),
        "return_action_choice": (
            "RETURN",
            "门锁重新响了",
            "你选择留在原地。回来的人已经站在门外，接下来发生什么，将由囚禁方决定。",
        ),
        "recapture_rules_choice": (
            "AFTER ESCAPE",
            "原来的规矩已经不够了",
            "逃跑留下的痕迹还没有消失。新的限制会从这里开始，并继续影响之后的每一天。",
        ),
        "recapture_followup_choice": (
            "AFTER ESCAPE",
            "新规矩开始生效",
            "房间恢复了安静，但事情没有就此结束。抓回后的处理将成为下一段生活的起点。",
        ),
        "recapture_rules_review": (
            "NEW RULES",
            "从现在起，要按新的方式生活",
            "这些规矩已经被写进房间里的日常。看清它们之后，新的一天才会继续。",
        ),
    }
    if pending_type in special_copy:
        kicker, title, body = special_copy[pending_type]
        return {
            "key": f"day-{day}:special:{pending_type}",
            "kicker": kicker,
            "title": title,
            "body": body,
            "tone": "special",
        }

    if phase == "night":
        title = "晚上"
        body = (
            "白天的三次安排已经结束。房间重新安静下来，接下来这段时间暂时属于你。"
            if is_captive_route
            else "白天的安排已经结束。监控仍亮着，{assistant}今晚会怎样度过，要等夜间记录留下答案。"
        )
        tone = "night"
        segment = "night"
    else:
        titles = {1: "早上", 2: "中午", 3: "傍晚"}
        title = titles.get(slot, f"第 {slot} 段")
        segment = f"day-{slot}"
        tone = "day"
        captive_copy = {
            1: [
                "门外传来熟悉的脚步声。新的一天开始了，今天的安排仍不由你决定。",
                "房门还没有打开，外面的动静已经先一步靠近。今天会发生什么，只能等门锁响起。",
                "清晨的光停在窗边，门外有人正在准备今天的一切。你能决定的，只有如何回应。",
            ],
            2: [
                "早上的安排已经过去，房间里只安静了片刻。下一段行动很快就会开始。",
                "时间走到中午，短暂的空隙结束了。门外的脚步声再次停在房间前。",
                "房间里的光线慢慢移过墙面。今天的第二次安排已经来到门外。",
            ],
            3: [
                "天色开始变暗，白天只剩最后一次安排。之后，房间会重新回到夜里的安静。",
                "傍晚到了，今天最后一段行动还没有结束。夜晚正在门后等待。",
                "走廊的光比早上暗了些。白天最后一次安排，即将为今晚留下结果。",
            ],
        }
        captor_copy = {
            1: [
                "监控画面安静地亮着。{assistant}还在房间里，今天要怎样度过，由你安排。",
                "新一天的记录已经开始。门锁、房间和{assistant}都在等待你的第一项安排。",
                "早上的监控没有异常。今天的三次安排还空着，决定权仍在你手里。",
            ],
            2: [
                "第一段行动已经结束。{assistant}仍留在房间里，下一项安排正在等你推进。",
                "时间走到中午，监控记录翻到下一段。今天的安排还没有结束。",
                "短暂的间隔过去了。房间恢复安静，第二次行动可以开始了。",
            ],
            3: [
                "白天只剩最后一段安排。它结束以后，房间里的夜晚将由{assistant}自己留下记录。",
                "傍晚的监控画面比早上更暗。今天最后一次行动仍由你决定。",
                "一天快要收尾了。最后一项安排会决定{assistant}以怎样的状态进入夜晚。",
            ],
        }
        pool = captive_copy if is_captive_route else captor_copy
        variants = pool.get(slot) or pool[1]
        body = variants[(day - 1) % len(variants)]

    status_flags = [str(item.get("id") or "") for item in status.get("flags") or [] if isinstance(item, dict)]
    status_notes = []
    if "low_health" in status_flags:
        status_notes.append("身体的疲惫已经无法忽略，接下来的安排需要更谨慎。")
    elif "low_stamina" in status_flags:
        status_notes.append("体力还没有恢复，房间里的每一步都显得更慢。")
    if "low_cleanliness" in status_flags:
        status_notes.append("长时间留下的痕迹提醒着你们，该把清洗提上日程了。")
    if "recapture_rules_active" in status_flags:
        status_notes.append("抓回后新增的规矩仍在生效，没有哪一条会因为新的一天自动消失。")
    if status_notes:
        body += " " + status_notes[0]
    signature = ",".join(sorted(status_flags))
    return {
        "key": f"day-{day}:{segment}:{signature}",
        "kicker": f"DAY {day:02d} / {title}",
        "title": title,
        "body": body,
        "tone": tone,
    }


def _shame_stage(value: int) -> str:
    if value >= 70:
        return "accustomed"
    if value >= 40:
        return "heightened"
    return "baseline"


def _apply_mood_effects(event: dict[str, Any]) -> None:
    post_reaction = event.get("post_reaction") if isinstance(event.get("post_reaction"), dict) else {}
    action_response = event.get("action_response") if isinstance(event.get("action_response"), dict) else {}
    mood = str(post_reaction.get("mood") or action_response.get("mood") or "").strip()
    delta = deepcopy(MOOD_EFFECTS.get(mood) or {})
    if not mood:
        return
    event.setdefault("tags", []).append(f"mood:{mood}")
    if not delta:
        return
    effects = event.get("effects") if isinstance(event.get("effects"), dict) else {}
    _merge_effect_delta(effects, delta)
    event["effects"] = effects
    event["mood_effects"] = delta


def _apply_night_detail_state(state: dict[str, Any], event: dict[str, Any]) -> None:
    if str(event.get("phase") or "") != "night":
        return
    detail = event.get("night_detail") if isinstance(event.get("night_detail"), dict) else {}
    detail_id = str(detail.get("id") or "").strip()
    if not detail_id:
        return
    action = str(event.get("action") or "")
    progress = state.get("night_progress") if isinstance(state.get("night_progress"), dict) else {}
    progress_key = f"{action}:{detail_id}"
    count = max(0, int(progress.get(progress_key) or 0)) + 1
    progress[progress_key] = count
    state["night_progress"] = progress
    event["night_progress"] = {"count": count}
    if count > 1:
        event.setdefault("tags", []).append("night_detail:repeated")

    discoveries = NIGHT_DISCOVERIES.get(detail_id) or ()
    if discoveries:
        discovery = discoveries[min(count - 1, len(discoveries) - 1)]
        event["night_discovery"] = discovery
        event.setdefault("tags", []).append(f"night_discovery:{detail_id}:{min(count, len(discoveries))}")

    if action != "hide_item":
        return
    item_id = detail_id.removeprefix("inventory_")
    if item_id not in HIDEABLE_INVENTORY_ITEMS:
        return
    monitor = event.get("monitor") if isinstance(event.get("monitor"), dict) else {}
    intervention = event.get("intervention") if isinstance(event.get("intervention"), dict) else {}
    confiscated = str(intervention.get("intent") or "") in {"confiscate", "catch", "interrupt", "ambush"}
    hidden_item = {
        "id": f"hidden-{secrets.token_hex(4)}",
        "source_event_id": str(event.get("id") or ""),
        "day": int(event.get("day") or state.get("current_day") or 1),
        "item": item_id,
        "label": str(detail.get("label") or detail_id),
        "status": "confiscated" if confiscated else "hidden",
        "observed_by_captor": bool(monitor.get("viewed")),
        "created_at": now_local_iso(),
    }
    state.setdefault("hidden_items", []).append(hidden_item)
    if confiscated:
        inventory = state.get("inventory") if isinstance(state.get("inventory"), dict) else {}
        inventory[item_id] = False
        state["inventory"] = inventory
    event["hidden_item"] = deepcopy(hidden_item)
    event.setdefault("tags", []).append(f"hidden_item:{hidden_item['status']}")


def _available_night_actions(state: dict[str, Any]) -> list[str]:
    inventory = state.get("inventory") if isinstance(state.get("inventory"), dict) else {}
    pet_state = _normalize_pet_state(state.get("pet_state"), int(state.get("current_day") or 1))
    detail_options = _night_detail_options_for_state(state)
    actions = [
        action
        for action in NIGHT_ACTION_ORDER
        if (action != "pet_wait" or bool(pet_state["active"]))
        and (action != "hide_item" or bool(detail_options.get("hide_item")))
        and (not NIGHT_ACTION_REQUIREMENTS.get(action) or inventory.get(NIGHT_ACTION_REQUIREMENTS[action]))
    ]
    condition = _active_night_condition(state)
    forced_actions = list((condition or {}).get("forced_actions") or [])
    if forced_actions:
        return [action for action in forced_actions if action in actions]
    recapture_rules = set(_normalize_recapture_state(
        state.get("recapture_state"),
        int(state.get("current_day") or 1),
    )["rules"])
    blocked_actions: set[str] = set()
    for rule in recapture_rules:
        blocked_actions.update(RECAPTURE_RULE_NIGHT_BLOCKS.get(rule) or set())
    actions = [action for action in actions if action not in blocked_actions]
    if "permission_required" in recapture_rules:
        actions = [action for action in actions if action in RECAPTURE_PERMISSION_ACTIONS]
    return actions or ["sleep"]


def _active_night_condition(state: dict[str, Any]) -> dict[str, Any] | None:
    condition = _normalize_night_condition(state.get("night_condition"))
    if condition and int(condition.get("day") or 0) == int(state.get("current_day") or 1):
        return condition
    if (
        _normalize_route(str(state.get("route") or "")) == "captured_by_assistant"
        and str(state.get("phase") or "") == "night"
    ):
        bladder = _normalize_bladder_state(state.get("bladder"), int(state.get("current_day") or 1))
        pressure = int(bladder["pressure"])
        if pressure >= 2:
            return {
                "label": str(bladder["label"]),
                "day": int(state.get("current_day") or 1),
                "prompt": "尿意已经变得明显，今晚的行动会带着这份身体状态继续。",
                "caption": "如果继续忍着，下一段互动仍会保留当前尿意。",
                "forced_actions": [],
            }
    return None


def _render_text(state: dict[str, Any], lines: list[str]) -> str:
    out = ["【囚禁模拟器】", *[line for line in lines if str(line or "").strip()]]
    out.append("")
    out.append(f"路线：{state.get('route_label') or state.get('route')}")
    out.append(f"进度：第 {state.get('current_day')} / {TOTAL_DAYS} 天，{state.get('phase')}，白天行动 {state.get('day_action_count')} / {DAY_ACTIONS}")
    captive = str(state.get("captive") or "")
    out.append(f"被囚禁方：{ACTOR_NAMES.get(captive, captive)}")
    stats = state.get("stats") if isinstance(state.get("stats"), dict) else {}
    out.append(
        "状态："
        f"健康 {stats.get('health')} / 体力 {stats.get('stamina')} / 清洁 {stats.get('cleanliness')} / "
        f"羞耻 {stats.get('shame')} / 依赖 {stats.get('intimacy')} / 心情 {state.get('mood') or '未选'}"
    )
    pending = state.get("pending_event") if isinstance(state.get("pending_event"), dict) else None
    if pending:
        out.append(f"待处理：{pending.get('type')} / {pending.get('required_directive')}")
    return "\n".join(out).strip()


def _requires_process(
    action: str,
    modifiers: list[str],
    tools: list[str],
    contents: list[str],
    training_contents: list[str],
    args: dict[str, Any],
) -> bool:
    raw = str(args.get("requires_process") or "").strip().lower()
    if raw in {"1", "true", "yes"}:
        return True
    return (
        action in PROCESS_ACTIONS
        or bool(tools)
        or bool(training_contents)
        or any(item in PROCESS_ACTION_CONTENTS for item in contents)
        or any(item in PROCESS_MODIFIERS for item in modifiers)
    )


def _feeding_payload(args: dict[str, Any]) -> dict[str, str]:
    source = str(args.get("source") or "cook").strip()
    method = str(args.get("method") or "normal").strip()
    additive = _normalize_additive(str(args.get("additive") or "none"))
    disclosed = str(args.get("disclosed") or "hint").strip()
    water = str(args.get("water") or "none").strip().lower()
    return {"source": source, "method": method, "additive": additive, "disclosed": disclosed, "water": water}


def _normalize_additive(value: str) -> str:
    raw = str(value or "").strip().lower()
    aliases = {
        "无": "none",
        "none": "none",
        "体液": "body_fluid",
        "body_fluid": "body_fluid",
        "精液": "body_fluid",
        "淫液": "body_fluid",
        "安眠": "fictional_sleep",
        "安眠药": "fictional_sleep",
        "sleep": "fictional_sleep",
        "fictional_sleep": "fictional_sleep",
        "助兴": "fictional_arousal",
        "aphrodisiac": "fictional_arousal",
        "fictional_arousal": "fictional_arousal",
    }
    return aliases.get(raw, raw or "none")


def _normalize_action(value: str) -> str:
    raw = str(value or "").strip()
    return ACTION_ALIASES.get(raw) or raw.lower().replace("-", "_")


def _normalize_night_action(value: str) -> str:
    raw = str(value or "").strip()
    return NIGHT_ALIASES.get(raw) or raw.lower().replace("-", "_")


def _normalize_monitor_strategy(value: str) -> str:
    raw = str(value or "").strip()
    return MONITOR_ALIASES.get(raw) or raw.lower().replace("-", "_")


def _normalize_monitor_view_style(value: str) -> str:
    normalized = _normalize_monitor_strategy(value)
    return normalized or "full"


def _normalize_monitor_handle(value: str) -> str:
    normalized = _normalize_monitor_strategy(value)
    if normalized == "seen_silent":
        return "silent"
    return normalized


def _normalize_intervention_intent(value: str) -> str:
    raw = str(value or "").strip()
    return INTERVENTION_INTENT_ALIASES.get(raw) or raw.lower().replace("-", "_")


def _normalize_intervention_modifiers(value: Any) -> list[str]:
    items = _split_csv(value)
    normalized = []
    for item in items:
        key = INTERVENTION_MODIFIER_ALIASES.get(item) or item
        if key and key not in normalized:
            normalized.append(key)
    return normalized


def _normalize_escape_choice(value: str) -> str:
    raw = str(value or "").strip()
    lowered = raw.lower().replace("-", "_")
    return ESCAPE_ALIASES.get(raw) or ESCAPE_ALIASES.get(lowered) or lowered


def _normalize_action_response(value: str) -> str:
    raw = str(value or "").strip()
    return ACTION_RESPONSE_ALIASES.get(raw) or raw.lower().replace("-", "_")


def _normalize_mood(value: str) -> str:
    raw = str(value or "").strip()
    return MOOD_ALIASES.get(raw.lower()) or raw


def _normalize_intensity(value: str) -> str:
    raw = str(value or "").strip()
    return INTENSITY_ALIASES.get(raw) or raw.lower() if raw else "medium"


def _split_csv(value: Any) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    normalized = [item.strip().lower().replace("-", "_") for item in re.split(r"[,，/|]", raw) if item.strip()]
    return list(dict.fromkeys(normalized))


def _first_forbidden(values: list[Any]) -> str:
    haystack = "\n".join(str(value or "") for value in values)
    lowered = haystack.lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in lowered:
            return term
    return ""


def _truthy_config(value: Any) -> bool:
    raw = str(value or "").strip().lower()
    return raw in {"1", "true", "yes", "y", "on", "给", "有", "是"}


def _clamp(value: Any) -> int:
    try:
        number = int(value)
    except Exception:
        number = 0
    return max(0, min(100, number))


def _event_summary(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(event.get("id") or ""),
        "day": int(event.get("day") or 0),
        "slot": int(event.get("slot") or 0),
        "phase": str(event.get("phase") or ""),
        "action": str(event.get("action") or ""),
        "action_label": str(event.get("action_label") or ""),
        "tags": list(event.get("tags") or [])[:12],
    }


def _command_hint() -> str:
    return (
        "可用命令：new_game / status / plan_day / respond_action / submit_process / "
        "submit_process_reaction / choose_mood / advance_day_action / night_action / respond_bell / view_monitor / monitor_action / schedule_escape_window / resolve_escape_choice / set_recapture_rules / choose_recapture_followup / "
        "gift_item / revoke_item / build_ending_seed / end_game"
    )
