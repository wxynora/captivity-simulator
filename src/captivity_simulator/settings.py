from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("CAPTIVITY_DATA_DIR") or PROJECT_ROOT / "data").expanduser().resolve()
CONFIG_PATH = Path(
    os.environ.get("CAPTIVITY_CONFIG") or PROJECT_ROOT / "config" / "local.json"
).expanduser().resolve()
