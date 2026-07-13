from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from .configuration import render_placeholders
from .reference import get_reference, reference_tool_schema


class AdapterError(RuntimeError):
    pass


GAME_CHANNEL_LABEL = "（囚禁模拟器频道）"


def _request_chat_completion(body: dict[str, Any], *, base_url: str, api_key: str, timeout: int) -> dict[str, Any]:
    req = request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AdapterError(f"AI request failed: {exc}") from exc
    return payload if isinstance(payload, dict) else {}


def request_assistant(prompt: str, config: dict[str, Any], player_message: str = "") -> str:
    ai = config.get("ai") if isinstance(config.get("ai"), dict) else {}
    if not ai.get("enabled"):
        raise AdapterError("AI adapter is disabled; copy the generated prompt into your assistant manually.")
    base_url = str(ai.get("base_url") or "").rstrip("/")
    model = str(ai.get("model") or "")
    env_name = str(ai.get("api_key_env") or "CAPTIVITY_AI_API_KEY")
    api_key = os.environ.get(env_name, "")
    if not base_url or not model or not api_key:
        raise AdapterError("AI adapter config is incomplete.")
    channel_message = (
        f"{GAME_CHANNEL_LABEL}\n{{user}}：{player_message.strip()}"
        if player_message.strip()
        else "（囚禁模拟器频道系统提示）{user}没有发文字消息给你"
    )
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": str(render_placeholders(channel_message, config)),
            },
        ],
        "tools": [reference_tool_schema()],
        "tool_choice": "auto",
        "temperature": float(ai.get("temperature") or 0.9),
        "stream": False,
    }
    timeout = int(ai.get("timeout_seconds") or 120)
    for _ in range(3):
        payload = _request_chat_completion(body, base_url=base_url, api_key=api_key, timeout=timeout)
        try:
            message = payload["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AdapterError("AI response does not contain choices[0].message.") from exc
        tool_calls = message.get("tool_calls") if isinstance(message, dict) else None
        if not isinstance(tool_calls, list) or not tool_calls:
            return str((message or {}).get("content") or "").strip()
        body["messages"].append(message)
        for tool_call in tool_calls:
            function = tool_call.get("function") if isinstance(tool_call, dict) else {}
            if str((function or {}).get("name") or "") != "captivity_simulator_reference":
                result = {"error": "unknown_tool"}
            else:
                try:
                    arguments = json.loads(str((function or {}).get("arguments") or "{}"))
                except json.JSONDecodeError:
                    arguments = {}
                result = get_reference(str((arguments or {}).get("分类") or (arguments or {}).get("category") or ""))
            body["messages"].append({
                "role": "tool",
                "tool_call_id": str(tool_call.get("id") or ""),
                "content": result,
            })
    raise AdapterError("AI exceeded the reference-tool round limit.")
