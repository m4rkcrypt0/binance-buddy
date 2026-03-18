#!/usr/bin/env python3
import fcntl
import json
import os
import subprocess
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_FILE = os.path.join(ROOT_DIR, "data", "alerts.json")
LOCK_FILE = os.path.join(ROOT_DIR, "data", "alert-watcher.lock")
LOG_FILE = os.path.join(ROOT_DIR, "data", "alert-watcher.log")
CHECK_SCRIPT = os.path.join(os.path.dirname(__file__), "check_alerts.py")
SLEEP_SECONDS = 60


def load_active_count():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return 0
    alerts = data.get("alerts", [])
    if not isinstance(alerts, list):
        return 0
    return sum(1 for alert in alerts if alert.get("active", True))


def main():
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    with open(LOCK_FILE, "w", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("watcher already running")
            return 0

        while True:
            active_count = load_active_count()
            if active_count <= 0:
                return 0

            with open(LOG_FILE, "a", encoding="utf-8") as log_handle:
                process = subprocess.run(
                    [CHECK_SCRIPT],
                    stdout=log_handle,
                    stderr=log_handle,
                    text=True,
                    check=False,
                )
                log_handle.write("\n")
                log_handle.flush()

            if process.returncode != 0:
                time.sleep(SLEEP_SECONDS)
                continue

            if load_active_count() <= 0:
                return 0

            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
