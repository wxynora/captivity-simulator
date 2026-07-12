from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

from .configuration import load_config, render_placeholders
from .engine import run_command
from .server import _save_path


SERVER_NAME = "captivity-simulator-mcp"
SERVER_VERSION = "0.1.0"
DEFAULT_PROTOCOL_VERSION = "2025-06-18"
TOOL_NAME = "captivity_simulator"
RESOURCE_URI = "captivity-simulator://save/default"


@dataclass
class RpcError(Exception):
    code: int
    message: str
    data: Any | None = None


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _params_object(params: Any) -> dict[str, Any]:
    if params is None:
        return {}
    if not isinstance(params, dict):
        raise RpcError(-32602, "Invalid params: expected an object")
    return params


def _tool_definition() -> dict[str, Any]:
    return {
        "name": TOOL_NAME,
        "description": (
            "Read or advance the local Captivity Simulator save. Call status first, then submit exactly "
            "one command allowed by the returned pending event. The rules engine owns state changes and "
            "returns both human-readable text and structured state for the captive and captor views."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "Rules-engine command, for example: status, new_game route=captured_by_assistant, "
                        "plan_day ..., respond_action ..., submit_process ..., night_action ..., or view_monitor ..."
                    ),
                },
                "save_id": {
                    "type": "string",
                    "description": "Local save identifier. Defaults to default.",
                    "default": "default",
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    }


def _configured_status(save_id: str) -> dict[str, Any]:
    payload = run_command("status", save_path=_save_path(save_id))
    return render_placeholders(payload, load_config())


def _call_tool(params: Any) -> dict[str, Any]:
    body = _params_object(params)
    name = str(body.get("name") or "")
    if name != TOOL_NAME:
        raise RpcError(-32602, f"Unknown tool: {name or '<missing>'}")

    arguments = body.get("arguments") or {}
    if not isinstance(arguments, dict):
        raise RpcError(-32602, "Invalid params: tool arguments must be an object")

    command = str(arguments.get("command") or "").strip()
    if not command:
        raise RpcError(-32602, "Invalid params: command is required")
    save_id = str(arguments.get("save_id") or "default")
    payload = run_command(command, save_path=_save_path(save_id))
    configured = render_placeholders(payload, load_config())
    result: dict[str, Any] = {
        "content": [{"type": "text", "text": str(configured.get("text") or "")}],
        "structuredContent": configured,
    }
    if configured.get("ok") is False:
        result["isError"] = True
    return result


def _read_resource(params: Any) -> dict[str, Any]:
    body = _params_object(params)
    uri = str(body.get("uri") or "")
    if uri != RESOURCE_URI:
        raise RpcError(-32602, f"Unknown resource: {uri or '<missing>'}")
    payload = _configured_status("default")
    return {
        "contents": [
            {
                "uri": RESOURCE_URI,
                "mimeType": "application/json",
                "text": _json_dump(payload),
            }
        ]
    }


def _dispatch(method: str, params: Any) -> dict[str, Any]:
    if method == "initialize":
        body = _params_object(params)
        protocol_version = str(body.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION)
        return {
            "protocolVersion": protocol_version,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"listChanged": False},
            },
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }
    if method in {"notifications/initialized", "ping"}:
        return {}
    if method == "tools/list":
        return {"tools": [_tool_definition()]}
    if method == "tools/call":
        return _call_tool(params)
    if method == "resources/list":
        return {
            "resources": [
                {
                    "uri": RESOURCE_URI,
                    "name": "Captivity Simulator default save",
                    "description": "Current status payload for the default local save.",
                    "mimeType": "application/json",
                }
            ]
        }
    if method == "resources/read":
        return _read_resource(params)
    raise RpcError(-32601, f"Method not found: {method}")


def handle_request(message: Any) -> dict[str, Any] | list[dict[str, Any]] | None:
    if isinstance(message, list):
        if not message:
            return _error(None, -32600, "Invalid Request")
        responses = [item for item in (handle_request(entry) for entry in message) if item is not None]
        return responses or None
    if not isinstance(message, dict):
        return _error(None, -32600, "Invalid Request")
    if "method" not in message:
        return None

    has_id = "id" in message
    request_id = message.get("id")
    method = message.get("method")
    if not isinstance(method, str):
        return _error(request_id if has_id else None, -32600, "Invalid Request") if has_id else None
    try:
        result = _dispatch(method, message.get("params"))
    except RpcError as exc:
        return _error(request_id, exc.code, exc.message, exc.data) if has_id else None
    except Exception as exc:  # pragma: no cover - stdout is reserved for MCP JSON-RPC.
        print(f"{SERVER_NAME}: internal error while handling {method}: {exc}", file=sys.stderr)
        return _error(request_id, -32603, "Internal error") if has_id else None
    return _response(request_id, result) if has_id else None


def serve_stdio() -> None:
    for raw_line in sys.stdin.buffer:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            response = _error(None, -32700, "Parse error", {"detail": str(exc)})
        else:
            response = handle_request(message)
        if response is not None:
            sys.stdout.write(_json_dump(response) + "\n")
            sys.stdout.flush()


def main() -> None:
    serve_stdio()


if __name__ == "__main__":
    main()
