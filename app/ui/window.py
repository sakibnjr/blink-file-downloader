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
from app.config import config_manager, CATEGORIES, SPEED_PROFILES
from app.clipboard import ClipboardMonitor

CSS_STYLES = """
/* Blink Downloader - 2026 Liquid Glass Design System */

/* Window & View Styling */
window.background {
    background-color: #0b0f19;
}

.transparent-list {
    background: transparent;
}

.transparent-list > row {
    background: transparent;
    padding: 0;
    margin: 0;
    border: none;
    box-shadow: none;
}

.transparent-list > row:hover {
    background: transparent;
}

/* Liquid Glass Cards */
.download-row {
    background-color: rgba(22, 30, 49, 0.65);
    background-image: linear-gradient(135deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.75) 100%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    margin: 6px 10px;
    padding: 2px 4px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.12);
    transition: all 250ms cubic-bezier(0.16, 1, 0.3, 1);
}

.download-row:hover {
    background-color: rgba(30, 45, 72, 0.75);
    background-image: linear-gradient(135deg, rgba(38, 56, 88, 0.75) 0%, rgba(18, 28, 48, 0.85) 100%);
    border-color: rgba(56, 189, 248, 0.4);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.25), 0 0 20px rgba(56, 189, 248, 0.15);
}

/* File Icon Container */
.file-icon-box {
    background-color: rgba(56, 189, 248, 0.08);
    background-image: linear-gradient(135deg, rgba(56, 189, 248, 0.16) 0%, rgba(99, 102, 241, 0.08) 100%);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-radius: 14px;
    padding: 10px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 4px 12px rgba(0, 0, 0, 0.25);
}

/* Liquid Status Pills */
.status-pill {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.2px;
    padding: 3px 10px;
    border-radius: 9999px;
    border: 1px solid transparent;
}

.status-active {
    background-color: rgba(14, 165, 233, 0.16);
    color: #38bdf8;
    border-color: rgba(56, 189, 248, 0.4);
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.18);
}

.status-complete {
    background-color: rgba(16, 185, 129, 0.16);
    color: #34d399;
    border-color: rgba(52, 211, 153, 0.4);
    box-shadow: 0 0 12px rgba(52, 211, 153, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.18);
}

.status-paused {
    background-color: rgba(245, 158, 11, 0.16);
    color: #fbbf24;
    border-color: rgba(251, 191, 36, 0.4);
    box-shadow: 0 0 12px rgba(251, 191, 36, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

.status-error {
    background-color: rgba(239, 68, 68, 0.16);
    color: #f87171;
    border-color: rgba(248, 113, 113, 0.4);
}

/* Shimmer Progress Bar */
progressbar.download-progress {
    min-height: 8px;
    padding: 0;
}

progressbar.download-progress trough {
    min-height: 8px;
    border-radius: 9999px;
    background-color: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.5);
}

progressbar.download-progress progress {
    min-height: 8px;
    border-radius: 9999px;
    background-image: linear-gradient(to right, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%);
    border: none;
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.35);
}

/* Action Buttons in Rows */
.action-circle-btn {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 9999px;
    padding: 7px;
    color: #94a3b8;
    transition: all 200ms cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.action-circle-btn:hover {
    background-color: rgba(255, 255, 255, 0.14);
    border-color: rgba(255, 255, 255, 0.3);
    color: #ffffff;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35), 0 0 12px rgba(56, 189, 248, 0.3);
}

.action-circle-btn.delete-btn:hover {
    background-color: rgba(239, 68, 68, 0.2);
    border-color: rgba(248, 113, 113, 0.45);
    color: #fca5a5;
    box-shadow: 0 4px 14px rgba(239, 68, 68, 0.35);
}

/* Speed Highlight Text */
.speed-highlight {
    font-weight: 800;
    color: #38bdf8;
    letter-spacing: 0.2px;
}

/* Speed Badge in HeaderBar */
.speed-badge {
    background-color: rgba(14, 165, 233, 0.16);
    background-image: linear-gradient(135deg, rgba(14, 165, 233, 0.22) 0%, rgba(99, 102, 241, 0.2) 100%);
    color: #38bdf8;
    font-weight: 800;
    font-size: 12px;
    padding: 5px 12px;
    border-radius: 9999px;
    border: 1px solid rgba(56, 189, 248, 0.4);
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.18);
    transition: all 200ms ease;
}

.speed-badge.inactive {
    background-color: rgba(255, 255, 255, 0.04);
    background-image: none;
    color: rgba(255, 255, 255, 0.4);
    border-color: rgba(255, 255, 255, 0.08);
    box-shadow: none;
}

/* Speed Profile Switcher Pill */
.profile-pill-btn {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 9999px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 12px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
    transition: all 200ms ease;
}

.profile-pill-btn:hover {
    background-color: rgba(255, 255, 255, 0.1);
    border-color: rgba(56, 189, 248, 0.35);
}

/* Suggested Action Add Button */
.suggested-action-liquid {
    background-color: #0ea5e9;
    background-image: linear-gradient(135deg, #0ea5e9 0%, #3b82f6 100%);
    color: #ffffff;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 4px 14px rgba(14, 165, 233, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.35);
    transition: all 200ms ease;
}

.suggested-action-liquid:hover {
    background-image: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
    box-shadow: 0 6px 20px rgba(14, 165, 233, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

/* Filter Segmented Buttons */
.filter-group {
    background-color: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 12px;
    padding: 3px;
    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.3);
}

.filter-group button {
    border-radius: 9px;
    border: none;
    color: #94a3b8;
    font-weight: 600;
    font-size: 12px;
    padding: 5px 12px;
    background: transparent;
    transition: all 200ms ease;
}

.filter-group button:hover {
    color: #f1f5f9;
}

.filter-group button:checked {
    background-color: rgba(56, 189, 248, 0.18);
    background-image: linear-gradient(135deg, rgba(56, 189, 248, 0.25) 0%, rgba(99, 102, 241, 0.22) 100%);
    color: #ffffff;
    border: 1px solid rgba(56, 189, 248, 0.35);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

/* Bottom Status Bar */
.bottom-status-bar {
    background-color: rgba(15, 23, 42, 0.75);
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding: 8px 16px;
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
        self.category_filter = "all"
        self.search_query = ""
        self._shown_background_hint = False

        # Close-request: minimize to background if enabled
        self.connect("close-request", self._on_close_request)

        # Load custom CSS
        self._apply_css()

        # Clipboard Monitor for automatic link detection
        self.clipboard_monitor = ClipboardMonitor(
            engine=self.engine,
            notifier=self.notifier,
            on_link_detected=self._on_clipboard_link_detected
        )

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
        add_btn.add_css_class("suggested-action-liquid")
        add_btn.connect("clicked", lambda b: self._open_add_dialog())
        header.pack_start(add_btn)

        # Clear Completed Button
        clear_btn = Gtk.Button.new_from_icon_name("edit-clear-all-symbolic")
        clear_btn.set_tooltip_text("Clear Completed Downloads")
        clear_btn.add_css_class("flat")
        clear_btn.connect("clicked", self._on_clear_completed)
        header.pack_start(clear_btn)

        # Speed Profile Switcher Button
        self.profile_btn = Gtk.MenuButton()
        self.profile_btn.set_tooltip_text("Speed Profile (Bandwidth Throttler)")
        self.profile_btn.add_css_class("profile-pill-btn")

        profile_menu = Gio.Menu()
        profile_menu.append("Turbo 🚀 (Unlimited)", "win.profile_turbo")
        profile_menu.append("Balanced ⚖️ (3 MB/s)", "win.profile_balanced")
        profile_menu.append("Background 🌙 (500 KB/s)", "win.profile_background")
        self.profile_btn.set_menu_model(profile_menu)

        curr_pid = self.engine.get_speed_profile() if self.engine else "turbo"
        curr_name = SPEED_PROFILES.get(curr_pid, {}).get("name", "Turbo 🚀")
        self.profile_label = Gtk.Label(label=curr_name)
        self.profile_label.add_css_class("caption")
        self.profile_btn.set_child(self.profile_label)
        header.pack_end(self.profile_btn)

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
        menu.append("Open Categories Folders", "win.open_categories")
        menu.append("Chrome Extension Setup", "win.chrome_setup")
        menu.append("About Blink", "win.about")
        menu.append("Quit Blink (Ctrl+Q)", "win.quit")
        menu_btn.set_menu_model(menu)

        self._setup_actions()
        header.pack_end(menu_btn)

        return header

    def _setup_actions(self):
        # Speed profile actions
        for p_id in ("turbo", "balanced", "background"):
            act = Gio.SimpleAction.new(f"profile_{p_id}", None)
            act.connect("activate", lambda a, p, pid=p_id: self._set_speed_profile(pid))
            self.add_action(act)

        open_dl_action = Gio.SimpleAction.new("open_downloads", None)
        open_dl_action.connect("activate", lambda a, p: self._open_downloads_folder())
        self.add_action(open_dl_action)

        open_cat_action = Gio.SimpleAction.new("open_categories", None)
        open_cat_action.connect("activate", lambda a, p: self._open_categories_folder())
        self.add_action(open_cat_action)

        chrome_action = Gio.SimpleAction.new("chrome_setup", None)
        chrome_action.connect("activate", lambda a, p: self._open_preferences())
        self.add_action(chrome_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", lambda a, p: self._show_about_dialog())
        self.add_action(about_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda a, p: self.get_application().quit_app())
        self.add_action(quit_action)
        self.get_application().set_accels_for_action("win.quit", ["<Control>q"])

    def _build_toolbar(self):
        toolbar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toolbar_box.set_margin_top(8)
        toolbar_box.set_margin_bottom(8)
        toolbar_box.set_margin_start(14)
        toolbar_box.set_margin_end(14)

        # Filter Segmented Buttons (Status)
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        filter_box.add_css_class("filter-group")

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

        # Category Filter DropDown
        self.cat_model = Gtk.StringList.new(["All Categories", "Videos", "Music", "Archives", "Documents", "Packages"])
        self.cat_dropdown = Gtk.DropDown.new(self.cat_model, None)
        self.cat_dropdown.connect("notify::selected-item", self._on_category_changed)
        toolbar_box.append(self.cat_dropdown)

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
            "Ready to accelerate your downloads on Fedora.\\n"
            "Right-click any link or media in Google Chrome to download instantly,\\n"
            "or click 'Add Download' to paste a URL."
        )

        add_btn = Gtk.Button(label="Add Download URL ⚡")
        add_btn.set_halign(Gtk.Align.CENTER)
        add_btn.add_css_class("suggested-action-liquid")
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
        self.list_box.add_css_class("transparent-list")
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

    def _on_category_changed(self, dropdown, param):
        item = dropdown.get_selected_item()
        if item:
            val = item.get_string()
            self.category_filter = "all" if val == "All Categories" else val
            self.list_box.invalidate_filter()

    def _list_filter_func(self, row):
        if not isinstance(row, DownloadRow):
            return True

        status = row.data.get("status", "")

        # Status filter
        if self.current_filter == "active" and status != "active":
            return False
        if self.current_filter == "complete" and status != "complete":
            return False
        if self.current_filter == "paused" and status not in ("paused", "waiting"):
            return False

        # Category filter
        if self.category_filter != "all":
            allowed_exts = CATEGORIES.get(self.category_filter, set())
            fname = row.filename or ""
            ext = os.path.splitext(fname)[1].lower()
            if ext not in allowed_exts:
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
        # Called from HTTP server when Chrome extension triggers download or profile change
        if event_type == "profile_changed":
            GLib.idle_add(self._update_profile_ui, data)
        else:
            GLib.idle_add(self._poll_engine)

    def _set_speed_profile(self, profile_id):
        if self.engine:
            self.engine.set_speed_profile(profile_id)
        self._update_profile_ui(profile_id)

    def _update_profile_ui(self, profile_id):
        profile = SPEED_PROFILES.get(profile_id, {})
        name = profile.get("name", "Turbo 🚀")
        self.profile_label.set_text(name)

    def _on_clipboard_link_detected(self, url, filename):
        if self.is_visible():
            dialog = AddDownloadDialog(self, self.engine, on_added_cb=lambda gid: self._poll_engine())
            dialog.url_row.set_text(url)
            dialog.present()

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

    def _on_close_request(self, window):
        if config_manager.get("run_in_background", True):
            self.hide()
            if not self._shown_background_hint:
                self._shown_background_hint = True
                if self.notifier:
                    self.notifier.notify_info(
                        "Blink Running in Background ⚡",
                        "Blink will keep downloading and catching Chrome downloads. Press Ctrl+Q or use the menu to quit."
                    )
            return True
        self.get_application().quit_app()
        return False

    def _open_categories_folder(self):
        base_dir = self.engine.download_dir
        for cat in CATEGORIES.keys():
            os.makedirs(os.path.join(base_dir, cat), exist_ok=True)
        try:
            subprocess.Popen(["xdg-open", base_dir])
        except Exception as e:
            print(f"Failed to open category folders: {e}")

