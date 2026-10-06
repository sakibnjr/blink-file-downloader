#!/usr/bin/env python3
"""
Chrome Native Messaging Host for Blink Downloader
Receives download requests directly from Google Chrome via stdin/stdout native messaging.
"""

import sys
import json
import struct
import urllib.request
import subprocess
import os
from pathlib import Path

BLINK_API_URL = "http://127.0.0.1:9632/api/download"
APP_DIR = Path(__file__).resolve().parent


def read_message():
    """Reads a message from Chrome (4 bytes length + JSON)."""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack('@I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)


def send_message(message_data):
    """Sends a message back to Chrome (4 bytes length + JSON)."""
    encoded = json.dumps(message_data).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('@I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def ensure_app_running():
    """Checks if Blink API is responding; if not, attempts to launch Blink."""
    try:
        req = urllib.request.Request("http://127.0.0.1:9632/api/status")
        with urllib.request.urlopen(req, timeout=0.8):
            return True
    except Exception:
        pass

    # Launch app in background
    try:
        main_script = APP_DIR / "main.py"
        subprocess.Popen(
            [sys.executable, str(main_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return True
    except Exception as e:
        return False


def main():
    while True:
        try:
            msg = read_message()
            if msg is None:
                break

            action = msg.get("action", "download")
            url = msg.get("url", "")
            referrer = msg.get("referrer", "")
            title = msg.get("title", "")

            if not url:
                send_message({"success": False, "error": "No URL provided"})
                continue

            ensure_app_running()

            # Forward to local Blink HTTP API
            payload = json.dumps({"url": url, "referrer": referrer, "title": title}).encode("utf-8")
            req = urllib.request.Request(
                BLINK_API_URL,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                send_message({"success": True, "data": result})

        except Exception as e:
            send_message({"success": False, "error": str(e)})
            break


if __name__ == "__main__":
    main()
