from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".json", ".md", ".toml", ".html", ".css"}
FORBIDDEN = {
    "private user name": "\u5c0f\u73a5",
    "private full user name": "\u8f9b\u73a5",
    "private assistant name": "\u6e21",
    "old user actor id": "xin" + "yue",
    "old assistant route id": "captured_by_" + "du",
    "old captor route id": "capture_" + "du",
    "old assistant identifier": "du" + "_captive",
    "old assistant constant": "ENDING_" + "DU",
    "private sync route": "sync-" + "du",
    "private storage service": "r2_" + "store",
    "private gateway name": "du-" + "gateway",
    "private miniapp API": "miniapp-" + "api",
    "private deployment host": "duxy-" + "home",
}


def main() -> int:
    failures: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in {".git", "node_modules", "dist"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, needle in FORBIDDEN.items():
            if needle in text:
                failures.append(f"{path.relative_to(ROOT)}: {label}")
    if failures:
        print("Open-source audit failed:")
        print("\n".join(f"- {item}" for item in failures))
        return 1
    print("Open-source audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
