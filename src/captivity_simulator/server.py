from __future__ import annotations

import re
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .adapter import AdapterError, request_assistant
from .configuration import load_config, render_placeholders
from .engine import run_command
from .prompts import build_assistant_prompt
from .projection import project_payload
from .protocol import directive_to_command
from .settings import DATA_DIR, PROJECT_ROOT


WEB_DIST = PROJECT_ROOT / "web" / "dist"


def _safe_save_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "default"))[:80].strip("._-")
    return cleaned or "default"


def _save_path(save_id: str) -> Path:
    return DATA_DIR / "saves" / f"{_safe_save_id(save_id)}.json"


def _configured_result(payload: dict, config: dict) -> dict:
    return render_placeholders(payload, config)


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "game": "captivity_simulator"})

    @app.get("/api/config")
    def public_config():
        config = load_config()
        return jsonify({"actors": config.get("actors") or {}, "ai_enabled": bool((config.get("ai") or {}).get("enabled"))})

    @app.post("/api/game/command")
    def game_command():
        body = request.get_json(silent=True) or {}
        config = load_config()
        result = run_command(str(body.get("command") or "status"), save_path=_save_path(str(body.get("save_id") or "default")))
        projected = project_payload(result, "user")
        return jsonify(_configured_result(projected, config)), 200 if result.get("ok") else 400

    @app.post("/api/game/sync-assistant")
    def sync_assistant():
        body = request.get_json(silent=True) or {}
        save_id = str(body.get("save_id") or "default")
        config = load_config()
        payload = run_command("status", save_path=_save_path(save_id))
        prompt = build_assistant_prompt(payload, config, str(body.get("message") or ""))
        try:
            reply_text = request_assistant(prompt, config)
        except AdapterError as exc:
            response = _configured_result(project_payload(payload, "user"), config)
            response.update({"ok": False, "error": str(exc), "sync_result": "adapter_required"})
            return jsonify(response), 409
        command = directive_to_command(reply_text, payload)
        result = run_command(command, save_path=_save_path(save_id)) if command else payload
        response = _configured_result(project_payload(result, "user"), config)
        response.update({
            "sync_result": "applied" if command and result.get("ok") else "no_directive",
        })
        return jsonify(response), 200 if response.get("ok") else 400

    @app.get("/")
    @app.get("/<path:path>")
    def web(path: str = "index.html"):
        target = WEB_DIST / path
        if path != "index.html" and target.is_file():
            return send_from_directory(WEB_DIST, path)
        if (WEB_DIST / "index.html").is_file():
            return send_from_directory(WEB_DIST, "index.html")
        return "Web build not found. Run: cd web && npm install && npm run build", 503

    return app


def main() -> None:
    config = load_config()
    server = config.get("server") if isinstance(config.get("server"), dict) else {}
    create_app().run(
        host=str(server.get("host") or "127.0.0.1"),
        port=int(server.get("port") or 5058),
        debug=False,
    )


if __name__ == "__main__":
    main()
