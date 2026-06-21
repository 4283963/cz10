import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
STRATEGY_FILE = DATA_DIR / "strategies.json"

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

DEFAULT_TEMPLATE = {
    "version": 1,
    "updated_at": 0,
    "templates": {
        "default": {
            "name": "默认策略",
            "blacklist": [],
            "whitelist": [],
            "enable_blacklist": True,
            "enable_whitelist": False,
            "hide_root": True,
            "hide_bootloader": True
        }
    }
}
