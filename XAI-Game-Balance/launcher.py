"""
launcher.py
Starts the analysis service and the interface together, then opens the browser.
Used by the START scripts; can also be run directly with `python launcher.py`.
Close the window (or press Ctrl+C) to stop both.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_PORT = int(os.getenv("GB_API_PORT", "8001"))
UI_PORT = int(os.getenv("GB_UI_PORT", "8501"))
API_URL = f"http://127.0.0.1:{API_PORT}"
UI_URL = f"http://localhost:{UI_PORT}"


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for(url: str, timeout: float, proc: subprocess.Popen) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            time.sleep(0.5)
    return False


def stop(*procs: subprocess.Popen) -> None:
    for p in procs:
        if p and p.poll() is None:
            p.terminate()
    for p in procs:
        if p:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


def main() -> int:
    for port, what in ((API_PORT, "analysis service"), (UI_PORT, "interface")):
        if port_in_use(port):
            print(f"\nPort {port} (needed by the {what}) is already in use.")
            print("The tool may already be running in another window: check your browser at "
                  f"{UI_URL}, or close the other window and try again.")
            print("To use different ports, set GB_API_PORT / GB_UI_PORT before starting.")
            return 1

    # PYTHONUTF8: text files and console output in UTF-8 on every system (Windows included)
    env = dict(os.environ, API_BASE_URL=API_URL, GB_API_PORT=str(API_PORT), PYTHONUTF8="1")

    print("Starting the analysis service ...")
    api = subprocess.Popen([sys.executable, "run.py"], cwd=ROOT, env=env)
    if not wait_for(f"{API_URL}/health", 90, api):
        print("\nThe analysis service did not start. See the messages above, "
              "or data/logs/server.log.")
        stop(api)
        return 1

    print("Starting the interface ...")
    ui = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"),
         "--server.port", str(UI_PORT),
         "--server.address", "localhost",
         "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=ROOT, env=env,
    )
    if not wait_for(UI_URL, 90, ui):
        print("\nThe interface did not start. See the messages above.")
        stop(ui, api)
        return 1

    print("\n" + "=" * 60)
    print(f"  i-Game Game Balance Tool is running at {UI_URL}")
    print("  Close this window or press Ctrl+C to stop.")
    print("=" * 60 + "\n")
    if os.getenv("GB_NO_BROWSER") != "1":
        webbrowser.open(UI_URL)

    try:
        while api.poll() is None and ui.poll() is None:
            time.sleep(1)
        print("\nOne of the components stopped unexpectedly. Shutting down.")
        return 1
    except KeyboardInterrupt:
        print("\nStopping ...")
        return 0
    finally:
        stop(ui, api)


if __name__ == "__main__":
    sys.exit(main())
