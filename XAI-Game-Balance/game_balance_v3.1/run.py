"""
run.py
Launch the Game Balance API from the project root.
All output is saved to data/logs/server.log as well as printed to the terminal.

Usage:
    python run.py
"""
import logging
import os
import sys
from pathlib import Path

# Suppress Windows-specific ConnectionResetError (WinError 10054) noise
# This is a known asyncio/proactor issue on Windows — not a real error
if sys.platform == "win32":
    import asyncio
    _original_call_connection_lost = None
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        def _silence_connection_reset(self, exc):
            if isinstance(exc, ConnectionResetError):
                logging.getLogger("uvicorn.error").debug(
                    "ConnectionResetError suppressed (WinError 10054) — client closed connection."
                )
                return
            if _original_call_connection_lost:
                _original_call_connection_lost(self, exc)
        _original_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost
        _ProactorBasePipeTransport._call_connection_lost = _silence_connection_reset
    except Exception:
        pass

# Ensure log directory exists
log_dir = Path(__file__).resolve().parent / "data" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_path = log_dir / "server.log"

# Set up file logging only — let uvicorn handle its own colored terminal output
log_handler = logging.FileHandler(log_path, encoding="utf-8")
log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.getLogger().addHandler(log_handler)
logging.getLogger().setLevel(logging.INFO)

import uvicorn

if __name__ == "__main__":
    logging.getLogger().info(f"Server log will be saved to: {log_path}")
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
    )
