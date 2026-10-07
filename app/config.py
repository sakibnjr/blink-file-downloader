"""
Configuration and File Categorization Manager for Blink Downloader
Saves and loads settings to ~/.config/blink/config.json
"""

import os
import json
from pathlib import Path
from urllib.parse import urlparse

CONFIG_DIR = Path.home() / ".config" / "blink"
CONFIG_FILE = CONFIG_DIR / "config.json"

CATEGORIES = {
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v"},
    "Music": {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus"},
    "Archives": {".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".tgz", ".zst"},
    "Documents": {".pdf", ".epub", ".mobi", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".odt"},
    "Packages": {".rpm", ".deb", ".iso", ".img", ".AppImage", ".flatpakref"}
}

SPEED_PROFILES = {
    "turbo": {
        "id": "turbo",
        "name": "Turbo 🚀",
        "down_limit": "0",
        "connections": 16,
        "description": "Unlimited maximum speed (16 connections)"
    },
    "balanced": {
        "id": "balanced",
        "name": "Balanced ⚖️",
        "down_limit": "3M",
        "connections": 8,
        "description": "Throttled to 3 MB/s for smooth web browsing"
    },
    "background": {
        "id": "background",
        "name": "Background 🌙",
        "down_limit": "500K",
        "connections": 4,
        "description": "Quiet 500 KB/s background download"
    }
}

DEFAULT_CONFIG = {
    "download_dir": str(Path.home() / "Downloads"),
    "auto_categorize": True,
    "run_in_background": True,
    "clipboard_detection": True,
    "speed_profile": "turbo",
    "max_concurrent": 5,
    "connections_per_server": 16,
    "max_download_limit": 0,
    "max_upload_limit": 0
}


class ConfigManager:
    def __init__(self):
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
        except Exception as e:
            print(f"[Config] Error loading settings: {e}")

    def save(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[Config] Error saving settings: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def get_target_directory(self, filename_or_url: str) -> str:
        """
        Determines the target folder. If auto_categorize is enabled,
        returns the subfolder (Videos, Archives, Documents, etc.).
        """
        base_dir = self.data.get("download_dir", str(Path.home() / "Downloads"))
        if not self.data.get("auto_categorize", True):
            os.makedirs(base_dir, exist_ok=True)
            return base_dir

        # Extract file extension
        path = filename_or_url
        if path.startswith("http://") or path.startswith("https://") or path.startswith("ftp://"):
            parsed = urlparse(path)
            path = parsed.path

        # Handle clean basename
        basename = os.path.basename(path).split("?")[0]
        ext = os.path.splitext(basename)[1].lower()

        # Check against categories
        matched_category = None
        for cat_name, extensions in CATEGORIES.items():
            if ext in extensions:
                matched_category = cat_name
                break

        if matched_category:
            cat_dir = os.path.join(base_dir, matched_category)
            os.makedirs(cat_dir, exist_ok=True)
            return cat_dir

        os.makedirs(base_dir, exist_ok=True)
        return base_dir


config_manager = ConfigManager()
