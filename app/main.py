#!/usr/bin/env python3
"""
Blink Downloader - Fedora Linux High-Speed File Downloader
Main entry point.
"""

import sys
import os
import signal
from pathlib import Path

# Ensure blink root is in Python module search path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib

from app.engine import DownloadEngine
from app.server import BlinkAPIServer
from app.notifications import NotificationManager
from app.config import config_manager
from app.ui.window import MainWindow


class BlinkApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.blink.downloader",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        )
        self.engine = None
        self.server = None
        self.notifier = None
        self.main_window = None
        self.is_held = False

    def do_startup(self):
        Adw.Application.do_startup(self)

        # Hold application so it remains active in background even when window is closed
        if not self.is_held:
            self.hold()
            self.is_held = True

        # Initialize Notification Manager
        self.notifier = NotificationManager("Blink Downloader")

        # Initialize and start Aria2c Engine
        self.engine = DownloadEngine(rpc_port=6800)
        engine_started = self.engine.start()
        if not engine_started:
            print("[Blink] Warning: Could not start aria2c backend daemon.")

        # Initialize and start HTTP API server for Google Chrome Extension
        self.server = BlinkAPIServer(
            engine=self.engine,
            notifier=self.notifier,
            host="127.0.0.1",
            port=9632,
            ui_callback=self._on_server_event
        )
        self.server.start()

    def _on_server_event(self, event, data):
        if event == "open_window":
            GLib.idle_add(self.activate)
        elif self.main_window and hasattr(self.main_window, "_on_server_event"):
            self.main_window._on_server_event(event, data)

    def do_activate(self):
        if not self.main_window:
            self.main_window = MainWindow(
                app=self,
                engine=self.engine,
                server=self.server,
                notifier=self.notifier
            )
        self.main_window.present()

    def do_command_line(self, command_line):
        args = command_line.get_arguments()
        self.activate()

        # If URL passed via CLI (e.g. blink https://...)
        if len(args) > 1:
            for arg in args[1:]:
                if arg.startswith("http://") or arg.startswith("https://") or arg.startswith("magnet:") or arg.startswith("ftp://"):
                    try:
                        self.engine.add_uri(arg)
                        if self.notifier:
                            self.notifier.notify_started(arg.split("/")[-1] or "file", arg)
                    except Exception as e:
                        print(f"[Blink] Error adding CLI download {arg}: {e}")

        return 0

    def quit_app(self):
        """Cleanly quits the application and daemon services."""
        print("[Blink] Explicit quit requested.")
        if self.main_window:
            self.main_window.destroy()
            self.main_window = None

        if self.is_held:
            self.release()
            self.is_held = False

        self.quit()

    def do_shutdown(self):
        print("[Blink] Shutting down Blink services...")
        if self.server:
            self.server.stop()
        if self.engine:
            self.engine.stop()
        Adw.Application.do_shutdown(self)


def main():
    # Handle CTRL+C cleanly
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = BlinkApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
