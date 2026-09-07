"""
MAESTRO 24/7 Autonomous YouTube Autopilot Daemon.
Run this script to operate your autonomous channel 24/7 without opening any browser.

Features:
- Headless 24/7 operation on Windows, Linux VPS, or Cloud Containers.
- Automatically launches FastAPI, YouTube Scheduler Daemon, and Autonomous Director Agent.
- Self-optimizing loop: Evaluates views/analytics -> Doubles down on winners -> Auto-generates videos -> Uploads to YouTube.
"""
import os
import sys
import time
import signal
import threading
import logging
from pathlib import Path

# Set up paths
APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

# Logging configuration
LOGS_DIR = APP_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR / "autonomous_daemon.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("MAESTRO_247_Daemon")

# Enable analytics agent dynamically in config
from backend.core.config import get_config, save_config
cfg = get_config()
if "features" not in cfg:
    cfg["features"] = {}
cfg["features"]["enable_analytics_agent"] = True
save_config(cfg)
logger.info("Enabled 24/7 Autonomous Channel Director in config.")

import uvicorn
from backend.services.youtube_scheduler import start_scheduler_daemon
from backend.services.analytics_agent import start_analytics_agent, trigger_autonomous_cycle

_RUNNING = True


def signal_handler(sig, frame):
    global _RUNNING
    logger.info("Shutdown signal received. Gracefully terminating 24/7 daemon...")
    _RUNNING = False
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def run_server():
    """Runs uvicorn in a dedicated thread."""
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8765, log_level="warning")


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("   MAESTRO - 24/7 AUTONOMOUS YOUTUBE CHANNEL AUTOPILOT DAEMON")
    logger.info("   Multi-Agent Autonomous Engine for Scalable Transmedia Production")
    logger.info("=" * 70)

    # 1. Start Server Thread
    server_thread = threading.Thread(target=run_server, daemon=True, name="MAESTRO_Uvicorn")
    server_thread.start()
    logger.info("MAESTRO API Server running on port 8765.")

    # 2. Wait 2 seconds for server boot
    time.sleep(2)

    # 3. Start Background Daemons
    start_scheduler_daemon()
    start_analytics_agent()
    logger.info("YouTube Scheduler Daemon and Closed-Loop Analytics Agent are ACTIVE.")

    # 4. Trigger initial bootstrap cycle if desired
    try:
        logger.info("Executing initial autonomous channel director diagnostic...")
        res = trigger_autonomous_cycle(force=False)
        logger.info(f"Initial cycle status: {res.get('strategy', 'complete')} | Topic: {res.get('topic', 'N/A')}")
    except Exception as e:
        logger.warning(f"Initial autonomous cycle deferred: {e}")

    logger.info("Daemon running 24/7 on autopilot. Press Ctrl+C to stop.")
    while _RUNNING:
        time.sleep(60)
