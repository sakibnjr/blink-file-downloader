"""
Main Window for Blink Downloader
Built with Python 3, GTK 4, and Libadwaita for Fedora Linux.
"""

import os
import subprocess
from urllib.parse import urlparse
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gdk, Gio, GLib

from app.ui.download_row import DownloadRow, format_bytes, format_speed
from app.ui.add_dialog import AddDownloadDialog
from app.ui.preferences import PreferencesWindow

CSS_STYLES = """
/* Blink Downloader Custom Styling */
.download-row {
    background: alpha(@theme_base_color, 0.4);
    border: 1px solid alpha(@borders, 0.5);
    border-radius: 12px;
    margin: 4px 8px;
    transition: all 200ms ease-in-out;
}

.download-row:hover {
    background: alpha(@theme_selected_bg_color, 0.08);
    border-color: alpha(@theme_selected_bg_color, 0.3);
}

.status-pill {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 9999px;
    border: 1px solid transparent;
}

.status-active {
    background: alpha(#3b82f6, 0.15);
    color: #60a5fa;
    border-color: alpha(#3b82f6, 0.3);
}

.status-complete {
    background: alpha(#10b981, 0.15);
    color: #34d399;
    border-color: alpha(#10b981, 0.3);
}

.status-paused {
    background: alpha(#f59e0b, 0.15);
    color: #fbbf24;
    border-color: alpha(#f59e0b, 0.3);
}

.status-error {
    background: alpha(#ef4444, 0.15);
    color: #f87171;
    border-color: alpha(#ef4444, 0.3);
}

.speed-highlight {
    font-weight: 700;
    color: #38bdf8;
}

.speed-badge {
    background: alpha(#2563eb, 0.18);
    color: #60a5fa;
    font-weight: 700;
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 14px;
    border: 1px solid alpha(#3b82f6, 0.3);
}

.speed-badge.inactive {
    background: alpha(@theme_fg_color, 0.06);
    color: alpha(@theme_fg_color, 0.5);
    border-color: transparent;
}

.bottom-status-bar {
    background: alpha(@theme_base_color, 0.6);
    border-top: 1px solid alpha(@borders, 0.6);
    padding: 6px 14px;
}
"""


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app, engine, server, notifier):
        super().__init__(application=app)
        self.engine = engine
        self.server = server
        self.notifier = notifier

        self.set_title("Blink")
        self.set_default_size(920, 640)
        self.set_icon_name("folder-download-symbolic")

        # Map of gid -> DownloadRow
        self.row_widgets = {}
        # Track known states to trigger completion notifications
        self.last_known_status = {}
        self.current_filter = "all"
        self.search_query = ""

        # Load custom CSS
        self._apply_css()

        # Connect server callback to refresh immediately on download added
        if self.server:
            self.server.ui_callback = self._on_server_event

        # Main layout container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header Bar
        header_bar = self._build_header_bar()
        main_box.append(header_bar)

        # Toolbar / Filter & Search Bar
        toolbar = self._build_toolbar()
        main_box.append(toolbar)

        # Content Area (Stack: Empty Page vs List View)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_vexpand(True)

        # Empty State
        empty_page = self._build_empty_page()
        self.stack.add_named(empty_page, "empty")

        # Downloads List Page
        list_page = self._build_list_page()
        self.stack.add_named(list_page, "list")

        main_box.append(self.stack)

        # Bottom Status Bar
        status_bar = self._build_bottom_bar()
        main_box.append(status_bar)

        # Setup 1-second polling timer
        GLib.timeout_add(1000, self._poll_engine)

        # Initial poll
        self._poll_engine()

    def _apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS_STYLES)
        disp = Gdk.Display.get_default()
        if disp:
            Gtk.StyleContext.add_provider_for_display(
                disp, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _build_header_bar(self):
        header = Adw.HeaderBar()

        # Title
        title_widget = Adw.WindowTitle(
            title="Blink Downloader",
            subtitle="Multi-connection Accelerator for Fedora"
        )
        header.set_title_widget(title_widget)

        # Add Download Button (Primary / Suggested)
        add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        add_btn.set_tooltip_text("Add New Download (Ctrl+N)")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", lambda b: self._open_add_dialog())
        header.pack_start(add_btn)

        # Clear Completed Button
        clear_btn = Gtk.Button.new_from_icon_name("edit-clear-all-symbolic")
        clear_btn.set_tooltip_text("Clear Completed Downloads")
        clear_btn.add_css_class("flat")
        clear_btn.connect("clicked", self._on_clear_completed)
        header.pack_start(clear_btn)

        # Speed Badge Pill
        self.speed_badge = Gtk.Label(label="⚡ 0 KB/s")
        self.speed_badge.add_css_class("speed-badge")
        self.speed_badge.add_css_class("inactive")
        header.pack_end(self.speed_badge)

        # Preferences Button
        prefs_btn = Gtk.Button.new_from_icon_name("preferences-system-symbolic")
        prefs_btn.set_tooltip_text("Preferences")
        prefs_btn.add_css_class("flat")
        prefs_btn.connect("clicked", lambda b: self._open_preferences())
        header.pack_end(prefs_btn)

        # Menu Button
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_tooltip_text("Main Menu")

        menu = Gio.Menu()
        menu.append("Open Downloads Folder", "win.open_downloads")
        menu.append("Chrome Extension Setup", "win.chrome_setup")
        menu.append("About Blink", "win.about")
        menu_btn.set_menu_model(menu)

        self._setup_actions()
        header.pack_end(menu_btn)

        return header

    def _setup_actions(self):
        open_dl_action = Gio.SimpleAction.new("open_downloads", None)
        open_dl_action.connect("activate", lambda a, p: self._open_downloads_folder())
        self.add_action(open_dl_action)

        chrome_action = Gio.SimpleAction.new("chrome_setup", None)
        chrome_action.connect("activate", lambda a, p: self._open_preferences())
        self.add_action(chrome_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", lambda a, p: self._show_about_dialog())
        self.add_action(about_action)

    def _build_toolbar(self):
        toolbar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toolbar_box.set_margin_top(8)
        toolbar_box.set_margin_bottom(8)
        toolbar_box.set_margin_start(14)
        toolbar_box.set_margin_end(14)

        # Filter Segmented Buttons
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        filter_box.add_css_class("linked")

        self.btn_all = Gtk.ToggleButton(label="All (0)")
        self.btn_all.set_active(True)
        self.btn_all.connect("toggled", lambda b: self._set_filter("all", b))
        filter_box.append(self.btn_all)

        self.btn_downloading = Gtk.ToggleButton(label="Downloading (0)")
        self.btn_downloading.connect("toggled", lambda b: self._set_filter("active", b))
        filter_box.append(self.btn_downloading)

        self.btn_completed = Gtk.ToggleButton(label="Completed (0)")
        self.btn_completed.connect("toggled", lambda b: self._set_filter("complete", b))
        filter_box.append(self.btn_completed)

        self.btn_paused = Gtk.ToggleButton(label="Paused (0)")
        self.btn_paused.connect("toggled", lambda b: self._set_filter("paused", b))
        filter_box.append(self.btn_paused)

        toolbar_box.append(filter_box)

        # Search Entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Filter downloads by name or link...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        toolbar_box.append(self.search_entry)

        return toolbar_box

    def _build_empty_page(self):
        status_page = Adw.StatusPage()
        status_page.set_icon_name("folder-download-symbolic")
        status_page.set_title("No Downloads")
        status_page.set_description(
            "Ready to accelerate your downloads on Fedora.\n"
            "Right-click any link or media in Google Chrome to download instantly,\n"
            "or click 'Add Download' to paste a URL."
        )

        add_btn = Gtk.Button(label="Add Download URL ⚡")
        add_btn.set_halign(Gtk.Align.CENTER)
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("pill")
        add_btn.connect("clicked", lambda b: self._open_add_dialog())
        status_page.set_child(add_btn)

        return status_page

    def _build_list_page(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_margin_start(10)
        self.list_box.set_margin_end(10)
        self.list_box.set_margin_bottom(10)

        # Custom filter func for ListBox
        self.list_box.set_filter_func(self._list_filter_func)

        scrolled.set_child(self.list_box)
        return scrolled

    def _build_bottom_bar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.add_css_class("bottom-status-bar")

        # Chrome API Status
        chrome_status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dot = Gtk.Label(label="●")
        dot.add_css_class("speed-highlight")
        chrome_status_box.append(dot)

        self.chrome_status_label = Gtk.Label(label="Chrome Companion API: 127.0.0.1:9632 (Active)")
        self.chrome_status_label.add_css_class("caption")
        self.chrome_status_label.add_css_class("dim-label")
        chrome_status_box.append(self.chrome_status_label)
        box.append(chrome_status_box)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        box.append(spacer)

        # Total Info
        self.global_info_label = Gtk.Label(label="0 Downloads | 0 KB/s")
        self.global_info_label.add_css_class("caption")
        self.global_info_label.add_css_class("dim-label")
        box.append(self.global_info_label)

        return box

    def _set_filter(self, filter_name, button):
        if not button.get_active():
            return
        self.current_filter = filter_name

        # Deactivate other filter buttons
        for name, btn in [
            ("all", self.btn_all),
            ("active", self.btn_downloading),
            ("complete", self.btn_completed),
            ("paused", self.btn_paused)
        ]:
            if name != filter_name:
                btn.set_active(False)

        self.list_box.invalidate_filter()

    def _on_search_changed(self, entry):
        self.search_query = entry.get_text().lower().strip()
        self.list_box.invalidate_filter()

    def _list_filter_func(self, row):
        if not isinstance(row, DownloadRow):
            return True

        status = row.data.get("status", "")

        # Category filter
        if self.current_filter == "active" and status != "active":
            return False
        if self.current_filter == "complete" and status != "complete":
            return False
        if self.current_filter == "paused" and status not in ("paused", "waiting"):
            return False

        # Search query filter
        if self.search_query:
            filename = (row.filename or "").lower()
            url = (row.url_label.get_text() or "").lower()
            if self.search_query not in filename and self.search_query not in url:
                return False

        return True

    def _poll_engine(self):
        try:
            downloads = self.engine.get_all_downloads()
            stats = self.engine.get_global_stat()

            global_speed = int(stats.get("downloadSpeed", 0))

            # Update Header Speed Badge
            if global_speed > 0:
                self.speed_badge.set_text(f"⚡ {format_speed(global_speed)}")
                self.speed_badge.remove_css_class("inactive")
            else:
                self.speed_badge.set_text("⚡ 0 KB/s")
                self.speed_badge.add_css_class("inactive")

            # Update count badges
            total_count = len(downloads)
            active_count = sum(1 for d in downloads if d.get("status") == "active")
            completed_count = sum(1 for d in downloads if d.get("status") == "complete")
            paused_count = sum(1 for d in downloads if d.get("status") in ("paused", "waiting"))

            self.btn_all.set_label(f"All ({total_count})")
            self.btn_downloading.set_label(f"Downloading ({active_count})")
            self.btn_completed.set_label(f"Completed ({completed_count})")
            self.btn_paused.set_label(f"Paused ({paused_count})")

            self.global_info_label.set_text(
                f"Active: {active_count} | Total Speed: {format_speed(global_speed)}"
            )

            # Switch between empty state and list view
            if total_count == 0:
                self.stack.set_visible_child_name("empty")
            else:
                self.stack.set_visible_child_name("list")

            # Update rows
            current_gids = set()
            for dl in downloads:
                gid = dl.get("gid")
                if not gid:
                    continue
                current_gids.add(gid)

                status = dl.get("status")
                prev_status = self.last_known_status.get(gid)

                # Detect download completion
                if prev_status == "active" and status == "complete":
                    files = dl.get("files", [])
                    filepath = files[0].get("path", "") if files else ""
                    filename = os.path.basename(filepath) if filepath else "File"
                    if self.notifier:
                        self.notifier.notify_completed(filename, filepath)

                # Detect download failure
                elif prev_status == "active" and status in ("error", "removed"):
                    err = dl.get("errorMessage", "")
                    if self.notifier:
                        self.notifier.notify_error(gid, err)

                self.last_known_status[gid] = status

                # Update or create row
                if gid in self.row_widgets:
                    self.row_widgets[gid].update_data(dl)
                else:
                    row = DownloadRow(self.engine, dl, on_action_cb=self._on_row_action)
                    self.row_widgets[gid] = row
                    self.list_box.append(row)

            # Remove rows for deleted downloads
            for gid in list(self.row_widgets.keys()):
                if gid not in current_gids:
                    row = self.row_widgets.pop(gid)
                    self.list_box.remove(row)
                    self.last_known_status.pop(gid, None)

            self.list_box.invalidate_filter()

        except Exception as e:
            # aria2c might still be initializing
            pass

        return True  # Keep GLib timer active

    def _on_server_event(self, event_type, data):
        # Called from HTTP server when Chrome extension triggers download
        GLib.idle_add(self._poll_engine)

    def _on_row_action(self):
        GLib.idle_add(self._poll_engine)

    def _open_add_dialog(self):
        dialog = AddDownloadDialog(self, self.engine, on_added_cb=lambda gid: self._poll_engine())
        dialog.present()

    def _open_preferences(self):
        prefs = PreferencesWindow(self, self.engine, self.server)
        prefs.present()

    def _on_clear_completed(self, btn):
        try:
            self.engine.purge_completed()
            self._poll_engine()
        except Exception as e:
            print(f"[Window] Error clearing completed: {e}")

    def _open_downloads_folder(self):
        try:
            subprocess.Popen(["xdg-open", self.engine.download_dir])
        except Exception as e:
            print(f"Failed to open downloads folder: {e}")

    def _show_about_dialog(self):
        about = Adw.AboutWindow(
            transient_for=self,
            application_name="Blink Downloader",
            application_icon="folder-download-symbolic",
            developer_name="Built for Fedora Linux",
            version="1.0.0",
            copyright="© 2026 Blink Contributors",
            website="https://github.com/sakibnjr/blink",
            issue_url="https://github.com/sakibnjr/blink/issues",
            license_type=Gtk.License.GPL_3_0
        )
        about.present()
