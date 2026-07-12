from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .settings import CONFIG_PATH, PROJECT_ROOT


DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "default.json"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def load_config(path: Path | None = None) -> dict[str, Any]:
    return _merge(_read_json(DEFAULT_CONFIG_PATH), _read_json(path or CONFIG_PATH))


def actor_names(config: dict[str, Any]) -> dict[str, str]:
    actors = config.get("actors") if isinstance(config.get("actors"), dict) else {}
    return {
        "user": str(actors.get("user") or "{user}"),
        "assistant": str(actors.get("assistant") or "{assistant}"),
    }


def render_placeholders(value: Any, config: dict[str, Any]) -> Any:
    names = actor_names(config)
    if isinstance(value, str):
        return value.replace("{user}", names["user"]).replace("{assistant}", names["assistant"])
    if isinstance(value, list):
        return [render_placeholders(item, config) for item in value]
    if isinstance(value, dict):
        return {key: render_placeholders(item, config) for key, item in value.items()}
    return value
