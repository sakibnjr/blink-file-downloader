"""
Custom GTK4 Download Row for Blink Downloader
"""

import os
import subprocess
from urllib.parse import urlparse
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Pango, GLib


def format_bytes(num_bytes, decimals=1):
    try:
        b = float(num_bytes)
    except (ValueError, TypeError):
        return "0 B"
    if b <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while b >= 1024.0 and i < len(units) - 1:
        b /= 1024.0
        i += 1
    return f"{b:.{decimals}f} {units[i]}"


def format_speed(num_bytes):
    try:
        b = float(num_bytes)
    except (ValueError, TypeError):
        return "0 KB/s"
    if b <= 0:
        return "0 KB/s"
    return f"{format_bytes(b)}/s"


def format_eta(remaining_bytes, speed_bytes):
    try:
        rem = float(remaining_bytes)
        spd = float(speed_bytes)
        if spd <= 0 or rem <= 0:
            return ""
        secs = int(rem / spd)
        if secs < 60:
            return f"{secs}s left"
        mins = secs // 60
        secs = secs % 60
        if mins < 60:
            return f"{mins}m {secs}s left"
        hours = mins // 60
        mins = mins % 60
        return f"{hours}h {mins}m left"
    except Exception:
        return ""


def get_icon_for_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv'):
        return 'video-x-generic-symbolic'
    if ext in ('.mp3', '.flac', '.wav', '.ogg', '.m4a', '.aac'):
        return 'audio-x-generic-symbolic'
    if ext in ('.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar'):
        return 'package-x-generic-symbolic'
    if ext in ('.iso', '.img'):
        return 'media-optical-symbolic'
    if ext in ('.pdf', '.epub', '.mobi'):
        return 'x-office-document-symbolic'
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp'):
        return 'image-x-generic-symbolic'
    if ext in ('.rpm', '.deb', '.flatpakref', '.AppImage'):
        return 'system-software-install-symbolic'
    return 'folder-download-symbolic'


