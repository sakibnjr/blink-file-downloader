"""
Smart Clipboard Link Detector for Blink Downloader
Monitors clipboard for downloadable files and magnet links.
"""

import os
from urllib.parse import urlparse
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GLib

from app.config import config_manager

DOWNLOAD_EXTENSIONS = {
    # Archives
    '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar', '.tgz', '.zst',
    # Disk images & packages
    '.iso', '.img', '.rpm', '.deb', '.appimage', '.flatpakref', '.apk', '.dmg',
    # Media
    '.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv',
    '.mp3', '.flac', '.wav', '.ogg', '.m4a', '.aac',
    # Documents
    '.pdf', '.epub', '.mobi', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
}


class ClipboardMonitor:
    def __init__(self, engine, notifier=None, on_link_detected=None):
        self.engine = engine
        self.notifier = notifier
        self.on_link_detected = on_link_detected
        self.seen_urls = set()
        self.last_text = ""
        self.timer_id = None

        display = Gdk.Display.get_default()
        if display:
            self.clipboard = display.get_clipboard()
            # Listen to changed signal
            self.clipboard.connect("changed", self._on_clipboard_changed)
            # Gentle poll as fallback for Wayland background checks
            self.timer_id = GLib.timeout_add_seconds(2, self._poll_check)

    def _on_clipboard_changed(self, clipboard):
        self._check_now()

    def _poll_check(self):
        self._check_now()
        return True  # Keep timer running

    def _check_now(self):
        if not config_manager.get("clipboard_detection", True):
            return

        if not hasattr(self, 'clipboard') or not self.clipboard:
            return

        self.clipboard.read_text_async(None, self._on_text_read)

    def _on_text_read(self, clipboard, result):
        try:
            text = clipboard.read_text_finish(result)
            if not text:
                return

            text = text.strip()
            if text == self.last_text:
                return

            self.last_text = text

            if self._is_downloadable_url(text):
                if text not in self.seen_urls:
                    self.seen_urls.add(text)
                    self._handle_detected_url(text)
        except Exception:
            pass

    def _is_downloadable_url(self, text: str) -> bool:
        if text.startswith("magnet:?"):
            return True

        if not (text.startswith("http://") or text.startswith("https://") or text.startswith("ftp://")):
            return False

        # Parse URL
        try:
            parsed = urlparse(text)
            path = parsed.path.lower()
            
            # Check for direct file extension match
            for ext in DOWNLOAD_EXTENSIONS:
                if path.endswith(ext):
                    return True
                if f"{ext}?" in text.lower():
                    return True

            # Check query parameters like ?filename=test.zip
            query = parsed.query.lower()
            for ext in DOWNLOAD_EXTENSIONS:
                if ext in query:
                    return True

        except Exception:
            return False

        return False

    def _handle_detected_url(self, url: str):
        # Extract filename preview
        filename = "File"
        if url.startswith("magnet:"):
            filename = "Magnet Link"
        else:
            path = urlparse(url).path
            base = os.path.basename(path).split("?")[0]
            if base:
                filename = base

        print(f"[Clipboard] Download link detected: {filename} ({url})")

        # Invoke UI callback if window is open
        if self.on_link_detected:
            GLib.idle_add(self.on_link_detected, url, filename)

        # Also send desktop notification
        if self.notifier:
            self.notifier.notify_clipboard(url, filename, self._quick_download)

    def _quick_download(self, url: str):
        try:
            self.engine.add_uri(url)
            if self.notifier:
                filename = os.path.basename(urlparse(url).path) or "File"
                self.notifier.notify_started(filename, url)
        except Exception as e:
            print(f"[Clipboard] Error adding download: {e}")
