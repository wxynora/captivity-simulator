import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft as ChevronLeftIcon } from "lucide-react";
import { ApiError, apiJson } from "./api";
import recaptureBackgroundUrl from "./assets/captivity-recapture-background.webp";

type RouteKey = "captured_by_assistant" | "capture_assistant";
type UserRole = "captive" | "captor";

type CaptivityStats = Partial<Record<"health" | "stamina" | "cleanliness" | "shame" | "intimacy", number>>;

type NightCondition = {
  additive?: string;
  label?: string;
  day?: number;
  exposure_count?: number;
  tolerance_count?: number;
  potency?: string;
  prompt?: string;
  caption?: string;
  forced_actions?: string[];
};

type StatusFlag = {
  id?: string;
  label?: string;
  prompt?: string;
};

type SceneCopy = {
  key?: string;
  kicker?: string;
  title?: string;
  body?: string;
  tone?: "day" | "night" | "special" | string;
};

type DeferredMonitorMaterial = {
  id?: string;
  status?: string;
  day?: number;
  available_from_day?: number;
  action?: string;
  action_label?: string;
  detail_label?: string;
  line?: string;
  monitor_style?: string;
  monitor_note?: string;
  created_at?: string;
  used_day?: number;
  used_at?: string;
};

type CaptivityEvent = {
  id?: string;
  day?: number;
  slot?: number;
  phase?: string;
  route?: string;
  action?: string;
  action_label?: string;
  intensity?: string;
  line?: string;
  mood?: string;
  mood_after?: string;
  modifiers?: string[];
  tools?: string[];
  contents?: string[];
  training_contents?: string[];
  tags?: string[];
  feeding?: Record<string, string>;
  effects?: Record<string, number>;
  process_text?: string;
  process_saved_at?: string;
  resolved_at?: string;
  created_at?: string;
  requires_process?: boolean;
  action_response?: {
    response?: string;
    response_label?: string;
    mood?: string;
    line?: string;
  };
  post_reaction?: {
    mood?: string;
    line?: string;
  };
  monitor?: {
    viewed?: boolean;
    style?: string;
    strategy?: string;
    handle?: string;
    note?: string;
  };
  escape?: {
    choice?: string;
    choice_label?: string;
  };
  recapture_context?: {
    source_event_id?: string;
    followup?: string;
    followup_label?: string;
    rule_ids?: string[];
    rule_labels?: string[];
  };
  recapture_rules?: {
    rule_ids?: string[];
    rule_labels?: string[];
  };
  intervention?: {
    intent?: string;
    intent_label?: string;
    modifiers?: string[];
    modifier_labels?: string[];
    training_contents?: string[];
    training_content_labels?: string[];
    tools?: string[];
    line?: string;
  };
  feeding_aftereffect?: NightCondition & { effect_bonus?: number };
  night_detail?: { id?: string; label?: string };
  night_progress?: { count?: number };
  night_discovery?: string;
  private_note?: string;
  bell_voice?: {
    line?: string;
    first_reveal?: boolean;
  };
  hidden_item?: Record<string, unknown>;
  mood_effects?: Record<string, number>;
  shame_stage?: string;
};

type CaptivityPending = {
  id?: string;
  type?: string;
  day?: number;
  slot?: number;
  actor?: string;
  captive?: string;
  action?: string;
  phase?: string;
  sealed?: boolean;
  hint?: string;
  bait?: string;
  alert_label?: string;
  condition_prompt?: string;
  condition_caption?: string;
  available_actions?: string[];
  available_rules?: string[];
  rule_ids?: string[];
  rule_labels?: string[];
  source_event_id?: string;
  available_night_actions?: string[];
  detail_options?: Record<string, Record<string, string>>;
  status_flags?: StatusFlag[];
  intensity_cap?: string;
  required_directive?: string;
  item_secret?: {
    item_id?: string;
    item_label?: string;
    content?: string;
    text?: string;
    sequence?: number;
    total?: number;
  };
  event?: CaptivityEvent;
};

type DayPlanSpec = {
  action?: string;
  action_label?: string;
  intensity?: string;
  modifiers?: string[];
  tools?: string[];
  contents?: string[];
  training_contents?: string[];
  line?: string;
  feeding?: Record<string, string>;
};

type CaptivityView = {
  route?: RouteKey | string;
  route_label?: string;
  viewer?: "captive" | "captor" | string;
  current_day?: number;
  total_days?: number;
  day_action_count?: number;
  day_action_limit?: number;
  phase?: string;
  captive?: string;
  captive_name?: string;
  captor?: string;
  stats?: CaptivityStats;
  bladder?: {
    pressure?: number;
    label?: string;
    last_changed_day?: number;
  };
  mood?: string;
  mood_line?: string;
  pending_event?: CaptivityPending | null;
  event_log?: CaptivityEvent[];
  ending_state?: string;
  ending_seed?: Record<string, unknown> | null;
  ending_title?: string;
  ending_text?: string;
  ending_notified_at?: string;
  previous_ending?: { title?: string; route?: string; notified_at?: string };
  game_over?: boolean;
  result?: string;
  updated_at?: string;
  day_plan?: DayPlanSpec[];
  escape_windows?: Array<Record<string, unknown>>;
  hidden_items?: Array<Record<string, unknown>>;
  inventory?: Record<string, boolean | undefined>;
  inventory_secrets?: Record<string, {
    content?: string;
    entries?: string[];
    revealed?: boolean;
    revealed_count?: number;
    total_count?: number;
    revealed_entries?: string[];
    configured_by?: string;
    configured_at?: string;
  }>;
  call_bell_voice?: {
    line?: string;
    revealed?: boolean;
    configured_by?: string;
    configured_at?: string;
  };
  night_condition?: NightCondition | null;
  night_detail_options?: Record<string, Record<string, string>>;
  deferred_monitor_materials?: DeferredMonitorMaterial[];
  available_night_actions?: string[];
  status_flags?: StatusFlag[];
  intensity_cap?: string;
  shame_stage?: string;
  scene_copy?: SceneCopy | null;
  escape_hint?: {
    hint?: string;
    bait?: string;
  };
  recapture_state?: {
    active?: boolean;
    rules?: string[];
    source_event_id?: string;
    source_day?: number;
    followup_history?: Array<Record<string, unknown>>;
  };
};

type CaptivityPayload = {
  ok?: boolean;
  error?: string;
  message?: string;
  text?: string;
  player_text?: string;
  reply_text?: string;
  reply_preview?: string;
  sync_result?: string;
  state?: CaptivityView;
  captive_view?: CaptivityView;
  captor_view?: CaptivityView;
  game_over?: boolean;
  result?: string;
  applied_reply_commands?: Array<{ command?: string; ok?: boolean; error?: string; player_text?: string }>;
  followup_wakeups?: Array<{ ok?: boolean; reply_preview?: string; error?: string }>;
};

type PlanSlot = {
  action: string;
  intensity: string;
  modifiers: string[];
  tools: string[];
  contents: string[];
  trainingContents: string[];
  line: string;
  feedingSource: string;
  feedingAdditive: string;
};

type WaitState = {
  visible: boolean;
  title: string;
  detail: string;
  error?: string;
};

type ProcessReview = {
  event: CaptivityEvent;
  text: string;
  moodRequired: boolean;
};

const SAVE_ID = "default";

const STAT_LABELS: Array<{ key: keyof CaptivityStats; label: string }> = [
  { key: "health", label: "健康" },
  { key: "stamina", label: "体力" },
  { key: "cleanliness", label: "清洁" },
  { key: "shame", label: "羞耻" },
  { key: "intimacy", label: "依赖" },
];

const ACTION_OPTIONS = [
  { id: "feeding", label: "喂食" },
  { id: "cleaning", label: "清洗" },
  { id: "training", label: "服从调教" },
  { id: "reward", label: "奖励取悦" },
  { id: "punishment", label: "违令惩戒" },
  { id: "comfort", label: "事后安抚" },
  { id: "rest", label: "看管休息" },
  { id: "check", label: "私密检查" },
  { id: "room_search", label: "突击搜查" },
];

const ACTION_CONTENT_OPTIONS: Record<string, Array<{ id: string; label: string }>> = {
  reward: [
    { id: "caress_reward", label: "抚摸奖励" },
    { id: "kiss_reward", label: "亲吻奖励" },
    { id: "masturbation_permission", label: "允许自慰" },
    { id: "orgasm_permission", label: "允许高潮" },
    { id: "toy_reward", label: "玩具奖励" },
    { id: "freedom_reward", label: "增加自由" },
  ],
  punishment: [
    { id: "impact_discipline", label: "拍打惩戒" },
    { id: "bondage_discipline", label: "束缚惩戒" },
    { id: "orgasm_denial", label: "禁止高潮" },
    { id: "toy_discipline", label: "玩具惩戒" },
    { id: "confiscation", label: "没收物品" },
    { id: "interrogation", label: "审问" },
    { id: "rule_escalation", label: "规则加码" },
  ],
  comfort: [
    { id: "embrace", label: "拥抱" },
    { id: "kiss", label: "亲吻" },
    { id: "body_care", label: "身体清理" },
    { id: "massage", label: "按摩" },
    { id: "feeding_care", label: "喂水喂食" },
    { id: "cuddle_rest", label: "抱着休息" },
    { id: "partial_release", label: "解除部分束缚" },
  ],
  rest: [
    { id: "forced_nap", label: "强制午睡" },
    { id: "cuddle_sleep", label: "抱睡" },
    { id: "supervised_sleep", label: "陪睡" },
    { id: "restrained_rest", label: "固定姿势休息" },
    { id: "quiet_time", label: "安静待着" },
  ],
  check: [
    { id: "body_check", label: "身体检查" },
    { id: "mark_check", label: "痕迹检查" },
    { id: "sensitivity_check", label: "敏感反应检查" },
    { id: "restraint_check", label: "束缚状态检查" },
    { id: "chastity_check", label: "贞操装置检查" },
  ],
  room_search: [
    { id: "bed_search", label: "翻查床铺" },
    { id: "hidden_item_search", label: "搜查私藏物" },
    { id: "body_search", label: "搜身" },
    { id: "key_trace_check", label: "检查钥匙痕迹" },
    { id: "search_confiscation", label: "没收物品" },
    { id: "on_site_questioning", label: "现场盘问" },
  ],
};

const TRAINING_CONTENT_OPTIONS = [
  { id: "obedience_commands", label: "口令服从" },
  { id: "position_training", label: "姿势训练" },
  { id: "bondage_training", label: "束缚训练" },
  { id: "sensory_deprivation", label: "感官控制" },
  { id: "impact_play", label: "拍打调教" },
  { id: "wax_play", label: "滴蜡调教" },
  { id: "clamp_play", label: "夹具调教" },
  { id: "toy_training", label: "玩具调教" },
  { id: "anal_training", label: "后庭调教" },
  { id: "chastity_control", label: "贞操控制" },
  { id: "orgasm_control", label: "高潮控制" },
  { id: "forced_orgasm", label: "强制高潮" },
  { id: "masturbation_control", label: "自慰控制" },
  { id: "humiliation_play", label: "羞耻调教" },
  { id: "exposure_training", label: "展示训练" },
  { id: "pet_play", label: "小狗身份建立" },
  { id: "leash_training", label: "牵引训练" },
  { id: "service_training", label: "服务训练" },
  { id: "inspection_training", label: "检查调教" },
  { id: "pet_position_wait", label: "定点等候" },
  { id: "pet_crawl_training", label: "爬行训练" },
  { id: "pet_feeding", label: "宠物式喂食" },
  { id: "pet_permission", label: "按铃求许可" },
  { id: "pet_voice_training", label: "叫声与回应" },
  { id: "pet_owner_address", label: "主人称呼训练" },
  { id: "pet_begging", label: "宠物式求欢" },
  { id: "pet_display", label: "宠物展示检查" },
  { id: "toilet_control", label: "如厕控制" },
  { id: "assisted_urination", label: "抱着把尿" },
];
const CAPTIVE_ROUTE_ONLY_TRAINING_IDS = new Set(["toilet_control", "assisted_urination"]);

const PROCESS_ACTION_CONTENT_IDS = new Set([
  "masturbation_permission",
  "orgasm_permission",
  "toy_reward",
  "impact_discipline",
  "bondage_discipline",
  "orgasm_denial",
  "toy_discipline",
  "sensitivity_check",
  "chastity_check",
  "body_search",
]);

const INTENSITY_OPTIONS = [
  { id: "light", label: "低" },
  { id: "medium", label: "中" },
  { id: "heavy", label: "高" },
];

const MODIFIER_OPTIONS = [
  { id: "training", label: "调教" },
  { id: "sex", label: "性交" },
];

const INTERVENTION_INTENT_OPTIONS = [
  { id: "catch", label: "抓现行" },
  { id: "confiscate", label: "没收物品" },
  { id: "interrupt", label: "打断带走" },
  { id: "ambush", label: "突袭" },
  { id: "question", label: "审问" },
  { id: "command_stop", label: "命令停下" },
  { id: "reward", label: "奖励" },
  { id: "punishment", label: "惩罚" },
];

const INTERVENTION_MODIFIER_OPTIONS = [
  { id: "training", label: "调教" },
  { id: "sex", label: "性行为" },
];

type ToolOption = { id: string; label: string; category: string; contexts: string[] };
const TOOL_OPTIONS: ToolOption[] = [
  { id: "toy", label: "跳蛋", category: "玩具", contexts: ["training:toy_training", "training:orgasm_control", "training:forced_orgasm", "training:masturbation_control", "content:toy_reward", "content:toy_discipline", "modifier:sex"] },
  { id: "vibrating_wand", label: "振动棒", category: "玩具", contexts: ["training:toy_training", "training:orgasm_control", "training:forced_orgasm", "training:masturbation_control", "content:toy_reward", "content:toy_discipline", "modifier:sex"] },
  { id: "dildo", label: "假阳具", category: "玩具", contexts: ["training:toy_training", "training:forced_orgasm", "content:toy_reward", "content:toy_discipline", "modifier:sex"] },
  { id: "remote_control", label: "遥控器", category: "玩具", contexts: ["training:toy_training", "training:orgasm_control", "training:forced_orgasm", "training:masturbation_control", "content:toy_reward", "content:toy_discipline"] },
  { id: "lubricant", label: "润滑剂", category: "辅助", contexts: ["training:toy_training", "training:anal_training", "training:forced_orgasm", "modifier:sex"] },
  { id: "collar", label: "项圈", category: "束缚", contexts: ["training:obedience_commands", "training:position_training", "training:pet_play", "training:pet_position_wait", "training:pet_crawl_training", "training:pet_feeding", "training:pet_permission", "training:pet_voice_training", "training:pet_owner_address", "training:pet_begging", "training:pet_display", "training:leash_training", "training:service_training", "content:bondage_discipline", "content:restrained_rest", "modifier:sex"] },
  { id: "leash", label: "牵引绳", category: "束缚", contexts: ["training:position_training", "training:pet_play", "training:pet_position_wait", "training:pet_crawl_training", "training:pet_begging", "training:pet_display", "training:leash_training", "training:service_training", "content:bondage_discipline"] },
  { id: "handcuffs", label: "手铐", category: "束缚", contexts: ["training:bondage_training", "training:position_training", "training:sensory_deprivation", "training:exposure_training", "training:toilet_control", "training:assisted_urination", "content:bondage_discipline", "content:restrained_rest", "modifier:sex"] },
  { id: "ankle_cuffs", label: "脚铐", category: "束缚", contexts: ["training:bondage_training", "training:position_training", "training:exposure_training", "training:toilet_control", "training:assisted_urination", "content:bondage_discipline", "content:restrained_rest", "modifier:sex"] },
  { id: "rope", label: "绳子", category: "束缚", contexts: ["training:bondage_training", "training:position_training", "training:exposure_training", "training:toilet_control", "training:assisted_urination", "content:bondage_discipline", "content:restrained_rest", "modifier:sex"] },
  { id: "bondage_tape", label: "束缚胶带", category: "束缚", contexts: ["training:bondage_training", "training:sensory_deprivation", "training:toilet_control", "training:assisted_urination", "content:bondage_discipline", "content:restrained_rest", "modifier:sex"] },
  { id: "spreader_bar", label: "分腿杆", category: "束缚", contexts: ["training:bondage_training", "training:position_training", "training:exposure_training", "training:toilet_control", "training:assisted_urination", "content:bondage_discipline", "modifier:sex"] },
  { id: "blindfold", label: "眼罩", category: "感官", contexts: ["training:sensory_deprivation", "training:inspection_training", "content:sensitivity_check", "modifier:sex"] },
  { id: "gag", label: "口球", category: "束缚", contexts: ["training:obedience_commands", "training:sensory_deprivation", "training:humiliation_play", "training:pet_play", "training:pet_voice_training", "training:pet_begging", "training:pet_display", "modifier:sex"] },
  { id: "muzzle", label: "口套", category: "束缚", contexts: ["training:obedience_commands", "training:humiliation_play", "training:pet_play", "training:pet_voice_training", "training:pet_owner_address", "training:pet_begging"] },
  { id: "whip", label: "软鞭", category: "训诫", contexts: ["training:impact_play", "content:impact_discipline"] },
  { id: "flogger", label: "多尾鞭", category: "训诫", contexts: ["training:impact_play", "content:impact_discipline"] },
  { id: "paddle", label: "拍板", category: "训诫", contexts: ["training:impact_play", "content:impact_discipline"] },
  { id: "cane", label: "藤条", category: "训诫", contexts: ["training:impact_play", "content:impact_discipline"] },
  { id: "ruler", label: "戒尺", category: "训诫", contexts: ["training:impact_play", "content:impact_discipline"] },
  { id: "candle", label: "蜡烛", category: "感官", contexts: ["training:wax_play", "modifier:sex"] },
  { id: "ice_cube", label: "冰块", category: "感官", contexts: ["training:sensory_deprivation", "training:inspection_training", "content:sensitivity_check", "modifier:sex"] },
  { id: "pinwheel", label: "滚轮", category: "感官", contexts: ["training:sensory_deprivation", "training:inspection_training", "content:sensitivity_check", "modifier:sex"] },
  { id: "feather", label: "羽毛", category: "感官", contexts: ["training:sensory_deprivation", "training:inspection_training", "content:sensitivity_check", "modifier:sex"] },
  { id: "nipple_clamps", label: "乳夹", category: "夹具", contexts: ["training:clamp_play", "training:inspection_training", "content:sensitivity_check", "modifier:sex"] },
  { id: "suction_cups", label: "乳吸", category: "夹具", contexts: ["training:clamp_play", "training:inspection_training", "content:sensitivity_check", "modifier:sex"] },
  { id: "chastity_ring", label: "贞操锁", category: "控制", contexts: ["training:chastity_control", "training:orgasm_control", "content:chastity_check"] },
  { id: "anal_plug", label: "肛塞", category: "后庭", contexts: ["training:anal_training", "training:toy_training", "modifier:sex"] },
  { id: "anal_beads", label: "拉珠", category: "后庭", contexts: ["training:anal_training", "training:toy_training", "modifier:sex"] },
  { id: "feeding_spoon", label: "喂食器具", category: "喂食", contexts: ["action:feeding", "content:feeding_care", "training:pet_feeding"] },
];

const INVENTORY_OPTIONS = [
  { id: "book", label: "书", usage: "解锁看书" },
  { id: "switch", label: "Switch", usage: "解锁玩游戏" },
  { id: "notebook", label: "日记本", usage: "解锁写日记" },
  { id: "music_player", label: "音乐播放器", usage: "解锁听音乐" },
  { id: "tablet", label: "平板", usage: "解锁看视频" },
  { id: "night_light", label: "小夜灯", usage: "改善睡觉" },
  { id: "pillow", label: "抱枕", usage: "改善休息" },
  { id: "call_bell", label: "呼叫铃", usage: "按下后替你发声" },
] as const;
type InventoryItemId = (typeof INVENTORY_OPTIONS)[number]["id"];

const PROGRESSIVE_SECRET_ITEMS = new Set<InventoryItemId>(["book", "switch", "music_player", "tablet"]);
const PROGRESSIVE_SECRET_COPY: Partial<Record<InventoryItemId, { label: string; placeholder: string }>> = {
  book: {
    label: "这本书曾由你使用。逐行填写页码标记、批注或夹页痕迹；对方每次看书只会发现下一条。",
    placeholder: "例：第 47 页折过角，旁边留着一行批注\n例：书签停在你反复读过的那一页",
  },
  switch: {
    label: "这台 Switch 曾由你使用。逐行填写游戏记录或账号痕迹；对方每次玩游戏只会发现下一条。",
    placeholder: "例：最近游玩记录停在某个存档\n例：相册里留着一张没有删掉的截图",
  },
  music_player: {
    label: "这个播放器曾由你使用。逐行填写喜欢的歌或歌单痕迹；对方每次听音乐只会发现下一条。",
    placeholder: "例：最常播放的歌被单独收藏\n例：某张歌单循环过很多次",
  },
  tablet: {
    label: "这台平板曾由你使用。逐行填写浏览或观看记录；对方每次使用只会发现下一条。",
    placeholder: "例：浏览记录停在某个页面\n例：观看历史里留下了一段未播完的视频",
  },
};

const FEEDING_SOURCE_OPTIONS = [
  { id: "cook", label: "自己做" },
  { id: "takeout", label: "点外卖" },
];

const FEEDING_ADDITIVE_OPTIONS = [
  { id: "none", label: "不加料" },
  { id: "body_fluid", label: "体液" },
  { id: "fictional_sleep", label: "安眠" },
  { id: "fictional_arousal", label: "助兴" },
];

const FEEDING_WATER_OPTIONS = [
  { id: "none", label: "不额外喂水" },
  { id: "glass", label: "喂一杯水" },
  { id: "lots", label: "喂很多水" },
];

const RESPONSE_OPTIONS = [
  { id: "accept", label: "接受" },
  { id: "refuse", label: "拒绝" },
  { id: "silent", label: "沉默" },
  { id: "bargain", label: "讨价还价" },
  { id: "tease", label: "嘴硬" },
];

const MOOD_OPTIONS = ["平静", "黏人", "害羞", "闹脾气", "亢奋", "疲惫", "烦躁", "委屈", "低落", "抗拒"];

const DAY_SEGMENT_LABELS = ["早上", "中午", "傍晚"];

const NIGHT_ACTION_LABELS: Record<string, string> = {
  sleep: "老实睡觉",
  self_touch: "自慰",
  read: "看书",
  game: "玩游戏",
  listen_music: "听音乐",
  watch_video: "看视频",
  search_exit: "偷偷找出口",
  hide_item: "藏东西",
  diary: "写私密日记",
  blind_spot: "去监控盲区",
  ring_bell: "按铃",
  pet_wait: "按宠物规矩等候",
};

const DAY_ACTION_SELECTION_COPY: Record<string, string> = {
  feeding: "这一段从食物开始。端进房间的东西，由你决定。",
  cleaning: "水声会盖过房间里一部分动静，也会洗掉一部分痕迹。",
  training: "这一段会留下新的口令、姿势或规矩。",
  reward: "顺从会得到怎样的回应，由你决定。",
  punishment: "这次违令会被怎样记住，由你决定。",
  comfort: "强硬的部分结束后，要不要收一收力度，也由你决定。",
  rest: "门不会打开，但这一段时间可以暂时安静下来。",
  check: "灯会亮得更清楚，遗漏的痕迹也会被重新确认。",
  room_search: "床铺、角落和私藏物都会在这一段被重新翻查。",
};

const NIGHT_ACTION_SELECTION_COPY: Record<string, string> = {
  sleep: "房间里的灯还亮着，你决定先躺下。",
  self_touch: "你确认了一下门外的动静，准备把这一小段时间留给自己。",
  read: "书页会在安静的房间里发出很轻的声音。",
  game: "屏幕亮起后，房间里终于会多出一点别的光。",
  listen_music: "耳机里的声音会暂时盖过门外的动静。",
  watch_video: "平板的光会在黑下来的房间里格外明显。",
  search_exit: "你没有立刻靠近门，只是先重新打量整个房间。",
  hide_item: "你从已经收到的物品里选了一件，开始寻找不会被轻易发现的位置。",
  diary: "有些话不能说出口，但这一页会真正留下来，也可能被监控翻到。",
  blind_spot: "你开始留意镜头转开的方向和停留的时间。",
  ring_bell: "手指已经放在按钮上，按下去之后就不能假装没有发生。",
  pet_wait: "你戴着项圈回到指定位置，按主人留下的宠物规矩摆好姿势。",
};

const NIGHT_MONITOR_SCENE_COPY: Record<string, string> = {
  sleep: "画面里的人很早就躺下了，之后只剩偶尔翻身的动静。",
  self_touch: "被角和呼吸的起伏持续了一阵，监控完整留下了这段动静。",
  read: "画面里的人靠着床头翻书，偶尔会停在同一页很久。",
  game: "掌机的屏幕一直亮着，按键声在安静的房间里断断续续。",
  listen_music: "画面里的人戴着耳机，几乎没有注意门外的声音。",
  watch_video: "平板的光映在脸上，画面明暗跟着视频不断变化。",
  search_exit: "画面里的人沿着房间边缘慢慢移动，反复检查几个位置。",
  hide_item: "画面里的人背对镜头停留了一会，随后若无其事地回到原处。",
  diary: "画面里的人低头写了很久，写完后立刻把本子合上。",
  blind_spot: "人影从画面边缘消失了一阵，回来时位置已经变了。",
  ring_bell: "呼叫铃亮了一次，按下按钮的人没有立刻把手收回去。",
  pet_wait: "画面里的人戴着项圈回到指定位置，按规矩维持着被要求的姿势。",
};

const NIGHT_DETAIL_MONITOR_SCENE_COPY: Record<string, string> = {
  follow_bookmark: "书页沿着原来的书签继续往后翻，停在被特意折过的位置。",
  inspect_margins: "画面里的人把书凑近灯光，逐页寻找页边留下的笔迹。",
  reread_marked_page: "同一页被反复读了很久，指尖一直停在被标记的句子旁。",
  read_aloud: "房间里响起很轻的念书声，断断续续地持续了一阵。",
  continue_save: "旧存档被重新打开，掌机画面一路推进到新的区域。",
  inspect_profile: "画面停在用户资料页很久，似乎发现了之前没留意的内容。",
  challenge_mode: "按键声越来越快，屏幕上的分数不断刷新。",
  start_new_save: "唯一的空存档位被选中，一个新的记录从今晚开始。",
  door_lock: "画面里的人贴近门锁，手指沿着锁孔和门缝检查了几遍。",
  window: "窗边的人影停了很久，似乎在确认窗扣和外面的高度。",
  room_route: "画面里的人反复走过同一段路线，像是在默记距离。",
  outside_sound: "人影贴在门边没有动作，只是在听外面的脚步声。",
  inventory_book: "书被合上后没有放回原位，而是消失在镜头难以看清的角落。",
  inventory_switch: "掌机屏幕熄灭后，被悄悄藏进了房间里。",
  inventory_notebook: "日记本被压进一个不容易被翻到的位置。",
  inventory_music_player: "音乐播放器被攥在手里带离原处，之后没有再出现在画面中。",
  inventory_tablet: "平板被关屏后藏了起来，原来的位置只剩一块空白。",
  inventory_call_bell: "呼叫铃被从显眼的位置挪走，藏到了伸手仍能碰到的地方。",
  record_day: "日记本写满了一页，内容从白天一直记到现在。",
  write_feelings: "写字的人几次停笔，最后还是把那一页写完了。",
  record_rules: "几条现有规矩被逐条写下，又重新排列了一遍。",
  escape_plan: "纸页上画出了简略路线，写完后立刻被合上。",
  camera_angle: "画面里的人一直抬头观察镜头转向，像在计算角度。",
  stay_hidden: "监控有一段时间只拍到空房间，直到人影重新出现。",
  move_item: "镜头边缘的物品被悄悄换了位置。",
  test_duration: "人影数次进出盲区，每次停留都比上一次更久。",
  kneel_wait: "画面里的人在指定位置跪坐下来，之后一直没有离开。",
  prone_wait: "人影按要求伏在指定位置，长时间维持着同一个姿势。",
  collared_wait: "项圈始终留在画面中央，被要求等候的人没有擅自摘下。",
  hold_command: "口令结束后，画面里的人仍保持着被指定的姿势。",
};

const DEFAULT_NIGHT_ACTIONS = ["sleep", "self_touch", "search_exit", "blind_spot"];

const NIGHT_DETAIL_OPTIONS: Record<string, Array<{ id: string; label: string }>> = {
  read: [
    { id: "follow_bookmark", label: "沿着书签继续读" },
    { id: "inspect_margins", label: "找页边批注" },
    { id: "reread_marked_page", label: "重读被标记的那页" },
    { id: "read_aloud", label: "小声念出来" },
  ],
  game: [
    { id: "continue_save", label: "继续现有存档" },
    { id: "inspect_profile", label: "查看用户资料" },
    { id: "challenge_mode", label: "挑战更高难度" },
    { id: "start_new_save", label: "新建一个存档" },
  ],
  search_exit: [
    { id: "door_lock", label: "检查门锁" },
    { id: "window", label: "检查窗户" },
    { id: "room_route", label: "记住房间路线" },
    { id: "outside_sound", label: "听门外动静" },
  ],
  diary: [
    { id: "record_day", label: "记录今天发生的事" },
    { id: "write_feelings", label: "写下此刻心情" },
    { id: "record_rules", label: "整理现有规则" },
    { id: "escape_plan", label: "写下逃跑计划" },
  ],
  blind_spot: [
    { id: "camera_angle", label: "观察镜头转向" },
    { id: "stay_hidden", label: "躲一会" },
    { id: "move_item", label: "偷偷移动东西" },
    { id: "test_duration", label: "试探能停留多久" },
  ],
  pet_wait: [
    { id: "kneel_wait", label: "跪坐等候" },
    { id: "prone_wait", label: "趴伏等候" },
    { id: "collared_wait", label: "戴着项圈等候" },
    { id: "hold_command", label: "按口令保持姿势" },
  ],
};

const MONITOR_HANDLE_OPTIONS = [
  { id: "silent", label: "看见但不说" },
  { id: "review_later", label: "明天再处理" },
  { id: "intervene", label: "当场介入" },
];

const MONITOR_STYLE_LABELS: Record<string, string> = {
  occasional: "偶尔看",
  full: "全程看",
};

const MONITOR_RECORD_HANDLE_LABELS: Record<string, string> = {
  none: "不看",
  silent: "看见但不说",
  review_later: "明天再处理",
  intervene: "当场介入",
};

const ESCAPE_OPTIONS = [
  { id: "escape", label: "尝试逃跑" },
  { id: "stay", label: "老实待着" },
];

const ESCAPE_CONFIRM_STEPS = [
  {
    prompt: "真的要逃跑吗？",
    title: "钥匙就在手边。",
    text: "只要伸手就能拿到。现在停下，还什么都没有发生。",
    continueLabel: "伸手拿钥匙",
    stayLabel: "老实待着",
    abortChoice: "abort_before_key",
  },
  {
    prompt: "还要继续吗？",
    title: "钥匙已经拿到了。",
    text: "门锁就在前面。现在把钥匙放回去，也许还能装作只是看了一眼。",
    continueLabel: "走到门边",
    stayLabel: "把钥匙放回去",
    abortChoice: "abort_with_key",
  },
  {
    prompt: "要推开门吗？",
    title: "门已经开了一条缝。",
    text: "都走到这里了，还要回头吗？",
    continueLabel: "推门逃跑",
    stayLabel: "停下",
    abortChoice: "abort_at_door",
  },
];

const ESCAPE_CHOICE_LABELS: Record<string, string> = {
  escape: "尝试逃跑",
  stay: "老实待着",
  abort_before_key: "逃跑未遂：临时退缩",
  abort_with_key: "逃跑未遂：拿到钥匙后退缩",
  abort_at_door: "逃跑未遂：开门后退缩",
  observe: "观察",
  take_key: "拿钥匙",
  probe: "试探",
  leave_trace: "试探",
};

const RECAPTURE_RULE_OPTIONS = [
  { id: "double_lock", label: "加装双重门锁" },
  { id: "key_isolation", label: "禁止接触钥匙和门锁" },
  { id: "movement_limit", label: "限制离开指定区域" },
  { id: "daily_search", label: "每日搜查" },
  { id: "monitoring_upgrade", label: "加强全天监控" },
  { id: "item_restriction", label: "限制持有物品" },
  { id: "permission_required", label: "行动前必须得到许可" },
  { id: "restraint_required", label: "独处时保持束缚" },
];

const RECAPTURE_FOLLOWUP_OPTIONS = [
  { id: "punishment", label: "惩戒" },
  { id: "search_confiscation", label: "搜查没收" },
  { id: "monitoring_upgrade", label: "加强监控" },
  { id: "movement_restriction", label: "限制行动" },
  { id: "training", label: "调教" },
  { id: "aftercare", label: "事后照料" },
];

const ESCAPE_ROOM_OPTIONS = [
  { id: "entry", label: "玄关", bait: "备用钥匙压在玄关地垫下面" },
  { id: "living", label: "客厅", bait: "备用钥匙藏在客厅茶几抽屉里" },
  { id: "bedroom", label: "卧室", bait: "备用钥匙放在卧室床头柜后面" },
  { id: "bathroom", label: "浴室", bait: "备用钥匙贴在浴室洗手台底下" },
  { id: "study", label: "书房", bait: "备用钥匙夹在书房第二层书架里" },
  { id: "kitchen", label: "厨房", bait: "备用钥匙藏在厨房调料架后面" },
  { id: "storage", label: "储物间", bait: "备用钥匙挂在储物间门后的旧挂钩上" },
  { id: "balcony", label: "阳台", bait: "备用钥匙压在阳台花盆底下" },
] as const;
type EscapeRoomId = (typeof ESCAPE_ROOM_OPTIONS)[number]["id"];

function escapeRoomBait(roomId: EscapeRoomId | string): string {
  return ESCAPE_ROOM_OPTIONS.find((item) => item.id === roomId)?.bait || ESCAPE_ROOM_OPTIONS[0].bait;
}

function defaultPlanSlots(): PlanSlot[] {
  return [
    {
      action: "feeding",
      intensity: "medium",
      modifiers: [],
      tools: [],
      contents: [],
      trainingContents: [],
      line: "",
      feedingSource: "cook",
      feedingAdditive: "none",
    },
    {
      action: "cleaning",
      intensity: "light",
      modifiers: [],
      tools: [],
      contents: [],
      trainingContents: [],
      line: "",
      feedingSource: "cook",
      feedingAdditive: "none",
    },
    {
      action: "training",
      intensity: "medium",
      modifiers: [],
      tools: ["collar"],
      contents: [],
      trainingContents: ["obedience_commands"],
      line: "",
      feedingSource: "cook",
      feedingAdditive: "none",
    },
  ];
}

