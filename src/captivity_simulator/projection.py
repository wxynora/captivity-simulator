from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal


Audience = Literal["user", "assistant"]


def _route(payload: dict[str, Any]) -> str:
    for key in ("captor_view", "captive_view", "state"):
        view = payload.get(key)
        if isinstance(view, dict) and str(view.get("route") or ""):
            return str(view["route"])
    return "captured_by_assistant"


def _viewer_for(route: str, audience: Audience) -> str:
    user_is_captor = route == "capture_assistant"
    if audience == "user":
        return "captor" if user_is_captor else "captive"
    return "captive" if user_is_captor else "captor"


def _safe_player_text(view: dict[str, Any], ok: bool) -> str:
    if not ok:
        return "操作没有完成，请检查当前步骤后重试。"
    day = int(view.get("current_day") or 1)
    total = int(view.get("total_days") or 30)
    phase = "夜间" if str(view.get("phase") or "") == "night" else "白天"
    return f"囚禁模拟器状态已更新：第 {day} / {total} 天，{phase}。"


def project_payload(
    payload: dict[str, Any],
    audience: Audience,
    *,
    include_commands: bool = False,
    include_engine_text: bool = False,
) -> dict[str, Any]:
    route = _route(payload)
    viewer = _viewer_for(route, audience)
    view_key = f"{viewer}_view"
    raw_view = payload.get(view_key)
    if not isinstance(raw_view, dict):
        raw_view = payload.get("state") if isinstance(payload.get("state"), dict) else {}
    view = deepcopy(raw_view)

    result: dict[str, Any] = {
        "ok": bool(payload.get("ok")),
        "game_id": str(payload.get("game_id") or "captivity_simulator"),
        "game_over": bool(payload.get("game_over") or view.get("game_over")),
        "result": str(payload.get("result") or view.get("result") or ""),
        "state": deepcopy(view),
        view_key: deepcopy(view),
    }
    if include_commands:
        result["commands"] = deepcopy(payload.get("commands") or [])
    text = str(payload.get("text") or payload.get("player_text") or "") if include_engine_text else ""
    result["text"] = text or _safe_player_text(view, result["ok"])
    result["player_text"] = result["text"]
    return result
