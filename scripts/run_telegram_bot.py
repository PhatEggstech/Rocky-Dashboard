# -*- coding: utf-8 -*-
"""Run the Rocky Telegram adapter using the same machine-local MCP env file."""
from __future__ import annotations

import os
import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    env_path = Path(os.environ.get("MCP_ENV_FILE", PROJECT_ROOT / ".env"))
    load_dotenv(env_path, override=True, encoding="utf-8-sig")
except ImportError:
    pass

log_dir = Path(os.environ.get("MCP_LOG_DIR", PROJECT_ROOT / "logs"))
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=log_dir / "telegram_bot.log",
    level=getattr(logging, os.environ.get("MCP_LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
# httpx includes the full Bot API URL in its INFO access logs. That URL embeds
# the Telegram token, so retain warnings/errors only.
logging.getLogger("httpx").setLevel(logging.WARNING)

from mcp_server.telegram_bot import main


if __name__ == "__main__":
    main()
