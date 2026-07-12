from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request


class AdapterError(RuntimeError):
    pass


def request_assistant(prompt: str, config: dict[str, Any]) -> str:
    ai = config.get("ai") if isinstance(config.get("ai"), dict) else {}
    if not ai.get("enabled"):
        raise AdapterError("AI adapter is disabled; copy the generated prompt into your assistant manually.")
    base_url = str(ai.get("base_url") or "").rstrip("/")
    model = str(ai.get("model") or "")
    env_name = str(ai.get("api_key_env") or "CAPTIVITY_AI_API_KEY")
    api_key = os.environ.get(env_name, "")
    if not base_url or not model or not api_key:
        raise AdapterError("AI adapter config is incomplete.")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": prompt}],
        "temperature": float(ai.get("temperature") or 0.9),
        "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{base_url}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=int(ai.get("timeout_seconds") or 120)) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AdapterError(f"AI request failed: {exc}") from exc
    try:
        return str(payload["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise AdapterError("AI response does not contain choices[0].message.content.") from exc
