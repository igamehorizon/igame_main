"""
preflight.py
Checks run by the START scripts before the first setup. Exits 1 with a message
when setup would fail.
"""
import os
import sys

# Longest file path the installed packages create inside the environment's
# site-packages folder: measured at 115-117 characters (Python 3.10-3.15),
# plus a small margin for future package versions.
LONGEST_PACKAGE_PATH = 125
WINDOWS_PATH_LIMIT = 260


def long_paths_enabled() -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\FileSystem") as key:
            return winreg.QueryValueEx(key, "LongPathsEnabled")[0] == 1
    except OSError:
        return False


def problems(version, folder: str, windows: bool, long_paths: bool) -> list:
    """Returns the messages that would stop setup (empty list = OK)."""
    if tuple(version[:2]) < (3, 10):
        return [f"Python {version[0]}.{version[1]} is too old: Python 3.10 or newer is needed."]
    if windows and not long_paths:
        site_packages_len = len(folder) + len("\\.venv\\Lib\\site-packages\\")
        if site_packages_len + LONGEST_PACKAGE_PATH >= WINDOWS_PATH_LIMIT:
            return ["The path of this folder is too long for Windows to install the tool's packages:",
                    f"  {folder}",
                    "Move the folder somewhere with a shorter path, for example C:\\igame-game-balance-tool,",
                    "and double-click the START file again."]
    return []


def main() -> int:
    windows = os.name == "nt"
    msgs = problems(sys.version_info, os.getcwd(), windows, windows and long_paths_enabled())
    for m in msgs:
        print(m)
    return 1 if msgs else 0


if __name__ == "__main__":
    sys.exit(main())