function defaultContentsForAction(action: string): string[] {
  const options = ACTION_CONTENT_OPTIONS[action] || [];
  return options.length ? [options[0].id] : [];
}

function clampPercent(value: unknown): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, Math.round(n)));
}

function labelOf(options: Array<{ id: string; label: string }>, id: unknown): string {
  const raw = String(id || "");
  return options.find((item) => item.id === raw)?.label || raw || "未设置";
}

function actionLabel(action: unknown): string {
  return labelOf(ACTION_OPTIONS, action);
}

function intensityLabel(intensity: unknown): string {
  return labelOf(INTENSITY_OPTIONS, intensity);
}

function nightActionLabel(action: unknown): string {
  const raw = String(action || "");
  return NIGHT_ACTION_LABELS[raw] || raw || "未设置";
}

function modifierLabel(modifier: unknown): string {
  if (String(modifier || "") === "process") return "";
  if (String(modifier || "") === "escape") return "逃跑";
  return labelOf(MODIFIER_OPTIONS, modifier);
}

function actionContentLabel(content: unknown): string {
  const raw = String(content || "");
  const options = Object.values(ACTION_CONTENT_OPTIONS).flat();
  return labelOf(options, raw);
}

function trainingContentLabel(content: unknown): string {
  return labelOf(TRAINING_CONTENT_OPTIONS, content);
}

function visibleModifierLabels(modifiers: unknown[] | undefined): string[] {
  return (modifiers || []).map(modifierLabel).filter(Boolean);
}

function interventionIntentLabel(intent: unknown): string {
  return labelOf(INTERVENTION_INTENT_OPTIONS, intent);
}

function interventionModifierLabel(modifier: unknown): string {
  return labelOf(INTERVENTION_MODIFIER_OPTIONS, modifier);
}

function monitorStyleLabel(style: unknown): string {
  const raw = String(style || "");
  return MONITOR_STYLE_LABELS[raw] || raw || "未查看";
}

function monitorHandleLabel(handle: unknown): string {
  const raw = String(handle || "");
  return MONITOR_RECORD_HANDLE_LABELS[raw] || raw || "未处理";
}

function escapeChoiceLabel(choice: unknown): string {
  const raw = String(choice || "");
  return ESCAPE_CHOICE_LABELS[raw] || raw || "未记录";
}

function monitorRecordTime(record: DeferredMonitorMaterial | CaptivityEvent): string {
  const day = Number(record.day || 1);
  const phase = "phase" in record ? record.phase : "night";
  return `第 ${day} 天 / ${phase === "night" ? "夜间" : "白天"}`;
}

function monitorRecordSummary(record: DeferredMonitorMaterial | CaptivityEvent): string {
  const action = record.action_label || nightActionLabel(record.action) || actionLabel(record.action) || "夜间行动";
  const detail = (record as CaptivityEvent).night_detail?.label || (record as DeferredMonitorMaterial).detail_label;
  const line = "line" in record ? textLine(record.line) : "";
  const summary = detail ? `${action}（${detail}）` : action;
  return line ? `${summary}：${line}` : summary;
}

function monitorRecordSceneCopy(record: DeferredMonitorMaterial | CaptivityEvent): string {
  const event = record as CaptivityEvent;
  const detailId = String(event.night_detail?.id || "");
  if (detailId && NIGHT_DETAIL_MONITOR_SCENE_COPY[detailId]) return NIGHT_DETAIL_MONITOR_SCENE_COPY[detailId];
  const action = String(record.action || "");
  return NIGHT_MONITOR_SCENE_COPY[action] || "监控保留了这一段画面，房间里的动静已经写进记录。";
}

function statusAtmosphereCopy(stats: CaptivityStats, mood: string | undefined, role: UserRole, flags: StatusFlag[] = []): string {
  const health = clampPercent(stats.health);
  const stamina = clampPercent(stats.stamina);
  const cleanliness = clampPercent(stats.cleanliness);
  const shame = clampPercent(stats.shame);
  const intimacy = clampPercent(stats.intimacy);
  if (health < 30) return role === "captor" ? "状态读数不太好，今天的安排需要留意身体承受程度。" : "身体的不适已经很明显，连安静待着都很难完全忽略。";
  if (stamina < 20) return role === "captor" ? "体力读数已经接近下限，高强度安排暂时不合适。" : "四肢有些发沉，稍微动一下都比平时更费力。";
  if (cleanliness < 25) return role === "captor" ? "监控里还能看见没处理干净的痕迹。" : "身上还留着没有处理干净的痕迹，很难不去在意。";
  if (flags.some((flag) => flag.id === "pet_identity_active")) return role === "captor" ? "项圈和定点规矩仍在生效，监控会继续记录是否遵守。" : "项圈和现有规矩仍在提醒你，房间里哪些位置属于你。";
  if (shame >= 70) return role === "captor" ? "羞耻反馈已经很明显，简单的注视也足够留下影响。" : "只是想起之前发生的事，脸上就又开始发热。";
  if (intimacy >= 70) return role === "captor" ? "依赖已经变得稳定，短暂离开也会引起明显反应。" : "房间安静得太久时，你会下意识去听门外有没有脚步声。";
  const captiveMoodCopy: Record<string, string> = {
    黏人: "门外一点轻微的动静，都会让注意力立刻转过去。",
    害羞: "视线落到监控指示灯上时，还是会本能地移开。",
    闹脾气: "房间里的每一样东西看起来都比平时更碍眼。",
    亢奋: "身体还没有完全安静下来，连时间都像过得更慢。",
    疲惫: "现在最明显的感觉只剩下累。",
    烦躁: "安静没有带来放松，反而让每一点声音都更清楚。",
    委屈: "有些话堵在心里，没有找到合适的时机说出来。",
    低落: "房间似乎比平时更空，也更安静。",
    抗拒: "现有的安排没有让戒备真正放下来。",
  };
  const captorMoodCopy: Record<string, string> = {
    黏人: "监控里的注意力总会被门外动静带走，等待已经变得明显。",
    害羞: "对方仍会下意识避开镜头，尤其是在意识到有人可能正看着时。",
    闹脾气: "监控里的动作比平时更重，情绪没有被藏得很好。",
    亢奋: "状态迟迟没有安静下来，夜间反应可能会更明显。",
    疲惫: "动作和反应都慢了下来，现在最需要的是恢复体力。",
    烦躁: "对方频繁留意房间里的声音，安静没有带来放松。",
    委屈: "有些话没有直接说出来，但情绪已经留在动作里。",
    低落: "监控里的活动明显变少，房间显得比平时更空。",
    抗拒: "戒备仍然很明显，现有安排还没有让对方放松下来。",
  };
  const moodCopy = role === "captor" ? captorMoodCopy : captiveMoodCopy;
  if (mood && moodCopy[mood]) return moodCopy[mood];
  return role === "captor" ? "状态读数暂时平稳，今天仍可以按原定节奏继续。" : "房间暂时很安静，身体也没有新的不适。";
}

function dayMilestoneCopy(day: number, role: UserRole): string {
  const copies: Record<number, [string, string]> = {
    7: ["房间里的生活开始有了固定的节奏。", "监控和事件记录已经积累了整整一周。"],
    15: ["日历已经翻过一半，有些声音和规矩变得越来越熟悉。", "三十天已经过半，许多反应不再需要反复确认。"],
    23: ["日历只剩下最后几页，房间里的时间却没有因此变快。", "记录进入最后阶段，之前留下的选择正在彼此叠加。"],
    30: ["第三十天到了，门外的脚步声和往常听起来不太一样。", "最后一天的画面已经亮起，所有记录都在等待收束。"],
  };
  return copies[day]?.[role === "captor" ? 1 : 0] || "";
}

function runtimeBridgeCopy(view: CaptivityView, pending: CaptivityPending | null, role: UserRole): string {
  const type = String(pending?.type || "");
  const actor = String(pending?.actor || "");
  if (type === "advance_action") return "这一段已经收进记录，下一段安排还没有开始。";
  if (type === "action_response") return role === "captive" ? "你的回应会和这一段一起留下。" : "这项安排已经送达，正在等对方回应。";
  if (type === "reaction_choice") return "具体经过已经结束，此刻的心情会成为这一段的结尾。";
  if (type === "process_write" || type === "process_reaction_write") return "事件素材已经送出，具体经过仍在另一边继续。";
  if (type === "monitor_gate") return "夜间记录已经封存，监控另一端还没有作出选择。";
  if (type === "monitor_handle") return "这段监控已经打开，接下来只差如何处理。";
  if (type === "day_plan_choice") return role === "captor" ? "新一天还没有安排，三个时段都在等你落笔。" : "新一天的安排还没有送到，房间暂时没有新的动静。";
  if (actor === "assistant") return "这一步已经交到另一边，房间暂时安静下来。";
  if (String(view.phase || "") === "night") return "白天的记录已经结束，夜间仍会留下自己的痕迹。";
  return "";
}

function waitAtmosphereCopy(wait: WaitState): string {
  if (wait.error) return "这次交接没有完成，已经完成的本地记录仍然保留着。";
  const title = String(wait.title || "");
  if (title.includes("同步")) return "这段记录已经送出，另一边正在决定接下来怎么做。";
  if (title.includes("保存") || title.includes("封存") || title.includes("记录")) return "刚才的选择正在写进今天的记录。";
  if (title.includes("监控")) return "监控画面正在解锁，夜里的动静很快就会重新出现。";
  if (title.includes("进入") || title.includes("推进")) return "这一段已经结束，时间正在向下一格移动。";
  return "当前操作正在写入本地规则状态。";
}

function toolLabel(tool: unknown): string {
  return labelOf(TOOL_OPTIONS, tool);
}

function feedingValueLabel(key: string, value: unknown): string {
  const raw = String(value || "");
  if (!raw) return "";
  if (key === "source") return labelOf(FEEDING_SOURCE_OPTIONS, raw);
  if (key === "additive") return labelOf(FEEDING_ADDITIVE_OPTIONS, raw);
  if (key === "water") return labelOf(FEEDING_WATER_OPTIONS, raw);
  if (key === "method") return raw === "normal" ? "正常喂食" : raw;
  if (key === "disclosed") return ({ told: "已经告知", hint: "有所暗示", hidden: "没有告知" } as Record<string, string>)[raw] || raw;
  return raw;
}

function timeSegmentLabel(view: CaptivityView, pending: CaptivityPending | null): string {
  const phase = String(view.phase || "day");
  if (view.game_over || phase === "ending") return "结局";
  if (phase === "night") return "晚上";
  const limit = Math.max(1, Number(view.day_action_limit || 3));
  const pendingSlot = Number(pending?.slot || 0);
  const completed = Number(view.day_action_count || 0);
  const currentSlot = pendingSlot > 0 ? pendingSlot : Math.min(completed + 1, limit);
  return DAY_SEGMENT_LABELS[currentSlot - 1] || `第 ${currentSlot} 段`;
}

function quoteArg(value: string): string {
  const raw = String(value || "");
  if (!raw) return "\"\"";
  return `"${raw.replace(/(["\\$`])/g, "\\$1")}"`;
}

function textLine(value: unknown): string {
  return String(value || "").trim();
}

function displayActor(actor: unknown): string {
  const raw = String(actor || "");
  if (raw === "assistant") return "{assistant}";
  if (raw === "user") return "我";
  return raw || "SYSTEM";
}

function payloadRoute(payload: CaptivityPayload | null): RouteKey | "" {
  const raw = String(payload?.captor_view?.route || payload?.captive_view?.route || payload?.state?.route || "");
  return raw === "capture_assistant" || raw === "captured_by_assistant" ? raw : "";
}

function roleFromPayload(payload: CaptivityPayload | null): UserRole {
  return payloadRoute(payload) === "capture_assistant" ? "captor" : "captive";
}

function viewFromPayload(payload: CaptivityPayload | null): CaptivityView {
  if (!payload) return {};
  const nextRole = roleFromPayload(payload);
  if (nextRole === "captor") return payload.captor_view?.route ? payload.captor_view : (payload.captive_view || payload.state || {});
  return payload.captive_view || payload.state || {};
}

function processEventKey(event: CaptivityEvent | undefined | null): string {
  if (!event) return "";
  const text = textLine(event.process_text);
  if (!text) return "";
  return [
    event.id,
    event.day,
    event.slot,
    event.phase,
    event.action,
    event.process_saved_at || event.resolved_at || "",
    text.length,
  ].filter((part) => part !== undefined && part !== null && String(part) !== "").join(":");
}

function processKeysFromPayload(payload: CaptivityPayload | null): Set<string> {
  const view = viewFromPayload(payload);
  const keys = new Set<string>();
  const pendingEvent = view.pending_event?.event;
  const pendingKey = processEventKey(pendingEvent);
  if (pendingKey) keys.add(pendingKey);
  (view.event_log || []).forEach((event) => {
    const key = processEventKey(event);
    if (key) keys.add(key);
  });
  return keys;
}

function findNewProcessReview(next: CaptivityPayload, previous: CaptivityPayload | null): ProcessReview | null {
  const view = viewFromPayload(next);
  const beforeKeys = processKeysFromPayload(previous);
  const pendingEvent = view.pending_event?.event;
  const candidates = [
    pendingEvent,
    ...(view.event_log || []).slice().reverse(),
  ].filter(Boolean) as CaptivityEvent[];

  for (const event of candidates) {
    const key = processEventKey(event);
    if (!key || beforeKeys.has(key)) continue;
    const pendingKey = processEventKey(pendingEvent);
    const pendingType = String(view.pending_event?.type || "");
    const pendingActor = String(view.pending_event?.actor || "");
    return {
      event,
      text: textLine(event.process_text),
      moodRequired: roleFromPayload(next) === "captive"
        && pendingType === "reaction_choice"
        && pendingActor !== "assistant"
        && pendingKey === key,
    };
  }
  return null;
}

function processReviewTransition(review: ProcessReview): SceneCopy {
  const event = review.event;
  const action = textLine(event.action_label || actionLabel(event.action) || "这一段行动");
  return {
    key: `process:${processEventKey(event)}`,
    kicker: `DAY ${String(event.day || 1).padStart(2, "0")} / ${action}`,
    title: action,
    body: "门锁在身后合上，房间里只剩下你们。接下来的一切，从这里开始。",
    tone: "special",
  };
}

function nextStageTransition(next: CaptivityPayload): SceneCopy {
  const view = viewFromPayload(next);
  const pending = view.pending_event || {};
  const phase = String(view.phase || "day");
  const day = Number(view.current_day || 1);
  const pendingSlot = Number(pending.slot || 0);
  const slot = pendingSlot > 0 ? pendingSlot : Math.min(Number(view.day_action_count || 0) + 1, 3);
  const title = phase === "night" ? "晚上" : ({ 1: "早上", 2: "中午", 3: "傍晚" } as Record<number, string>)[slot] || "下一段";
  const waitingAdvance = String(pending.type || "") === "advance_action";
  const body = phase === "night"
    ? "白天的行动已经收进回顾。房间重新安静下来，夜间的安排将从这里开始。"
    : waitingAdvance
      ? "上一段已经收进回顾。下一项安排仍停在这里，等你亲手推进。"
      : "上一段已经收进回顾。短暂的间隔过去，下一项安排即将开始。";
  return {
    key: `after-process:${day}:${phase}:${slot}:${String(pending.type || "idle")}`,
    kicker: `DAY ${String(day).padStart(2, "0")} / NEXT`,
    title,
    body,
    tone: phase === "night" ? "night" : "day",
  };
}

function readProcessPreviewRole(): UserRole | "" {
  if (!import.meta.env.DEV || typeof window === "undefined") return "";
  const value = new URLSearchParams(window.location.search).get("captivity_process_preview");
  return value === "captor" || value === "captive" ? value : "";
}

function readPlanPreviewRole(): UserRole | "" {
  if (!import.meta.env.DEV || typeof window === "undefined") return "";
  return new URLSearchParams(window.location.search).get("captivity_plan_preview") === "captor" ? "captor" : "";
}

function readPlanPreviewSlot(): 1 | 2 | 3 {
  if (!import.meta.env.DEV || typeof window === "undefined") return 1;
  const slot = Number(new URLSearchParams(window.location.search).get("captivity_plan_slot") || 1);
  return slot === 2 || slot === 3 ? slot : 1;
}

function readNightPreviewRole(): UserRole | "" {
  if (!import.meta.env.DEV || typeof window === "undefined") return "";
  return new URLSearchParams(window.location.search).get("captivity_night_preview") === "captive" ? "captive" : "";
}

function readEscapePreviewRole(): UserRole | "" {
  if (!import.meta.env.DEV || typeof window === "undefined") return "";
  const value = new URLSearchParams(window.location.search).get("captivity_escape_preview");
  return value === "captor" || value === "captive" ? value : "";
}

function readEndingPreviewRole(): UserRole | "" {
  if (!import.meta.env.DEV || typeof window === "undefined") return "";
  const value = new URLSearchParams(window.location.search).get("captivity_ending_preview");
  return value === "captor" || value === "captive" ? value : "";
}

function buildPlannerPreview(): CaptivityPayload {
  const slot = readPlanPreviewSlot();
  const sceneBySlot: Record<1 | 2 | 3, SceneCopy> = {
    1: {
      key: "preview-captor-morning",
      kicker: "DAY 07 / 早上",
      title: "早上",
      body: "监控画面安静地亮着。{assistant}还在房间里，今天要怎样度过，由你安排。",
      tone: "day",
    },
    2: {
      key: "preview-captor-noon",
      kicker: "DAY 07 / 中午",
      title: "中午",
      body: "第一段行动已经结束。{assistant}仍留在房间里，下一项安排正在等你推进。",
      tone: "day",
    },
    3: {
      key: "preview-captor-evening",
      kicker: "DAY 07 / 傍晚",
      title: "傍晚",
      body: "白天只剩最后一段安排。它结束以后，房间里的夜晚将由{assistant}自己留下记录。",
      tone: "day",
    },
  };
  const view: CaptivityView = {
    route: "capture_assistant",
    route_label: "囚禁方",
    viewer: "captor",
    current_day: 7,
    total_days: 30,
    day_action_count: slot - 1,
    day_action_limit: 3,
    phase: "day",
    captive: "assistant",
    captive_name: "被囚禁方",
    captor: "user",
    stats: { health: 80, stamina: 68, cleanliness: 72, shame: 34, intimacy: 41 },
    mood: "害羞",
    intensity_cap: "heavy",
    scene_copy: sceneBySlot[slot],
    pending_event: slot === 1 ? null : {
      id: `preview-captor-slot-${slot}`,
      type: "advance_action",
      actor: "user",
      day: 7,
      slot,
    },
    event_log: [
      {
        id: "preview-monitor-bell",
        day: 4,
        slot: 0,
        phase: "night",
        action: "ring_bell",
        action_label: "按铃",
        monitor: { viewed: true, style: "full", strategy: "intervene" },
      },
      {
        id: "preview-monitor-door-lock",
        day: 5,
        slot: 0,
        phase: "night",
        action: "search_exit",
        action_label: "偷偷找出口",
        night_detail: { id: "door_lock", label: "检查门锁" },
        monitor: { viewed: true, style: "occasional", strategy: "review_later" },
      },
      {
        id: "preview-monitor-game",
        day: 6,
        slot: 0,
        phase: "night",
        action: "game",
        action_label: "玩游戏",
        monitor: { viewed: true, style: "full", strategy: "silent" },
      },
    ],
    day_plan: [],
    inventory: {},
  };
  return {
    ok: true,
    captor_view: view,
    player_text: "本地预览：配置今日安排。",
  };
}

function buildNightPreview(): CaptivityPayload {
  const view: CaptivityView = {
    route: "captured_by_assistant",
    route_label: "被囚禁方",
    viewer: "captive",
    current_day: 7,
    total_days: 30,
    day_action_count: 3,
    day_action_limit: 3,
    phase: "night",
    captive: "user",
    captive_name: "被囚禁方",
    stats: { health: 27, stamina: 18, cleanliness: 16, shame: 48, intimacy: 41 },
    mood: "害羞",
    status_flags: [
      { id: "low_health", label: "需要照料", prompt: "健康偏低，高强度行动暂不可选。" },
      { id: "low_stamina", label: "体力不足", prompt: "体力不足，高强度行动暂不可选。" },
      { id: "low_cleanliness", label: "建议清洗", prompt: "清洁度偏低，建议优先安排清洗。" },
      { id: "heightened_shame", label: "羞耻升高", prompt: "羞耻反馈已经更明显。" },
      { id: "pet_identity_active", label: "小狗身份中", prompt: "当前处于小狗身份。现有规矩：佩戴项圈并接受小狗身份、在指定位置等候。" },
    ],
    intensity_cap: "medium",
    scene_copy: {
      key: "preview-captive-night",
      kicker: "DAY 07 / 晚上",
      title: "晚上",
      body: "白天的三次安排已经结束。房间重新安静下来，接下来这段时间暂时属于你。",
      tone: "night",
    },
    pending_event: null,
    event_log: [],
    inventory: { notebook: true, book: true, switch: true, call_bell: true },
    available_night_actions: ["sleep", "self_touch", "read", "game", "search_exit", "hide_item", "diary", "blind_spot", "ring_bell", "pet_wait"],
    night_detail_options: {
      ...Object.fromEntries(Object.entries(NIGHT_DETAIL_OPTIONS).map(([action, options]) => [
        action,
        Object.fromEntries(options.map((option) => [option.id, option.label])),
      ])),
      hide_item: {
        inventory_book: "藏起书",
        inventory_switch: "藏起Switch",
        inventory_notebook: "藏起日记本",
        inventory_call_bell: "藏起呼叫铃",
      },
    },
  };
  return {
    ok: true,
    captive_view: view,
    player_text: "本地预览：夜间自由行动。",
  };
}

function buildEscapePreview(role: UserRole = "captive"): CaptivityPayload {
  const route: RouteKey = role === "captor" ? "capture_assistant" : "captured_by_assistant";
  const captive = role === "captor" ? "assistant" : "user";
  const captor = role === "captor" ? "user" : "assistant";
  const view: CaptivityView = {
    route,
    route_label: role === "captor" ? "囚禁方" : "被囚禁方",
    viewer: role,
    current_day: 12,
    total_days: 30,
    day_action_count: 0,
    day_action_limit: 3,
    phase: "day",
    captive,
    captive_name: "被囚禁方",
    captor,
    stats: { health: 76, stamina: 61, cleanliness: 70, shame: 42, intimacy: 47 },
    mood: "紧张",
    scene_copy: {
      key: `preview-escape-${role}`,
      kicker: "SPECIAL DAY",
      title: "今天，{assistant}没有出现",
      body: "门外安静得反常。直到你发现，备用钥匙正压在玄关地垫下面。",
      tone: "special",
    },
    pending_event: role === "captor" ? {
      id: "preview-recapture-rules-after-process",
      type: "recapture_rules_choice",
      day: 12,
      slot: 0,
      actor: "user",
      captive: "assistant",
      phase: "waiting_recapture_rules",
      source_event_id: "preview-assistant-recapture-process",
      available_rules: RECAPTURE_RULE_OPTIONS.map((item) => item.id),
      event: {
        id: "preview-assistant-recapture-process",
        day: 12,
        slot: 0,
        phase: "day",
        route: "capture_assistant",
        action: "escape_choice",
        action_label: "逃跑失败：被抓回",
        tags: ["preview", "escape", "recapture", "rules_reset"],
        escape: { choice: "escape", choice_label: "尝试逃跑" },
        process_text: "{assistant}写下的抓回经过已经保存。",
        process_saved_at: "preview-local",
      },
    } : {
      id: "preview-escape-choice",
      type: "escape_choice",
      day: 12,
      slot: 0,
      actor: captive,
      captive,
      phase: "waiting_escape_choice",
      hint: "{assistant}今天有事出去了。",
      bait: "备用钥匙压在玄关地垫下面。",
      required_directive: "resolve_escape_choice escape|stay",
    },
    event_log: [],
    inventory: { book: true, notebook: true, call_bell: true },
  };
  return {
    ok: true,
    captive_view: { ...view, viewer: "captive" },
    captor_view: { ...view, viewer: "captor" },
    player_text: "本地预览：逃跑诱导选择。",
  };
}

function buildEndingPreview(role: UserRole = "captive"): CaptivityPayload {
  const route: RouteKey = role === "captor" ? "capture_assistant" : "captured_by_assistant";
  const title = role === "captor" ? "余生" : "长夜";
  const text = role === "captor"
    ? "第三十天结束时，你和{assistant}照旧完成进食、清洁、夜间安排与监控，没有人为这场生活按下结束。日历翻到第三十一天，你照常推门进来，{assistant}也照常望向你。余下的日期仍是一片空白。"
    : "第三十天夜里，{assistant}照常看过监控记录，带着你最常用的礼物回到房间。你们已经熟悉彼此的回应与沉默。灯熄灭后房门依旧关闭，你在黑暗里握住他的手；这一夜不会在清晨结束。";
  const view: CaptivityView = {
    route,
    route_label: role === "captor" ? "囚禁方" : "被囚禁方",
    viewer: role,
    current_day: 30,
    total_days: 30,
    day_action_count: 3,
    day_action_limit: 3,
    phase: "ending",
    captive: role === "captor" ? "assistant" : "user",
    captive_name: "被囚禁方",
    captor: role === "captor" ? "user" : "assistant",
    stats: { health: 74, stamina: 58, cleanliness: 70, shame: 62, intimacy: 79 },
    pending_event: null,
    event_log: [],
    ending_state: "ending_ready_to_notify",
    ending_title: title,
    ending_text: text,
    ending_notified_at: "",
    game_over: true,
    result: "ending_ready_to_notify",
  };
  return {
    ok: true,
    game_over: true,
    state: view,
    captive_view: { ...view, viewer: "captive" },
    captor_view: { ...view, viewer: "captor" },
    player_text: `本地预览：结局「${title}」。`,
  };
}

function buildEscapeRecaptureReview(
  payload: CaptivityPayload | null,
  role: UserRole = "captive",
  choice = "escape",
): { payload: CaptivityPayload; review: ProcessReview } {
  const currentView = viewFromPayload(payload || buildEscapePreview(role));
  const abortedLabels: Record<string, string> = {
    abort_before_key: "临时退缩",
    abort_with_key: "拿到钥匙后退缩",
    abort_at_door: "开门后退缩",
  };
  const choiceLabel = choice === "escape" ? "尝试逃跑" : `逃跑未遂：${abortedLabels[choice] || "中途退缩"}`;
  const opening = choice === "abort_before_key"
    ? "手已经伸向了钥匙，却在碰到它之前停了下来。"
    : choice === "abort_with_key"
      ? "钥匙已经被握进手里，又被迟疑着放回了原处。"
      : choice === "abort_at_door"
        ? "门已经开了一条缝，最后却还是停在了门边。"
        : "门把手刚被压下去，玄关外便传来了停在近处的脚步声。";
  const event: CaptivityEvent = {
    id: "preview-escape-recapture",
    day: 12,
    slot: 0,
    phase: "day",
    route: role === "captor" ? "capture_assistant" : "captured_by_assistant",
    action: "escape_choice",
    action_label: choice === "escape" ? "逃跑失败：被抓回" : choiceLabel,
    intensity: "medium",
    modifiers: ["escape"],
    tools: [],
    contents: [],
    training_contents: [],
    tags: ["preview", "escape", `escape:${choice}`, "recapture", "rules_reset"],
    feeding: {},
    effects: { health: 0, stamina: -8, cleanliness: 0, shame: 5, intimacy: 0 },
    escape: { choice, choice_label: choiceLabel },
    recapture_rules: role === "captive" ? {
      rule_ids: ["double_lock", "key_isolation"],
      rule_labels: ["加装双重门锁", "禁止接触钥匙和门锁"],
    } : undefined,
    requires_process: true,
    process_saved_at: "preview-local",
    process_text: [
      opening,
      "",
      "备用钥匙是真的，留下的空隙也是真的；但从点下尝试逃跑的那一刻起，一举一动就已经落进了观察范围里。停下来并没有让这次试探消失。",
      "",
      "门重新在身后落锁，钥匙也被收走。房间恢复安静，只剩下逃跑失败后尚未说出口的新规矩。",
    ].join("\n"),
  };
  const nextView: CaptivityView = {
    ...currentView,
    stats: { ...currentView.stats, stamina: 53, shame: 47 },
    pending_event: {
      id: "preview-escape-reaction",
      type: "reaction_choice",
      day: 12,
      slot: 0,
      actor: role === "captor" ? "assistant" : "user",
      captive: role === "captor" ? "assistant" : "user",
      phase: "waiting_reaction",
      event,
    },
  };
  return {
    payload: {
      ok: true,
      captive_view: nextView,
      captor_view: { ...nextView, viewer: "captor" },
      player_text: "本地预览：逃跑失败，抓回事件已经写入。",
    },
    review: {
      event,
      text: textLine(event.process_text),
      moodRequired: role === "captive",
    },
  };
}

function buildProcessPreview(role: UserRole): { payload: CaptivityPayload; review: ProcessReview } {
  const route: RouteKey = role === "captor" ? "capture_assistant" : "captured_by_assistant";
  const fakeEvent: CaptivityEvent = {
    id: `preview-process-${role}`,
    day: 7,
    slot: 2,
    phase: "day",
    route,
    action: "training",
    action_label: "服从调教",
    intensity: "medium",
    line: "今晚的规则重新确认一遍。",
    modifiers: [],
    contents: [],
    training_contents: ["obedience_commands", "leash_training"],
    tools: ["collar"],
    tags: ["preview", "process"],
    feeding: {},
    effects: { health: 0, stamina: -3, cleanliness: 0, shame: 4, intimacy: 2 },
    requires_process: true,
    process_saved_at: "preview-local",
    process_text: [
      "{assistant}写下了这一段事件经过。",
      "",
      "房间里的灯只留了一盏，所有动作都被压得很慢。对方先确认了今天的规则，又把项圈扣回原位，让这次训练从一句简短的回应开始。",
      "",
      "中途没有切走，也没有跳过过程；细节被完整记录下来，等你看完以后，再决定这件事结束后留下来的心情。",
    ].join("\n"),
    action_response: {
      response: "accept",
      response_label: "接受",
      mood: "害羞",
      line: "嗯。",
    },
  };
  const baseView: CaptivityView = {
    route,
    route_label: role === "captor" ? "囚禁方" : "被囚禁方",
    viewer: role,
    current_day: 7,
    total_days: 30,
    day_action_count: 1,
    day_action_limit: 3,
    phase: "day",
    captive: role === "captor" ? "assistant" : "user",
    captive_name: "被囚禁方",
    captor: role === "captor" ? "user" : "assistant",
    stats: { health: 80, stamina: 68, cleanliness: 72, shame: 34, intimacy: 41 },
    mood: "害羞",
    pending_event: role === "captive"
      ? {
        id: "preview-pending-reaction",
        type: "reaction_choice",
        day: 7,
        slot: 2,
        actor: "user",
        captive: "user",
        action: "training",
        phase: "waiting_reaction",
        event: fakeEvent,
      }
      : {
        id: "preview-pending-advance",
        type: "advance_action",
        day: 7,
        slot: 2,
        actor: "user",
        captive: "assistant",
        action: "training",
        phase: "waiting_advance",
        event: fakeEvent,
      },
    event_log: role === "captor" ? [fakeEvent] : [],
  };
  const payload: CaptivityPayload = role === "captor"
    ? {
      ok: true,
      captor_view: baseView,
      captive_view: { ...baseView, viewer: "captive" },
      player_text: "本地预览：事件经过阅读页。",
    }
    : {
      ok: true,
      captive_view: baseView,
      captor_view: { ...baseView, viewer: "captor" },
      player_text: "本地预览：事件经过阅读页。",
    };
  return {
    payload,
    review: {
      event: fakeEvent,
      text: textLine(fakeEvent.process_text),
      moodRequired: role === "captive",
    },
  };
}

function buildProcessPreviewAfterSave(role: UserRole, mood: string, line: string): CaptivityPayload {
  const preview = buildProcessPreview(role);
  const view = viewFromPayload(preview.payload);
  const archivedEvent: CaptivityEvent = {
    ...preview.review.event,
    post_reaction: role === "captive"
      ? {
        mood,
        line,
      }
      : preview.review.event.post_reaction,
    mood_after: role === "captive" ? mood : preview.review.event.mood_after,
  };
  const nextEvent: CaptivityEvent = {
    id: `preview-next-${role}`,
    day: 7,
    slot: 3,
    phase: "day",
    action: "reward",
    action_label: "奖励取悦",
    intensity: "light",
    line: "第三段安排已经接上来了。",
    modifiers: [],
    tools: [],
    contents: ["caress_reward"],
    training_contents: [],
    tags: ["preview", "next_action"],
    feeding: {},
    effects: { health: 1, stamina: -1, cleanliness: 0, shame: 1, intimacy: 1 },
    requires_process: false,
  };
  const nextPending: CaptivityPending = role === "captive"
    ? {
      id: "preview-next-action",
      type: "action_response",
      day: 7,
      slot: 3,
      actor: "user",
      captive: "user",
      action: "reward",
      phase: "waiting_response",
      event: nextEvent,
    }
    : {
      id: "preview-next-advance",
      type: "advance_action",
      day: 7,
      slot: 2,
      actor: "user",
      captive: "assistant",
      phase: "waiting_advance_action",
      required_directive: "advance_day_action",
    };
  const nextView: CaptivityView = {
    ...view,
    day_action_count: role === "captive" ? 2 : 1,
    pending_event: nextPending,
    event_log: [archivedEvent],
    mood: role === "captive" ? mood : view.mood,
    mood_line: role === "captive" ? line : view.mood_line,
  };
  return role === "captor"
    ? {
      ok: true,
      captor_view: nextView,
      captive_view: { ...nextView, viewer: "captive" },
      player_text: "本地预览：事件已保存，等待推进下一段行动。",
    }
    : {
      ok: true,
      captive_view: nextView,
      captor_view: { ...nextView, viewer: "captor" },
      player_text: "本地预览：事件已保存，下一段行动已经接上。",
    };
}

function hasMeaningfulProgress(view: CaptivityView | undefined): boolean {
  if (!view) return false;
  if (Number(view.current_day || 1) > 1) return true;
  if (Number(view.day_action_count || 0) > 0) return true;
  if (String(view.phase || "day") !== "day") return true;
  if (view.game_over || view.ending_state) return true;
  if ((view.event_log || []).length > 0) return true;
  if ((view.day_plan || []).length > 0) return true;
  const pendingType = String(view.pending_event?.type || "");
  return Boolean(pendingType);
}

function shouldResumeGame(payload: CaptivityPayload): boolean {
  const view = (payload.captor_view?.route === "capture_assistant" ? payload.captor_view : payload.captive_view || payload.state) || {};
  return hasMeaningfulProgress(view);
}

const COMMAND_ARG_PATTERN = /\b(?:action|intensity|intent|modifiers|tools|contents|training_contents|source|additive|response|mood|line|day|hint|bait)=/;