class DownloadRow(Gtk.ListBoxRow):
    def __init__(self, engine, data, on_action_cb=None):
        super().__init__()
        self.engine = engine
        self.data = data
        self.gid = data.get("gid", "")
        self.on_action_cb = on_action_cb
        self.filepath = ""
        self.filename = ""

        self.set_activatable(False)
        self.set_selectable(False)
        self.add_css_class("download-row")

        # Outer Container
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        main_box.set_margin_start(14)
        main_box.set_margin_end(14)

        # File Icon
        self.icon_image = Gtk.Image.new_from_icon_name("folder-download-symbolic")
        self.icon_image.set_pixel_size(36)
        self.icon_image.add_css_class("accent-icon")
        main_box.append(self.icon_image)

        # Info Box (Center)
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        info_box.set_hexpand(True)

        # Header Line: Filename + Status Badge
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        self.title_label = Gtk.Label()
        self.title_label.set_halign(Gtk.Align.START)
        self.title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.title_label.set_hexpand(True)
        self.title_label.add_css_class("title-4")
        self.title_label.add_css_class("heading")
        header_box.append(self.title_label)

        self.status_badge = Gtk.Label()
        self.status_badge.add_css_class("status-pill")
        header_box.append(self.status_badge)
        info_box.append(header_box)

        # Subtitle / URL
        self.url_label = Gtk.Label()
        self.url_label.set_halign(Gtk.Align.START)
        self.url_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.url_label.add_css_class("dim-label")
        self.url_label.add_css_class("caption")
        info_box.append(self.url_label)

        # Progress Bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_hexpand(True)
        self.progress_bar.add_css_class("download-progress")
        info_box.append(self.progress_bar)

        # Stats Line: Speed, Progress sizes, Connections, ETA
        stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self.stats_label = Gtk.Label()
        self.stats_label.set_halign(Gtk.Align.START)
        self.stats_label.add_css_class("caption")
        self.stats_label.add_css_class("dim-label")
        stats_box.append(self.stats_label)

        self.speed_label = Gtk.Label()
        self.speed_label.set_halign(Gtk.Align.START)
        self.speed_label.add_css_class("caption")
        self.speed_label.add_css_class("speed-highlight")
        stats_box.append(self.speed_label)

        self.eta_label = Gtk.Label()
        self.eta_label.set_halign(Gtk.Align.START)
        self.eta_label.add_css_class("caption")
        self.eta_label.add_css_class("dim-label")
        stats_box.append(self.eta_label)

        info_box.append(stats_box)
        main_box.append(info_box)

        # Actions Box (Right side)
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions_box.set_valign(Gtk.Align.CENTER)

        # Pause / Resume Button
        self.toggle_btn = Gtk.Button.new_from_icon_name("media-playback-pause-symbolic")
        self.toggle_btn.set_tooltip_text("Pause Download")
        self.toggle_btn.add_css_class("flat")
        self.toggle_btn.add_css_class("circular")
        self.toggle_btn.connect("clicked", self._on_toggle_clicked)
        actions_box.append(self.toggle_btn)

        # Open File Button
        self.open_file_btn = Gtk.Button.new_from_icon_name("document-open-symbolic")
        self.open_file_btn.set_tooltip_text("Open File")
        self.open_file_btn.add_css_class("flat")
        self.open_file_btn.add_css_class("circular")
        self.open_file_btn.set_visible(False)
        self.open_file_btn.connect("clicked", self._on_open_file_clicked)
        actions_box.append(self.open_file_btn)

        # Show in Folder Button
        self.open_folder_btn = Gtk.Button.new_from_icon_name("folder-open-symbolic")
        self.open_folder_btn.set_tooltip_text("Show in Folder")
        self.open_folder_btn.add_css_class("flat")
        self.open_folder_btn.add_css_class("circular")
        self.open_folder_btn.connect("clicked", self._on_open_folder_clicked)
        actions_box.append(self.open_folder_btn)

        # Delete / Cancel Button
        self.delete_btn = Gtk.Button.new_from_icon_name("edit-delete-symbolic")
        self.delete_btn.set_tooltip_text("Cancel & Remove")
        self.delete_btn.add_css_class("flat")
        self.delete_btn.add_css_class("circular")
        self.delete_btn.connect("clicked", self._on_delete_clicked)
        actions_box.append(self.delete_btn)

        main_box.append(actions_box)
        self.set_child(main_box)

        # Update initial data
        self.update_data(data)

    def update_data(self, data):
        self.data = data
        status = data.get("status", "active")
        completed = int(data.get("completedLength", 0))
        total = int(data.get("totalLength", 0))
        speed = int(data.get("downloadSpeed", 0))
        connections = data.get("connections", "1")

        # Resolve filename and path
        files = data.get("files", [])
        raw_path = ""
        filename = ""
        uris = []
        if files:
            first_file = files[0]
            raw_path = first_file.get("path", "")
            uris = [u.get("uri", "") for u in first_file.get("uris", [])]
            if raw_path:
                filename = os.path.basename(raw_path)

        if not filename and uris:
            filename = os.path.basename(urlparse(uris[0]).path)
        if not filename:
            filename = data.get("name") or f"Download-{self.gid[:6]}"

        self.filename = filename
        self.filepath = raw_path

        self.title_label.set_text(self.filename)
        self.icon_image.set_from_icon_name(get_icon_for_file(self.filename))

        # URL label
        url_text = uris[0] if uris else ""
        if not url_text:
            url_text = f"GID: {self.gid}"
        self.url_label.set_text(url_text)

        # Progress calculation
        fraction = 0.0
        if total > 0:
            fraction = min(1.0, max(0.0, completed / total))
        self.progress_bar.set_fraction(fraction)

        # Stats strings
        if total > 0:
            size_str = f"{format_bytes(completed)} / {format_bytes(total)} ({int(fraction * 100)}%)"
        else:
            size_str = f"{format_bytes(completed)} downloaded"
        self.stats_label.set_text(size_str)

        # Status handling
        self.status_badge.remove_css_class("status-active")
        self.status_badge.remove_css_class("status-complete")
        self.status_badge.remove_css_class("status-paused")
        self.status_badge.remove_css_class("status-error")

        if status == "active":
            self.status_badge.set_text(f"⚡ Downloading ({connections} conns)")
            self.status_badge.add_css_class("status-active")
            self.speed_label.set_text(format_speed(speed))
            rem = max(0, total - completed)
            self.eta_label.set_text(format_eta(rem, speed))
            self.toggle_btn.set_icon_name("media-playback-pause-symbolic")
            self.toggle_btn.set_tooltip_text("Pause Download")
            self.toggle_btn.set_visible(True)
            self.open_file_btn.set_visible(False)

        elif status == "paused":
            self.status_badge.set_text("⏸ Paused")
            self.status_badge.add_css_class("status-paused")
            self.speed_label.set_text("0 KB/s")
            self.eta_label.set_text("")
            self.toggle_btn.set_icon_name("media-playback-start-symbolic")
            self.toggle_btn.set_tooltip_text("Resume Download")
            self.toggle_btn.set_visible(True)
            self.open_file_btn.set_visible(False)

        elif status == "complete":
            self.status_badge.set_text("✓ Completed")
            self.status_badge.add_css_class("status-complete")
            self.speed_label.set_text("")
            self.eta_label.set_text("")
            self.progress_bar.set_fraction(1.0)
            self.toggle_btn.set_visible(False)
            self.open_file_btn.set_visible(True)

        elif status in ("error", "removed"):
            err_msg = data.get("errorMessage", "Failed")
            self.status_badge.set_text(f"✕ {err_msg}")
            self.status_badge.add_css_class("status-error")
            self.speed_label.set_text("")
            self.eta_label.set_text("")
            self.toggle_btn.set_visible(False)
            self.open_file_btn.set_visible(False)

        elif status == "waiting":
            self.status_badge.set_text("⏳ Queued")
            self.status_badge.add_css_class("status-paused")
            self.speed_label.set_text("")
            self.eta_label.set_text("")
            self.toggle_btn.set_icon_name("media-playback-pause-symbolic")
            self.toggle_btn.set_visible(True)
            self.open_file_btn.set_visible(False)

    def _on_toggle_clicked(self, btn):
        status = self.data.get("status")
        if status == "active":
            try:
                self.engine.pause(self.gid)
            except Exception as e:
                print(f"[Row] Error pausing {self.gid}: {e}")
        elif status in ("paused", "waiting"):
            try:
                self.engine.unpause(self.gid)
            except Exception as e:
                print(f"[Row] Error resuming {self.gid}: {e}")
        if self.on_action_cb:
            self.on_action_cb()

    def _on_delete_clicked(self, btn):
        try:
            self.engine.remove(self.gid)
        except Exception as e:
            print(f"[Row] Error removing {self.gid}: {e}")
        if self.on_action_cb:
            self.on_action_cb()

    def _on_open_file_clicked(self, btn):
        if self.filepath and os.path.exists(self.filepath):
            try:
                subprocess.Popen(["xdg-open", self.filepath])
            except Exception as e:
                print(f"Failed to open file: {e}")

    def _on_open_folder_clicked(self, btn):
        target_dir = os.path.dirname(self.filepath) if self.filepath else self.engine.download_dir
        if not target_dir or not os.path.exists(target_dir):
            target_dir = self.engine.download_dir
        try:
            subprocess.Popen(["xdg-open", target_dir])
        except Exception as e:
            print(f"Failed to open folder: {e}")
