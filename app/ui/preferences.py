"""
Preferences Window for Blink Downloader
"""

import os
import subprocess
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio
from app.config import config_manager


class PreferencesWindow(Adw.PreferencesWindow):
    def __init__(self, parent, engine, server):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title("Preferences")
        self.set_default_size(560, 480)

        self.engine = engine
        self.server = server

        # --- General Page ---
        general_page = Adw.PreferencesPage()
        general_page.set_title("General")
        general_page.set_icon_name("preferences-system-symbolic")

        # Download Directory Group
        dl_group = Adw.PreferencesGroup()
        dl_group.set_title("Downloads Storage")
        dl_group.set_description("Configure where downloaded files are saved on Fedora.")

        self.folder_row = Adw.ActionRow()
        self.folder_row.set_title("Default Download Directory")
        self.folder_row.set_subtitle(self.engine.download_dir)

        browse_btn = Gtk.Button.new_from_icon_name("folder-open-symbolic")
        browse_btn.set_valign(Gtk.Align.CENTER)
        browse_btn.set_tooltip_text("Select Directory")
        browse_btn.connect("clicked", self._on_choose_folder)
        self.folder_row.add_suffix(browse_btn)
        dl_group.add(self.folder_row)

        # Auto-Categorization Switch
        self.categorize_row = Adw.SwitchRow()
        self.categorize_row.set_title("Automatic File Categorization")
        self.categorize_row.set_subtitle("Automatically sort finished files into Videos, Music, Archives, Documents, Packages")
        self.categorize_row.set_active(config_manager.get("auto_categorize", True))
        self.categorize_row.connect("notify::active", lambda r, p: config_manager.set("auto_categorize", r.get_active()))
        dl_group.add(self.categorize_row)

        # Background Daemon Switch
        self.bg_row = Adw.SwitchRow()
        self.bg_row.set_title("Keep Running in Background")
        self.bg_row.set_subtitle("Closing the window minimizes to background so Chrome is always connected")
        self.bg_row.set_active(config_manager.get("run_in_background", True))
        self.bg_row.connect("notify::active", lambda r, p: config_manager.set("run_in_background", r.get_active()))
        dl_group.add(self.bg_row)

        # Smart Clipboard Detection Switch
        self.clip_row = Adw.SwitchRow()
        self.clip_row.set_title("Smart Clipboard Detection")
        self.clip_row.set_subtitle("Automatically prompt when a download URL or magnet link is copied")
        self.clip_row.set_active(config_manager.get("clipboard_detection", True))
        self.clip_row.connect("notify::active", lambda r, p: config_manager.set("clipboard_detection", r.get_active()))
        dl_group.add(self.clip_row)

        general_page.add(dl_group)

        # Acceleration Group
        engine_group = Adw.PreferencesGroup()
        engine_group.set_title("Engine Acceleration")
        engine_group.set_description("Tweak aria2c multi-segmented parallel connection parameters.")

        self.threads_row = Adw.SpinRow.new_with_range(1, 32, 1)
        self.threads_row.set_title("Connections Per Server")
        self.threads_row.set_subtitle("Parallel segments & connections (up to 32 split threads, max 16 per host)")
        self.threads_row.set_value(config_manager.get("connections_per_server", 16))
        self.threads_row.connect("changed", self._on_threads_changed)
        engine_group.add(self.threads_row)

        self.concurrent_row = Adw.SpinRow.new_with_range(1, 10, 1)
        self.concurrent_row.set_title("Maximum Active Downloads")
        self.concurrent_row.set_subtitle("Queue extra downloads if this limit is reached")
        self.concurrent_row.set_value(config_manager.get("max_concurrent", 5))
        self.concurrent_row.connect("changed", self._on_concurrent_changed)
        engine_group.add(self.concurrent_row)

        general_page.add(engine_group)
        self.add(general_page)

        # --- Chrome Integration Page ---
        chrome_page = Adw.PreferencesPage()
        chrome_page.set_title("Google Chrome")
        chrome_page.set_icon_name("web-browser-symbolic")

        status_group = Adw.PreferencesGroup()
        status_group.set_title("Extension Companion")
        status_group.set_description("Integrates right-click downloading directly with Google Chrome on Fedora.")

        server_row = Adw.ActionRow()
        server_row.set_title("Blink Extension API")
        server_row.set_subtitle("Listening on http://127.0.0.1:9632 (Ready)")
        status_icon = Gtk.Image.new_from_icon_name("emblem-default-symbolic")
        status_icon.add_css_class("accent")
        server_row.add_suffix(status_icon)
        status_group.add(server_row)

        how_row = Adw.ActionRow()
        how_row.set_title("Chrome Extension Location")
        ext_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "chrome-extension"))
        how_row.set_subtitle(ext_path)

        open_chrome_btn = Gtk.Button(label="Open Extensions in Chrome")
        open_chrome_btn.set_valign(Gtk.Align.CENTER)
        open_chrome_btn.add_css_class("suggested-action")
        open_chrome_btn.connect("clicked", self._open_chrome_extensions)
        how_row.add_suffix(open_chrome_btn)
        status_group.add(how_row)

        instructions_row = Adw.ActionRow()
        instructions_row.set_title("How to Load Extension in Chrome:")
        instructions_row.set_subtitle(
            "1. In Chrome, enable 'Developer mode' (top right)\n"
            "2. Click 'Load unpacked'\n"
            "3. Select the chrome-extension directory"
        )
        status_group.add(instructions_row)

        chrome_page.add(status_group)
        self.add(chrome_page)

        # --- Network Page ---
        net_page = Adw.PreferencesPage()
        net_page.set_title("Network")
        net_page.set_icon_name("network-wired-symbolic")

        limits_group = Adw.PreferencesGroup()
        limits_group.set_title("Bandwidth Limits")
        limits_group.set_description("Limit download and upload bandwidth usage (0 = unlimited).")

        self.max_down_row = Adw.SpinRow.new_with_range(0, 100000, 500)
        self.max_down_row.set_title("Max Download Speed (KB/s)")
        self.max_down_row.set_value(config_manager.get("max_download_limit", 0))
        self.max_down_row.connect("changed", self._on_speed_changed)
        limits_group.add(self.max_down_row)

        self.max_up_row = Adw.SpinRow.new_with_range(0, 50000, 200)
        self.max_up_row.set_title("Max Upload Speed (KB/s)")
        self.max_up_row.set_value(config_manager.get("max_upload_limit", 0))
        self.max_up_row.connect("changed", self._on_speed_changed)
        limits_group.add(self.max_up_row)

        net_page.add(limits_group)
        self.add(net_page)

    def _on_choose_folder(self, btn):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Default Download Directory")
        initial_folder = Gio.File.new_for_path(self.engine.download_dir)
        dialog.set_initial_folder(initial_folder)

        dialog.select_folder(self, None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                if path:
                    self.engine.download_dir = path
                    self.folder_row.set_subtitle(path)
                    config_manager.set("download_dir", path)
                    try:
                        self.engine.change_global_option({"dir": path})
                    except Exception:
                        pass
        except Exception as e:
            print(f"[Prefs] Folder selection failed: {e}")

    def _on_threads_changed(self, spin):
        val = int(spin.get_value())
        config_manager.set("connections_per_server", val)
        try:
            self.engine.change_global_option({
                "split": str(val),
                "max-connection-per-server": str(min(val, 16))
            })
        except Exception as e:
            print(f"[Prefs] Failed to set connections: {e}")

    def _on_concurrent_changed(self, spin):
        val = int(spin.get_value())
        config_manager.set("max_concurrent", val)
        try:
            self.engine.change_global_option({"max-concurrent-downloads": str(val)})
        except Exception as e:
            print(f"[Prefs] Failed to set max concurrent: {e}")

    def _on_speed_changed(self, spin):
        down = int(self.max_down_row.get_value())
        up = int(self.max_up_row.get_value())
        config_manager.set("max_download_limit", down)
        config_manager.set("max_upload_limit", up)
        try:
            opts = {
                "max-overall-download-limit": f"{down}K" if down > 0 else "0",
                "max-overall-upload-limit": f"{up}K" if up > 0 else "0"
            }
            self.engine.change_global_option(opts)
        except Exception as e:
            print(f"[Prefs] Failed to set speed limit: {e}")

    def _open_chrome_extensions(self, btn):
        try:
            subprocess.Popen(["google-chrome", "chrome://extensions"])
        except Exception:
            try:
                subprocess.Popen(["xdg-open", "chrome://extensions"])
            except Exception as e:
                print(f"Failed to open chrome: {e}")