const PENDING_LABELS: Record<string, string> = {
  day_plan_choice: "安排今天的三段行动。",
  action_response: "选择你的回应和此刻心情。",
  process_write: "等待{assistant}补写这一段过程。",
  process_reaction_write: "等待{assistant}写下回应、过程和心情。",
  reaction_choice: "过程已经归档，选择此刻心情。",
  advance_action: "这一段已结束，可以推进下一段行动。",
  night_action_choice: "选择今晚的自由行动。",
  bell_voice_reveal: "按铃记录已生成，预录台词正在播放。",
  bell_response_choice: "等待{assistant}决定是否过去。",
  item_secret_reveal: "物品里的一条使用痕迹出现了。",
  monitor_gate: "夜间行动已封存，等待是否打开监控。",
  monitor_handle: "监控内容已打开，选择处理方式。",
  escape_choice: "逃跑机会出现了，等待你的选择。",
  return_action_choice: "你选择了老实待着，等待{assistant}回来后决定接下来怎么做。",
  recapture_rules_choice: "抓回经过已保存，等待重新立规矩。",
  recapture_followup_choice: "新规矩已生效，等待选择后续处理。",
  recapture_rules_review: "查看抓回后生效的新规矩。",
  ending_ready_to_notify: "结局已收录，等待同步给{assistant}。",
};

const CAPTOR_WAITING_LABELS: Record<string, string> = {
  action_response: "等待{assistant}选择回应和此刻心情。",
  process_write: "等待{assistant}补写这一段过程。",
  process_reaction_write: "等待{assistant}提交回应、过程和心情。",
  reaction_choice: "等待{assistant}选择此刻心情。",
  night_action_choice: "等待{assistant}选择今晚的自由行动。",
  bell_voice_reveal: "等待{assistant}听完本次语音铃播放。",
  bell_response_choice: "等待{assistant}决定是否过去。",
  item_secret_reveal: "等待{assistant}查看这次发现的物品痕迹。",
  escape_choice: "等待{assistant}选择尝试逃跑或老实待着。",
  return_action_choice: "{assistant}选择了老实待着，决定回来后如何处理。",
  recapture_rules_review: "等待{assistant}查看抓回后生效的新规矩。",
  ending_ready_to_notify: "结局已收录，等待同步给{assistant}。",
};

const DIRECTIVE_LABELS: Record<string, string> = {
  advance_day_action: "推进下一段行动",
  advance_action: "推进下一段行动",
  next_action: "推进下一段行动",
  plan_day: "安排今天的三段行动",
  day_action: "确定回来后的行为",
  submit_process: "保存事件经过",
  choose_mood: "记录此刻心情",
  ack_bell_voice: "听完本次播放",
  respond_bell: "回应语音铃",
  ack_item_secret: "看完本次发现",
  view_monitor: "查看夜间监控",
  monitor_action: "处理监控记录",
  set_recapture_rules: "保存抓回后的新规矩",
  choose_recapture_followup: "确定抓回后的处理",
  confirm_recapture_rules: "记住新规矩",
  build_ending_seed: "收录结局",
};

function pendingLabel(pending: CaptivityPending | null | undefined, role?: UserRole): string {
  const type = String(pending?.type || "");
  const assistantIsActing = String(pending?.actor || "") === "assistant";
  if (role === "captor" && CAPTOR_WAITING_LABELS[type] && (assistantIsActing || type === "return_action_choice")) {
    return CAPTOR_WAITING_LABELS[type];
  }
  return PENDING_LABELS[type] || "等待下一步处理。";
}

function publicDirectiveText(value: unknown, pending?: CaptivityPending | null, role?: UserRole): string {
  const raw = textLine(value);
  if (!raw) return "";
  if (role === "captor" && String(pending?.actor || "") === "assistant") return pendingLabel(pending, role);
  const directiveKey = raw.trim().split(/\s+/)[0].replace(/[【】：:]/g, "");
  if (DIRECTIVE_LABELS[directiveKey]) return DIRECTIVE_LABELS[directiveKey];
  if (raw.includes("今日安排")) return DIRECTIVE_LABELS.plan_day;
  if (raw.includes("夜间行动")) return "选择今晚的自由行动";
  if (raw.startsWith("resolve_escape_choice")) return "选择逃跑回应";
  if (COMMAND_ARG_PATTERN.test(raw)) return pendingLabel(pending, role);
  return raw;
}

function publicSystemText(value: unknown, pending?: CaptivityPending | null, role?: UserRole): string {
  const raw = textLine(value);
  if (!raw) return "";
  if (role === "captor" && String(pending?.actor || "") === "assistant") return pendingLabel(pending, role);
  for (const [directive, label] of Object.entries(DIRECTIVE_LABELS)) {
    if (raw.includes(directive)) return label;
  }
  if (COMMAND_ARG_PATTERN.test(raw)) {
    if (raw.includes("day_plan_choice") || raw.includes("今日安排")) return PENDING_LABELS.day_plan_choice;
    return "当前状态已更新，等待下一步处理。";
  }
  return raw;
}

function activeTaskMeta(event: CaptivityEvent, pending: CaptivityPending | null, view: CaptivityView, role: UserRole): string {
  const slot = Number(pending?.slot || event.slot || view.day_action_count || 0);
  const specialDay = ["escape_choice", "return_action_choice", "recapture_rules_choice", "recapture_rules_review", "recapture_followup_choice"].includes(String(pending?.type || ""))
    || event.tags?.includes("special_day")
    || event.tags?.includes("recapture");
  const rows = [
    pending?.type === "escape_choice" && pending.actor === "assistant"
      ? "等待{assistant}选择逃跑回应"
      : pending ? pendingLabel(pending, role).replace(/[。.]$/, "") : event.action_label || "当前待机",
    event.intensity ? `强度 ${intensityLabel(event.intensity)}` : "",
    specialDay ? "特殊事件" : slot > 0 ? `第 ${slot} 段` : `白天行动 ${view.day_action_count || 0} / ${view.day_action_limit || 3}`,
  ].filter(Boolean);
  return rows.join(" / ");
}

function commandText(payload: CaptivityPayload | null): string {
  const role = roleFromPayload(payload);
  const view = viewFromPayload(payload);
  return publicSystemText(payload?.player_text || payload?.text || payload?.reply_text || payload?.reply_preview, view.pending_event, role);
}

async function executeCaptivityCommand(command: string): Promise<CaptivityPayload> {
  const payload = await apiJson<CaptivityPayload>("/api/game/command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command, save_id: SAVE_ID }),
  });
  if (!payload?.ok) throw new Error(payload?.message || payload?.error || "囚禁模拟器命令失败");
  return payload;
}

async function syncCaptivityToAssistant(
  mode: "chat" | "state_update" | "ending",
  message = "",
  userInitiated = false,
): Promise<CaptivityPayload> {
  try {
    const payload = await apiJson<CaptivityPayload>("/api/game/sync-assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ save_id: SAVE_ID, mode, message, user_initiated: userInitiated }),
    });
    if (!payload?.ok && !["applied", "applied_with_warning"].includes(String(payload?.sync_result || ""))) {
      throw new Error(payload?.message || payload?.error || "同步{assistant}失败");
    }
    return payload;
  } catch (e) {
    const maybePayload = e instanceof ApiError ? e.payload : null;
    if (maybePayload?.state || maybePayload?.captive_view || maybePayload?.captor_view) {
      return maybePayload as CaptivityPayload;
    }
    throw e;
  }
}

function ToggleButton({
  active,
  children,
  onClick,
  disabled,
}: {
  active?: boolean;
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button className={`btn ${active ? "active" : ""}`} type="button" disabled={disabled} onClick={onClick}>
      {children}
    </button>
  );
}

type PaintedIconKind =
  | "toy"
  | "vibrating_wand"
  | "dildo"
  | "collar"
  | "leash"
  | "handcuffs"
  | "ankle_cuffs"
  | "whip"
  | "flogger"
  | "paddle"
  | "cane"
  | "candle"
  | "rope"
  | "bondage_tape"
  | "spreader_bar"
  | "blindfold"
  | "gag"
  | "muzzle"
  | "pinwheel"
  | "feather"
  | "nipple_clamps"
  | "suction_cups"
  | "chastity_ring"
  | "anal_plug"
  | "anal_beads"
  | "remote_control"
  | "lubricant"
  | "ruler"
  | "ice_cube"
  | "feeding_spoon"
  | "book"
  | "switch"
  | "notebook"
  | "music_player"
  | "tablet"
  | "night_light"
  | "pillow"
  | "call_bell";

function PaintedIcon({ kind }: { kind: PaintedIconKind }) {
  const common = { vectorEffect: "non-scaling-stroke" as const };
  return (
    <span className={`painted-icon painted-icon-${kind}`} aria-hidden="true">
      <svg viewBox="0 0 48 48" focusable="false">
        {kind === "toy" ? (
          <>
            <path {...common} className="paint-fill rose" d="M17 33c-5-5-3-15 4-20 7-5 16-3 18 3 2 7-6 8-11 13-4 4-5 10-11 4Z" />
            <path {...common} className="paint-stroke" d="M21 30c4-3 7-8 13-10" />
            <circle className="paint-light" cx="24" cy="18" r="3.2" />
          </>
        ) : null}
        {kind === "vibrating_wand" ? (
          <>
            <circle {...common} className="paint-fill rose" cx="31" cy="15" r="9" />
            <path {...common} className="paint-fill dark" d="M26 22l6 5-13 16-7-6 14-15Z" />
            <path className="paint-light" d="M28 11c3-2 7-1 9 2M17 36l4 3" />
          </>
        ) : null}
        {kind === "dildo" ? (
          <>
            <path {...common} className="paint-fill rose" d="M25 7c6 1 8 8 6 14l-5 14H15l5-15c-2-6 0-12 5-13Z" />
            <path {...common} className="paint-fill dark" d="M11 35h19c6 0 8 5 3 7H9c-5-2-3-7 2-7Z" />
            <path className="paint-light" d="M24 11c3 4 2 10 0 16" />
          </>
        ) : null}
        {kind === "collar" ? (
          <>
            <path {...common} className="paint-fill dark" d="M11 25c2-10 24-10 26 0 2 11-28 11-26 0Z" />
            <path {...common} className="paint-stroke pink" d="M13 23c5 5 17 6 22 0" />
            <rect className="paint-fill metal" x="21" y="24" width="7" height="8" rx="2" />
            <circle className="paint-light" cx="24.5" cy="27.5" r="1.3" />
          </>
        ) : null}
        {kind === "leash" ? (
          <>
            <path {...common} className="paint-stroke pink" d="M9 12c10-6 22 3 20 13-1 8-10 8-10 2 0-5 8-4 13 0 5 5 4 11 0 15" />
            <rect {...common} className="paint-fill dark" x="5" y="8" width="9" height="7" rx="2" transform="rotate(-25 9.5 11.5)" />
            <circle {...common} className="paint-stroke metal thin" cx="33" cy="41" r="3" />
          </>
        ) : null}
        {kind === "handcuffs" ? (
          <>
            <circle {...common} className="paint-stroke metal" cx="16" cy="26" r="8" />
            <circle {...common} className="paint-stroke metal" cx="32" cy="26" r="8" />
            <path {...common} className="paint-stroke pink" d="M23 26h2" />
            <path className="paint-light" d="M12 21c2-2 5-3 8-1" />
            <path className="paint-light" d="M28 21c2-2 5-3 8-1" />
          </>
        ) : null}
        {kind === "ankle_cuffs" ? (
          <>
            <g transform="rotate(-10 13 25)">
              <rect {...common} className="paint-fill rose" x="4" y="16" width="18" height="18" rx="7" />
              <rect {...common} className="paint-fill dark" x="8" y="20" width="10" height="10" rx="4" />
              <rect {...common} className="paint-fill metal" x="17" y="20" width="6" height="9" rx="2" />
              <circle className="paint-fill pink" cx="20" cy="24.5" r="1.4" />
              <path className="paint-light" d="M7 19c3-2 8-2 11 0" />
            </g>
            <g transform="rotate(10 35 25)">
              <rect {...common} className="paint-fill rose" x="26" y="16" width="18" height="18" rx="7" />
              <rect {...common} className="paint-fill dark" x="30" y="20" width="10" height="10" rx="4" />
              <rect {...common} className="paint-fill metal" x="25" y="20" width="6" height="9" rx="2" />
              <circle className="paint-fill pink" cx="28" cy="24.5" r="1.4" />
              <path className="paint-light" d="M30 19c3-2 8-2 11 0" />
            </g>
            <ellipse {...common} className="paint-stroke metal thin" cx="22" cy="25" rx="3.5" ry="2.4" />
            <ellipse {...common} className="paint-stroke metal thin" cx="26" cy="25" rx="3.5" ry="2.4" />
          </>
        ) : null}
        {kind === "whip" ? (
          <>
            <path {...common} className="paint-fill dark" d="M7 35l9-9 4 4-9 9c-1.5 1.5-5.5-2.5-4-4Z" />
            <path {...common} className="paint-stroke metal thin" d="M15 27l4 4" />
            <circle {...common} className="paint-stroke metal thin" cx="21" cy="25" r="2.8" />
            <path {...common} className="paint-stroke pink" d="M24 23c8-12 22-10 19 1-2 8-16 5-18 14" />
            <path {...common} className="paint-stroke metal thin" d="M26 21c7-5 16-5 17 1" />
            <path {...common} className="paint-stroke pink thin" d="M25 38l-4 5" />
            <path className="paint-light" d="M9 36l6-6M31 20c4-2 9-1 11 2" />
          </>
        ) : null}
        {kind === "flogger" ? (
          <>
            <rect {...common} className="paint-fill dark" x="21" y="25" width="7" height="18" rx="3" />
            <rect {...common} className="paint-fill metal" x="20" y="21" width="9" height="7" rx="2" />
            <path {...common} className="paint-stroke pink thin" d="M24 22L8 5M25 22L16 3M25 22L25 3M26 22L35 4M27 22L43 7" />
          </>
        ) : null}
        {kind === "paddle" ? (
          <>
            <path {...common} className="paint-fill rose" d="M12 8c7-5 17 0 17 8 0 6-4 10-8 12l15 13-5 5-15-15C8 33 3 27 4 19c1-5 4-9 8-11Z" />
            <circle className="paint-fill dark" cx="15" cy="18" r="3" />
          </>
        ) : null}
        {kind === "cane" ? (
          <>
            <path {...common} className="paint-stroke pink" d="M9 42L37 10c5-6 11 1 5 6l-3 3" />
            <path {...common} className="paint-stroke metal thin" d="M11 38l4 4M34 13l4 4" />
          </>
        ) : null}
        {kind === "candle" ? (
          <>
            <path className="paint-fill rose" d="M18 19h13v20H18z" />
            <path className="paint-fill light" d="M21 19h4v20h-4z" />
            <path className="paint-fill pink" d="M19 19c4 3 8 3 12 0v5c-4 3-8 3-12 0Z" />
            <path className="paint-fill flame" d="M25 6c6 6 2 12-1 13-4-3-5-8 1-13Z" />
            <path className="paint-light" d="M25 10c2 3 1 5-1 7" />
          </>
        ) : null}
        {kind === "rope" ? (
          <>
            <ellipse {...common} className="paint-stroke pink thick" cx="21" cy="24" rx="14" ry="10" />
            <ellipse {...common} className="paint-stroke metal thin" cx="21" cy="24" rx="9" ry="6" />
            <ellipse {...common} className="paint-stroke dark thin" cx="21" cy="24" rx="5" ry="3" />
            <circle {...common} className="paint-fill rose" cx="34" cy="31" r="5" />
            <path {...common} className="paint-stroke pink thick" d="M36 34c3 2 5 5 7 8M32 35c0 4-1 7-3 10" />
            <path className="paint-light" d="M10 19c5-5 13-6 20-3M9 27c5 5 13 7 20 4M33 29c2 0 4 1 5 3" />
          </>
        ) : null}
        {kind === "bondage_tape" ? (
          <>
            <circle {...common} className="paint-fill dark" cx="21" cy="24" r="14" />
            <circle className="paint-fill light" cx="21" cy="24" r="6" />
            <path {...common} className="paint-fill pink" d="M31 27l14 7-3 8-15-9 4-6Z" />
            <path className="paint-light" d="M12 17c5-5 13-6 19-2" />
          </>
        ) : null}
        {kind === "spreader_bar" ? (
          <>
            <rect {...common} className="paint-fill metal" x="8" y="21" width="32" height="6" rx="3" />
            <circle {...common} className="paint-stroke pink" cx="7" cy="24" r="5" />
            <circle {...common} className="paint-stroke pink" cx="41" cy="24" r="5" />
            <path className="paint-light" d="M14 23h20" />
          </>
        ) : null}
        {kind === "blindfold" ? (
          <>
            <rect {...common} className="paint-fill pink" x="7" y="18" width="34" height="12" rx="5" />
          </>
        ) : null}
        {kind === "gag" ? (
          <>
            <path {...common} className="paint-stroke dark" d="M8 24h32" />
            <circle {...common} className="paint-fill rose" cx="24" cy="24" r="8" />
            <path {...common} className="paint-stroke pink" d="M16 24h16" />
            <path className="paint-light" d="M21 20c2-1 5-1 7 0" />
          </>
        ) : null}
        {kind === "muzzle" ? (
          <>
            <path {...common} className="paint-fill dark" d="M14 18h20l4 13-7 8H17l-7-8 4-13Z" />
            <path {...common} className="paint-stroke pink thin" d="M10 20L4 14M38 20l6-6M16 25h16M18 31h12" />
            <circle className="paint-fill metal" cx="24" cy="20" r="2" />
          </>
        ) : null}
        {kind === "pinwheel" ? (
          <>
            <circle {...common} className="paint-stroke metal thin" cx="25" cy="18" r="11" />
            {Array.from({ length: 12 }).map((_, index) => {
              const angle = (index * Math.PI) / 6;
              const x1 = 25 + Math.cos(angle) * 10;
              const y1 = 18 + Math.sin(angle) * 10;
              const x2 = 25 + Math.cos(angle) * 15;
              const y2 = 18 + Math.sin(angle) * 15;
              return <path className="paint-stroke pink thin" d={`M${x1} ${y1}L${x2} ${y2}`} key={index} />;
            })}
            <path {...common} className="paint-stroke dark" d="M25 29l-7 15" />
          </>
        ) : null}
        {kind === "feather" ? (
          <>
            <path {...common} className="paint-fill rose" d="M39 6C21 5 8 18 11 35c10 2 24-9 28-29Z" />
            <path {...common} className="paint-stroke dark thin" d="M8 43C17 31 26 21 37 9M16 32l-4-8M22 25l-2-10M27 20l7-4M19 29l10 1" />
          </>
        ) : null}
        {kind === "nipple_clamps" ? (
          <>
            <circle {...common} className="paint-stroke metal thin" cx="8" cy="9" r="4" />
            <path {...common} className="paint-stroke metal thin" d="M11 12l4 4-2 3 5 4" />
            <path {...common} className="paint-fill metal" d="M17 21l22-8 3 6-21 10-4-8Z" />
            <path {...common} className="paint-fill pink" d="M20 29l22 1-1 7-23-2 2-6Z" />
            <circle {...common} className="paint-fill dark" cx="20" cy="28" r="5" />
            <circle {...common} className="paint-stroke metal thin" cx="20" cy="28" r="2" />
            <path {...common} className="paint-stroke dark thin" d="M39 13l5-2 2 6-4 2M42 30l4 1-1 7-4-1" />
            <path className="paint-light" d="M23 24l14-6M24 32l14 1" />
          </>
        ) : null}
        {kind === "suction_cups" ? (
          <>
            <path {...common} className="paint-fill rose" d="M11 17h26l-4 18H15l-4-18Z" />
            <ellipse {...common} className="paint-stroke pink" cx="24" cy="17" rx="13" ry="5" />
            <path {...common} className="paint-stroke dark" d="M24 12V5M20 5h8" />
            <path className="paint-light" d="M18 22h12" />
          </>
        ) : null}
        {kind === "chastity_ring" ? (
          <>
            <circle {...common} className="paint-stroke metal" cx="23" cy="25" r="11" />
            <circle {...common} className="paint-stroke pink" cx="23" cy="25" r="6" />
            <rect {...common} className="paint-fill dark" x="29" y="18" width="9" height="14" rx="3" />
            <path className="paint-light" d="M32 22h3M32 26h3" />
          </>
        ) : null}
        {kind === "anal_plug" ? (
          <>
            <path {...common} className="paint-fill rose" d="M24 8c8 6 7 18 0 25-7-7-8-19 0-25Z" />
            <path {...common} className="paint-fill dark" d="M15 34c4-4 14-4 18 0 3 4-21 4-18 0Z" />
            <path {...common} className="paint-stroke pink" d="M24 13c2 5 2 11 0 17" />
            <path className="paint-light" d="M21 13c-2 5-1 11 2 16" />
          </>
        ) : null}
        {kind === "anal_beads" ? (
          <>
            <path {...common} className="paint-stroke pink thin" d="M24 7v31" />
            <circle {...common} className="paint-fill rose" cx="24" cy="11" r="4" />
            <circle {...common} className="paint-fill rose" cx="24" cy="20" r="5" />
            <circle {...common} className="paint-fill rose" cx="24" cy="31" r="6" />
            <path {...common} className="paint-stroke dark" d="M17 41h14" />
          </>
        ) : null}
        {kind === "remote_control" ? (
          <>
            <rect {...common} className="paint-fill dark" x="15" y="7" width="18" height="34" rx="6" />
            <circle className="paint-fill pink" cx="24" cy="15" r="4" />
            <circle className="paint-fill metal" cx="20" cy="25" r="2" />
            <circle className="paint-fill metal" cx="28" cy="25" r="2" />
            <path className="paint-light" d="M20 33h8" />
          </>
        ) : null}
        {kind === "lubricant" ? (
          <>
            <path {...common} className="paint-fill rose" d="M17 13h17l-3 27H14l3-27Z" />
            <rect {...common} className="paint-fill dark" x="18" y="7" width="15" height="7" rx="2" />
            <path className="paint-light" d="M20 20h8M19 25h10" />
          </>
        ) : null}
        {kind === "ruler" ? (
          <>
            <rect {...common} className="paint-fill rose" x="7" y="20" width="35" height="9" rx="2" transform="rotate(-18 24.5 24.5)" />
            <path {...common} className="paint-stroke dark thin" d="M12 29l-1-4M18 27l-1-3M24 25l-1-4M30 23l-1-3M36 21l-1-4" />
          </>
        ) : null}
        {kind === "ice_cube" ? (
          <>
            <path {...common} className="paint-fill light" d="M13 16l12-7 11 7v16l-12 7-11-7V16Z" />
            <path {...common} className="paint-stroke pink thin" d="M13 16l11 7 12-7M24 23v16" />
            <path className="paint-light" d="M18 16l7-4" />
          </>
        ) : null}
        {kind === "feeding_spoon" ? (
          <>
            <ellipse {...common} className="paint-fill rose" cx="32" cy="13" rx="9" ry="7" transform="rotate(-35 32 13)" />
            <path {...common} className="paint-stroke metal thick" d="M27 19L9 40" />
            <path className="paint-light" d="M29 10c3-2 6-1 8 1" />
          </>
        ) : null}
        {kind === "book" ? (
          <>
            <path {...common} className="paint-fill dark" d="M10 12h14c3 0 5 2 5 5v21H15c-3 0-5-2-5-5V12Z" />
            <path {...common} className="paint-fill rose" d="M24 12h14v26H24V12Z" />
            <path {...common} className="paint-stroke pink" d="M24 14v23" />
            <path className="paint-light" d="M15 19h6M15 24h5M29 19h5M29 24h6" />
          </>
        ) : null}
        {kind === "switch" ? (
          <>
            <rect {...common} className="paint-fill pink" x="2" y="15" width="9" height="18" rx="4.5" />
            <rect {...common} className="paint-fill dark" x="37" y="15" width="9" height="18" rx="4.5" />
            <rect {...common} className="paint-fill dark" x="10" y="16" width="28" height="16" rx="2.2" />
            <rect className="paint-fill light" x="12" y="17.6" width="24" height="12.8" rx="1.8" />
            <circle className="paint-fill dark" cx="6.5" cy="20.5" r="1.55" />
            <path className="paint-stroke metal" d="M6.5 26v3.6M4.7 27.8h3.6" />
            <circle className="paint-fill metal" cx="41.5" cy="20.5" r="1.25" />
            <circle className="paint-fill metal" cx="41.5" cy="27.8" r="1.25" />
            <path className="paint-light" d="M15 21h17M15 24.8h13" />
          </>
        ) : null}
        {kind === "notebook" ? (
          <>
            <rect {...common} className="paint-fill rose" x="13" y="10" width="24" height="30" rx="3" />
            <path {...common} className="paint-stroke dark thin" d="M18 10v30" />
            <path className="paint-light" d="M23 18h9M23 23h8M23 28h7" />
            <path {...common} className="paint-stroke pink thin" d="M9 15h7M9 22h7M9 29h7" />
          </>
        ) : null}
        {kind === "music_player" ? (
          <>
            <rect {...common} className="paint-fill dark" x="14" y="10" width="20" height="28" rx="4" />
            <rect className="paint-fill light" x="18" y="14" width="12" height="7" rx="1.5" />
            <circle className="paint-fill rose" cx="24" cy="29" r="5.5" />
            <circle className="paint-fill dark" cx="24" cy="29" r="2" />
            <path className="paint-light" d="M19 24h10" />
          </>
        ) : null}
        {kind === "tablet" ? (
          <>
            <rect {...common} className="paint-fill dark" x="8" y="12" width="32" height="24" rx="3" />
            <rect className="paint-fill light" x="12" y="16" width="24" height="16" rx="1.8" />
            <path className="paint-light" d="M16 21h14M16 25h10" />
            <circle className="paint-fill pink" cx="24" cy="34" r="1.3" />
          </>
        ) : null}
        {kind === "night_light" ? (
          <>
            <path {...common} className="paint-fill rose" d="M15 18c1-6 17-6 18 0l3 16H12l3-16Z" />
            <rect {...common} className="paint-fill dark" x="19" y="34" width="10" height="5" rx="1.5" />
          </>
        ) : null}
        {kind === "pillow" ? (
          <>
            <rect {...common} className="paint-fill rose" x="12" y="14" width="24" height="24" rx="4" />
          </>
        ) : null}
        {kind === "call_bell" ? (
          <>
            <path {...common} className="paint-fill rose" d="M14 29c1-8 5-13 10-13s9 5 10 13H14Z" />
            <rect {...common} className="paint-fill dark" x="11" y="29" width="26" height="5" rx="2.5" />
            <circle className="paint-fill metal" cx="24" cy="14" r="3" />
            <circle className="paint-fill dark" cx="24" cy="34.5" r="2" />
          </>
        ) : null}
      </svg>
    </span>
  );
}

type ToolContext = {
  action: string;
  modifiers: string[];
  contents: string[];
  trainingContents: string[];
};

function toolContextTokens(context: ToolContext): Set<string> {
  return new Set([
    `action:${context.action}`,
    ...context.modifiers.map((item) => `modifier:${item}`),
    ...context.contents.map((item) => `content:${item}`),
    ...context.trainingContents.map((item) => `training:${item}`),
  ]);
}

function toolFitsContext(toolId: string, context?: ToolContext): boolean {
  if (!context) return true;
  const option = TOOL_OPTIONS.find((item) => item.id === toolId);
  if (!option) return false;
  const tokens = toolContextTokens(context);
  return option.contexts.some((item) => tokens.has(item));
}

