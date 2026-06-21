import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _resolve_project_root() -> Path:
    env_root = os.getenv("HMA_PROJECT_ROOT")
    if env_root:
        p = Path(env_root).expanduser().resolve()
        if not p.exists():
            logger.warning("HMA_PROJECT_ROOT 指定的目录不存在: %s，将自动回退", p)
        else:
            logger.info("使用环境变量 HMA_PROJECT_ROOT: %s", p)
            return p

    this_file = Path(__file__).resolve(strict=False)
    project_root = this_file.parent.parent

    try:
        project_root = project_root.resolve(strict=False)
    except Exception:
        project_root = Path(os.path.abspath(str(project_root)))

    alt_roots = [
        Path(os.getcwd()).resolve(),
        Path(sys.argv[0]).resolve().parent if len(sys.argv) > 0 else None,
    ]
    for root in alt_roots:
        if root and (root / "data").is_dir() and (root / "app").is_dir():
            project_root = root
            break

    return project_root


PROJECT_ROOT = _resolve_project_root()

ENV_DATA_DIR = os.getenv("HMA_DATA_DIR")
if ENV_DATA_DIR:
    DATA_DIR = Path(ENV_DATA_DIR).expanduser().resolve()
else:
    DATA_DIR = PROJECT_ROOT / "data"

ENV_STRATEGY_FILE = os.getenv("HMA_STRATEGY_FILE")
if ENV_STRATEGY_FILE:
    STRATEGY_FILE = Path(ENV_STRATEGY_FILE).expanduser().resolve()
else:
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


def dump_paths() -> dict:
    return {
        "project_root": str(PROJECT_ROOT),
        "data_dir": str(DATA_DIR),
        "strategy_file": str(STRATEGY_FILE),
        "strategy_file_exists": STRATEGY_FILE.exists(),
    }