function ToolSelectGrid({
  selected,
  disabled,
  context,
  onToggle,
}: {
  selected: string[];
  disabled?: boolean;
  context?: ToolContext;
  onToggle: (value: string) => void;
}) {
  const categories = Array.from(new Set(TOOL_OPTIONS.map((item) => item.category)));
  return (
    <div className="tool-groups">
      {categories.map((category) => (
        <div className="tool-group" key={category}>
          <div className="action-metadata tool-category-title">{category}</div>
          <div className="tool-grid">
            {TOOL_OPTIONS.filter((item) => item.category === category).map((item) => {
              const active = selected.includes(item.id);
              const compatible = toolFitsContext(item.id, context);
              return (
                <button
                  className={`tool-tile ${active ? "active" : ""} ${compatible ? "recommended" : ""}`}
                  type="button"
                  disabled={disabled || (!active && selected.length >= 2)}
                  title={compatible ? `${item.label}（推荐）` : item.label}
                  key={item.id}
                  onClick={() => onToggle(item.id)}
                >
                  <PaintedIcon kind={item.id as PaintedIconKind} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function InventoryWarehouse({
  activeItems,
  inventorySecrets,
  callBellVoice,
  disabled,
  onGiftInventoryItem,
  onRevokeInventoryItem,
}: {
  activeItems: Partial<Record<InventoryItemId, boolean>>;
  inventorySecrets?: CaptivityView["inventory_secrets"];
  callBellVoice?: CaptivityView["call_bell_voice"];
  disabled?: boolean;
  onGiftInventoryItem: (itemId: InventoryItemId, secret?: string) => void;
  onRevokeInventoryItem: (itemId: InventoryItemId) => void;
}) {
  const [selectedItem, setSelectedItem] = useState<InventoryItemId | "">("");
  const [itemSecretText, setItemSecretText] = useState("");
  const selectedOption = INVENTORY_OPTIONS.find((item) => item.id === selectedItem);
  const selectedActive = selectedItem ? Boolean(activeItems[selectedItem]) : false;
  const progressiveCopy = selectedItem ? PROGRESSIVE_SECRET_COPY[selectedItem] : undefined;
  const selectedSecret = selectedItem ? inventorySecrets?.[selectedItem] : undefined;
  const selectedEntries = selectedSecret?.entries || [];
  const selectedTotal = selectedSecret?.total_count ?? selectedEntries.length;
  const selectedRevealed = selectedSecret?.revealed_count ?? (selectedSecret?.revealed ? selectedTotal : 0);

  function handleItemAction() {
    if (!selectedItem) return;
    if (selectedActive) onRevokeInventoryItem(selectedItem);
    else onGiftInventoryItem(selectedItem, itemSecretText.trim() || undefined);
    setSelectedItem("");
    setItemSecretText("");
  }

  return (
    <div className="warehouse-panel">
      <div className="warehouse-title-row">
        <div className="panel-title warehouse-module-title">物品仓库 <span className="sub">ITEMS</span></div>
      </div>
      <div className="warehouse-grid">
        {INVENTORY_OPTIONS.map((item) => {
          const active = Boolean(activeItems[item.id]);
          return (
            <button
              className={`warehouse-tile ${active ? "active" : ""} ${selectedItem === item.id ? "selected" : ""}`}
              type="button"
              aria-pressed={active}
              aria-label={`${item.label}，${active ? "已赠送" : "可赠送"}`}
              disabled={disabled}
              key={item.id}
              onClick={() => {
                setSelectedItem(item.id);
                setItemSecretText("");
              }}
            >
              <PaintedIcon kind={item.id} />
              <span className="warehouse-name">{item.label}</span>
              <span className="warehouse-use">{item.usage}</span>
              <span className="warehouse-state">{active ? "已赠送" : "可赠送"}</span>
            </button>
          );
        })}
      </div>
      {selectedOption ? (
        <div className="warehouse-menu">
          <div>
            <div className="warehouse-menu-title">{selectedOption.label}</div>
            <div className="warehouse-menu-use">{selectedOption.usage}</div>
            <div className="warehouse-menu-state">{selectedActive ? "已赠送" : "未赠送"}</div>
          </div>
          {!selectedActive ? (
            <>
              <div className="warehouse-secret-label">
                {selectedItem === "call_bell"
                  ? "对方每次按下时，都会听见铃替他说出这句话。"
                  : progressiveCopy
                    ? progressiveCopy.label
                  : "对方第一次使用这个物品时会看到这句话。"}
              </div>
              <textarea
                className="warehouse-voice-input"
                value={itemSecretText}
                maxLength={progressiveCopy ? 1000 : 500}
                disabled={disabled}
                placeholder={selectedItem === "call_bell"
                  ? "输入铃声播放的预录台词"
                  : progressiveCopy?.placeholder || "可选：输入第一次使用时显示的内容"}
                onChange={(event) => setItemSecretText(event.target.value)}
              />
            </>
          ) : null}
          {selectedActive && (selectedItem === "call_bell" ? callBellVoice?.line : selectedSecret?.content || selectedEntries.length) ? (
            <div className="warehouse-voice-current">
              <div className="warehouse-menu-state">
                {selectedItem === "call_bell"
                  ? "每次播放的预录台词"
                  : PROGRESSIVE_SECRET_ITEMS.has(selectedItem as InventoryItemId)
                    ? `使用痕迹 · 已发现 ${selectedRevealed} / ${selectedTotal}`
                    : `首次使用文案 · ${selectedSecret?.revealed ? "已揭晓" : "未揭晓"}`}
              </div>
              <div>{selectedItem === "call_bell"
                ? callBellVoice?.line
                : selectedEntries.length
                  ? selectedEntries.map((entry, index) => `${index + 1}. ${entry}`).join("\n")
                  : selectedSecret?.content}</div>
            </div>
          ) : null}
          <div className="warehouse-actions">
            <button
              className="btn"
              type="button"
              disabled={disabled || (!selectedActive && (selectedItem === "call_bell" || PROGRESSIVE_SECRET_ITEMS.has(selectedItem as InventoryItemId)) && !itemSecretText.trim())}
              onClick={handleItemAction}
            >
              {selectedActive ? "收回" : "赠送"}
            </button>
            <button
              className="btn"
              type="button"
              disabled={disabled}
              onClick={() => {
                setSelectedItem("");
                setItemSecretText("");
              }}
            >取消</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function CaptiveRoomInventory({
  activeItems,
}: {
  activeItems: Partial<Record<InventoryItemId, boolean>>;
}) {
  const unlockedItems = INVENTORY_OPTIONS.filter((item) => Boolean(activeItems[item.id]));
  return (
    <div className="warehouse-panel room-inventory-panel">
      <div className="warehouse-title-row">
        <div className="panel-title warehouse-module-title">房间物品 <span className="sub">ITEMS</span></div>
      </div>
      {unlockedItems.length ? (
        <div className="warehouse-grid">
          {unlockedItems.map((item) => (
            <div className="warehouse-tile active room-inventory-tile" key={item.id}>
              <PaintedIcon kind={item.id} />
              <span className="warehouse-name">{item.label}</span>
              <span className="warehouse-use">{item.usage}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="monitor-record-item faded">
          <div className="action-metadata">暂无房间物品</div>
          <div className="event-sub">收到的物品会出现在这里。</div>
        </div>
      )}
    </div>
  );
}

export function CaptivitySimulatorGameTab({ onBack }: { onBack: () => void }) {
  const [payload, setPayload] = useState<CaptivityPayload | null>(null);
  const [screen, setScreen] = useState<"selector" | "game">("selector");
  const [identityConfirmOpen, setIdentityConfirmOpen] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [backgroundSyncing, setBackgroundSyncing] = useState(false);
  const [footerTab, setFooterTab] = useState<"status" | "history" | "special">("status");
  const [wait, setWait] = useState<WaitState>({
    visible: false,
    title: "",
    detail: "",
  });
  const [planSlots, setPlanSlots] = useState<PlanSlot[]>(defaultPlanSlots);
  const [response, setResponse] = useState("accept");
  const [responseMood, setResponseMood] = useState("害羞");
  const [responseLine, setResponseLine] = useState("");
  const [reactionMood, setReactionMood] = useState("害羞");
  const [reactionLine, setReactionLine] = useState("");
  const [nightAction, setNightAction] = useState("sleep");
  const [nightDetail, setNightDetail] = useState("");
  const [nightNote, setNightNote] = useState("");
  const [nightLine, setNightLine] = useState("");
  const [monitorNote, setMonitorNote] = useState("");
  const [interventionIntent, setInterventionIntent] = useState("catch");
  const [interventionModifiers, setInterventionModifiers] = useState<string[]>([]);
  const [interventionTrainingContents, setInterventionTrainingContents] = useState<string[]>([]);
  const [interventionTools, setInterventionTools] = useState<string[]>([]);
  const [interventionLine, setInterventionLine] = useState("");
  const [processReview, setProcessReview] = useState<ProcessReview | null>(null);
  const [historyDetail, setHistoryDetail] = useState<CaptivityEvent | null>(null);
  const [monitorRoomOpen, setMonitorRoomOpen] = useState(false);
  const [inventoryRoomOpen, setInventoryRoomOpen] = useState(false);
  const [escapeDay, setEscapeDay] = useState(12);
  const [escapeRoom, setEscapeRoom] = useState<EscapeRoomId>("entry");
  const [escapeHint, setEscapeHint] = useState("{assistant}今天有事出去了");
  const [escapeBait, setEscapeBait] = useState(escapeRoomBait("entry"));
  const [recaptureRules, setRecaptureRules] = useState<string[]>(["double_lock"]);
  const [recaptureFollowup, setRecaptureFollowup] = useState("punishment");
  const [recaptureIntensity, setRecaptureIntensity] = useState("medium");
  const [recaptureModifiers, setRecaptureModifiers] = useState<string[]>([]);
  const [recaptureTrainingContents, setRecaptureTrainingContents] = useState<string[]>([]);
  const [recaptureTools, setRecaptureTools] = useState<string[]>([]);
  const [recaptureLine, setRecaptureLine] = useState("");
  const [sceneTransition, setSceneTransition] = useState<SceneCopy | null>(null);
  const [recaptureBridgeVisible, setRecaptureBridgeVisible] = useState(false);
  const initialLoadStartedRef = useRef(false);
  const lastSceneKeyRef = useRef("");
  const lastProcessTransitionKeyRef = useRef("");
  const sceneTransitionTimerRef = useRef<number | null>(null);
  const previewSyncReadyAtRef = useRef(0);
  const lastFailedRetryRef = useRef<(() => void) | null>(null);
  const mainScreenRef = useRef<HTMLElement | null>(null);
  const [hasFailedRetry, setHasFailedRetry] = useState(false);
  const processPreviewRole = readProcessPreviewRole();
  const planPreviewRole = readPlanPreviewRole();
  const nightPreviewRole = readNightPreviewRole();
  const escapePreviewRole = readEscapePreviewRole();
  const endingPreviewRole = readEndingPreviewRole();
  const previewRole = processPreviewRole || planPreviewRole || nightPreviewRole || escapePreviewRole || endingPreviewRole;

  const captiveView = payload?.captive_view || payload?.state || {};
  const captorView = payload?.captor_view || {};
  const route = String((captorView.route || captiveView.route || "captured_by_assistant")) as RouteKey;
  const role: UserRole = roleFromPayload(payload);
  const view: CaptivityView = role === "captor" ? (captorView.route ? captorView : captiveView) : captiveView;
  const pending = view.pending_event || null;
  const stats = view.stats || {};
  const phase = String(view.phase || "day");
  const isGameOver = Boolean(view.game_over || payload?.game_over);
  const lastText = commandText(payload);
  const busy = (wait.visible && !wait.error) || backgroundSyncing;
  const pendingType = String(pending?.type || "");
  const milestoneCopy = dayMilestoneCopy(Number(view.current_day || 1), role);
  const hasExistingProgress = hasMeaningfulProgress(view);

  const eventLog = useMemo(() => view.event_log || [], [view.event_log]);
  const latestEvent = eventLog[eventLog.length - 1];
  const currentEvent = pending ? pending.event : latestEvent;
  const availableNightActions = view.available_night_actions?.length
    ? view.available_night_actions
    : pending?.available_actions?.length
      ? pending.available_actions
      : DEFAULT_NIGHT_ACTIONS;
  const fallbackNightDetailOptions = Object.fromEntries(
    (NIGHT_DETAIL_OPTIONS[nightAction] || []).map((item) => [item.id, item.label]),
  );
  const activeNightDetailOptionMap = view.night_detail_options?.[nightAction]
    || pending?.detail_options?.[nightAction]
    || fallbackNightDetailOptions;
  const activeNightDetailOptions = Object.entries(activeNightDetailOptionMap).map(([id, label]) => ({ id, label }));
  const activeNightDetailOptionsKey = JSON.stringify(activeNightDetailOptionMap);
  const userIsPendingActor = pending ? String(pending.actor || "") !== "assistant" : false;
  const waitingForAssistant = pending ? String(pending.actor || "") === "assistant" : false;
  const showPlanner = role === "captor"
    && phase === "day"
    && !(view.day_plan || []).length
    && !isGameOver
    && (
      (!pending && Number(view.day_action_count || 0) === 0)
      || ((pendingType === "day_plan_choice" || pendingType === "advance_action") && userIsPendingActor)
      || (pendingType === "return_action_choice" && userIsPendingActor)
    );
  const isReturnActionPlanner = pendingType === "return_action_choice" && userIsPendingActor;
  const canChooseNight = role === "captive"
    && phase === "night"
    && (!pending || String(pending.type || "") === "night_action_choice")
    && !isGameOver;
  const inventoryActiveItems = useMemo<Partial<Record<InventoryItemId, boolean>>>(() => {
    const inventory = view.inventory || captorView.inventory || {};
    return Object.fromEntries(
      INVENTORY_OPTIONS.map((item) => [item.id, Boolean(inventory[item.id])]),
    ) as Partial<Record<InventoryItemId, boolean>>;
  }, [captorView.inventory, view.inventory]);

  const applyPayload = useCallback((next: CaptivityPayload) => {
    setPayload(next);
  }, []);

  const dismissSceneTransition = useCallback(() => {
    if (sceneTransitionTimerRef.current !== null) {
      window.clearTimeout(sceneTransitionTimerRef.current);
      sceneTransitionTimerRef.current = null;
    }
    setSceneTransition(null);
  }, []);

  const playSceneTransition = useCallback((scene: SceneCopy) => {
    if (sceneTransitionTimerRef.current !== null) {
      window.clearTimeout(sceneTransitionTimerRef.current);
    }
    setSceneTransition(scene);
    sceneTransitionTimerRef.current = window.setTimeout(() => {
      sceneTransitionTimerRef.current = null;
      setSceneTransition(null);
    }, sceneTransitionDuration(scene));
  }, []);

  useEffect(() => () => {
    if (sceneTransitionTimerRef.current !== null) window.clearTimeout(sceneTransitionTimerRef.current);
  }, []);

  const runWithWait = useCallback(async (
    title: string,
    detail: string,
    task: () => Promise<CaptivityPayload>,
    quiet = false,
  ) => {
    const retry = () => {
      void runWithWait(title, detail, task, quiet);
    };
    if (!quiet) setWait({ visible: true, title, detail });
    try {
      const next = await task();
      lastFailedRetryRef.current = null;
      setHasFailedRetry(false);
      applyPayload(next);
      if (!quiet) setWait({ visible: false, title: "", detail: "" });
      return next;
    } catch (e: any) {
      const message = String(e?.message || e || "操作失败");
      lastFailedRetryRef.current = retry;
      setHasFailedRetry(true);
      setWait({
        visible: true,
        title: "同步失败",
        detail: message,
        error: message,
      });
      return null;
    }
  }, [applyPayload]);

  const showPreviewSyncWait = useCallback(function previewSyncWait() {
    previewSyncReadyAtRef.current = Date.now() + 1200;
    lastFailedRetryRef.current = null;
    setHasFailedRetry(false);
    setWait({
      visible: true,
      title: "正在同步{assistant}...",
      detail: "STATUS: ENCRYPTING DATA",
    });
  }, []);

  const refreshStatus = useCallback(async (silent = false) => {
    if (previewRole) {
      if (!silent) {
        const readyAt = previewSyncReadyAtRef.current;
        if (!readyAt || Date.now() >= readyAt) {
          previewSyncReadyAtRef.current = 0;
          setWait({ visible: false, title: "", detail: "" });
          setRecaptureBridgeVisible(false);
        }
      }
      return;
    }
    try {
      const next = await executeCaptivityCommand("status");
      const refreshedView = viewFromPayload(next);
      if (silent) {
        lastSceneKeyRef.current = String(refreshedView.scene_copy?.key || "");
      }
      applyPayload(next);
      if (!silent) {
        lastFailedRetryRef.current = null;
        setHasFailedRetry(false);
        if (String(refreshedView.pending_event?.actor || "") !== "assistant") {
          setWait({ visible: false, title: "", detail: "" });
          setRecaptureBridgeVisible(false);
        } else {
          setWait((current) => current.visible ? {
            visible: true,
            title: "正在同步{assistant}...",
            detail: "STATUS: ENCRYPTING DATA",
          } : current);
        }
      }
      if (shouldResumeGame(next)) {
        setScreen("game");
      } else {
        setScreen("selector");
      }
    } catch (e: any) {
      const message = String(e?.message || e || (silent ? "读取存档失败" : "刷新失败"));
      const retry = () => void refreshStatus(false);
      lastFailedRetryRef.current = retry;
      setHasFailedRetry(true);
      setWait({
        visible: true,
        title: silent ? "读取存档失败" : "刷新失败",
        detail: message,
        error: message,
      });
    }
  }, [applyPayload, previewRole]);

  function retryLastFailedOperation() {
    lastFailedRetryRef.current?.();
  }

  useEffect(() => {
    if (endingPreviewRole) {
      setPayload(buildEndingPreview(endingPreviewRole));
      setProcessReview(null);
      setScreen("game");
      setFooterTab("status");
      setBootstrapping(false);
      return;
    }
    if (escapePreviewRole) {
      setPayload(buildEscapePreview(escapePreviewRole));
      setProcessReview(null);
      setScreen("game");
      setFooterTab("status");
      setBootstrapping(false);
      return;
    }
    if (planPreviewRole) {
      setPayload(buildPlannerPreview());
      setProcessReview(null);
      setScreen("game");
      setFooterTab("status");
      setBootstrapping(false);
      return;
    }
    if (nightPreviewRole) {
      setPayload(buildNightPreview());
      setProcessReview(null);
      setScreen("game");
      setFooterTab("status");
      setBootstrapping(false);
      return;
    }
    if (processPreviewRole) {
      const preview = buildProcessPreview(processPreviewRole);
      setPayload(preview.payload);
      setProcessReview(preview.review);
      setScreen("game");
      setFooterTab("history");
      setBootstrapping(false);
      return;
    }
    if (initialLoadStartedRef.current) return;
    initialLoadStartedRef.current = true;
    void refreshStatus(true).finally(() => setBootstrapping(false));
  }, [endingPreviewRole, escapePreviewRole, nightPreviewRole, planPreviewRole, processPreviewRole, refreshStatus]);

  useEffect(() => {
    const first = availableNightActions[0];
    if (first && !availableNightActions.includes(nightAction)) setNightAction(first);
  }, [availableNightActions, nightAction]);

  useEffect(() => {
    const scene = view.scene_copy;
    const sceneKey = String(scene?.key || "");
    const revealPending = pendingType === "bell_voice_reveal" || pendingType === "item_secret_reveal";
    if (screen !== "game" || processReview || monitorRoomOpen || inventoryRoomOpen || revealPending || !scene || !sceneKey) return;
    if (lastSceneKeyRef.current === sceneKey) return;
    lastSceneKeyRef.current = sceneKey;
    playSceneTransition(scene);
  }, [inventoryRoomOpen, monitorRoomOpen, pendingType, playSceneTransition, processReview, screen, view.scene_copy]);

  useLayoutEffect(() => {
    if (!processReview || recaptureBridgeVisible) return;
    const processKey = processEventKey(processReview.event);
    if (!processKey || lastProcessTransitionKeyRef.current === processKey) return;
    lastProcessTransitionKeyRef.current = processKey;
    const transition = processReviewTransition(processReview);
    playSceneTransition(transition);
  }, [playSceneTransition, processReview, recaptureBridgeVisible]);

  useEffect(() => {
    const options = activeNightDetailOptions;
    setNightDetail((current) => options.some((item) => item.id === current) ? current : (options[0]?.id || ""));
    if (nightAction !== "diary") setNightNote("");
  }, [activeNightDetailOptionsKey, nightAction]);

  useEffect(() => {
    if (screen !== "game") return;
    mainScreenRef.current?.scrollTo({ top: 0, behavior: "auto" });
  }, [footerTab, screen]);

  useEffect(() => {
    if (view.intensity_cap !== "medium") return;
    setPlanSlots((current) => current.map((slot) => slot.intensity === "heavy" ? { ...slot, intensity: "medium" } : slot));
  }, [view.intensity_cap]);

  function startRoute(nextRoute: RouteKey) {
    if (previewRole) {
      setPayload(nextRoute === "capture_assistant" ? buildPlannerPreview() : buildNightPreview());
      setProcessReview(null);
      setScreen("game");
      setFooterTab("status");
      setPlanSlots(defaultPlanSlots());
      return;
    }
    void runWithWait(
      "正在建立囚禁档案...",
      "STATUS: INITIALIZING ROUTE",
      () => executeCaptivityCommand(`new_game route=${nextRoute}`),
    ).then((next) => {
      if (!next) return;
      lastSceneKeyRef.current = String(viewFromPayload(next).scene_copy?.key || "");
      setScreen("game");
      setFooterTab("status");
      setPlanSlots(defaultPlanSlots());
      continueAutomaticSync(next, true, true);
    });
  }

  function returnToSelector() {
    setIdentityConfirmOpen(false);
    setProcessReview(null);
    setRecaptureBridgeVisible(false);
    setHistoryDetail(null);
    setMonitorRoomOpen(false);
    setInventoryRoomOpen(false);
    setFooterTab("status");
    setWait({ visible: false, title: "", detail: "" });
    setScreen("selector");
  }

  function updatePlanSlot(index: number, patch: Partial<PlanSlot>) {
    setPlanSlots((prev) => prev.map((slot, i) => {
      if (i !== index) return slot;
      if (!patch.action || patch.action === slot.action) return { ...slot, ...patch };
      const nextAction = patch.action;
      const nextModifiers = nextAction === "training"
        ? slot.modifiers.filter((item) => item !== "training")
        : slot.modifiers;
      return {
        ...slot,
        ...patch,
        contents: defaultContentsForAction(nextAction),
        tools: [],
        modifiers: nextModifiers,
        trainingContents: nextAction === "training"
          ? (slot.trainingContents.length ? slot.trainingContents : ["obedience_commands"])
          : nextModifiers.includes("training") ? slot.trainingContents : [],
      };
    }));
  }

  function togglePlanValue(index: number, key: "modifiers" | "tools" | "contents" | "trainingContents", value: string) {
    setPlanSlots((prev) => prev.map((slot, i) => {
      if (i !== index) return slot;
      const current = new Set(slot[key]);
      if (current.has(value)) {
        const mustKeepOne = (
          (key === "contents" && Boolean((ACTION_CONTENT_OPTIONS[slot.action] || []).length))
          || (key === "trainingContents" && (slot.action === "training" || slot.modifiers.includes("training")))
        );
        if (!mustKeepOne || current.size > 1) current.delete(value);
      }
      else {
        const limit = key === "tools" ? 2 : (key === "contents" || key === "trainingContents") ? 3 : Number.POSITIVE_INFINITY;
        if (current.size < limit) current.add(value);
      }
      const next: PlanSlot = { ...slot, [key]: Array.from(current) };
      if (key === "modifiers" && value === "training") {
        next.trainingContents = current.has("training")
          ? (slot.trainingContents.length ? slot.trainingContents : ["obedience_commands"])
          : [];
      }
      return next;
    }));
  }

  function toggleInterventionValue(kind: "modifiers" | "tools", value: string) {
    if (kind === "modifiers" && value === "training") {
      const enabling = !interventionModifiers.includes("training");
      setInterventionTrainingContents(enabling ? ["obedience_commands"] : []);
    }
    const setter = kind === "modifiers" ? setInterventionModifiers : setInterventionTools;
    setter((prev) => {
      const current = new Set(prev);
      if (current.has(value)) current.delete(value);
      else if (kind !== "tools" || current.size < 2) current.add(value);
      return Array.from(current);
    });
  }

  function toggleInterventionTrainingContent(value: string) {
    setInterventionTrainingContents((prev) => {
      const current = new Set(prev);
      if (current.has(value)) {
        if (current.size > 1) current.delete(value);
      }
      else if (current.size < 3) current.add(value);
      return Array.from(current);
    });
  }

  function toggleRecaptureRule(value: string) {
    setRecaptureRules((prev) => {
      const current = new Set(prev);
      if (current.has(value)) {
        if (current.size > 1) current.delete(value);
      } else if (current.size < 3) current.add(value);
      return Array.from(current);
    });
  }

  function toggleRecaptureModifier(value: string) {
    setRecaptureModifiers((prev) => {
      const current = new Set(prev);
      if (current.has(value)) current.delete(value);
      else current.add(value);
      if (value === "training") {
        setRecaptureTrainingContents(current.has("training") ? ["obedience_commands"] : []);
      }
      return Array.from(current);
    });
  }

  function toggleRecaptureTrainingContent(value: string) {
    setRecaptureTrainingContents((prev) => {
      const current = new Set(prev);
      if (current.has(value)) {
        if (current.size > 1) current.delete(value);
      } else if (current.size < 3) current.add(value);
      return Array.from(current);
    });
  }

  function toggleRecaptureTool(value: string) {
    setRecaptureTools((prev) => {
      const current = new Set(prev);
      if (current.has(value)) current.delete(value);
      else if (current.size < 2) current.add(value);
      return Array.from(current);
    });
  }

  function buildActionSpec(slot: PlanSlot) {
    const parts = [
      `action=${slot.action}`,
      `intensity=${slot.intensity}`,
    ];
    if (slot.modifiers.length) parts.push(`modifiers=${quoteArg(slot.modifiers.join(","))}`);
    if (slot.tools.length) parts.push(`tools=${quoteArg(slot.tools.join(","))}`);
    if (slot.contents.length) parts.push(`contents=${quoteArg(slot.contents.join(","))}`);
    if (slot.trainingContents.length) parts.push(`training_contents=${quoteArg(slot.trainingContents.join(","))}`);
    if (slot.line.trim()) parts.push(`line=${quoteArg(slot.line.trim())}`);
    if (slot.action === "feeding") {
      parts.push(`source=${slot.feedingSource}`);
      parts.push(`additive=${slot.feedingAdditive}`);
    }
    return parts.join(" ");
  }

  function buildPlanCommand() {
    return `plan_day ${planSlots.map(buildActionSpec).join(" || ")}`;
  }

  function buildReturnActionCommand() {
    return `day_action ${buildActionSpec(planSlots[0])}`;
  }

  function buildPreviewPlanPayload(singleAction = false): CaptivityPayload {
    const sourceSlots = singleAction ? planSlots.slice(0, 1) : planSlots;
    const dayPlan: DayPlanSpec[] = sourceSlots.map((slot) => ({
      action: slot.action,
      action_label: actionLabel(slot.action),
      intensity: slot.intensity,
      modifiers: [...slot.modifiers],
      tools: [...slot.tools],
      contents: [...slot.contents],
      training_contents: [...slot.trainingContents],
      line: slot.line.trim(),
      feeding: slot.action === "feeding"
        ? { source: slot.feedingSource, additive: slot.feedingAdditive }
        : {} as Record<string, string>,
    }));
    const first = dayPlan[0] || {};
    const requiresProcess = Boolean(
      (first.modifiers || []).some((item) => item === "training" || item === "sex" || item === "process")
      || (first.tools || []).length
      || (first.training_contents || []).length
      || (first.contents || []).some((item) => PROCESS_ACTION_CONTENT_IDS.has(item))
      || first.action === "training"
      || first.action === "punishment"
    );
    const event: CaptivityEvent = {
      id: "preview-planned-action",
      day: view.current_day || 7,
      slot: singleAction ? 0 : 1,
      phase: "day",
      route,
      action: first.action || "feeding",
      action_label: first.action_label || actionLabel(first.action) || "行动",
      intensity: first.intensity || "medium",
      line: first.line || "第一段安排已经下发。",
      modifiers: first.modifiers || [],
      tools: first.tools || [],
      contents: first.contents || [],
      training_contents: first.training_contents || [],
      feeding: first.feeding || {},
      effects: {},
      requires_process: requiresProcess,
      tags: singleAction ? ["preview", "special_day", "escape_stay_return"] : ["preview"],
    };
    const nextView: CaptivityView = {
      ...view,
      phase: "day",
      day_action_count: 0,
      day_plan: singleAction ? [] : dayPlan,
      pending_event: {
        id: "preview-planned-pending",
        type: requiresProcess ? "process_reaction_write" : "action_response",
        day: event.day,
        slot: event.slot,
        actor: "assistant",
        captive: "assistant",
        action: event.action,
        phase: requiresProcess ? "waiting_process_reaction" : "waiting_response",
        event,
      },
    };
    return {
      ok: true,
      captor_view: nextView,
      captive_view: { ...nextView, viewer: "captive" },
      player_text: singleAction ? "本地预览：回来后的行为已确定。" : "本地预览：今日安排已记录。",
    };
  }

  function submitPlan() {
    if (previewRole === "captor") {
      setPayload(buildPreviewPlanPayload(isReturnActionPlanner));
      setFooterTab("status");
      return;
    }
    void runWithWait(
      isReturnActionPlanner ? "正在确定回来后的行为..." : "正在下发今日安排...",
      "SYNC_RESULT: PENDING",
      () => executeCaptivityCommand(isReturnActionPlanner ? buildReturnActionCommand() : buildPlanCommand()),
    ).then((next) => continueAutomaticSync(next));
  }

  function submitResponse() {
    if (previewRole) return;
    void runWithWait(
      "正在提交回应...",
      "REASON: WAITING_FOR_SUBJECT_REACTION",
      () => executeCaptivityCommand(`respond_action response=${response} mood=${quoteArg(responseMood)} line=${quoteArg(responseLine.trim())}`),
    ).then((next) => {
      if (!next) return;
      setResponseLine("");
      continueAutomaticSync(next);
    });
  }

  function submitMood() {
    if (previewRole) return;
    void runWithWait(
      "正在记录此刻心情...",
      "STATUS: ARCHIVING PROCESS_REACTION",
      () => executeCaptivityCommand(`choose_mood mood=${quoteArg(reactionMood)} line=${quoteArg(reactionLine.trim())}`),
    ).then((next) => {
      if (!next) return;
      setReactionLine("");
      continueAutomaticSync(next);
    });
  }

  function submitNightAction() {
    if (nightAction === "diary" && !nightNote.trim()) return;
    if (nightPreviewRole) {
      if (nightAction === "ring_bell") {
        setPayload((previous) => {
          if (!previous) return previous;
          const previewView = previous.captive_view || previous.state || {};
          const event: CaptivityEvent = {
            id: "preview-bell-voice-first-use",
            day: previewView.current_day || 7,
            slot: 0,
            phase: "night",
            route: "captured_by_assistant",
            action: "ring_bell",
            action_label: "按响语音铃",
            line: nightLine.trim(),
            modifiers: ["night"],
            bell_voice: {
              line: "请主人来使用我。",
              first_reveal: true,
            },
          };
          const nextView: CaptivityView = {
            ...previewView,
            pending_event: {
              id: "preview-bell-voice-reveal",
              type: "bell_voice_reveal",
              day: previewView.current_day || 7,
              actor: "user",
              captive: "user",
              phase: "waiting_bell_voice_reveal",
              required_directive: "ack_bell_voice",
              event,
            },
          };
          return { ...previous, state: nextView, captive_view: nextView, player_text: "预录的声音第一次响了起来。" };
        });
      } else {
        const previewSecrets: Record<string, { itemId: string; itemLabel: string; text: string }> = {
          read: { itemId: "book", itemLabel: "书", text: "你翻开书，夹页里留着一行字：「翻到这里的时候，我就知道你会看。」" },
          game: { itemId: "switch", itemLabel: "Switch", text: "屏幕亮起，唯一的用户名称是「PLAYER 2」。" },
          diary: { itemId: "notebook", itemLabel: "日记本", text: "你翻开日记本，第一页写着：「第一页留给你。」" },
        };
        const secret = previewSecrets[nightAction];
        if (secret) {
          setPayload((previous) => {
            if (!previous) return previous;
            const previewView = previous.captive_view || previous.state || {};
            const nextView: CaptivityView = {
              ...previewView,
              pending_event: {
                id: "preview-item-secret-reveal",
                type: "item_secret_reveal",
                day: previewView.current_day || 7,
                actor: "user",
                captive: "user",
                phase: "waiting_item_secret_reveal",
                required_directive: "ack_item_secret",
                item_secret: {
                  item_id: secret.itemId,
                  item_label: secret.itemLabel,
                  text: secret.text,
                },
              },
            };
            return { ...previous, state: nextView, captive_view: nextView, player_text: `${secret.itemLabel}的隐藏彩蛋第一次出现了。` };
          });
        } else {
          showPreviewSyncWait();
        }
      }
      return;
    }
    if (previewRole) return;
    const parts = [`night_action action=${nightAction}`];
    if (nightDetail) parts.push(`detail=${nightDetail}`);
    if (nightAction === "diary" && nightNote.trim()) parts.push(`note=${quoteArg(nightNote.trim())}`);
    parts.push(`line=${quoteArg(nightLine.trim())}`);
    void runWithWait(
      "正在保存夜间行动...",
      "STATUS: SAVING MONITOR DATA",
      () => executeCaptivityCommand(parts.join(" ")),
    ).then((next) => continueAutomaticSync(next));
  }

  function ackBellVoice() {
    if (nightPreviewRole) {
      setPayload((previous) => {
        if (!previous) return previous;
        const previewView = previous.captive_view || previous.state || {};
        const nextView: CaptivityView = {
          ...previewView,
          pending_event: {
            id: "preview-bell-response-choice",
            type: "bell_response_choice",
            day: previewView.current_day || 7,
            actor: "assistant",
            captive: "user",
            phase: "waiting_bell_response",
            required_directive: "【选择：不过去】或【过去：完整亲密互动过程】",
            event: previewView.pending_event?.event,
          },
        };
        return { ...previous, state: nextView, captive_view: nextView, player_text: "等待{assistant}决定是否过去。" };
      });
      window.setTimeout(showPreviewSyncWait, 0);
      return;
    }
    if (previewRole) return;
    void runWithWait(
      "正在确认铃声...",
      "STATUS: BELL_VOICE_HEARD",
      () => executeCaptivityCommand("ack_bell_voice"),
    ).then((next) => continueAutomaticSync(next));
  }

  function ackItemSecret() {
    if (nightPreviewRole) {
      setPayload((previous) => {
        if (!previous) return previous;
        const previewView = previous.captive_view || previous.state || {};
        const nextView: CaptivityView = {
          ...previewView,
          pending_event: {
            id: "preview-item-monitor-gate",
            type: "monitor_gate",
            day: previewView.current_day || 7,
            actor: "assistant",
            captive: "user",
            phase: "waiting_monitor_gate",
            sealed: true,
          },
        };
        return { ...previous, state: nextView, captive_view: nextView, player_text: "物品彩蛋已经看完。" };
      });
      window.setTimeout(showPreviewSyncWait, 0);
      return;
    }
    if (previewRole) return;
    void runWithWait(
      "正在收起物品彩蛋...",
      "STATUS: ITEM_SECRET_SEEN",
      () => executeCaptivityCommand("ack_item_secret"),
    ).then((next) => continueAutomaticSync(next));
  }

  function continueAutomaticSync(next: CaptivityPayload | null, force = false, background = false) {
    if (!next) return;
    const nextView = viewFromPayload(next);
    const nextPendingType = String(nextView.pending_event?.type || "");
    if (nextPendingType === "bell_voice_reveal" || nextPendingType === "item_secret_reveal") return;
    const waitingForAssistantNext = String(nextView.pending_event?.actor || "") === "assistant";
    const endingNext = String(nextView.phase || "") === "ending" || nextPendingType.startsWith("ending_") || Boolean(nextView.ending_state);
    if (!force && !waitingForAssistantNext && !endingNext) return;
    syncAssistant(endingNext ? "ending" : "state_update", next, background);
  }

  function playNextStageForPayload(next: CaptivityPayload) {
    const backendSceneKey = String(viewFromPayload(next).scene_copy?.key || "");
    if (backendSceneKey) lastSceneKeyRef.current = backendSceneKey;
    playSceneTransition(nextStageTransition(next));
  }

  function syncAssistant(
    mode: "chat" | "state_update" | "ending" = "state_update",
    previousPayloadOverride?: CaptivityPayload | null,
    background = false,
  ) {
    if (previewRole) {
      showPreviewSyncWait();
      return;
    }
    const previousPayload = previousPayloadOverride === undefined ? payload : previousPayloadOverride;
    const handleResult = (next: CaptivityPayload | null) => {
      if (!next || mode === "ending") return;
      const review = findNewProcessReview(next, previousPayload);
      if (review) {
        setProcessReview(review);
        setFooterTab("history");
      }
      const nextView = viewFromPayload(next);
      if (String(nextView.pending_event?.actor || "") === "assistant") {
        lastFailedRetryRef.current = () => syncAssistant(mode, next, background);
        setHasFailedRetry(true);
      }
    };
    if (!background) {
      void runWithWait(
        "正在同步{assistant}...",
        "STATUS: ENCRYPTING DATA",
        () => syncCaptivityToAssistant(mode, "", true),
      ).then(handleResult);
      return;
    }
    setBackgroundSyncing(true);
    lastFailedRetryRef.current = null;
    setHasFailedRetry(false);
    void syncCaptivityToAssistant(mode, "", true)
      .then((next) => {
        applyPayload(next);
        handleResult(next);
      })
      .catch((error: any) => {
        const message = String(error?.message || error || "同步失败");
        lastFailedRetryRef.current = () => syncAssistant(mode, previousPayload, true);
        setHasFailedRetry(true);
        setWait({ visible: true, title: "同步失败", detail: message, error: message });
      })
      .finally(() => setBackgroundSyncing(false));
  }

  function saveProcessReview() {
    if (!processReview) return;
    if (escapePreviewRole) {
      const currentView = viewFromPayload(payload);
      const archivedEvent: CaptivityEvent = {
        ...processReview.event,
        post_reaction: {
          mood: reactionMood,
          line: reactionLine.trim(),
        },
        mood_after: reactionMood,
      };
      const embeddedRules = archivedEvent.recapture_rules || {};
      const nextView: CaptivityView = {
        ...currentView,
        pending_event: escapePreviewRole === "captive" ? {
          id: "preview-recapture-rules-review",
          type: "recapture_rules_review",
          day: 12,
          slot: 0,
          actor: "user",
          captive: "user",
          phase: "reviewing_recapture_rules",
          source_event_id: String(processReview.event.id || "preview-escape-recapture"),
          rule_ids: embeddedRules.rule_ids || ["double_lock", "key_isolation"],
          rule_labels: embeddedRules.rule_labels || ["加装双重门锁", "禁止接触钥匙和门锁"],
          event: archivedEvent,
        } : {
          id: "preview-recapture-rules",
          type: "recapture_rules_choice",
          day: 12,
          slot: 0,
          actor: "user",
          captive: "assistant",
          phase: "waiting_recapture_rules",
          source_event_id: String(processReview.event.id || "preview-escape-recapture"),
          available_rules: RECAPTURE_RULE_OPTIONS.map((item) => item.id),
          event: archivedEvent,
        },
        event_log: [...(currentView.event_log || []), archivedEvent],
        mood: reactionMood,
        mood_line: reactionLine.trim(),
      };
      setPayload({
        ok: true,
        captive_view: nextView,
        captor_view: { ...nextView, viewer: "captor" },
        player_text: "本地预览：抓回事件已保存，进入重新立规矩。",
      });
      setReactionLine("");
      setProcessReview(null);
      setFooterTab("status");
      playSceneTransition({
        key: `after-recapture:${String(archivedEvent.id || "event")}`,
        kicker: "AFTER ESCAPE / RULES",
        title: "重新立规矩",
        body: "抓回的经过已经收进回顾。接下来留下的规矩，会继续影响之后的日子。",
        tone: "special",
      });
      return;
    }
    if (processPreviewRole) {
      const next = buildProcessPreviewAfterSave(processPreviewRole, reactionMood, reactionLine.trim());
      setPayload(next);
      setReactionLine("");
      setProcessReview(null);
      setFooterTab("status");
      playNextStageForPayload(next);
      return;
    }
    if (!processReview.moodRequired) {
      setReactionLine("");
      setProcessReview(null);
      setFooterTab("status");
      if (role === "captor" && pendingType === "advance_action" && userIsPendingActor) {
        void runWithWait(
          "正在进入今日安排...",
          "STATUS: ADVANCING_ACTION",
          () => executeCaptivityCommand("advance_day_action"),
        ).then((next) => {
          if (!next) return;
          playNextStageForPayload(next);
          continueAutomaticSync(next);
        });
      } else if (payload) {
        playNextStageForPayload(payload);
      }
      return;
    }
    void runWithWait(
      "正在保存到回顾...",
      "STATUS: ARCHIVING PROCESS_REACTION",
      () => executeCaptivityCommand(`choose_mood mood=${quoteArg(reactionMood)} line=${quoteArg(reactionLine.trim())}`),
    ).then((next) => {
      if (!next) return;
      setReactionLine("");
      setProcessReview(null);
      setFooterTab("status");
      playNextStageForPayload(next);
      continueAutomaticSync(next);
    });
  }

  function advanceDayAction() {
    if (previewRole) return;
    void runWithWait(
      "正在推进下一段行动...",
      "STATUS: ADVANCING SLOT",
      () => executeCaptivityCommand("advance_day_action"),
    ).then((next) => continueAutomaticSync(next));
  }

  function chooseEscape(choice: string) {
    if (choice === "escape") {
      setRecaptureBridgeVisible(true);
      if (escapePreviewRole) previewSyncReadyAtRef.current = Date.now() + 1200;
    }
    if (escapePreviewRole) {
      if (choice === "escape" || choice.startsWith("abort_")) {
        const preview = buildEscapeRecaptureReview(payload, escapePreviewRole, choice);
        if (choice === "escape") {
          window.setTimeout(() => {
            setPayload(preview.payload);
            setProcessReview(preview.review);
            setFooterTab("history");
          }, 1000);
          return;
        }
        setPayload(preview.payload);
        setProcessReview(preview.review);
        setFooterTab("history");
        return;
      }
      const currentView = viewFromPayload(payload);
      const choiceLabel = ESCAPE_CHOICE_LABELS[choice] || choice;
      const event: CaptivityEvent = {
        id: `preview-escape-${choice}`,
        day: 12,
        slot: 0,
        phase: "day",
        action: "escape_choice",
        action_label: `逃跑诱导：${choiceLabel}`,
        escape: { choice, choice_label: choiceLabel },
        tags: ["preview", "escape", `escape:${choice}`],
      };
      const nextView: CaptivityView = {
        ...currentView,
        pending_event: choice === "stay" ? {
          id: "preview-return-action",
          type: "return_action_choice",
          day: 12,
          slot: 0,
          actor: currentView.captor || "assistant",
          captive: currentView.captive,
          phase: "waiting_return_action",
          source_event_id: event.id,
          available_actions: ACTION_OPTIONS.map((item) => item.id),
        } : null,
        event_log: [...(currentView.event_log || []), event],
      };
      setPayload({
        ok: true,
        captive_view: nextView,
        captor_view: { ...nextView, viewer: "captor" },
        player_text: `本地预览：已选择${choiceLabel}。`,
      });
      if (choice === "stay") {
        previewSyncReadyAtRef.current = Date.now() + 1200;
        setWait({
          visible: true,
          title: "正在同步{assistant}...",
          detail: "STATUS: ENCRYPTING DATA",
        });
      }
      return;
    }
    if (previewRole) return;
    void runWithWait(
      "正在记录逃跑选择...",
      "STATUS: RESOLVING ESCAPE_WINDOW",
      () => executeCaptivityCommand(`resolve_escape_choice ${choice}`),
      choice === "escape",
    ).then((next) => continueAutomaticSync(next, false, choice === "escape"));
  }

  function submitRecaptureRules() {
    if (escapePreviewRole) {
      const currentView = viewFromPayload(payload);
      const ruleLabels = recaptureRules.map((id) => labelOf(RECAPTURE_RULE_OPTIONS, id));
      const ruleEvent: CaptivityEvent = {
        id: "preview-recapture-rules-event",
        day: 12,
        slot: 0,
        phase: "day",
        route: "capture_assistant",
        action: "recapture_rules",
        action_label: "抓回后重新立规矩",
        tags: ["preview", "recapture", "recapture:rules_set"],
        recapture_context: { rule_ids: recaptureRules, rule_labels: ruleLabels },
      };
      const nextView: CaptivityView = {
        ...currentView,
        recapture_state: { active: true, rules: recaptureRules, source_day: 12 },
        event_log: [...(currentView.event_log || []), ruleEvent],
        pending_event: {
          id: "preview-recapture-followup",
          type: "recapture_followup_choice",
          day: 12,
          slot: 0,
          actor: "user",
          captive: "assistant",
          phase: "waiting_recapture_followup",
          available_actions: RECAPTURE_FOLLOWUP_OPTIONS.map((item) => item.id),
          event: ruleEvent,
        },
      };
      setPayload({ ok: true, captor_view: nextView, captive_view: { ...nextView, viewer: "captive" }, player_text: "本地预览：新规矩已生效。" });
      return;
    }
    if (previewRole) return;
    void runWithWait(
      "正在保存新规矩...",
      "STATUS: APPLYING RULES",
      () => executeCaptivityCommand(`set_recapture_rules rules=${quoteArg(recaptureRules.join(","))}`),
    ).then((next) => continueAutomaticSync(next));
  }

  function confirmRecaptureRules() {
    if (escapePreviewRole === "captive") {
      const currentView = viewFromPayload(payload);
      const ruleIds = currentView.pending_event?.rule_ids || [];
      const ruleLabels = currentView.pending_event?.rule_labels || [];
      const ruleEvent: CaptivityEvent = {
        id: "preview-recapture-rules-confirmed",
        day: 12,
        slot: 0,
        phase: "day",
        route: "captured_by_assistant",
        action: "recapture_rules",
        action_label: "抓回后重新立规矩",
        tags: ["preview", "recapture", "recapture:rules_set"],
        recapture_context: { rule_ids: ruleIds, rule_labels: ruleLabels },
      };
      const nextView: CaptivityView = {
        ...currentView,
        current_day: 13,
        day_action_count: 0,
        phase: "day",
        mood: "",
        mood_line: "",
        day_plan: [],
        recapture_state: { active: true, rules: ruleIds, source_day: 12 },
        event_log: [...(currentView.event_log || []), ruleEvent],
        pending_event: {
          id: "preview-next-day-plan",
          type: "day_plan_choice",
          day: 13,
          slot: 0,
          actor: "assistant",
          captive: "user",
          phase: "waiting_day_plan",
          available_actions: ACTION_OPTIONS.map((item) => item.id),
        },
      };
      setPayload({
        ok: true,
        captive_view: nextView,
        captor_view: { ...nextView, viewer: "captor" },
        player_text: "本地预览：新规矩已确认，进入第 13 天。",
      });
      return;
    }
    if (previewRole) return;
    void runWithWait(
      "正在进入新的一天...",
      "STATUS: CONFIRMING RULES",
      () => executeCaptivityCommand("confirm_recapture_rules"),
    ).then((next) => continueAutomaticSync(next));
  }

  function submitRecaptureFollowup() {
    if (escapePreviewRole) {
      const currentView = viewFromPayload(payload);
      const requiresProcess = recaptureFollowup === "punishment"
        || recaptureFollowup === "search_confiscation"
        || recaptureFollowup === "training"
        || recaptureModifiers.length > 0
        || recaptureTools.length > 0;
      const followupEvent: CaptivityEvent = {
        id: "preview-recapture-followup-event",
        day: 12,
        slot: 0,
        phase: "day",
        route: "capture_assistant",
        action: "recapture_followup",
        action_label: `抓回后处理：${labelOf(RECAPTURE_FOLLOWUP_OPTIONS, recaptureFollowup)}`,
        intensity: recaptureIntensity,
        modifiers: recaptureModifiers,
        training_contents: recaptureTrainingContents,
        tools: recaptureTools,
        line: recaptureLine,
        requires_process: requiresProcess,
        tags: ["preview", "recapture", "recapture:followup"],
        recapture_context: {
          followup: recaptureFollowup,
          followup_label: labelOf(RECAPTURE_FOLLOWUP_OPTIONS, recaptureFollowup),
          rule_ids: currentView.recapture_state?.rules || [],
          rule_labels: (currentView.recapture_state?.rules || []).map((id) => labelOf(RECAPTURE_RULE_OPTIONS, id)),
        },
      };
      const nextView: CaptivityView = {
        ...currentView,
        pending_event: {
          id: "preview-recapture-process",
          type: requiresProcess ? "process_reaction_write" : "action_response",
          day: 12,
          slot: 0,
          actor: "assistant",
          captive: "assistant",
          phase: requiresProcess ? "waiting_process_reaction" : "waiting_action_response",
          event: followupEvent,
        },
      };
      setPayload({ ok: true, captor_view: nextView, captive_view: { ...nextView, viewer: "captive" }, player_text: "本地预览：后续处理已确定，等待{assistant}回应。" });
      return;
    }
    if (previewRole) return;
    const parts = [
      `choose_recapture_followup action=${recaptureFollowup}`,
      `intensity=${recaptureIntensity}`,
    ];
    if (recaptureModifiers.length) parts.push(`modifiers=${quoteArg(recaptureModifiers.join(","))}`);
    if (recaptureTrainingContents.length) parts.push(`training_contents=${quoteArg(recaptureTrainingContents.join(","))}`);
    if (recaptureTools.length) parts.push(`tools=${quoteArg(recaptureTools.join(","))}`);
    if (recaptureLine.trim()) parts.push(`line=${quoteArg(recaptureLine.trim())}`);
    void runWithWait(
      "正在下发后续处理...",
      "STATUS: LINKING RECAPTURE EVENT",
      () => executeCaptivityCommand(parts.join(" ")),
    ).then((next) => continueAutomaticSync(next));
  }

  function openMonitor(style: "occasional" | "full") {
    if (previewRole) return;
    void runWithWait(
      "正在打开监控...",
      "STATUS: DECRYPTING NIGHT_LOG",
      () => executeCaptivityCommand(`view_monitor ${style}`),
    );
  }

  function handleMonitor(strategy: string) {
    if (previewRole) return;
    const parts = [`monitor_action ${strategy}`];
    if (strategy === "intervene") {
      const confirmed = typeof window === "undefined" || window.confirm("即将把本次监控介入同步给{assistant}，由{assistant}写具体经过。确认进入详细事件？");
      if (!confirmed) return;
      parts.push(`intent=${interventionIntent}`);
      if (interventionModifiers.length) parts.push(`modifiers=${quoteArg(interventionModifiers.join(","))}`);
      if (interventionTrainingContents.length) parts.push(`training_contents=${quoteArg(interventionTrainingContents.join(","))}`);
      if (interventionTools.length) parts.push(`tools=${quoteArg(interventionTools.join(","))}`);
      if (interventionLine.trim()) parts.push(`line=${quoteArg(interventionLine.trim())}`);
    }
    if (monitorNote.trim()) parts.push(`note=${quoteArg(monitorNote.trim())}`);
    void runWithWait(
      "正在记录监控处理...",
      "正在保存监控处理",
      () => executeCaptivityCommand(parts.join(" ")),
    ).then((next) => continueAutomaticSync(next));
  }

  function scheduleEscape() {
    if (previewRole) return;
    void runWithWait(
      "正在设置逃跑诱导...",
      "STATUS: SCHEDULING ESCAPE_WINDOW",
      () => executeCaptivityCommand(`schedule_escape_window day=${escapeDay} hint=${quoteArg(escapeHint.trim())} bait=${quoteArg(escapeBait.trim())}`),
    );
  }

  function applyInventoryItem(itemId: InventoryItemId, enabled: boolean, secret = "") {
    if (previewRole) {
      setPayload((previous) => {
        if (!previous) return previous;
        const previewCaptorView = previous.captor_view || {};
        return {
          ...previous,
          captor_view: {
            ...previewCaptorView,
            inventory: {
              ...(previewCaptorView.inventory || {}),
              [itemId]: enabled,
            },
            inventory_secrets: {
              ...(previewCaptorView.inventory_secrets || {}),
              [itemId]: enabled
                ? { content: secret || "默认彩蛋", revealed: false, configured_by: "user", configured_at: "preview-local" }
                : { content: "", revealed: false, configured_by: "", configured_at: "" },
            },
            call_bell_voice: itemId === "call_bell"
              ? (enabled
                ? { line: secret, revealed: false, configured_by: "user", configured_at: "preview-local" }
                : { line: "", revealed: false, configured_by: "", configured_at: "" })
              : previewCaptorView.call_bell_voice,
          },
        };
      });
      return;
    }
    void runWithWait(
      enabled ? "正在赠送物品..." : "正在收回物品...",
      "STATUS: UPDATING INVENTORY",
      () => executeCaptivityCommand(
        `${enabled ? "gift_item" : "revoke_item"} items=${itemId}${enabled && itemId === "call_bell" ? ` voice_line=${quoteArg(secret)}` : enabled && secret ? ` secret=${quoteArg(secret)}` : ""}`,
      ),
    ).then((next) => continueAutomaticSync(next, true));
  }

  function closeSubpage() {
    setMonitorRoomOpen(false);
    setInventoryRoomOpen(false);
    setFooterTab("special");
  }

  return (
      <div className="captivity-game">
      <div className="vertical-text uppercase">CAPTIVITY SIMULATOR / LOCAL_SAVE / SYSTEM_ALPHA</div>
      {monitorRoomOpen || inventoryRoomOpen ? null : (
        <button className="return-capsule" type="button" aria-label="返回游戏大厅" onClick={onBack}>
          <ChevronLeftIcon />
        </button>
      )}
      <div className="cross" style={{ top: "20%", left: "10%" }} />
      <div className="cross" style={{ bottom: "20%", right: "15%" }} />

      <section className={`screen bootstrap-screen ${bootstrapping ? "active" : ""}`}>
        <div className="serif bootstrap-title">Captivity <span className="pink-text">Simulator</span></div>
        <div className="uppercase bootstrap-copy">正在读取囚禁档案</div>
      </section>

      <section id="selector-screen" className={`screen ${!bootstrapping && screen === "selector" ? "active" : ""}`}>
        <h1 className="selector-title serif">
          <span>Captivity</span>
          <span>Simulator</span>
        </h1>
        {hasExistingProgress ? (
          <div className="selector-save-warning">
            当前存档仍保留。重新选择任一身份会开始新游戏并覆盖当前进度。
          </div>
        ) : null}
        <button className="identity-card" type="button" onClick={() => startRoute("captured_by_assistant")}>
          <div className="uppercase">CAPTIVE</div>
          <div className="identity-card-title serif">被囚禁方</div>
        </button>
        <button className="identity-card" type="button" onClick={() => startRoute("capture_assistant")}>
          <div className="uppercase">MASTER</div>
          <div className="identity-card-title serif">囚禁方</div>
        </button>
      </section>

      <section ref={mainScreenRef} id={role === "captor" ? "master-screen" : "captive-screen"} className={`screen ${!bootstrapping && screen === "game" && !monitorRoomOpen && !inventoryRoomOpen ? "active" : ""}`}>
        <div className="header">
          <div className="day-big">{view.total_days || 30}</div>
          <div className="header-meta">
            <div className="uppercase pink-text">DAY {view.current_day || 1} / {view.total_days || 30}</div>
            <button
              className="identity-switch uppercase serif"
              type="button"
              aria-label="返回身份选择"
              disabled={busy}
              onClick={() => setIdentityConfirmOpen(true)}
            >
              <span>IDENTITY: {role === "captor" ? "囚禁方" : "被囚禁方"}</span>
            </button>
          </div>
          <div className="title-line">
            <h2 className="serif title-main">
              {role === "captor" ? "掌控面板" : "囚禁日记"} / <span className="pink-text">{role === "captor" ? "CMD" : "Log"}</span>
            </h2>
            <div className="time-chip">{timeSegmentLabel(view, pending)}</div>
          </div>
        </div>

        {milestoneCopy ? <div className="serif day-milestone-copy">{milestoneCopy}</div> : null}

        {footerTab === "status" ? (
          <>
            {role === "captive" ? <StatusGrid stats={stats} mood={view.mood} flags={view.status_flags} role="captive" /> : null}
            {role === "captor" ? <TargetStatusPanel view={view} /> : null}
            {showPlanner ? (
              <PlannerPanel
                slots={isReturnActionPlanner ? planSlots.slice(0, 1) : planSlots}
                singleAction={isReturnActionPlanner}
                intensityCap={view.intensity_cap}
                disabled={busy}
                onSlotChange={updatePlanSlot}
                onToggle={togglePlanValue}
                onSubmit={submitPlan}
              />
            ) : (
              <RuntimePanel
                role={role}
                view={view}
                pending={pending}
                currentEvent={currentEvent}
                waitingForAssistant={waitingForAssistant}
                userIsPendingActor={userIsPendingActor}
                canChooseNight={canChooseNight}
                availableNightActions={availableNightActions}
                nightCondition={view.night_condition || null}
                response={response}
                responseMood={responseMood}
                responseLine={responseLine}
                reactionMood={reactionMood}
                reactionLine={reactionLine}
                nightAction={nightAction}
                nightDetail={nightDetail}
                nightDetailOptions={activeNightDetailOptions}
                nightNote={nightNote}
                nightLine={nightLine}
                monitorNote={monitorNote}
                interventionIntent={interventionIntent}
                interventionModifiers={interventionModifiers}
                interventionTrainingContents={interventionTrainingContents}
                interventionTools={interventionTools}
                interventionLine={interventionLine}
                recaptureRules={recaptureRules}
                recaptureFollowup={recaptureFollowup}
                recaptureIntensity={recaptureIntensity}
                recaptureModifiers={recaptureModifiers}
                recaptureTrainingContents={recaptureTrainingContents}
                recaptureTools={recaptureTools}
                recaptureLine={recaptureLine}
                lastText={lastText}
                disabled={busy}
                onResponseChange={setResponse}
                onResponseMoodChange={setResponseMood}
                onResponseLineChange={setResponseLine}
                onReactionMoodChange={setReactionMood}
                onReactionLineChange={setReactionLine}
                onNightActionChange={setNightAction}
                onNightDetailChange={setNightDetail}
                onNightNoteChange={setNightNote}
                onNightLineChange={setNightLine}
                onMonitorNoteChange={setMonitorNote}
                onInterventionIntentChange={setInterventionIntent}
                onInterventionModifierToggle={(value) => toggleInterventionValue("modifiers", value)}
                onInterventionTrainingContentToggle={toggleInterventionTrainingContent}
                onInterventionToolToggle={(value) => toggleInterventionValue("tools", value)}
                onInterventionLineChange={setInterventionLine}
                onRecaptureRuleToggle={toggleRecaptureRule}
                onRecaptureFollowupChange={(value) => {
                  setRecaptureFollowup(value);
                  if (value === "training" && !recaptureTrainingContents.length) setRecaptureTrainingContents(["obedience_commands"]);
                }}
                onRecaptureIntensityChange={setRecaptureIntensity}
                onRecaptureModifierToggle={toggleRecaptureModifier}
                onRecaptureTrainingContentToggle={toggleRecaptureTrainingContent}
                onRecaptureToolToggle={toggleRecaptureTool}
                onRecaptureLineChange={setRecaptureLine}
                onSubmitResponse={submitResponse}
                onSubmitMood={submitMood}
                onSubmitNightAction={submitNightAction}
                onAckBellVoice={ackBellVoice}
                onAckItemSecret={ackItemSecret}
                onAdvance={advanceDayAction}
                onChooseEscape={chooseEscape}
                onConfirmRecaptureRules={confirmRecaptureRules}
                onSubmitRecaptureRules={submitRecaptureRules}
                onSubmitRecaptureFollowup={submitRecaptureFollowup}
                onOpenMonitor={openMonitor}
                onHandleMonitor={handleMonitor}
                onRefresh={() => void refreshStatus(false)}
              />
            )}
            <StatusRecoveryBar
              disabled={busy}
              canRetry={hasFailedRetry}
              onRetry={retryLastFailedOperation}
              onRefresh={() => void refreshStatus(false)}
            />
          </>
        ) : null}

        {footerTab === "history" ? (
          processReview ? (
            <ProcessReviewPanel
              review={processReview}
              mood={reactionMood}
              line={reactionLine}
              disabled={busy}
              onMoodChange={setReactionMood}
              onLineChange={setReactionLine}
              onSave={saveProcessReview}
            />
          ) : (
            <HistoryPanel
              events={eventLog}
              lastText={lastText}
              detail={historyDetail}
              onOpenDetail={setHistoryDetail}
              onCloseDetail={() => setHistoryDetail(null)}
            />
          )
        ) : null}
        {footerTab === "special" ? (
          <SpecialPanel
            role={role}
            view={view}
            escapeDay={escapeDay}
            escapeRoom={escapeRoom}
            escapeHint={escapeHint}
            escapeBait={escapeBait}
            disabled={busy}
            onEscapeDayChange={setEscapeDay}
            onEscapeRoomChange={(roomId) => {
              setEscapeRoom(roomId);
              setEscapeBait(escapeRoomBait(roomId));
            }}
            onEscapeHintChange={setEscapeHint}
            onEscapeBaitChange={setEscapeBait}
            onOpenMonitorRoom={() => {
              setInventoryRoomOpen(false);
              setMonitorRoomOpen(true);
            }}
            onOpenInventoryRoom={() => {
              setMonitorRoomOpen(false);
              setInventoryRoomOpen(true);
            }}
            onScheduleEscape={scheduleEscape}
          />
        ) : null}
      </section>

      <section id="monitor-room-screen" className={`screen monitor-room-screen ${!bootstrapping && screen === "game" && !processReview && monitorRoomOpen && role === "captor" ? "active" : ""}`}>
        <button className="subpage-return" type="button" aria-label="回到特殊页" onClick={closeSubpage}>
          <ChevronLeftIcon />
        </button>
        <MonitorRoomPanel
          view={view}
          pendingType={pendingType}
          monitorNote={monitorNote}
          interventionIntent={interventionIntent}
          interventionModifiers={interventionModifiers}
          interventionTrainingContents={interventionTrainingContents}
          interventionTools={interventionTools}
          interventionLine={interventionLine}
          disabled={busy}
          onMonitorNoteChange={setMonitorNote}
          onInterventionIntentChange={setInterventionIntent}
          onInterventionModifierToggle={(value) => toggleInterventionValue("modifiers", value)}
          onInterventionTrainingContentToggle={toggleInterventionTrainingContent}
          onInterventionToolToggle={(value) => toggleInterventionValue("tools", value)}
          onInterventionLineChange={setInterventionLine}
          onOpenMonitor={openMonitor}
          onHandleMonitor={handleMonitor}
        />
      </section>

      <section id="inventory-room-screen" className={`screen inventory-room-screen ${!bootstrapping && screen === "game" && !processReview && inventoryRoomOpen ? "active" : ""}`}>
        <button className="subpage-return" type="button" aria-label="回到特殊页" onClick={closeSubpage}>
          <ChevronLeftIcon />
        </button>
        {role === "captor" ? (
          <InventoryWarehouse
            activeItems={inventoryActiveItems}
            inventorySecrets={view.inventory_secrets || captorView.inventory_secrets}
            callBellVoice={view.call_bell_voice || captorView.call_bell_voice}
            disabled={busy}
            onGiftInventoryItem={(itemId, voiceLine) => applyInventoryItem(itemId, true, voiceLine)}
            onRevokeInventoryItem={(itemId) => applyInventoryItem(itemId, false)}
          />
        ) : (
          <CaptiveRoomInventory activeItems={inventoryActiveItems} />
        )}
      </section>

      {recaptureBridgeVisible ? (
        <div className="escape-recapture-bridge" aria-label="{assistant}正在靠近中">
          <div className="loading-animation" aria-hidden="true">+</div>
          <div className="serif pink-text" style={{ fontSize: 30, marginBottom: 10 }}>{"{assistant}正在靠近中"}</div>
          <div className="serif wait-scene-copy">这段记录已经送出，另一边正在决定接下来怎么做。</div>
          <div className="uppercase" style={{ letterSpacing: "0.1em", lineHeight: 1.5 }}>
            STATUS: ENCRYPTING DATA<br />
            SYNC_RESULT: PENDING<br />
            REASON: WAITING_FOR_SUBJECT_REACTION
          </div>
          <div className="divider" />
          <div className="btn-group" style={{ marginTop: 30 }}>
            <button className="btn" type="button" onClick={() => setRecaptureBridgeVisible(false)}>关闭</button>
            <button className="btn" type="button" onClick={() => void refreshStatus(false)}>刷新</button>
            <button className="btn" type="button" aria-label="重试上次操作" disabled={!hasFailedRetry} onClick={retryLastFailedOperation}>重试</button>
          </div>
        </div>
      ) : null}

      {sceneTransition ? (
        <SceneTransitionOverlay scene={sceneTransition} onDismiss={dismissSceneTransition} />
      ) : null}

      {identityConfirmOpen ? (
        <div className="identity-confirm-overlay" role="dialog" aria-modal="true" aria-labelledby="identity-confirm-title">
          <div className="identity-confirm-dialog">
            <div className="action-metadata">IDENTITY</div>
            <div className="panel-title identity-confirm-title" id="identity-confirm-title">返回身份选择</div>
            <div className="event-sub identity-confirm-copy">
              当前存档不会立刻删除；但返回后重新选择任一身份，会开始新游戏并覆盖当前进度。
            </div>
            <div className="btn-group identity-confirm-actions">
              <button className="btn" type="button" onClick={() => setIdentityConfirmOpen(false)}>取消</button>
              <button className="btn active" type="button" onClick={returnToSelector}>返回选择</button>
            </div>
          </div>
        </div>
      ) : null}

      <div id="wait-overlay" className={`wait-overlay ${wait.visible ? "active" : ""}`}>
        <div className="loading-animation">+</div>
        <div className="serif pink-text" style={{ fontSize: 30, marginBottom: 10 }}>
          {wait.title || "正在同步{assistant}..."}
        </div>
        <div className="serif wait-scene-copy">{waitAtmosphereCopy(wait)}</div>
        <div className="uppercase" style={{ letterSpacing: "0.1em", lineHeight: 1.5 }}>
          STATUS: {wait.error ? "FAILED" : "ENCRYPTING DATA"}<br />
          SYNC_RESULT: {wait.error ? "RETRY_REQUIRED" : "PENDING"}<br />
          REASON: {wait.detail || "WAITING_FOR_SUBJECT_REACTION"}
        </div>
        {wait.error ? (
          <>
            <div className="divider" />
            <div style={{ color: "#aaa", fontSize: 12, lineHeight: 1.5 }}>{wait.error}</div>
          </>
        ) : null}
        <div className="divider" />
        <div className="btn-group" style={{ marginTop: 30 }}>
          <button className="btn" type="button" onClick={() => setWait({ visible: false, title: "", detail: "" })}>关闭</button>
          <button className="btn" type="button" onClick={() => void refreshStatus(false)}>刷新</button>
          <button className="btn" type="button" aria-label="重试上次操作" disabled={!hasFailedRetry} onClick={retryLastFailedOperation}>重试</button>
        </div>
      </div>

      <footer className="footer" id="main-footer" style={{ display: !bootstrapping && screen === "game" && !monitorRoomOpen && !inventoryRoomOpen ? "grid" : "none" }}>
        <button className={`footer-item ${footerTab === "status" ? "active" : ""}`} type="button" onClick={() => { setMonitorRoomOpen(false); setInventoryRoomOpen(false); setFooterTab("status"); }}>状态</button>
        <button className={`footer-item ${footerTab === "history" ? "active" : ""}`} type="button" onClick={() => { setMonitorRoomOpen(false); setInventoryRoomOpen(false); setFooterTab("history"); setHistoryDetail(null); }}>回顾</button>
        <button className={`footer-item ${footerTab === "special" ? "active" : ""}`} type="button" onClick={() => { setMonitorRoomOpen(false); setInventoryRoomOpen(false); setFooterTab("special"); }}>特殊</button>
      </footer>

      <style>
        {`
        .captivity-game {
            --pink: #EB79B0;
            --black: #121212;
            --white: #FFFFFF;
            --gray: #2A2A2A;
            --safe-top: env(safe-area-inset-top, 0px);
            --safe-bottom: env(safe-area-inset-bottom, 0px);
            --footer-bar-height: calc(56px + var(--safe-bottom));
            --font-display: "Times New Roman", serif;
            --font-ui: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            position: fixed;
            inset: 0;
            height: 100dvh;
            z-index: 34;
            background-color: var(--black);
            color: var(--white);
            font-family: var(--font-ui);
            font-size: 13px;
            line-height: 1.2;
            overflow-y: hidden;
            overflow-x: hidden;
            overscroll-behavior-y: contain;
            letter-spacing: -0.02em;
        }
        .captivity-game * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
        }
        .captivity-game button,
        .captivity-game input,
        .captivity-game select,
        .captivity-game textarea {
            font: inherit;
        }
        .captivity-game button {
            appearance: none;
        }
        .captivity-game .pink-text { color: var(--pink); }
        .captivity-game .serif { font-family: var(--font-display); font-style: italic; letter-spacing: -0.05em; }
        .captivity-game .uppercase { text-transform: uppercase; font-size: 10px; font-weight: 700; }
        .captivity-game .divider { border-bottom: 1px solid var(--gray); margin: 10px 0; }
        .captivity-game .cross { position: absolute; pointer-events: none; }
        .captivity-game .cross::before { content: '+'; color: var(--pink); font-size: 14px; }
        .captivity-game .screen {
            position: absolute;
            inset: 0;
            display: none;
            width: 100%;
            height: 100%;
            min-height: 0;
            padding: calc(var(--safe-top) + 18px) 20px calc(var(--footer-bar-height) + 122px);
            flex-direction: column;
            overflow-y: auto;
            overflow-x: hidden;
            overscroll-behavior-y: contain;
            -webkit-overflow-scrolling: touch;
        }
        .captivity-game .screen.active { display: flex; }
        .captivity-game .bootstrap-screen {
            align-items: center;
            justify-content: center;
            text-align: center;
        }
        .captivity-game .bootstrap-title {
            font-family: "SumiChatScript", cursive;
            font-size: 46px;
            font-style: normal;
            font-weight: 400;
            line-height: 1.05;
            letter-spacing: 0;
        }
        .captivity-game .bootstrap-copy {
            margin-top: 14px;
            color: #777;
            letter-spacing: 0.08em;
        }
        .captivity-game .selector-save-warning {
            width: min(100%, 430px);
            margin: 0 auto 16px;
            padding: 10px 12px;
            border-left: 2px solid var(--pink);
            color: #bbb;
            font-size: 11px;
            line-height: 1.6;
        }
        .captivity-game .monitor-room-screen,
        .captivity-game .inventory-room-screen {
            padding-top: calc(var(--safe-top) + 58px);
            padding-bottom: calc(var(--safe-bottom) + 34px);
        }
        .captivity-game .process-review-head {
            margin-bottom: 22px;
        }
        .captivity-game .process-review-title {
            font-size: 32px;
            line-height: 0.9;
            margin-top: 8px;
        }
        .captivity-game .process-review-meta {
            border-left: 0.5px solid var(--pink);
            padding-left: 10px;
            margin-bottom: 18px;
        }
        .captivity-game .process-review-body {
            margin: 0 0 26px;
        }
        .captivity-game .ending-card {
            border-left: 0.5px solid var(--pink);
            padding: 4px 0 4px 14px;
            margin-bottom: 24px;
        }
        .captivity-game .ending-title {
            font-size: 16px;
            font-weight: 800;
            margin-bottom: 16px;
        }
        .captivity-game .ending-body {
            margin-bottom: 16px;
        }
        .captivity-game .ending-sync-state {
            color: var(--pink);
        }
        .captivity-game .history-detail-body {
            margin: 0 0 26px;
        }
        .captivity-game .history-detail-meta {
            margin-top: 12px;
        }
        .captivity-game .history-back {
            width: max-content;
            background: transparent;
            border: 0;
            color: var(--pink);
            padding: 0;
            margin: 0 0 18px;
            font-family: var(--font-ui);
            font-size: 11px;
            cursor: pointer;
        }
        .captivity-game .process-mood-title {
            margin-top: 2px;
            margin-bottom: 8px;
            font-size: 10px;
            font-weight: 700;
        }
        .captivity-game .process-mood-title .sub {
            font-size: 7px;
            margin-left: 6px;
        }
        .captivity-game .process-save-btn {
            margin-top: 20px;
            margin-bottom: 78px;
        }
        .captivity-game #selector-screen {
            justify-content: center;
            align-items: center;
            text-align: center;
            background: radial-gradient(circle at center, #222 0%, #121212 100%);
        }
        .captivity-game .selector-title {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0;
            margin-bottom: 42px;
            font-size: 48px;
            font-weight: 400;
            line-height: 0.86;
        }
        .captivity-game .selector-title span:last-child {
            color: var(--pink);
            margin-left: 34px;
        }
        .captivity-game .identity-card {
            border: 1px solid var(--pink);
            background: transparent;
            color: inherit;
            padding: 40px 20px;
            margin: 10px;
            cursor: pointer;
            width: 80%;
            transition: all 0.3s;
        }
        .captivity-game .identity-card:hover,
        .captivity-game .identity-card:active {
            background: var(--pink);
            color: var(--black);
        }
        .captivity-game .identity-card-title {
            margin-top: 8px;
            font-size: 22px;
            line-height: 1;
        }
        .captivity-game .header {
            margin-bottom: 30px;
            position: relative;
        }
        .captivity-game .day-milestone-copy {
            margin: -18px 0 24px;
            color: #8e888c;
            font-size: 11px;
            font-style: italic;
            line-height: 1.7;
        }
        .captivity-game .title-line {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 12px;
            margin-top: 10px;
        }
        .captivity-game .title-main {
            flex: 1;
            min-width: 0;
            font-size: 30px;
            line-height: 0.95;
        }
        .captivity-game .time-chip {
            flex: 0 0 auto;
            border-bottom: 1px solid rgba(235, 121, 176, 0.42);
            color: #aaa;
            font-family: var(--font-display);
            font-style: italic;
            font-size: 11px;
            line-height: 1;
            padding-bottom: 4px;
            white-space: nowrap;
        }
        .captivity-game .return-capsule {
            position: fixed;
            top: calc(var(--safe-top) + 10px);
            left: 12px;
            z-index: 520;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
            border-radius: 999px;
            border: 1px solid rgba(235, 121, 176, 0.55);
            background: rgba(30, 27, 29, 0.62);
            -webkit-backdrop-filter: blur(10px) saturate(135%);
            backdrop-filter: blur(10px) saturate(135%);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.22);
            color: var(--pink);
            cursor: pointer;
            opacity: 0.82;
        }
        .captivity-game .return-capsule svg {
            width: 14px;
            height: 14px;
        }
        .captivity-game .return-capsule:active {
            background: var(--pink);
            color: var(--black);
        }
        .captivity-game .subpage-return {
            position: fixed;
            top: calc(var(--safe-top) + 10px);
            left: 12px;
            z-index: 520;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
            border-radius: 999px;
            border: 1px solid rgba(235, 121, 176, 0.55);
            background: rgba(30, 27, 29, 0.62);
            -webkit-backdrop-filter: blur(10px) saturate(135%);
            backdrop-filter: blur(10px) saturate(135%);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.22);
            color: var(--pink);
            cursor: pointer;
            opacity: 0.82;
        }
        .captivity-game .subpage-return svg {
            width: 14px;
            height: 14px;
        }
        .captivity-game .subpage-return:active {
            background: var(--pink);
            color: var(--black);
        }
        .captivity-game .day-big {
            font-size: 80px;
            line-height: 0.8;
            font-weight: 900;
            color: var(--pink);
            opacity: 0.2;
            position: absolute;
            top: -10px;
            left: -10px;
            z-index: -1;
        }
        .captivity-game .header-meta {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            align-items: baseline;
            border-bottom: 1px solid var(--pink);
            padding-bottom: 5px;
        }
        .captivity-game .header-meta > :first-child {
            grid-column: 2;
            text-align: center;
        }
        .captivity-game .header-meta > :last-child {
            grid-column: 3;
            justify-self: end;
        }
        .captivity-game .identity-switch {
            display: inline-flex;
            align-items: baseline;
            border: 0;
            background: transparent;
            color: var(--white);
            padding: 0;
            cursor: pointer;
        }
        .captivity-game .identity-switch:active {
            color: var(--pink);
        }
        .captivity-game .identity-switch:disabled {
            cursor: default;
            opacity: 0.45;
        }
        .captivity-game .status-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 30px;
        }
        .captivity-game .status-item {
            display: flex;
            flex-direction: column;
        }
        .captivity-game .status-label {
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            margin-bottom: 4px;
        }
        .captivity-game .bar-container {
            height: 2px;
            background: var(--gray);
            width: 100%;
            position: relative;
        }
        .captivity-game .bar-fill {
            height: 100%;
            background: var(--pink);
        }
        .captivity-game .tag-cloud {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 20px;
        }
        .captivity-game .status-tag {
            border: 1px solid var(--pink);
            padding: 4px 8px;
            font-size: 11px;
            color: var(--pink);
            background: transparent;
        }
        .captivity-game .status-atmosphere-copy {
            margin: -8px 0 28px;
            color: #aaa4a8;
            font-size: 11px;
            font-style: italic;
            line-height: 1.7;
        }
        .captivity-game .panel-title {
            font-size: 16px;
            font-weight: 800;
            margin-bottom: 15px;
            display: flex;
            align-items: baseline;
        }
        .captivity-game .panel-title .sub { font-size: 8px; margin-left: 10px; color: var(--pink); }
        .captivity-game .response-mood-title {
            margin-top: 24px;
        }
        .captivity-game .action-card {
            background: #1a1a1a;
            border-left: 3px solid var(--pink);
            padding: 15px;
            margin-bottom: 20px;
        }
        .captivity-game .planner-choice-copy,
        .captivity-game .night-choice-copy,
        .captivity-game .runtime-bridge-copy {
            color: #918b8f;
            font-size: 11px;
            font-style: italic;
            line-height: 1.7;
        }
        .captivity-game .planner-choice-copy {
            margin: 11px 0 2px;
        }
        .captivity-game .night-choice-copy {
            margin: 11px 2px 18px;
        }
        .captivity-game .runtime-bridge-copy {
            margin: -7px 0 20px;
        }
        .captivity-game .history-list-item {
            display: block;
            width: 100%;
            color: var(--white);
            text-align: left;
            cursor: pointer;
        }
        .captivity-game .history-title-row {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 14px;
        }
        .captivity-game .history-title-row .panel-title {
            margin-bottom: 0;
        }
        .captivity-game .history-day-select {
            flex: 0 0 auto;
            width: 104px;
            height: 30px;
            margin: 0;
            border: 0.5px solid rgba(255, 255, 255, 0.28);
            background: #1a1a1a;
            color: var(--white);
            padding: 0 24px 0 8px;
            font-size: 10px;
        }
        .captivity-game .history-day-group {
            margin-bottom: 20px;
        }
        .captivity-game .history-day-heading {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
            border-bottom: 0.5px solid rgba(235, 121, 176, 0.5);
            color: var(--pink);
            padding-bottom: 5px;
            font-family: var(--font-display);
            font-size: 11px;
            font-style: italic;
        }
        .captivity-game .history-list-item:active {
            background: var(--gray);
        }
        .captivity-game .action-card.faded {
            opacity: 0.5;
        }
        .captivity-game .action-card.white-line {
            border-left-color: white;
        }
        .captivity-game .captivity-slot-collapsed {
            display: block;
            width: 100%;
            color: var(--white);
            text-align: left;
        }
        .captivity-game .slot-heading {
            display: block;
            width: 100%;
            margin-bottom: 5px;
            background: transparent;
            border: 0;
            color: inherit;
            text-align: left;
        }
        .captivity-game .slot-tools-toggle {
            width: 100%;
            margin-top: 12px;
            border-width: 0.5px;
            text-align: center;
        }
        .captivity-game .slot-line-input {
            min-height: 58px;
        }
        .captivity-game .action-metadata {
            font-size: 10px;
            color: #666;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        .captivity-game .intervention-title {
            margin-top: 24px;
        }
        .captivity-game .special-section-title,
        .captivity-game .monitor-section-title {
            margin-top: 22px;
            margin-bottom: 12px;
        }
        .captivity-game .section-meta {
            margin-top: 14px;
        }
        .captivity-game .special-room-entry {
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            background: #1a1a1a;
            border: 0;
            border-left: 3px solid var(--pink);
            color: var(--white);
            padding: 15px;
            margin-bottom: 22px;
            text-align: left;
            cursor: pointer;
        }
        .captivity-game .special-room-entry .panel-title {
            margin-bottom: 8px;
        }
        .captivity-game .special-room-arrow {
            flex: 0 0 auto;
            color: var(--pink);
            font-size: 28px;
            line-height: 1;
        }
        .captivity-game .special-room-entry:disabled {
            cursor: default;
            opacity: 0.45;
        }
        .captivity-game .monitor-console {
            margin-bottom: 22px;
        }
        .captivity-game .monitor-screen {
            position: relative;
            overflow: hidden;
            aspect-ratio: 4 / 3;
            min-height: 0;
            padding: 14px;
            background:
                linear-gradient(rgba(235, 121, 176, 0.06) 1px, transparent 1px),
                #0d0d0d;
            background-size: 100% 9px, auto;
            border: 0.5px solid rgba(255, 255, 255, 0.3);
            border-left: 3px solid var(--pink);
        }
        .captivity-game .monitor-screen::after {
            content: "";
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at center, transparent 0, rgba(0, 0, 0, 0.5) 74%);
            pointer-events: none;
        }
        .captivity-game .monitor-screen-top {
            position: relative;
            z-index: 1;
            display: flex;
            justify-content: space-between;
            color: var(--pink);
            font-size: 9px;
            font-weight: 800;
            letter-spacing: 0;
        }
        .captivity-game .monitor-screen-body {
            position: relative;
            z-index: 1;
            height: calc(100% - 13px);
            display: flex;
            flex-direction: column;
            justify-content: center;
            text-align: center;
        }
        .captivity-game .monitor-controls {
            grid-template-columns: repeat(3, minmax(0, 1fr));
            margin-top: 10px;
        }
        .captivity-game .monitor-record-title .panel-title {
            margin-top: 20px;
            margin-bottom: 10px;
        }
        .captivity-game .monitor-record-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 20px;
        }
        .captivity-game .monitor-record-item {
            background: #171717;
            border-left: 1px solid rgba(235, 121, 176, 0.78);
            padding: 12px;
        }
        .captivity-game .monitor-live-scene {
            max-width: 420px;
            margin: 10px auto 0;
            color: #b0a9ad;
            font-size: 10px;
            font-style: italic;
            line-height: 1.6;
        }
        .captivity-game .monitor-record-scene {
            color: #8f898d;
            font-style: italic;
            line-height: 1.7;
        }
        .captivity-game .event-main {
            font-size: 14px;
            margin-bottom: 10px;
            white-space: pre-wrap;
        }
        .captivity-game .event-sub {
            font-size: 12px;
            color: #aaa;
            line-height: 1.5;
            white-space: pre-wrap;
        }
        .captivity-game .night-condition-caption {
            margin-top: 6px;
            color: #777;
        }
        .captivity-game .process-text {
            font-family: var(--font-display);
            font-style: normal;
            letter-spacing: 0;
            font-size: 12px;
            line-height: 1.65;
            color: #ddd;
            white-space: pre-wrap;
        }
        .captivity-game .btn-group {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
            gap: 5px;
            margin-top: 15px;
        }
        .captivity-game .mood-grid,
        .captivity-game .response-grid {
            grid-template-columns: repeat(5, minmax(0, 1fr));
        }
        .captivity-game .content-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }
        .captivity-game .night-detail-grid {
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }
        .captivity-game .content-grid .btn {
            min-height: 38px;
            padding: 8px 4px;
            font-size: 10px;
            line-height: 1.25;
        }
        .captivity-game .mood-grid .btn,
        .captivity-game .response-grid .btn {
            padding: 9px 4px;
            font-size: 10px;
        }
        .captivity-game .sync-action-bar {
            position: fixed;
            left: 0;
            right: 0;
            bottom: var(--footer-bar-height);
            z-index: 610;
            margin-top: 0;
            padding: 8px 14px 10px;
            background: linear-gradient(to top, var(--black) 70%, rgba(18, 18, 18, 0));
            border-top: 0;
        }
        .captivity-game .btn {
            background: transparent;
            border: 0.5px solid rgba(255, 255, 255, 0.58);
            color: var(--white);
            padding: 10px;
            text-align: center;
            cursor: pointer;
            font-size: 11px;
            text-transform: uppercase;
        }
        .captivity-game .btn.active,
        .captivity-game .btn:active {
            background: var(--pink);
            color: var(--black);
            border-color: var(--pink);
        }
        .captivity-game .btn:disabled {
            cursor: default;
            opacity: 0.45;
        }
        .captivity-game .sync-action-bar .btn {
            border-width: 0.5px;
            border-color: rgba(255, 255, 255, 0.28);
            color: rgba(255, 255, 255, 0.9);
        }
        .captivity-game .tool-groups {
            display: grid;
            gap: 12px;
            margin-top: 15px;
        }
        .captivity-game .tool-group {
            min-width: 0;
        }
        .captivity-game .tool-category-title {
            margin-bottom: 4px;
            color: rgba(255, 255, 255, 0.62);
        }
        .captivity-game .tool-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 5px;
        }
        .captivity-game .tool-tile,
        .captivity-game .warehouse-tile {
            background: rgba(255, 255, 255, 0.02);
            border: 0.5px solid rgba(255, 255, 255, 0.26);
            color: var(--white);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }
        .captivity-game .tool-tile {
            min-width: 0;
            height: 68px;
            padding: 5px 2px 6px;
            gap: 2px;
            font-size: 9px;
            line-height: 1.1;
        }
        .captivity-game .tool-tile::after,
        .captivity-game .warehouse-tile::after {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(145deg, rgba(255, 255, 255, 0.08), transparent 48%, rgba(235, 121, 176, 0.1));
            opacity: 0.6;
            pointer-events: none;
        }
        .captivity-game .tool-tile.active,
        .captivity-game .warehouse-tile.active {
            border-color: rgba(235, 121, 176, 0.9);
            background: rgba(235, 121, 176, 0.14);
        }
        .captivity-game .tool-tile.recommended:not(.active) {
            border-color: rgba(235, 121, 176, 0.46);
        }
        .captivity-game .tool-tile:disabled,
        .captivity-game .warehouse-tile:disabled {
            cursor: default;
            opacity: 0.45;
        }
        .captivity-game .painted-icon {
            width: 36px;
            height: 36px;
            display: block;
            filter: drop-shadow(0 5px 8px rgba(0, 0, 0, 0.28));
        }
        .captivity-game .painted-icon svg {
            width: 100%;
            height: 100%;
            display: block;
        }
        .captivity-game .paint-fill {
            stroke: rgba(255, 255, 255, 0.22);
            stroke-width: 1.2;
            stroke-linejoin: round;
        }
        .captivity-game .paint-fill.rose { fill: rgba(235, 121, 176, 0.62); }
        .captivity-game .paint-fill.dark { fill: rgba(46, 39, 45, 0.88); }
        .captivity-game .paint-fill.metal { fill: rgba(207, 207, 214, 0.66); }
        .captivity-game .paint-fill.pink { fill: rgba(235, 121, 176, 0.78); }
        .captivity-game .paint-fill.light { fill: rgba(255, 233, 244, 0.72); }
        .captivity-game .paint-fill.flame { fill: rgba(255, 190, 111, 0.86); }
        .captivity-game .paint-stroke {
            fill: none;
            stroke: rgba(255, 235, 246, 0.78);
            stroke-width: 3;
            stroke-linecap: round;
            stroke-linejoin: round;
        }
        .captivity-game .paint-stroke.pink { stroke: rgba(235, 121, 176, 0.88); }
        .captivity-game .paint-stroke.dark { stroke: rgba(44, 37, 43, 0.9); }
        .captivity-game .paint-stroke.metal { stroke: rgba(212, 212, 218, 0.72); }
        .captivity-game .paint-stroke.thin { stroke-width: 2; }
        .captivity-game .paint-stroke.thick { stroke-width: 5; }
        .captivity-game .paint-light {
            fill: none;
            stroke: rgba(255, 255, 255, 0.68);
            stroke-width: 1.5;
            stroke-linecap: round;
        }
        .captivity-game .warehouse-panel {
            margin-top: 0;
        }
        .captivity-game .warehouse-title-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 12px;
        }
        .captivity-game .warehouse-module-title {
            margin: 0;
        }
        .captivity-game .warehouse-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin-top: 10px;
        }
        .captivity-game .warehouse-tile {
            min-height: 108px;
            gap: 4px;
            padding: 10px 6px;
        }
        .captivity-game .warehouse-tile .painted-icon {
            width: 44px;
            height: 44px;
        }
        .captivity-game .warehouse-name {
            position: relative;
            z-index: 1;
            font-size: 12px;
            font-weight: 800;
        }
        .captivity-game .warehouse-use {
            position: relative;
            z-index: 1;
            max-width: 100%;
            color: #aaa;
            font-size: 9px;
            line-height: 1.25;
            text-align: center;
        }
        .captivity-game .warehouse-state {
            position: relative;
            z-index: 1;
            min-width: 42px;
            padding: 2px 5px;
            border: 1px solid rgba(255, 255, 255, 0.16);
            font-size: 10px;
            color: #aaa;
            text-align: center;
        }
        .captivity-game .warehouse-tile.active .warehouse-state {
            color: var(--pink);
            border-color: rgba(235, 121, 176, 0.5);
            background: rgba(235, 121, 176, 0.08);
        }
        .captivity-game .room-inventory-tile {
            cursor: default;
        }
        .captivity-game .room-inventory-panel .monitor-record-item {
            margin-top: 10px;
        }
        .captivity-game .warehouse-tile.selected {
            border-color: rgba(235, 121, 176, 0.9);
        }
        .captivity-game .warehouse-menu {
            margin-top: 10px;
            padding: 10px;
            border-left: 2px solid var(--pink);
            background: rgba(255, 255, 255, 0.035);
        }
        .captivity-game .warehouse-menu-title {
            font-size: 12px;
            font-weight: 900;
            color: var(--white);
        }
        .captivity-game .warehouse-menu-state {
            margin-top: 3px;
            font-size: 10px;
            color: #aaa;
        }
        .captivity-game .warehouse-menu-use {
            margin-top: 4px;
            color: #aaa;
            font-size: 10px;
        }
        .captivity-game .warehouse-secret-label {
            margin-top: 10px;
            color: #ccc;
            font-size: 10px;
            line-height: 1.5;
        }
        .captivity-game .warehouse-actions {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 6px;
            margin-top: 10px;
        }
        .captivity-game .warehouse-actions .btn {
            padding: 10px 8px;
            border-width: 0.5px;
        }
        .captivity-game .warehouse-voice-input {
            min-height: 84px;
            margin-top: 10px;
            font-size: 12px;
        }
        .captivity-game .warehouse-voice-current {
            margin-top: 10px;
            padding: 10px 12px;
            border-left: 2px solid var(--pink);
            color: var(--white);
            font-size: 12px;
            line-height: 1.7;
            white-space: pre-wrap;
        }
        .captivity-game .scene-transition-overlay {
            position: fixed;
            inset: 0;
            z-index: 950;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            padding: 28px;
            border: 0;
            background: rgba(8, 8, 8, 0.9);
            color: var(--white);
            cursor: pointer;
            overflow: hidden;
            text-align: center;
            animation: captivitySceneVeil var(--scene-duration, 3400ms) linear both;
        }
        .captivity-game .scene-transition-overlay.night {
            background: rgba(2, 2, 3, 0.96);
        }
        .captivity-game .scene-transition-overlay.special {
            background: rgba(12, 5, 8, 0.96);
        }
        .captivity-game .scene-transition-scan {
            position: absolute;
            left: 15%;
            top: 12%;
            width: 70%;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(235, 121, 176, 0.62), transparent);
            box-shadow: 0 0 14px rgba(235, 121, 176, 0.28);
            animation: captivitySceneScan 1.65s cubic-bezier(0.22, 1, 0.36, 1) both;
            will-change: transform, opacity;
        }
        .captivity-game .scene-transition-content {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: min(100%, 560px);
        }
        .captivity-game .scene-transition-kicker {
            color: var(--pink);
            font-size: 9px;
            letter-spacing: 0;
            animation: captivitySceneKicker 0.52s cubic-bezier(0.22, 1, 0.36, 1) both;
        }
        .captivity-game .scene-transition-title {
            margin-top: 12px;
            font-size: 24px;
            font-style: italic;
            line-height: 1.1;
        }
        .captivity-game .scene-transition-body {
            max-width: 460px;
            margin-top: 16px;
            color: #cfcacf;
            font-size: 12px;
            line-height: 1.9;
            opacity: 0;
            transform: translate3d(0, 7px, 0);
            will-change: transform, opacity;
            animation: captivitySceneBody 0.72s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }
        .captivity-game .scene-transition-char {
            display: inline-block;
            opacity: 0;
            transform: translate3d(0, 6px, 0) scale(0.985);
            backface-visibility: hidden;
            will-change: transform, opacity;
            animation: captivitySceneCharacter 0.72s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }
        .captivity-game .scene-transition-char.space {
            width: 0.32em;
        }
        @keyframes captivitySceneVeil {
            0% { opacity: 0; }
            9%, 90% { opacity: 1; }
            100% { opacity: 0; }
        }
        @keyframes captivitySceneScan {
            0% { opacity: 0; transform: translate3d(0, -18vh, 0); }
            18% { opacity: 0.72; }
            72% { opacity: 0.32; }
            100% { opacity: 0; transform: translate3d(0, 76vh, 0); }
        }
        @keyframes captivitySceneKicker {
            from { opacity: 0; transform: translate3d(0, 5px, 0); }
            to { opacity: 1; transform: translate3d(0, 0, 0); }
        }
        @keyframes captivitySceneBody {
            from { opacity: 0; transform: translate3d(0, 7px, 0); }
            to { opacity: 1; transform: translate3d(0, 0, 0); }
        }
        @keyframes captivitySceneCharacter {
            from { opacity: 0; transform: translate3d(0, 6px, 0) scale(0.985); }
            to { opacity: 1; transform: translate3d(0, 0, 0) scale(1); }
        }
        .captivity-game .bell-voice-overlay {
            position: fixed;
            inset: 0;
            z-index: 930;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            background: rgba(0, 0, 0, 0.82);
            backdrop-filter: blur(8px);
        }
        .captivity-game .bell-voice-dialog {
            width: min(100%, 420px);
            padding: 24px 22px 20px;
            border: 0.5px solid rgba(255, 255, 255, 0.32);
            border-left: 3px solid var(--pink);
            background: #151515;
        }
        .captivity-game .item-reveal-dialog {
            animation: captivityItemRevealIn 0.34s ease both;
        }
        .captivity-game .item-reveal-motif {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            height: 32px;
            margin: 14px 0 2px;
            color: var(--pink);
        }
        .captivity-game .item-reveal-motif span {
            display: block;
            width: 3px;
            height: 8px;
            background: currentColor;
        }
        .captivity-game .item-reveal-book .item-reveal-motif,
        .captivity-game .item-reveal-notebook .item-reveal-motif {
            perspective: 120px;
        }
        .captivity-game .item-reveal-book .item-reveal-motif span,
        .captivity-game .item-reveal-notebook .item-reveal-motif span {
            width: 22px;
            height: 26px;
            border: 1px solid rgba(235, 121, 176, 0.72);
            background: transparent;
        }
        .captivity-game .item-reveal-book .item-reveal-motif span:nth-child(n+3),
        .captivity-game .item-reveal-notebook .item-reveal-motif span:nth-child(n+3) {
            display: none;
        }
        .captivity-game .item-reveal-book .item-reveal-motif span:nth-child(2) {
            transform-origin: left center;
            animation: captivityPageTurn 0.8s ease both;
        }
        .captivity-game .item-reveal-notebook .item-reveal-motif span:nth-child(2) {
            width: 14px;
            height: 1px;
            border: 0;
            background: var(--pink);
            animation: captivityLineWrite 0.72s ease both;
        }
        .captivity-game .item-reveal-switch .item-reveal-motif,
        .captivity-game .item-reveal-tablet .item-reveal-motif {
            width: 82px;
            margin-left: auto;
            margin-right: auto;
            border: 1px solid rgba(235, 121, 176, 0.72);
            animation: captivityScreenWake 0.7s ease both;
        }
        .captivity-game .item-reveal-switch .item-reveal-motif {
            width: 108px;
        }
        .captivity-game .item-reveal-switch .item-reveal-motif::after {
            content: "GAME START";
            color: var(--pink);
            font-size: 8px;
            font-weight: 700;
            letter-spacing: 0;
            opacity: 0;
            animation: captivityGameStart 0.46s 0.38s ease forwards;
        }
        .captivity-game .item-reveal-switch .item-reveal-motif span,
        .captivity-game .item-reveal-tablet .item-reveal-motif span {
            display: none;
        }
        .captivity-game .item-reveal-music_player .item-reveal-motif span,
        .captivity-game .item-reveal-call_bell .item-reveal-motif span {
            animation: captivityWave 0.72s ease-in-out infinite alternate;
        }
        .captivity-game .item-reveal-music_player .item-reveal-motif span:nth-child(2),
        .captivity-game .item-reveal-call_bell .item-reveal-motif span:nth-child(2) { animation-delay: 0.1s; }
        .captivity-game .item-reveal-music_player .item-reveal-motif span:nth-child(3),
        .captivity-game .item-reveal-call_bell .item-reveal-motif span:nth-child(3) { animation-delay: 0.2s; }
        .captivity-game .item-reveal-music_player .item-reveal-motif span:nth-child(4),
        .captivity-game .item-reveal-call_bell .item-reveal-motif span:nth-child(4) { animation-delay: 0.3s; }
        .captivity-game .item-reveal-night_light .item-reveal-motif {
            width: 30px;
            margin-left: auto;
            margin-right: auto;
            border: 1px solid var(--pink);
            background: rgba(235, 121, 176, 0.28);
            box-shadow: 0 0 18px rgba(235, 121, 176, 0.45);
            animation: captivityLightWake 0.9s ease-in-out infinite alternate;
        }
        .captivity-game .item-reveal-night_light .item-reveal-motif span,
        .captivity-game .item-reveal-pillow .item-reveal-motif span { display: none; }
        .captivity-game .item-reveal-pillow .item-reveal-motif {
            width: 58px;
            margin-left: auto;
            margin-right: auto;
            border-bottom: 1px dashed var(--pink);
            animation: captivityStitch 0.75s steps(6, end) both;
        }
        @keyframes captivityItemRevealIn {
            from { opacity: 0; transform: translateY(7px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes captivityPageTurn {
            from { transform: rotateY(0deg); }
            to { transform: rotateY(-58deg); }
        }
        @keyframes captivityLineWrite {
            from { transform: scaleX(0); }
            to { transform: scaleX(1); }
        }
        @keyframes captivityScreenWake {
            0% { opacity: 0.2; box-shadow: none; }
            45% { opacity: 1; box-shadow: 0 0 20px rgba(235, 121, 176, 0.34); }
            100% { opacity: 0.82; box-shadow: 0 0 8px rgba(235, 121, 176, 0.18); }
        }
        @keyframes captivityGameStart {
            from { opacity: 0; transform: scale(0.9); filter: blur(2px); }
            to { opacity: 1; transform: scale(1); filter: blur(0); }
        }
        @keyframes captivityWave {
            from { height: 5px; opacity: 0.45; }
            to { height: 24px; opacity: 1; }
        }
        @keyframes captivityLightWake {
            from { opacity: 0.46; box-shadow: 0 0 4px rgba(235, 121, 176, 0.16); }
            to { opacity: 1; box-shadow: 0 0 24px rgba(235, 121, 176, 0.58); }
        }
        @keyframes captivityStitch {
            from { clip-path: inset(0 100% 0 0); }
            to { clip-path: inset(0 0 0 0); }
        }
        @media (prefers-reduced-motion: reduce) {
            .captivity-game .scene-transition-overlay,
            .captivity-game .scene-transition-scan,
            .captivity-game .scene-transition-content,
            .captivity-game .scene-transition-kicker,
            .captivity-game .scene-transition-body,
            .captivity-game .scene-transition-char,
            .captivity-game .item-reveal-dialog,
            .captivity-game .item-reveal-motif,
            .captivity-game .item-reveal-motif::after,
            .captivity-game .item-reveal-motif span,
            .captivity-game .escape-recapture-question,
            .captivity-game .escape-recapture-type,
            .captivity-game .escape-recapture-answer {
                animation: none !important;
            }
            .captivity-game .escape-recapture-type {
                opacity: var(--type-opacity, 1);
                filter: blur(var(--type-blur, 0px));
                transform: none;
            }
            .captivity-game .escape-recapture-answer {
                opacity: 1;
            }
            .captivity-game .scene-transition-body {
                opacity: 1;
                transform: none;
            }
            .captivity-game .item-reveal-switch .item-reveal-motif::after {
                opacity: 1;
            }
        }
        .captivity-game .bell-voice-kicker {
            margin-bottom: 8px;
            color: #777;
            font-size: 10px;
        }
        .captivity-game .bell-voice-line {
            margin: 24px 0 8px;
            color: var(--white);
            font-size: 13px;
            font-style: italic;
            line-height: 1.9;
            white-space: pre-wrap;
        }
        .captivity-game .bell-voice-continue {
            display: block;
            width: auto;
            min-width: 108px;
            margin: 14px auto 0;
            padding: 9px 24px;
            border: 0.5px solid rgba(255, 255, 255, 0.72);
            background: transparent;
            color: var(--white);
            font-size: 11px;
        }
        .captivity-game .btn-large {
            width: 100%;
            padding: 15px;
            margin-top: 20px;
            background: var(--white);
            color: var(--black);
            font-weight: 900;
        }
        .captivity-game textarea,
        .captivity-game input,
        .captivity-game select {
            width: 100%;
            background: var(--gray);
            border: none;
            color: var(--white);
            padding: 10px;
            font-family: var(--font-ui);
            margin-top: 10px;
            resize: none;
        }
        .captivity-game select,
        .captivity-game input.compact {
            background: transparent;
            border: 1px solid #333;
            padding: 5px;
        }
        .captivity-game option {
            color: var(--black);
        }
        .captivity-game .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .captivity-game .escape-room-row {
            grid-template-columns: repeat(2, minmax(0, 1fr));
            align-items: start;
            gap: 10px;
        }
        .captivity-game .compact-field {
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        .captivity-game .compact-field > span {
            color: #aaa;
            font-size: 9px;
            font-weight: 800;
            line-height: 1;
        }
        .captivity-game .compact-field input.compact,
        .captivity-game .compact-field select.compact {
            height: 34px;
            margin-top: 0;
        }
        .captivity-game .escape-room-select {
            width: 100%;
        }
        .captivity-game .form-grid select {
            margin-top: 0;
        }
        .captivity-game .wait-overlay {
            position: fixed;
            inset: 0;
            background: var(--black);
            z-index: 1000;
            display: none;
            padding: calc(var(--safe-top) + 40px) 40px calc(var(--safe-bottom) + 40px);
            flex-direction: column;
            justify-content: center;
        }
        .captivity-game .wait-overlay.active { display: flex; }
        .captivity-game .identity-confirm-overlay {
            position: fixed;
            inset: 0;
            z-index: 970;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: calc(var(--safe-top) + 22px) 22px calc(var(--safe-bottom) + 22px);
            background: rgba(0, 0, 0, 0.76);
            -webkit-backdrop-filter: blur(8px);
            backdrop-filter: blur(8px);
        }
        .captivity-game .identity-confirm-dialog {
            width: min(100%, 390px);
            padding: 22px 20px 20px;
            border: 0.5px solid #555;
            border-left: 3px solid var(--pink);
            background: #151515;
        }
        .captivity-game .identity-confirm-title { margin: 8px 0 14px; }
        .captivity-game .identity-confirm-copy { white-space: normal; line-height: 1.7; }
        .captivity-game .identity-confirm-actions {
            grid-template-columns: repeat(2, minmax(0, 1fr));
            margin-top: 20px;
        }
        .captivity-game .wait-scene-copy {
            max-width: 460px;
            margin-bottom: 18px;
            color: #aaa4a8;
            font-size: 12px;
            font-style: italic;
            line-height: 1.7;
        }
        .captivity-game .escape-choice-overlay {
            position: fixed;
            inset: 0;
            z-index: 900;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: calc(var(--safe-top) + 22px) 22px calc(var(--safe-bottom) + 22px);
            background: rgba(0, 0, 0, 0.76);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
        }
        .captivity-game .escape-choice-dialog {
            width: min(100%, 430px);
            max-height: calc(100dvh - 44px);
            overflow-y: auto;
            padding: 24px 20px 20px;
            background: #151515;
            border: 0.5px solid #555;
            border-left: 3px solid var(--pink);
        }
        .captivity-game .escape-choice-title {
            margin-bottom: 18px;
        }
        .captivity-game .escape-warning {
            margin-top: 12px;
            color: var(--pink);
            font-size: 10px;
        }
        .captivity-game .escape-choice-actions {
            margin-top: 18px;
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .captivity-game .escape-confirm-prompt {
            margin-top: 12px;
            color: #e0525c;
            font-size: 11px;
            font-weight: 700;
        }
        .captivity-game .escape-sting-dialog {
            min-height: 132px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .captivity-game .escape-sting-text {
            color: #e0525c;
            font-family: var(--font-display);
            font-size: 20px;
            font-style: italic;
            font-weight: 800;
        }
        .captivity-game .escape-recapture-question-overlay {
            background: #000;
            backdrop-filter: none;
            -webkit-backdrop-filter: none;
            overflow: hidden;
        }
        .captivity-game .escape-recapture-chains {
            position: absolute;
            inset: 0;
            z-index: 0;
            overflow: hidden;
            pointer-events: none;
        }
        .captivity-game .escape-recapture-background {
            display: block;
            width: 100%;
            height: 112%;
            object-fit: cover;
            object-position: center;
            opacity: 0.78;
            filter: brightness(0.72) saturate(0.82) contrast(1.04);
            transform: translateY(-9%);
            user-select: none;
        }
        .captivity-game .escape-recapture-chains::after {
            content: "";
            position: absolute;
            inset: 0;
            background: radial-gradient(ellipse at 50% 48%, rgba(0, 0, 0, 0.08) 0%, rgba(0, 0, 0, 0.28) 58%, rgba(0, 0, 0, 0.58) 100%);
        }
        .captivity-game .escape-recapture-dialog {
            position: relative;
            z-index: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            width: min(100%, 360px);
            gap: 28px;
        }
        .captivity-game .escape-recapture-question {
            position: relative;
            width: min(94vw, 360px);
            height: 150px;
            color: var(--pink);
            font-family: var(--font-display);
            font-weight: 600;
            line-height: 1;
        }
        .captivity-game .escape-recapture-type-line {
            position: absolute;
            left: 50%;
            display: flex;
            align-items: baseline;
            white-space: nowrap;
            transform: translateX(-50%);
        }
        .captivity-game .escape-recapture-type-line-top {
            top: 4px;
        }
        .captivity-game .escape-recapture-type-line-bottom {
            top: 78px;
        }
        .captivity-game .escape-recapture-type {
            position: relative;
            display: inline-block;
            line-height: 0.92;
            opacity: 0;
            filter: blur(3px);
            transform: translateY(7px);
            text-shadow: 0 0 16px rgba(235, 121, 176, 0.12);
            animation: captivityRecaptureTypeIn 0.62s var(--recapture-delay, 0ms) cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }
        .captivity-game .escape-recapture-type::after {
            content: attr(data-ghost);
            position: absolute;
            inset: 0 auto auto 0;
            opacity: 0;
            pointer-events: none;
        }
        .captivity-game .escape-recapture-type-ghost::after {
            opacity: 0.22;
            filter: blur(2.2px);
            transform: translate(7px, 2px) scaleX(1.08);
        }
        .captivity-game .type-why-1 { --type-opacity: 0.58; font-size: clamp(32px, 10vw, 42px); }
        .captivity-game .type-why-2 { --type-opacity: 0.42; --type-blur: 0.45px; margin-left: -5px; font-size: clamp(22px, 7vw, 29px); }
        .captivity-game .type-why-3 { --type-opacity: 0.7; margin-left: -5px; font-size: clamp(29px, 9vw, 38px); }
        .captivity-game .type-link { --type-opacity: 0.36; --type-blur: 0.5px; margin-left: -4px; font-size: clamp(20px, 6vw, 25px); }
        .captivity-game .type-run {
            --type-opacity: 1;
            margin-left: -4px;
            font-size: clamp(36px, 11.5vw, 46px);
            text-shadow: 0 0 22px rgba(235, 121, 176, 0.2);
        }
        .captivity-game .type-stay-1 { --type-opacity: 0.55; font-size: clamp(34px, 10vw, 42px); }
        .captivity-game .type-stay-2 { --type-opacity: 0.38; --type-blur: 0.55px; margin-left: -7px; font-size: clamp(23px, 7vw, 29px); }
        .captivity-game .type-me { --type-opacity: 0.76; margin-left: -5px; font-size: clamp(30px, 9vw, 38px); }
        .captivity-game .type-side-1 { --type-opacity: 0.96; margin-left: -5px; font-size: clamp(39px, 12vw, 49px); }
        .captivity-game .type-side-2 { --type-opacity: 0.68; margin-left: -7px; font-size: clamp(29px, 9vw, 37px); }
        .captivity-game .type-tail-1 { --type-opacity: 0.42; --type-blur: 0.35px; margin-left: -6px; font-size: clamp(23px, 7vw, 29px); }
        .captivity-game .type-tail-2 { --type-opacity: 0.56; margin-left: -5px; font-size: clamp(30px, 9vw, 38px); }
        .captivity-game .type-question-mark {
            --type-opacity: 0.56;
            --type-blur: 0px;
            position: absolute;
            left: 100%;
            bottom: 0;
            margin-left: 8px;
            font-family: "Songti SC", STSong, SimSun, serif;
            font-size: clamp(30px, 9vw, 38px);
            font-weight: 600;
            text-shadow: none;
        }
        .captivity-game .escape-recapture-answer {
            min-height: 30px;
            padding: 5px 2px 4px;
            border: 0;
            background: transparent;
            color: var(--white);
            font-family: var(--font-display);
            font-size: 12px;
            font-weight: 400;
            letter-spacing: 0.055em;
            line-height: 1.4;
            opacity: 0;
            animation: captivityRecaptureAnswer 0.5s ease-out forwards;
        }
        .captivity-game .escape-recapture-answer::before {
            content: "◇";
            margin-right: 0.75em;
            color: rgba(255, 255, 255, 0.48);
            font-size: 0.72em;
        }
        .captivity-game .escape-recapture-answer::after {
            content: "◇";
            margin-left: 0.75em;
            color: rgba(255, 255, 255, 0.48);
            font-size: 0.72em;
        }
        .captivity-game .escape-recapture-bridge {
            position: fixed;
            inset: 0;
            z-index: 940;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: calc(var(--safe-top) + 40px) 40px calc(var(--safe-bottom) + 40px);
            background: #000;
        }
        @keyframes captivityRecaptureTypeIn {
            from { opacity: 0; filter: blur(3px); transform: translateY(7px); }
            to { opacity: var(--type-opacity, 1); filter: blur(var(--type-blur, 0px)); transform: translateY(0); }
        }
        @keyframes captivityRecaptureAnswer {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .captivity-game .recapture-rules-review-overlay {
            position: fixed;
            inset: 0;
            z-index: 920;
            overflow-y: auto;
            padding: calc(var(--safe-top) + 72px) 22px calc(var(--safe-bottom) + 40px);
            background: var(--black);
        }
        .captivity-game .recapture-rules-review {
            width: min(100%, 430px);
            margin: 0 auto;
        }
        .captivity-game .recapture-rules-review-list {
            display: grid;
            gap: 8px;
            margin: 22px 0;
        }
        .captivity-game .recapture-rules-review-item {
            padding: 13px 14px;
            border-left: 2px solid var(--pink);
            background: #191919;
            color: #eee;
            font-size: 13px;
            line-height: 1.45;
        }
        .captivity-game .recapture-rules-review .btn {
            width: 100%;
        }
        .captivity-game .loading-animation {
            width: 40px;
            height: 40px;
            border: 1px solid var(--pink);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
            animation: captivityRotate 2s infinite linear;
        }
        @keyframes captivityRotate { 100% { transform: rotate(90deg); } }
        .captivity-game .footer {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            background: var(--black);
            border-top: 1px solid var(--gray);
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            min-height: var(--footer-bar-height);
            padding: 6px 0 calc(6px + var(--safe-bottom));
            z-index: 620;
        }
        .captivity-game .footer-item {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 44px;
            padding: 0 8px 5px;
            text-align: center;
            font-size: 11px;
            text-transform: uppercase;
            opacity: 0.6;
            background: transparent;
            border: 0;
            color: var(--white);
            outline: none;
            box-shadow: none;
            -webkit-tap-highlight-color: transparent;
        }
        .captivity-game .footer-item:focus,
        .captivity-game .footer-item:focus-visible { outline: none; box-shadow: none; }
        .captivity-game .footer-item.active { opacity: 1; color: var(--pink); }
        .captivity-game .footer-item.active::after {
            content: "♥";
            position: absolute;
            bottom: 3px;
            left: 50%;
            transform: translateX(-50%);
            color: var(--pink);
            font-size: 6px;
            line-height: 1;
        }
        .captivity-game .coord { font-size: 9px; color: #444; position: fixed; }
        .captivity-game .vertical-text {
            writing-mode: vertical-rl;
            position: fixed;
            right: 5px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 9px;
            color: #444;
            letter-spacing: 0.2em;
        }
        `}
      </style>
    </div>
  );
}

function StatusGrid({ stats, mood, flags = [], role }: { stats: CaptivityStats; mood?: string; flags?: StatusFlag[]; role: UserRole }) {
  return (
    <>
      <div className="status-grid">
        {STAT_LABELS.map((item) => {
          const value = clampPercent(stats[item.key]);
          return (
            <div className="status-item" key={item.key}>
              <div className="status-label"><span>{item.label}</span><span>{value}%</span></div>
              <div className="bar-container"><div className="bar-fill" style={{ width: `${value}%` }} /></div>
            </div>
          );
        })}
        <div className="status-item">
          <div className="status-label"><span>心情</span><span>{mood || "未选"}</span></div>
          <div className="bar-container"><div className="bar-fill" style={{ width: mood ? "66%" : "0%" }} /></div>
        </div>
      </div>
      {flags.length ? (
        <div className="tag-cloud status-flags">
          {flags.map((flag) => <span className="status-tag" title={flag.prompt} key={flag.id || flag.label}>{flag.label}</span>)}
        </div>
      ) : null}
      <div className="serif status-atmosphere-copy">{statusAtmosphereCopy(stats, mood, role, flags)}</div>
    </>
  );
}

function TargetStatusPanel({ view }: { view: CaptivityView }) {
  return (
    <>
      <div className="panel-title">对方状态 <span className="sub">{view.captive_name || displayActor(view.captive)}</span></div>
      <StatusGrid stats={view.stats || {}} mood={view.mood} flags={view.status_flags} role="captor" />
    </>
  );
}

function PlannerPanel({
  slots,
  singleAction = false,
  intensityCap,
  disabled,
  onSlotChange,
  onToggle,
  onSubmit,
}: {
  slots: PlanSlot[];
  singleAction?: boolean;
  intensityCap?: string;
  disabled?: boolean;
  onSlotChange: (index: number, patch: Partial<PlanSlot>) => void;
  onToggle: (index: number, key: "modifiers" | "tools" | "contents" | "trainingContents", value: string) => void;
  onSubmit: () => void;
}) {
  const [expandedSlots, setExpandedSlots] = useState<Set<number>>(() => new Set([0]));
  const [advancedSlots, setAdvancedSlots] = useState<Set<number>>(() => new Set());

  function toggleSlot(index: number) {
    setExpandedSlots((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      if (!next.size) next.add(index);
      return next;
    });
  }

  function toggleAdvanced(index: number) {
    setAdvancedSlots((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  const selectedActions = new Set(slots.map((slot) => slot.action));

  return (
    <>
      <div className="panel-title">{singleAction ? "回来之后" : "今日安排"} <span className="sub">{singleAction ? "RETURN" : "SCHEDULE"}</span></div>
      {slots.map((slot, index) => {
        const expanded = expandedSlots.has(index);
        const slotLabel = singleAction ? "回来后" : index === 0 ? "早间" : index === 1 ? "午后" : "傍晚";
        const advanced = advancedSlots.has(index);
        const contentOptions = ACTION_CONTENT_OPTIONS[slot.action] || [];
        const hasTraining = slot.action === "training" || slot.modifiers.includes("training");
        if (!expanded) {
          return (
            <div
              className="action-card faded captivity-slot-collapsed"
              role="button"
              tabIndex={disabled ? -1 : 0}
              aria-disabled={disabled}
              onClick={() => {
                if (!disabled) toggleSlot(index);
              }}
              onKeyDown={(event) => {
                if (!disabled && (event.key === "Enter" || event.key === " ")) toggleSlot(index);
              }}
              key={index}
            >
              <div className="uppercase pink-text" style={{ marginBottom: 5 }}>SLOT {String(index + 1).padStart(2, "0")} - {slotLabel}</div>
              <div className="uppercase">点击配置...</div>
            </div>
          );
        }
        return (
          <div className={`action-card ${index === 0 ? "white-line" : ""}`} key={index}>
            <button className="slot-heading" type="button" disabled={disabled} onClick={() => toggleSlot(index)}>
              <span className="uppercase pink-text">SLOT {String(index + 1).padStart(2, "0")} - {slotLabel}</span>
            </button>
            <div className="form-grid">
              <select value={slot.action} disabled={disabled} onChange={(event) => onSlotChange(index, { action: event.target.value })}>
                {ACTION_OPTIONS.map((item) => (
                  <option value={item.id} disabled={item.id !== slot.action && selectedActions.has(item.id)} key={item.id}>
                    行动类型: {item.label}
                  </option>
                ))}
              </select>
              <select value={slot.intensity} disabled={disabled} onChange={(event) => onSlotChange(index, { intensity: event.target.value })}>
                {INTENSITY_OPTIONS.map((item) => <option value={item.id} disabled={item.id === "heavy" && intensityCap === "medium"} key={item.id}>力度: {item.label}</option>)}
              </select>
            </div>
            <div className="serif planner-choice-copy">{DAY_ACTION_SELECTION_COPY[slot.action] || "这一段会按当前选择写进今日安排。"}</div>
            <button
              className={`btn slot-tools-toggle ${advanced ? "active" : ""}`}
              type="button"
              disabled={disabled}
              onClick={() => toggleAdvanced(index)}
            >
              {advanced ? "收起详细设置" : "选择具体内容/道具"}
            </button>
            {advanced ? (
              <>
                <textarea
                  className="slot-line-input"
                  value={slot.line}
                  disabled={disabled}
                  placeholder="可选：要说的话..."
                  onChange={(event) => onSlotChange(index, { line: event.target.value })}
                />
                {slot.action === "feeding" ? (
                  <div className="form-grid">
                    <select value={slot.feedingSource} disabled={disabled} onChange={(event) => onSlotChange(index, { feedingSource: event.target.value })}>
                      {FEEDING_SOURCE_OPTIONS.map((item) => <option value={item.id} key={item.id}>食物: {item.label}</option>)}
                    </select>
                    <select value={slot.feedingAdditive} disabled={disabled} onChange={(event) => onSlotChange(index, { feedingAdditive: event.target.value })}>
                      {FEEDING_ADDITIVE_OPTIONS.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}
                    </select>
                  </div>
                ) : null}
                {contentOptions.length ? (
                  <>
                    <div className="action-metadata section-meta">具体内容</div>
                    <div className="btn-group content-grid">
                      {contentOptions.map((item) => (
                        <ToggleButton
                          active={slot.contents.includes(item.id)}
                          disabled={disabled || (!slot.contents.includes(item.id) && slot.contents.length >= 3)}
                          key={item.id}
                          onClick={() => onToggle(index, "contents", item.id)}
                        >
                          {item.label}
                        </ToggleButton>
                      ))}
                    </div>
                  </>
                ) : null}
                <div className="action-metadata section-meta">附加项</div>
                <div className="btn-group">
                  {MODIFIER_OPTIONS.filter((item) => item.id !== "training" || slot.action !== "training").map((item) => (
                    <ToggleButton
                      active={slot.modifiers.includes(item.id)}
                      disabled={disabled}
                      key={item.id}
                      onClick={() => onToggle(index, "modifiers", item.id)}
                    >
                      {item.label}
                    </ToggleButton>
                  ))}
                </div>
                {hasTraining ? (
                  <>
                    <div className="action-metadata section-meta">调教内容</div>
                    <div className="btn-group content-grid">
                      {TRAINING_CONTENT_OPTIONS.filter((item) => !CAPTIVE_ROUTE_ONLY_TRAINING_IDS.has(item.id)).map((item) => (
                        <ToggleButton
                          active={slot.trainingContents.includes(item.id)}
                          disabled={disabled || (!slot.trainingContents.includes(item.id) && slot.trainingContents.length >= 3)}
                          key={item.id}
                          onClick={() => onToggle(index, "trainingContents", item.id)}
                        >
                          {item.label}
                        </ToggleButton>
                      ))}
                    </div>
                  </>
                ) : null}
                <div className="action-metadata section-meta">道具</div>
                <ToolSelectGrid
                  selected={slot.tools}
                  disabled={disabled}
                  context={{ action: slot.action, modifiers: slot.modifiers, contents: slot.contents, trainingContents: slot.trainingContents }}
                  onToggle={(value) => onToggle(index, "tools", value)}
                />
              </>
            ) : null}
          </div>
        );
      })}
      <button className="btn btn-large" type="button" disabled={disabled} onClick={onSubmit}>{singleAction ? "确定这个行为" : "下发所有指令"}</button>
    </>
  );
}

function RuntimePanel({
  role,
  view,
  pending,
  currentEvent,
  waitingForAssistant,
  userIsPendingActor,
  canChooseNight,
  availableNightActions,
  nightCondition,
  response,
  responseMood,
  responseLine,
  reactionMood,
  reactionLine,
  nightAction,
  nightDetail,
  nightDetailOptions,
  nightNote,
  nightLine,
  monitorNote,
  interventionIntent,
  interventionModifiers,
  interventionTrainingContents,
  interventionTools,
  interventionLine,
  recaptureRules,
  recaptureFollowup,
  recaptureIntensity,
  recaptureModifiers,
  recaptureTrainingContents,
  recaptureTools,
  recaptureLine,
  lastText,
  disabled,
  onResponseChange,
  onResponseMoodChange,
  onResponseLineChange,
  onReactionMoodChange,
  onReactionLineChange,
  onNightActionChange,
  onNightDetailChange,
  onNightNoteChange,
  onNightLineChange,
  onMonitorNoteChange,
  onInterventionIntentChange,
  onInterventionModifierToggle,
  onInterventionTrainingContentToggle,
  onInterventionToolToggle,
  onInterventionLineChange,
  onRecaptureRuleToggle,
  onRecaptureFollowupChange,
  onRecaptureIntensityChange,
  onRecaptureModifierToggle,
  onRecaptureTrainingContentToggle,
  onRecaptureToolToggle,
  onRecaptureLineChange,
  onSubmitResponse,
  onSubmitMood,
  onSubmitNightAction,
  onAckBellVoice,
  onAckItemSecret,
  onAdvance,
  onChooseEscape,
  onConfirmRecaptureRules,
  onSubmitRecaptureRules,
  onSubmitRecaptureFollowup,
  onOpenMonitor,
  onHandleMonitor,
  onRefresh,
}: {
  role: UserRole;
  view: CaptivityView;
  pending: CaptivityPending | null;
  currentEvent?: CaptivityEvent;
  waitingForAssistant: boolean;
  userIsPendingActor: boolean;
  canChooseNight: boolean;
  availableNightActions: string[];
  nightCondition: NightCondition | null;
  response: string;
  responseMood: string;
  responseLine: string;
  reactionMood: string;
  reactionLine: string;
  nightAction: string;
  nightDetail: string;
  nightDetailOptions: Array<{ id: string; label: string }>;
  nightNote: string;
  nightLine: string;
  monitorNote: string;
  interventionIntent: string;
  interventionModifiers: string[];
  interventionTrainingContents: string[];
  interventionTools: string[];
  interventionLine: string;
  recaptureRules: string[];
  recaptureFollowup: string;
  recaptureIntensity: string;
  recaptureModifiers: string[];
  recaptureTrainingContents: string[];
  recaptureTools: string[];
  recaptureLine: string;
  lastText: string;
  disabled?: boolean;
  onResponseChange: (value: string) => void;
  onResponseMoodChange: (value: string) => void;
  onResponseLineChange: (value: string) => void;
  onReactionMoodChange: (value: string) => void;
  onReactionLineChange: (value: string) => void;
  onNightActionChange: (value: string) => void;
  onNightDetailChange: (value: string) => void;
  onNightNoteChange: (value: string) => void;
  onNightLineChange: (value: string) => void;
  onMonitorNoteChange: (value: string) => void;
  onInterventionIntentChange: (value: string) => void;
  onInterventionModifierToggle: (value: string) => void;
  onInterventionTrainingContentToggle: (value: string) => void;
  onInterventionToolToggle: (value: string) => void;
  onInterventionLineChange: (value: string) => void;
  onRecaptureRuleToggle: (value: string) => void;
  onRecaptureFollowupChange: (value: string) => void;
  onRecaptureIntensityChange: (value: string) => void;
  onRecaptureModifierToggle: (value: string) => void;
  onRecaptureTrainingContentToggle: (value: string) => void;
  onRecaptureToolToggle: (value: string) => void;
  onRecaptureLineChange: (value: string) => void;
  onSubmitResponse: () => void;
  onSubmitMood: () => void;
  onSubmitNightAction: () => void;
  onAckBellVoice: () => void;
  onAckItemSecret: () => void;
  onAdvance: () => void;
  onChooseEscape: (choice: string) => void;
  onConfirmRecaptureRules: () => void;
  onSubmitRecaptureRules: () => void;
  onSubmitRecaptureFollowup: () => void;
  onOpenMonitor: (style: "occasional" | "full") => void;
  onHandleMonitor: (strategy: string) => void;
  onRefresh: () => void;
}) {
  const pendingType = String(pending?.type || "");
  const isRulesReview = pendingType === "recapture_rules_review" && userIsPendingActor;
  const isRecaptureDecision = pendingType === "recapture_rules_choice" || pendingType === "recapture_followup_choice";
  const hideRecaptureDecision = isRecaptureDecision && waitingForAssistant && role === "captive";
  const event = isRecaptureDecision ? {} : currentEvent || {};
  const isEnding = String(view.phase || "") === "ending" || Boolean(view.ending_state);
  const isNightSelfChoice = pendingType === "night_action_choice" && userIsPendingActor;
  const petRulePrompt = view.status_flags?.find((item) => item.id === "pet_identity_active")?.prompt || "";
  const activeTitle = isNightSelfChoice
    ? "你的安排"
    : pendingType === "recapture_rules_choice"
      ? "重新立规矩"
    : pendingType === "recapture_followup_choice"
      ? "后续处理"
    : pendingType === "escape_choice" && waitingForAssistant
      ? "等待{assistant}回应"
    : waitingForAssistant
      ? (role === "captor" ? "当前指令" : "{assistant}的安排")
      : "当前事件";
  const hasEventDetail = Boolean(
    event.action_label
    || event.action
    || event.line
    || event.intensity
    || event.modifiers?.length
    || event.contents?.length
    || event.training_contents?.length
    || event.tools?.length
    || (event.feeding && Object.keys(event.feeding).length),
  );
  const staleDayEventAtNight = String(view.phase || "") === "night" && String(event.phase || "") === "day";
  const showActiveCard = Boolean(pending || hasEventDetail || isEnding)
    && !isNightSelfChoice
    && !staleDayEventAtNight
    && !(pendingType === "escape_choice" && userIsPendingActor)
    && !(pendingType === "bell_voice_reveal" && userIsPendingActor)
    && !(pendingType === "item_secret_reveal" && userIsPendingActor)
    && !(isRecaptureDecision && userIsPendingActor)
    && !isRulesReview
    && !hideRecaptureDecision;
  const bridgeCopy = runtimeBridgeCopy(view, pending, role);

  if (isEnding) {
    const endingTitle = String(view.ending_title || "已收录结局").trim();
    const endingText = String(view.ending_text || "").trim();
    const endingNotified = Boolean(String(view.ending_notified_at || "").trim());
    return (
      <>
        <div className="panel-title">结局 <span className="sub">ENDING</span></div>
        <div className="ending-card">
          <div className="event-main ending-title">{endingTitle}</div>
          <div className="process-text ending-body">{endingText || "结局正文正在准备。"}</div>
          <div className="event-sub ending-sync-state">{endingNotified ? "已同步给{assistant}" : "等待同步给{assistant}"}</div>
        </div>
      </>
    );
  }

  return (
    <>
      {isRulesReview ? (
        <RecaptureRulesReviewPanel
          rules={pending?.rule_labels || []}
          disabled={disabled}
          onConfirm={onConfirmRecaptureRules}
        />
      ) : null}
      {showActiveCard ? (
        <>
          <div className="panel-title">
            {activeTitle} <span className="sub">EVENT</span>
          </div>
          <div className="action-card">
            <div className="action-metadata">
              {activeTaskMeta(event, pending, view, role)}
            </div>
            <div className="event-main">
              {pendingType === "escape_choice" && waitingForAssistant
                ? "逃跑诱导已经送达{assistant}。"
                : isRecaptureDecision
                  ? pendingLabel(pending, role)
                : event.line || event.action_label || publicDirectiveText(pending?.required_directive, pending, role) || (isEnding ? "30 天闭环已完成，等待结局。" : "等待下一段事件。")}
            </div>
            <div className="divider" />
            <div className="event-sub">
              {renderEventSummary(event, pending, view, role)}
            </div>
          </div>
        </>
      ) : null}

      {bridgeCopy ? <div className="serif runtime-bridge-copy">{bridgeCopy}</div> : null}

      {pendingType === "action_response" && userIsPendingActor ? (
        <ActionResponsePanel
          response={response}
          mood={responseMood}
          line={responseLine}
          disabled={disabled}
          onResponseChange={onResponseChange}
          onMoodChange={onResponseMoodChange}
          onLineChange={onResponseLineChange}
          onSubmit={onSubmitResponse}
        />
      ) : null}

      {pendingType === "reaction_choice" && userIsPendingActor ? (
        <MoodPanel
          title="此刻心情"
          mood={reactionMood}
          line={reactionLine}
          disabled={disabled}
          onMoodChange={onReactionMoodChange}
          onLineChange={onReactionLineChange}
          onSubmit={onSubmitMood}
        />
      ) : null}

      {canChooseNight ? (
        <NightActionPanel
          actions={availableNightActions}
          condition={nightCondition}
          petRulePrompt={petRulePrompt}
          value={nightAction}
          detail={nightDetail}
          detailOptions={nightDetailOptions}
          note={nightNote}
          line={nightLine}
          disabled={disabled}
          onChange={onNightActionChange}
          onDetailChange={onNightDetailChange}
          onNoteChange={onNightNoteChange}
          onLineChange={onNightLineChange}
          onSubmit={onSubmitNightAction}
        />
      ) : null}

      {pendingType === "bell_voice_reveal" && userIsPendingActor ? (
        <BellVoiceRevealPanel
          line={pending?.event?.bell_voice?.line || ""}
          disabled={disabled}
          onConfirm={onAckBellVoice}
        />
      ) : null}

      {pendingType === "item_secret_reveal" && userIsPendingActor ? (
        <ItemSecretRevealPanel
          itemId={pending?.item_secret?.item_id || "item"}
          itemLabel={pending?.item_secret?.item_label || "物品"}
          text={pending?.item_secret?.text || "你发现了预先藏在物品里的内容。"}
          sequence={pending?.item_secret?.sequence}
          total={pending?.item_secret?.total}
          disabled={disabled}
          onConfirm={onAckItemSecret}
        />
      ) : null}

      {pendingType === "escape_choice" && userIsPendingActor ? (
        <EscapeChoicePanel pending={pending} disabled={disabled} onChoose={onChooseEscape} />
      ) : null}

      {pendingType === "recapture_rules_choice" && userIsPendingActor ? (
        <RecaptureRulesPanel
          value={recaptureRules}
          disabled={disabled}
          onToggle={onRecaptureRuleToggle}
          onSubmit={onSubmitRecaptureRules}
        />
      ) : null}

      {pendingType === "recapture_followup_choice" && userIsPendingActor ? (
        <RecaptureFollowupPanel
          action={recaptureFollowup}
          intensity={recaptureIntensity}
          modifiers={recaptureModifiers}
          trainingContents={recaptureTrainingContents}
          tools={recaptureTools}
          line={recaptureLine}
          disabled={disabled}
          onActionChange={onRecaptureFollowupChange}
          onIntensityChange={onRecaptureIntensityChange}
          onModifierToggle={onRecaptureModifierToggle}
          onTrainingContentToggle={onRecaptureTrainingContentToggle}
          onToolToggle={onRecaptureToolToggle}
          onLineChange={onRecaptureLineChange}
          onSubmit={onSubmitRecaptureFollowup}
        />
      ) : null}

      {pendingType === "advance_action" && userIsPendingActor ? (
        <>
          <div className="panel-title">推进 <span className="sub">NEXT_SLOT</span></div>
          <button className="btn btn-large" type="button" disabled={disabled} onClick={onAdvance}>推进下一段行动</button>
        </>
      ) : null}

      {pendingType === "monitor_gate" && userIsPendingActor ? (
        <MonitorGatePanel pending={pending} disabled={disabled} onOpenMonitor={onOpenMonitor} onHandleNone={() => onHandleMonitor("none")} />
      ) : null}

      {pendingType === "monitor_handle" && userIsPendingActor ? (
        <MonitorHandlePanel
          note={monitorNote}
          interventionIntent={interventionIntent}
          interventionModifiers={interventionModifiers}
          interventionTrainingContents={interventionTrainingContents}
          interventionTools={interventionTools}
          interventionLine={interventionLine}
          disabled={disabled}
          onNoteChange={onMonitorNoteChange}
          onInterventionIntentChange={onInterventionIntentChange}
          onInterventionModifierToggle={onInterventionModifierToggle}
          onInterventionTrainingContentToggle={onInterventionTrainingContentToggle}
          onInterventionToolToggle={onInterventionToolToggle}
          onInterventionLineChange={onInterventionLineChange}
          onHandle={onHandleMonitor}
        />
      ) : null}

      {!pending && !canChooseNight && !isEnding ? (
        <div className="action-card faded">
          <div className="uppercase pink-text" style={{ marginBottom: 5 }}>SYSTEM_IDLE</div>
          <div className="event-sub">{lastText || "当前没有待处理事件。"}</div>
          <button className="btn btn-large" type="button" disabled={disabled} onClick={onRefresh}>刷新状态</button>
        </div>
      ) : null}
    </>
  );
}

function renderEventSummary(event: CaptivityEvent, pending: CaptivityPending | null, view: CaptivityView, role: UserRole): string {
  if (pending?.sealed) {
    return "夜间行动已经封存。囚禁方尚未打开监控前，不显示具体内容。";
  }
  const intervention = event.intervention || {};
  const modifiers = visibleModifierLabels(event.modifiers);
  const feeding = event.feeding || {};
  const visibleFeeding = role === "captor"
    ? feeding
    : Object.fromEntries(
      Object.entries(feeding).filter(([key, value]) => {
        if (key === "source" || key === "water") return String(value || "") !== "none";
        return key === "additive" && !["", "none"].includes(String(value || ""));
      }),
    );
  const feedingRows = Object.entries(visibleFeeding)
    .map(([key, value]) => feedingValueLabel(key, value))
    .filter(Boolean);
  const recaptureContext = event.recapture_context || {};
  const rows = [
    event.action_label || event.action ? `行动：${event.action_label || actionLabel(event.action)}` : "",
    event.contents?.length ? `具体内容：${event.contents.map(actionContentLabel).join(" / ")}` : "",
    event.training_contents?.length ? `调教内容：${event.training_contents.map(trainingContentLabel).join(" / ")}` : "",
    modifiers.length ? `修饰：${modifiers.join(" / ")}` : "",
    event.tools?.length ? `道具：${event.tools.map(toolLabel).join(" / ")}` : "",
    event.night_detail?.label ? `具体动向：${event.night_detail.label}` : "",
    event.night_discovery ? `发现：${event.night_discovery}` : "",
    event.private_note ? `私密日记：${event.private_note}` : "",
    feedingRows.length ? `喂食：${feedingRows.join(" / ")}` : "",
    event.action_response?.response_label ? `回应：${event.action_response.response_label} / 心情：${event.action_response.mood || "未选"}` : "",
    event.post_reaction?.mood ? `此刻心情：${event.post_reaction.mood}` : "",
    event.monitor?.viewed ? `监控：${event.monitor.style || "view"} / ${event.monitor.handle || "未处理"}` : "",
    intervention.intent ? `当场介入：${intervention.intent_label || interventionIntentLabel(intervention.intent)}` : "",
    intervention.modifiers?.length ? `介入附加：${intervention.modifiers.map(interventionModifierLabel).join(" / ")}` : "",
    intervention.training_contents?.length ? `介入调教：${intervention.training_contents.map(trainingContentLabel).join(" / ")}` : "",
    intervention.tools?.length ? `介入道具：${intervention.tools.map(toolLabel).join(" / ")}` : "",
    intervention.line ? `介入台词：${intervention.line}` : "",
    recaptureContext.rule_labels?.length ? `新规矩：${recaptureContext.rule_labels.join(" / ")}` : "",
    recaptureContext.followup_label ? `后续处理：${recaptureContext.followup_label}` : "",
    pending?.type === "escape_choice" && pending.actor === "assistant"
      ? "等待：{assistant}选择尝试逃跑或老实待着"
      : pending?.required_directive ? `等待：${publicDirectiveText(pending.required_directive, pending, role)}` : "",
    pending?.type === "return_action_choice" || event.tags?.includes("special_day")
      ? `进度：第 ${view.current_day || 1} / ${view.total_days || 30} 天，特殊事件`
      : `进度：第 ${view.current_day || 1} / ${view.total_days || 30} 天，白天行动 ${view.day_action_count || 0} / ${view.day_action_limit || 3}`,
  ].filter(Boolean);
  return rows.join("\n");
}

function processReviewMeta(event: CaptivityEvent): string {
  const intervention = event.intervention || {};
  const modifiers = visibleModifierLabels(event.modifiers);
  const rows = [
    `第 ${event.day || 1} 天`,
    event.phase === "night" ? "夜间" : event.slot ? `第 ${event.slot} 段` : "",
    event.action_label || event.action ? `行动：${event.action_label || actionLabel(event.action)}` : "",
    event.contents?.length ? `内容：${event.contents.map(actionContentLabel).join(" / ")}` : "",
    event.training_contents?.length ? `调教：${event.training_contents.map(trainingContentLabel).join(" / ")}` : "",
    modifiers.length ? `修饰：${modifiers.join(" / ")}` : "",
    event.tools?.length ? `道具：${event.tools.map(toolLabel).join(" / ")}` : "",
    event.night_detail?.label ? `动向：${event.night_detail.label}` : "",
    intervention.intent ? `介入：${intervention.intent_label || interventionIntentLabel(intervention.intent)}` : "",
    intervention.modifiers?.length ? `附加：${intervention.modifiers.map(interventionModifierLabel).join(" / ")}` : "",
    intervention.training_contents?.length ? `介入调教：${intervention.training_contents.map(trainingContentLabel).join(" / ")}` : "",
    intervention.tools?.length ? `介入道具：${intervention.tools.map(toolLabel).join(" / ")}` : "",
  ].filter(Boolean);
  return rows.join(" / ");
}

function historyEventText(event: CaptivityEvent): string {
  return [
    event.process_text,
    event.private_note,
    event.line,
  ].filter(Boolean).join("\n\n");
}

function ProcessReviewPanel({
  review,
  mood,
  line,
  disabled,
  onMoodChange,
  onLineChange,
  onSave,
}: {
  review: ProcessReview;
  mood: string;
  line: string;
  disabled?: boolean;
  onMoodChange: (value: string) => void;
  onLineChange: (value: string) => void;
  onSave: () => void;
}) {
  return (
    <>
      <div className="process-review-head">
        <h2 className="serif process-review-title">
          经过 / <span className="pink-text">Process</span>
        </h2>
      </div>
      <div className="process-review-meta">
        <div className="event-main">{review.event.action_label || actionLabel(review.event.action) || "事件"}</div>
        <div className="event-sub">{processReviewMeta(review.event)}</div>
      </div>
      <div className="process-text process-review-body">{review.text}</div>
      {review.moodRequired ? (
        <>
          <div className="panel-title process-mood-title">此刻心情 <span className="sub">MOOD</span></div>
          <div className="btn-group mood-grid">
            {MOOD_OPTIONS.map((item) => (
              <ToggleButton active={mood === item} disabled={disabled} key={item} onClick={() => onMoodChange(item)}>
                {item}
              </ToggleButton>
            ))}
          </div>
          <textarea placeholder="可选：你想补的一句话..." value={line} disabled={disabled} onChange={(event) => onLineChange(event.target.value)} />
        </>
      ) : null}
      <button className="btn btn-large process-save-btn" type="button" disabled={disabled} onClick={onSave}>保存到回顾</button>
    </>
  );
}

function ActionResponsePanel({
  response,
  mood,
  line,
  disabled,
  onResponseChange,
  onMoodChange,
  onLineChange,
  onSubmit,
}: {
  response: string;
  mood: string;
  line: string;
  disabled?: boolean;
  onResponseChange: (value: string) => void;
  onMoodChange: (value: string) => void;
  onLineChange: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <>
      <div className="panel-title">你的回应 <span className="sub">RESPONSE</span></div>
      <div className="btn-group response-grid">
        {RESPONSE_OPTIONS.map((item) => (
          <ToggleButton active={response === item.id} disabled={disabled} key={item.id} onClick={() => onResponseChange(item.id)}>
            {item.label}
          </ToggleButton>
        ))}
      </div>
      <div className="panel-title response-mood-title">此刻心情 <span className="sub">MOOD</span></div>
      <div className="btn-group mood-grid">
        {MOOD_OPTIONS.map((item) => (
          <ToggleButton active={mood === item} disabled={disabled} key={item} onClick={() => onMoodChange(item)}>
            {item}
          </ToggleButton>
        ))}
      </div>
      <textarea placeholder="你想说的一句话..." value={line} disabled={disabled} onChange={(event) => onLineChange(event.target.value)} />
      <button className="btn btn-large" type="button" disabled={disabled} onClick={onSubmit}>提交并同步</button>
    </>
  );
}

function MoodPanel({
  title,
  mood,
  line,
  disabled,
  onMoodChange,
  onLineChange,
  onSubmit,
}: {
  title: string;
  mood: string;
  line: string;
  disabled?: boolean;
  onMoodChange: (value: string) => void;
  onLineChange: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <>
      <div className="panel-title">{title} <span className="sub">MOOD</span></div>
      <div className="btn-group mood-grid">
        {MOOD_OPTIONS.map((item) => (
          <ToggleButton active={mood === item} disabled={disabled} key={item} onClick={() => onMoodChange(item)}>
            {item}
          </ToggleButton>
        ))}
      </div>
      <textarea placeholder="你想补的一句话..." value={line} disabled={disabled} onChange={(event) => onLineChange(event.target.value)} />
      <button className="btn btn-large" type="button" disabled={disabled} onClick={onSubmit}>记录心情</button>
    </>
  );
}

function NightActionPanel({
  actions,
  condition,
  petRulePrompt,
  value,
  detail,
  detailOptions,
  note,
  line,
  disabled,
  onChange,
  onDetailChange,
  onNoteChange,
  onLineChange,
  onSubmit,
}: {
  actions: string[];
  condition: NightCondition | null;
  petRulePrompt: string;
  value: string;
  detail: string;
  detailOptions: Array<{ id: string; label: string }>;
  note: string;
  line: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  onDetailChange: (value: string) => void;
  onNoteChange: (value: string) => void;
  onLineChange: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <>
      <div className="panel-title">你的安排 <span className="sub">NIGHT</span></div>
      <div className="action-card">
        {condition?.label ? <div className="action-metadata">{condition.label}</div> : null}
        <div className="event-sub">
          {condition?.prompt || "{assistant}可能在看监控关注你的动向。你准备晚上做什么？"}
        </div>
        {petRulePrompt ? <div className="event-sub night-condition-caption">{petRulePrompt}</div> : null}
        {condition?.caption ? <div className="event-sub night-condition-caption">{condition.caption}</div> : null}
      </div>
      <div className="btn-group">
        {actions.map((item) => (
          <ToggleButton active={value === item} disabled={disabled} key={item} onClick={() => onChange(item)}>
            {nightActionLabel(item)}
          </ToggleButton>
        ))}
      </div>
      <div className="serif night-choice-copy">{NIGHT_ACTION_SELECTION_COPY[value] || "今晚的选择会被监控记录下来。"}</div>
      {detailOptions.length ? (
        <>
          <div className="action-metadata section-meta">具体动向</div>
          <div className="btn-group content-grid night-detail-grid">
            {detailOptions.map((item) => (
              <ToggleButton active={detail === item.id} disabled={disabled} key={item.id} onClick={() => onDetailChange(item.id)}>
                {item.label}
              </ToggleButton>
            ))}
          </div>
        </>
      ) : null}
      {value === "diary" ? (
        <textarea placeholder="写下这一页的私密日记正文..." value={note} disabled={disabled} onChange={(event) => onNoteChange(event.target.value)} />
      ) : null}
      {value !== "ring_bell" ? (
        <textarea placeholder="可选：你想说的一句话..." value={line} disabled={disabled} onChange={(event) => onLineChange(event.target.value)} />
      ) : null}
      <button className="btn btn-large" type="button" disabled={disabled || (detailOptions.length > 0 && !detail) || (value === "diary" && !note.trim())} onClick={onSubmit}>确认夜间行动</button>
    </>
  );
}

function BellVoiceRevealPanel({
  line,
  disabled,
  onConfirm,
}: {
  line: string;
  disabled?: boolean;
  onConfirm: () => void;
}) {
  return (
    <div className="bell-voice-overlay item-reveal-call_bell" role="dialog" aria-modal="true" aria-label="语音铃播放">
      <div className="bell-voice-dialog item-reveal-dialog">
        <div className="bell-voice-kicker">SYSTEM / VOICE PLAYBACK</div>
        <div className="item-reveal-motif" aria-hidden="true"><span /><span /><span /><span /></div>
        <div className="serif bell-voice-line">
          铃响了，你听见「{line || "预录的声音"}」在静谧的房间里响起
        </div>
        <button className="btn bell-voice-continue" type="button" disabled={disabled} onClick={onConfirm}>继续</button>
      </div>
    </div>
  );
}

function SceneTransitionOverlay({
  scene,
  onDismiss,
}: {
  scene: SceneCopy;
  onDismiss: () => void;
}) {
  const tone = String(scene.tone || "day");
  const title = scene.title || "新的一段";
  const body = scene.body || "房间里的时间继续向前。";
  const titleStart = 320;
  const titleStep = 120;
  const bodyStart = titleStart + Math.max(0, Array.from(title).length - 1) * titleStep + 720 + 180;
  const duration = sceneTransitionDuration(scene);
  return (
    <button
      className={`scene-transition-overlay ${tone === "night" ? "night" : tone === "special" ? "special" : "day"}`}
      type="button"
      aria-label="跳过过场"
      onClick={onDismiss}
      style={{ "--scene-duration": `${duration}ms` } as React.CSSProperties}
    >
      <span className="scene-transition-scan" />
      <span className="scene-transition-content">
        <span className="scene-transition-kicker">{scene.kicker || "CAPTIVITY LOG"}</span>
        <StaggeredSceneText className="serif scene-transition-title" text={title} start={titleStart} step={titleStep} />
        <span className="scene-transition-body" style={{ animationDelay: `${bodyStart}ms` }}>{body}</span>
      </span>
    </button>
  );
}

function StaggeredSceneText({
  className,
  text,
  start,
  step,
}: {
  className: string;
  text: string;
  start: number;
  step: number;
}) {
  return (
    <span className={className} aria-label={text}>
      {Array.from(text).map((character, index) => (
        <span
          className={`scene-transition-char${character === " " ? " space" : ""}`}
          style={{ animationDelay: `${start + index * step}ms` }}
          aria-hidden="true"
          key={`${character}-${index}`}
        >
          {character === " " ? "\u00a0" : character}
        </span>
      ))}
    </span>
  );
}

function sceneTransitionDuration(scene: SceneCopy | null | undefined): number {
  const titleLength = Array.from(scene?.title || "新的一段").length;
  const bodyLength = Array.from(scene?.body || "房间里的时间继续向前。").length;
  const bodyStart = 320 + Math.max(0, titleLength - 1) * 120 + 720 + 180;
  return Math.min(6800, Math.max(3200, bodyStart + bodyLength * 55 + 1000));
}

function ItemSecretRevealPanel({
  itemId,
  itemLabel,
  text,
  sequence,
  total,
  disabled,
  onConfirm,
}: {
  itemId: string;
  itemLabel: string;
  text: string;
  sequence?: number;
  total?: number;
  disabled?: boolean;
  onConfirm: () => void;
}) {
  const progressive = Number(total || 0) > 1;
  return (
    <div className={`bell-voice-overlay item-reveal-${itemId}`} role="dialog" aria-modal="true" aria-label={`${itemLabel}${progressive ? "使用痕迹" : "第一次使用彩蛋"}`}>
      <div className="bell-voice-dialog item-reveal-dialog">
        <div className="bell-voice-kicker">
          {itemLabel} / {progressive ? `DISCOVERY ${sequence || 1} OF ${total}` : "FIRST DISCOVERY"}
        </div>
        <div className="item-reveal-motif" aria-hidden="true"><span /><span /><span /><span /></div>
        <div className="serif bell-voice-line">{text}</div>
        <button className="btn bell-voice-continue" type="button" disabled={disabled} onClick={onConfirm}>继续</button>
      </div>
    </div>
  );
}

function EscapeChoicePanel({
  pending,
  disabled,
  onChoose,
}: {
  pending: CaptivityPending | null;
  disabled?: boolean;
  onChoose: (choice: string) => void;
}) {
  const [confirmStep, setConfirmStep] = useState(-1);
  const [answerVisible, setAnswerVisible] = useState(false);
  const confirmation = confirmStep >= 0 ? ESCAPE_CONFIRM_STEPS[confirmStep] : null;
  const showSting = confirmStep === ESCAPE_CONFIRM_STEPS.length;
  const showRecaptureQuestion = confirmStep === ESCAPE_CONFIRM_STEPS.length + 1;

  useEffect(() => {
    if (!showSting) return;
    const timer = window.setTimeout(() => setConfirmStep(ESCAPE_CONFIRM_STEPS.length + 1), 1000);
    return () => window.clearTimeout(timer);
  }, [showSting]);

  useEffect(() => {
    if (!showRecaptureQuestion) {
      setAnswerVisible(false);
      return;
    }
    const timer = window.setTimeout(() => setAnswerVisible(true), 2600);
    return () => window.clearTimeout(timer);
  }, [showRecaptureQuestion]);

  function chooseEscape() {
    if (confirmStep < ESCAPE_CONFIRM_STEPS.length - 1) {
      setConfirmStep(confirmStep + 1);
      return;
    }
    setConfirmStep(ESCAPE_CONFIRM_STEPS.length);
  }

  if (showSting) {
    return (
      <div className="escape-choice-overlay" role="dialog" aria-modal="true" aria-label="坏孩子">
        <div className="escape-choice-dialog escape-sting-dialog">
          <div className="escape-sting-text">坏孩子</div>
        </div>
      </div>
    );
  }

  if (showRecaptureQuestion) {
    return (
      <div className="escape-choice-overlay escape-recapture-question-overlay" role="dialog" aria-modal="true" aria-label="为什么要跑">
        <div className="escape-recapture-chains" aria-hidden="true">
          <img className="escape-recapture-background" src={recaptureBackgroundUrl} alt="" draggable={false} />
        </div>
        <div className="escape-recapture-dialog">
          <div className="escape-recapture-question" aria-label="为什么要跑，待在我身边不好吗？">
            <div className="escape-recapture-type-line escape-recapture-type-line-top" aria-hidden="true">
              <span className="escape-recapture-type escape-recapture-type-ghost type-why-1" data-ghost="为" style={{ "--recapture-delay": "80ms" } as React.CSSProperties}>为</span>
              <span className="escape-recapture-type type-why-2" style={{ "--recapture-delay": "200ms" } as React.CSSProperties}>什</span>
              <span className="escape-recapture-type escape-recapture-type-ghost type-why-3" data-ghost="么" style={{ "--recapture-delay": "320ms" } as React.CSSProperties}>么</span>
              <span className="escape-recapture-type type-link" style={{ "--recapture-delay": "440ms" } as React.CSSProperties}>要</span>
              <span className="escape-recapture-type type-run" style={{ "--recapture-delay": "560ms" } as React.CSSProperties}>跑</span>
            </div>
            <div className="escape-recapture-type-line escape-recapture-type-line-bottom" aria-hidden="true">
              <span className="escape-recapture-type type-stay-1" style={{ "--recapture-delay": "900ms" } as React.CSSProperties}>待</span>
              <span className="escape-recapture-type escape-recapture-type-ghost type-stay-2" data-ghost="在" style={{ "--recapture-delay": "1020ms" } as React.CSSProperties}>在</span>
              <span className="escape-recapture-type type-me" style={{ "--recapture-delay": "1140ms" } as React.CSSProperties}>我</span>
              <span className="escape-recapture-type type-side-1" style={{ "--recapture-delay": "1260ms" } as React.CSSProperties}>身</span>
              <span className="escape-recapture-type escape-recapture-type-ghost type-side-2" data-ghost="边" style={{ "--recapture-delay": "1380ms" } as React.CSSProperties}>边</span>
              <span className="escape-recapture-type type-tail-1" style={{ "--recapture-delay": "1500ms" } as React.CSSProperties}>不</span>
              <span className="escape-recapture-type type-tail-1" style={{ "--recapture-delay": "1620ms" } as React.CSSProperties}>好</span>
              <span className="escape-recapture-type escape-recapture-type-ghost type-tail-2" data-ghost="吗" style={{ "--recapture-delay": "1740ms" } as React.CSSProperties}>吗</span>
              <span className="escape-recapture-type type-question-mark" style={{ "--recapture-delay": "1860ms" } as React.CSSProperties}>？</span>
            </div>
          </div>
          {answerVisible ? (
            <button className="escape-recapture-answer" type="button" disabled={disabled} onClick={() => onChoose("escape")}>
              对不起我再也不跑了
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="escape-choice-overlay" role="dialog" aria-modal="true" aria-label="逃跑机会">
      <div className="escape-choice-dialog">
        <div className="action-metadata">ESCAPE WINDOW</div>
        <div className="panel-title escape-choice-title">{confirmation?.title || "逃跑机会"}</div>
        <div className="event-main">{confirmation?.text || pending?.hint || "{assistant}今天有事出去了。"}</div>
        <div className="divider" />
        {!confirmation ? (
          <div className="event-sub">{pending?.bait || `${escapeRoomBait("entry")}。`} 你要怎么做？</div>
        ) : null}
        {confirmation ? <div className="escape-confirm-prompt">{confirmation.prompt}</div> : null}
        <div className="btn-group escape-choice-actions">
          {confirmation ? (
            <>
              <button className="btn" type="button" disabled={disabled} onClick={chooseEscape}>
                {confirmation.continueLabel}
              </button>
              <button className="btn" type="button" disabled={disabled} onClick={() => onChoose(confirmation.abortChoice)}>
                {confirmation.stayLabel}
              </button>
            </>
          ) : ESCAPE_OPTIONS.map((item) => (
            <button
              className="btn"
              type="button"
              disabled={disabled}
              key={item.id}
              onClick={() => item.id === "escape" ? setConfirmStep(0) : onChoose(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function RecaptureRulesReviewPanel({
  rules,
  disabled,
  onConfirm,
}: {
  rules: string[];
  disabled?: boolean;
  onConfirm: () => void;
}) {
  return (
    <div className="recapture-rules-review-overlay" role="dialog" aria-modal="true" aria-label="新规矩">
      <div className="recapture-rules-review">
        <div className="action-metadata">NEW RULES</div>
        <div className="panel-title">新规矩 <span className="sub">RULES</span></div>
        <div className="recapture-rules-review-list">
          {rules.map((rule) => (
            <div className="recapture-rules-review-item" key={rule}>{rule}</div>
          ))}
        </div>
        <button className="btn" type="button" disabled={disabled || !rules.length} onClick={onConfirm}>记住了</button>
      </div>
    </div>
  );
}

function RecaptureRulesPanel({
  value,
  disabled,
  onToggle,
  onSubmit,
}: {
  value: string[];
  disabled?: boolean;
  onToggle: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <>
      <div className="panel-title">重新立规矩 <span className="sub">NEW_RULES</span></div>
      <div className="action-card">
        <div className="event-sub">选择 1–3 条。保存后会持续影响之后的行动和具体经过。</div>
      </div>
      <div className="btn-group content-grid">
        {RECAPTURE_RULE_OPTIONS.map((item) => (
          <ToggleButton active={value.includes(item.id)} disabled={disabled} key={item.id} onClick={() => onToggle(item.id)}>
            {item.label}
          </ToggleButton>
        ))}
      </div>
      <button className="btn btn-large" type="button" disabled={disabled || value.length < 1 || value.length > 3} onClick={onSubmit}>保存新规矩</button>
    </>
  );
}

function RecaptureFollowupPanel({
  action,
  intensity,
  modifiers,
  trainingContents,
  tools,
  line,
  disabled,
  onActionChange,
  onIntensityChange,
  onModifierToggle,
  onTrainingContentToggle,
  onToolToggle,
  onLineChange,
  onSubmit,
}: {
  action: string;
  intensity: string;
  modifiers: string[];
  trainingContents: string[];
  tools: string[];
  line: string;
  disabled?: boolean;
  onActionChange: (value: string) => void;
  onIntensityChange: (value: string) => void;
  onModifierToggle: (value: string) => void;
  onTrainingContentToggle: (value: string) => void;
  onToolToggle: (value: string) => void;
  onLineChange: (value: string) => void;
  onSubmit: () => void;
}) {
  const needsTraining = action === "training" || modifiers.includes("training");
  return (
    <>
      <div className="panel-title">后续处理 <span className="sub">FOLLOW_UP</span></div>
      <div className="btn-group content-grid">
        {RECAPTURE_FOLLOWUP_OPTIONS.map((item) => (
          <ToggleButton active={action === item.id} disabled={disabled} key={item.id} onClick={() => onActionChange(item.id)}>
            {item.label}
          </ToggleButton>
        ))}
      </div>
      <div className="action-metadata section-meta">强度</div>
      <div className="btn-group intensity-grid">
        {INTENSITY_OPTIONS.map((item) => (
          <ToggleButton active={intensity === item.id} disabled={disabled} key={item.id} onClick={() => onIntensityChange(item.id)}>
            {item.label}
          </ToggleButton>
        ))}
      </div>
      <div className="action-metadata section-meta">可选附加</div>
      <div className="btn-group">
        {INTERVENTION_MODIFIER_OPTIONS.map((item) => (
          <ToggleButton active={modifiers.includes(item.id)} disabled={disabled} key={item.id} onClick={() => onModifierToggle(item.id)}>
            {item.label}
          </ToggleButton>
        ))}
      </div>
      {needsTraining ? (
        <>
          <div className="action-metadata section-meta">调教内容</div>
          <div className="btn-group content-grid">
            {TRAINING_CONTENT_OPTIONS.map((item) => (
              <ToggleButton active={trainingContents.includes(item.id)} disabled={disabled} key={item.id} onClick={() => onTrainingContentToggle(item.id)}>
                {item.label}
              </ToggleButton>
            ))}
          </div>
        </>
      ) : null}
      <div className="action-metadata section-meta">道具</div>
      <ToolSelectGrid
        selected={tools}
        disabled={disabled}
        context={{ action, modifiers, contents: [], trainingContents }}
        onToggle={onToolToggle}
      />
      <textarea placeholder="可选：你要说的话..." value={line} disabled={disabled} onChange={(event) => onLineChange(event.target.value)} />
      <button className="btn btn-large" type="button" disabled={disabled || (needsTraining && !trainingContents.length)} onClick={onSubmit}>确定后续处理</button>
    </>
  );
}

function MonitorGatePanel({
  pending,
  disabled,
  onOpenMonitor,
  onHandleNone,
}: {
  pending: CaptivityPending | null;
  disabled?: boolean;
  onOpenMonitor: (style: "occasional" | "full") => void;
  onHandleNone: () => void;
}) {
  return (
    <>
      <div className="panel-title">夜间监控 <span className="sub">MONITOR</span></div>
      <div className="action-card">
        <div className="action-metadata">{pending?.alert_label || "夜间行动已封存"}</div>
        <div className="event-sub">
          {pending?.alert_label
            ? "被囚禁方按响了呼叫铃。你可以打开监控查看，也可以选择不看。"
            : "被囚禁方的夜间行动已封存。你可以打开监控，也可以选择不看。"}
        </div>
      </div>
      <div className="btn-group">
        <button className="btn" type="button" disabled={disabled} onClick={() => onOpenMonitor("occasional")}>偶尔看</button>
        <button className="btn" type="button" disabled={disabled} onClick={() => onOpenMonitor("full")}>全程看</button>
        <button className="btn" type="button" disabled={disabled} onClick={onHandleNone}>不看</button>
      </div>
    </>
  );
}

function MonitorHandlePanel({
  note,
  interventionIntent,
  interventionModifiers,
  interventionTrainingContents,
  interventionTools,
  interventionLine,
  disabled,
  showTitle = true,
  onNoteChange,
  onInterventionIntentChange,
  onInterventionModifierToggle,
  onInterventionTrainingContentToggle,
  onInterventionToolToggle,
  onInterventionLineChange,
  onHandle,
}: {
  note: string;
  interventionIntent: string;
  interventionModifiers: string[];
  interventionTrainingContents: string[];
  interventionTools: string[];
  interventionLine: string;
  disabled?: boolean;
  showTitle?: boolean;
  onNoteChange: (value: string) => void;
  onInterventionIntentChange: (value: string) => void;
  onInterventionModifierToggle: (value: string) => void;
  onInterventionTrainingContentToggle: (value: string) => void;
  onInterventionToolToggle: (value: string) => void;
  onInterventionLineChange: (value: string) => void;
  onHandle: (strategy: string) => void;
}) {
  const passiveOptions = MONITOR_HANDLE_OPTIONS.filter((item) => item.id !== "intervene");
  return (
    <>
      {showTitle ? <div className="panel-title">监控处理 <span className="sub">HANDLE</span></div> : null}
      <div className="btn-group">
        {passiveOptions.map((item) => (
          <button className="btn" type="button" disabled={disabled} key={item.id} onClick={() => onHandle(item.id)}>
            {item.label}
          </button>
        ))}
      </div>
      <div className="panel-title intervention-title">当场介入 <span className="sub">INTERVENE</span></div>
      <div className="action-metadata">介入方式</div>
      <div className="btn-group">
        {INTERVENTION_INTENT_OPTIONS.map((item) => (
          <ToggleButton active={interventionIntent === item.id} disabled={disabled} key={item.id} onClick={() => onInterventionIntentChange(item.id)}>
            {item.label}
          </ToggleButton>
        ))}
      </div>
      <div className="action-metadata section-meta">附加项</div>
      <div className="btn-group response-grid">
        {INTERVENTION_MODIFIER_OPTIONS.map((item) => (
          <ToggleButton active={interventionModifiers.includes(item.id)} disabled={disabled} key={item.id} onClick={() => onInterventionModifierToggle(item.id)}>
            {item.label}
          </ToggleButton>
        ))}
      </div>
      {interventionModifiers.includes("training") ? (
        <>
          <div className="action-metadata section-meta">调教内容</div>
          <div className="btn-group content-grid">
            {TRAINING_CONTENT_OPTIONS.filter((item) => !CAPTIVE_ROUTE_ONLY_TRAINING_IDS.has(item.id)).map((item) => (
              <ToggleButton
                active={interventionTrainingContents.includes(item.id)}
                disabled={disabled || (!interventionTrainingContents.includes(item.id) && interventionTrainingContents.length >= 3)}
                key={item.id}
                onClick={() => onInterventionTrainingContentToggle(item.id)}
              >
                {item.label}
              </ToggleButton>
            ))}
          </div>
        </>
      ) : null}
      <div className="action-metadata section-meta">道具</div>
      <ToolSelectGrid selected={interventionTools} disabled={disabled} onToggle={onInterventionToolToggle} />
      <textarea placeholder="可选：你要说的话..." value={interventionLine} disabled={disabled} onChange={(event) => onInterventionLineChange(event.target.value)} />
      <textarea placeholder="可选：处理备注..." value={note} disabled={disabled} onChange={(event) => onNoteChange(event.target.value)} />
      <button className="btn btn-large" type="button" disabled={disabled} onClick={() => onHandle("intervene")}>当场介入</button>
    </>
  );
}

function StatusRecoveryBar({
  disabled,
  canRetry,
  onRetry,
  onRefresh,
}: {
  disabled?: boolean;
  canRetry: boolean;
  onRetry: () => void;
  onRefresh: () => void;
}) {
  return (
    <div className="btn-group sync-action-bar">
      <button className="btn" type="button" disabled={disabled || !canRetry} onClick={onRetry}>重试</button>
      <button className="btn" type="button" disabled={disabled} onClick={onRefresh}>刷新</button>
    </div>
  );
}

function HistoryPanel({
  events,
  lastText,
  detail,
  onOpenDetail,
  onCloseDetail,
}: {
  events: CaptivityEvent[];
  lastText: string;
  detail: CaptivityEvent | null;
  onOpenDetail: (event: CaptivityEvent) => void;
  onCloseDetail: () => void;
}) {
  const availableDays = useMemo(
    () => Array.from(new Set(events.map((event) => Number(event.day || 1)))).sort((a, b) => b - a),
    [events],
  );
  const [selectedDay, setSelectedDay] = useState("all");
  useEffect(() => {
    if (selectedDay !== "all" && !availableDays.includes(Number(selectedDay))) setSelectedDay("all");
  }, [availableDays, selectedDay]);
  const groupedEvents = useMemo(() => {
    const visibleEvents = selectedDay === "all"
      ? events
      : events.filter((event) => Number(event.day || 1) === Number(selectedDay));
    const groups = new Map<number, CaptivityEvent[]>();
    visibleEvents.slice().reverse().forEach((event) => {
      const day = Number(event.day || 1);
      const group = groups.get(day) || [];
      group.push(event);
      groups.set(day, group);
    });
    return Array.from(groups.entries()).sort(([dayA], [dayB]) => dayB - dayA);
  }, [events, selectedDay]);

  if (detail) {
    return (
      <>
        <button className="history-back" type="button" onClick={onCloseDetail}>回到回顾</button>
        <div className="process-review-meta history-detail-meta">
          <div className="event-main">{detail.action_label || actionLabel(detail.action) || "事件"}</div>
          <div className="event-sub">{processReviewMeta(detail)}</div>
        </div>
        <div className="process-text history-detail-body">{historyEventText(detail) || "这条事件没有正文。"}</div>
      </>
    );
  }
  return (
    <>
      <div className="history-title-row">
        <div className="panel-title">事件回顾 <span className="sub">ARCHIVE</span></div>
        {availableDays.length ? (
          <select className="history-day-select" aria-label="按日期筛选事件" value={selectedDay} onChange={(event) => setSelectedDay(event.target.value)}>
            <option value="all">全部日期</option>
            {availableDays.map((day) => <option value={String(day)} key={day}>第 {day} 天</option>)}
          </select>
        ) : null}
      </div>
      {groupedEvents.length ? groupedEvents.map(([day, dayEvents]) => (
        <section className="history-day-group" key={day}>
          <div className="history-day-heading">
            <span>第 {day} 天</span>
            <span>{dayEvents.length} 条</span>
          </div>
          {dayEvents.map((event) => {
            const segment = event.tags?.includes("out_of_band")
              ? "随时"
              : event.phase === "ending" || event.action === "ending"
              ? "结局"
              : event.phase === "night"
                ? "晚上"
                : DAY_SEGMENT_LABELS[Math.max(0, Number(event.slot || 1) - 1)] || `第 ${event.slot || 0} 段`;
            return (
              <button className="action-card history-list-item" key={event.id || `${event.day}-${event.slot}-${event.action}`} type="button" onClick={() => onOpenDetail(event)}>
                <div className="action-metadata">{segment}</div>
                <div className="event-main">{event.action_label || actionLabel(event.action) || "事件"}</div>
              </button>
            );
          })}
        </section>
      )) : (
          <div className="action-card faded">
            <div className="uppercase pink-text" style={{ marginBottom: 5 }}>暂无回顾</div>
            <div className="event-sub">{lastText || "还没有归档事件。"}</div>
          </div>
      )}
    </>
  );
}

function MonitorRoomPanel({
  view,
  pendingType,
  monitorNote,
  interventionIntent,
  interventionModifiers,
  interventionTrainingContents,
  interventionTools,
  interventionLine,
  disabled,
  onMonitorNoteChange,
  onInterventionIntentChange,
  onInterventionModifierToggle,
  onInterventionTrainingContentToggle,
  onInterventionToolToggle,
  onInterventionLineChange,
  onOpenMonitor,
  onHandleMonitor,
}: {
  view: CaptivityView;
  pendingType: string;
  monitorNote: string;
  interventionIntent: string;
  interventionModifiers: string[];
  interventionTrainingContents: string[];
  interventionTools: string[];
  interventionLine: string;
  disabled?: boolean;
  onMonitorNoteChange: (value: string) => void;
  onInterventionIntentChange: (value: string) => void;
  onInterventionModifierToggle: (value: string) => void;
  onInterventionTrainingContentToggle: (value: string) => void;
  onInterventionToolToggle: (value: string) => void;
  onInterventionLineChange: (value: string) => void;
  onOpenMonitor: (style: "occasional" | "full") => void;
  onHandleMonitor: (strategy: string) => void;
}) {
  const deferredRecords = (view.deferred_monitor_materials || []).filter(Boolean);
  const monitorRecords = (view.event_log || []).filter((event) => event.monitor).slice(-4).reverse();
  const hasLiveGate = pendingType === "monitor_gate";
  const hasActiveRecord = pendingType === "monitor_handle";
  const hasRecordContent = hasActiveRecord || deferredRecords.length > 0 || monitorRecords.length > 0;
  const activeMonitorRecord = view.pending_event?.event || deferredRecords[0] || null;
  return (
    <>
      <div className={`monitor-console ${hasLiveGate || hasActiveRecord ? "active" : ""}`}>
        <div className="monitor-screen">
          <div className="monitor-screen-top">
            <span>LIVE MONITOR</span>
            <span>{hasLiveGate ? "SEALED" : hasActiveRecord ? "OPEN" : "IDLE"}</span>
          </div>
          <div className="monitor-screen-body">
            <div className="event-main">
              {hasLiveGate ? "夜间行动已封存" : hasActiveRecord ? "正在查看监控记录" : "暂无实时画面"}
            </div>
            <div className="event-sub">
              {hasLiveGate
                ? "可以现在打开实时监控，也可以选择不看。"
                : hasActiveRecord
                  ? "选择处理方式，或把这条记录留到之后使用。"
                  : "被囚禁方完成夜间行动后，实时监控会出现在这里。"}
            </div>
            {activeMonitorRecord && (hasLiveGate || hasActiveRecord) ? (
              <div className="serif monitor-live-scene">{monitorRecordSceneCopy(activeMonitorRecord)}</div>
            ) : null}
          </div>
        </div>
        {hasLiveGate ? (
          <div className="btn-group monitor-controls">
            <button className="btn" type="button" disabled={disabled} onClick={() => onOpenMonitor("occasional")}>偶尔看</button>
            <button className="btn" type="button" disabled={disabled} onClick={() => onOpenMonitor("full")}>全程看</button>
            <button className="btn" type="button" disabled={disabled} onClick={() => onHandleMonitor("none")}>不看</button>
          </div>
        ) : null}
        {hasActiveRecord ? (
          <MonitorHandlePanel
            note={monitorNote}
            interventionIntent={interventionIntent}
            interventionModifiers={interventionModifiers}
            interventionTrainingContents={interventionTrainingContents}
            interventionTools={interventionTools}
            interventionLine={interventionLine}
            disabled={disabled}
            showTitle={false}
            onNoteChange={onMonitorNoteChange}
            onInterventionIntentChange={onInterventionIntentChange}
            onInterventionModifierToggle={onInterventionModifierToggle}
            onInterventionTrainingContentToggle={onInterventionTrainingContentToggle}
            onInterventionToolToggle={onInterventionToolToggle}
            onInterventionLineChange={onInterventionLineChange}
            onHandle={onHandleMonitor}
          />
        ) : null}
      </div>
      <div className="monitor-record-title">
        <div className="panel-title">监控记录 <span className="sub">RECORDS</span></div>
      </div>
      {deferredRecords.length ? (
        <div className="monitor-record-list">
          {deferredRecords.map((record) => (
            <div className="monitor-record-item" key={record.id || `${record.day}-${record.action}-${record.created_at}`}>
              <div className="action-metadata">{monitorRecordTime(record)}</div>
              <div className="event-main">{monitorRecordSummary(record)}</div>
              <div className="serif event-sub monitor-record-scene">{monitorRecordSceneCopy(record)}</div>
            </div>
          ))}
        </div>
      ) : null}
      {monitorRecords.length ? (
        <div className="monitor-record-list">
          {monitorRecords.map((event) => (
            <div className="monitor-record-item" key={event.id || `monitor-${event.day}-${event.slot}-${event.action}`}>
              <div className="action-metadata">{monitorRecordTime(event)}</div>
              <div className="event-main">{monitorRecordSummary(event)}</div>
              <div className="serif event-sub monitor-record-scene">{monitorRecordSceneCopy(event)}</div>
            </div>
          ))}
        </div>
      ) : null}
      {!hasRecordContent ? (
        <div className="monitor-record-item faded">
          <div className="action-metadata">暂无监控记录</div>
          <div className="event-sub">打开过的夜间监控会出现在这里。</div>
        </div>
      ) : null}
    </>
  );
}

function SpecialPanel({
  role,
  view,
  escapeDay,
  escapeRoom,
  escapeHint,
  escapeBait,
  disabled,
  onEscapeDayChange,
  onEscapeRoomChange,
  onEscapeHintChange,
  onEscapeBaitChange,
  onOpenMonitorRoom,
  onOpenInventoryRoom,
  onScheduleEscape,
}: {
  role: UserRole;
  view: CaptivityView;
  escapeDay: number;
  escapeRoom: EscapeRoomId;
  escapeHint: string;
  escapeBait: string;
  disabled?: boolean;
  onEscapeDayChange: (value: number) => void;
  onEscapeRoomChange: (value: EscapeRoomId) => void;
  onEscapeHintChange: (value: string) => void;
  onEscapeBaitChange: (value: string) => void;
  onOpenMonitorRoom: () => void;
  onOpenInventoryRoom: () => void;
  onScheduleEscape: () => void;
}) {
  const endingState = String(view.ending_state || "");
  const endingTitle = String(view.ending_title || "").trim();
  const roomItemCount = INVENTORY_OPTIONS.filter((item) => Boolean(view.inventory?.[item.id])).length;
  const roomItemUnlocked = roomItemCount > 0;
  const publicEscapeHint = view.escape_hint || {};
  const escapeRecords = (view.event_log || [])
    .filter((event) => event.escape)
    .slice(-3)
    .reverse();
  return (
    <>
      {role !== "captor" ? <div className="panel-title">特殊机制 <span className="sub">SPECIAL</span></div> : null}
      {role === "captor" ? (
        <>
          <button className="special-room-entry" type="button" disabled={disabled} onClick={onOpenMonitorRoom}>
            <div>
              <div className="panel-title">监控室 <span className="sub">MONITOR</span></div>
              <div className="event-sub">进入全屏监控台，查看实时画面和历史记录。</div>
            </div>
            <span className="special-room-arrow">›</span>
          </button>
          <button className="special-room-entry" type="button" disabled={disabled} onClick={onOpenInventoryRoom}>
            <div>
              <div className="panel-title">物品仓库 <span className="sub">ITEMS</span></div>
              <div className="event-sub">进入全屏仓库，管理可赠送物品。</div>
            </div>
            <span className="special-room-arrow">›</span>
          </button>
          <div className="panel-title special-section-title">逃跑诱导 <span className="sub">ESCAPE</span></div>
          <div className="action-card">
            <div className="form-grid escape-room-row">
              <label className="compact-field">
                <span>诱导日期</span>
                <input className="compact" type="number" min={1} max={30} value={escapeDay} disabled={disabled} onChange={(event) => onEscapeDayChange(Number(event.target.value || 1))} />
              </label>
              <label className="compact-field">
                <span>钥匙位置</span>
                <select className="compact escape-room-select" value={escapeRoom} disabled={disabled} onChange={(event) => onEscapeRoomChange(event.target.value as EscapeRoomId)}>
                  {ESCAPE_ROOM_OPTIONS.map((room) => (
                    <option value={room.id} key={room.id}>{room.label}</option>
                  ))}
                </select>
              </label>
            </div>
            <input className="compact" value={escapeHint} disabled={disabled} onChange={(event) => onEscapeHintChange(event.target.value)} />
            <input className="compact" value={escapeBait} disabled={disabled} onChange={(event) => onEscapeBaitChange(event.target.value)} />
            <button className="btn btn-large" type="button" disabled={disabled} onClick={onScheduleEscape}>设置逃跑诱导</button>
          </div>
          {escapeRecords.length ? (
            <div className="monitor-record-list escape-record-list">
              {escapeRecords.map((event) => (
                <div className="monitor-record-item" key={event.id || `escape-${event.day}-${event.created_at}`}>
                  <div className="action-metadata">逃跑记录 / 第 {event.day || 1} 天</div>
                  <div className="event-main">{event.escape?.choice_label || escapeChoiceLabel(event.escape?.choice)}</div>
                </div>
              ))}
            </div>
          ) : null}
        </>
      ) : (
        <>
          <button
            className="special-room-entry"
            type="button"
            disabled={disabled || !roomItemUnlocked}
            onClick={onOpenInventoryRoom}
          >
            <div>
              <div className="panel-title">房间物品 <span className="sub">ITEMS</span></div>
              <div className="event-sub">{roomItemUnlocked ? `已解锁 ${roomItemCount} 件，点击查看。` : "未解锁"}</div>
            </div>
            {roomItemUnlocked ? <span className="special-room-arrow">›</span> : null}
          </button>
          <div className="action-card">
            <div className="action-metadata">特殊提示</div>
            <div className="event-main">逃跑提示</div>
            <div className="event-sub">
              {publicEscapeHint.hint || publicEscapeHint.bait
                ? [publicEscapeHint.hint, publicEscapeHint.bait].filter(Boolean).join("\n")
                : "未出现"}
            </div>
          </div>
        </>
      )}
      <div className="panel-title">结局 <span className="sub">ENDING</span></div>
      <div className="action-card">
        <div className="action-metadata">{endingState ? "结局已触发" : "未收录"}</div>
        <div className="event-main">{view.game_over ? (endingTitle || "已收录结局") : "暂无结局"}</div>
        <div className="event-sub">
          {view.game_over ? "最终正文已保存到回顾。" : "30 天结算后会收录到这里。"}
        </div>
      </div>
    </>
  );
}
