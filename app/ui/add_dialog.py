"""
Add Download Dialog for Blink
"""

import os
from pathlib import Path
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio


class AddDownloadDialog(Adw.Window):
    def __init__(self, parent, engine, on_added_cb=None):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title("Add New Download")
        self.set_default_size(480, 360)
        self.set_resizable(False)

        self.engine = engine
        self.on_added_cb = on_added_cb
        self.selected_dir = engine.download_dir

        # Main Layout
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(content_box)

        # Header Bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)

        add_btn = Gtk.Button(label="Download ⚡")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_download_clicked)
        header.pack_end(add_btn)

        content_box.append(header)

        # Content Form
        clamp = Adw.Clamp()
        clamp.set_maximum_size(450)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(16)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)

        pref_group = Adw.PreferencesGroup()
        pref_group.set_title("Download Details")
        pref_group.set_description("Enter the file URL or Magnet link to download with multi-connection acceleration.")

        # URL Entry Row
        self.url_row = Adw.EntryRow()
        self.url_row.set_title("Download URL / Link")
        pref_group.add(self.url_row)

        # Try to paste from clipboard if URL is present
        clipboard = self.get_display().get_clipboard()
        clipboard.read_text_async(None, self._on_clipboard_read)

        # Optional Custom Filename Row
        self.filename_row = Adw.EntryRow()
        self.filename_row.set_title("Save As (Optional filename)")
        pref_group.add(self.filename_row)

        # Folder Chooser Row
        self.folder_row = Adw.ActionRow()
        self.folder_row.set_title("Save Location")
        self.folder_row.set_subtitle(self.selected_dir)
        browse_btn = Gtk.Button.new_from_icon_name("folder-open-symbolic")
        browse_btn.set_valign(Gtk.Align.CENTER)
        browse_btn.set_tooltip_text("Choose Folder")
        browse_btn.connect("clicked", self._on_browse_folder)
        self.folder_row.add_suffix(browse_btn)
        pref_group.add(self.folder_row)

        # Connections Spin Row
        self.conn_row = Adw.SpinRow.new_with_range(1, 32, 1)
        self.conn_row.set_title("Acceleration Connections")
        self.conn_row.set_subtitle("Number of simultaneous parallel streams (recommended: 16)")
        self.conn_row.set_value(16)
        pref_group.add(self.conn_row)

        clamp.set_child(pref_group)
        content_box.append(clamp)

    def _on_clipboard_read(self, clipboard, result):
        try:
            text = clipboard.read_text_finish(result)
            if text and (text.startswith("http://") or text.startswith("https://") or text.startswith("magnet:") or text.startswith("ftp://")):
                self.url_row.set_text(text.strip())
        except Exception:
            pass

    def _on_browse_folder(self, btn):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Download Directory")
        initial_folder = Gio.File.new_for_path(self.selected_dir)
        dialog.set_initial_folder(initial_folder)

        dialog.select_folder(self, None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                if path:
                    self.selected_dir = path
                    self.folder_row.set_subtitle(path)
        except Exception as e:
            print(f"[AddDialog] Folder selection cancelled or failed: {e}")

    def _on_download_clicked(self, btn):
        url = self.url_row.get_text().strip()
        if not url:
            self.url_row.add_css_class("error")
            return

        options = {
            "dir": self.selected_dir,
            "max-connection-per-server": str(int(self.conn_row.get_value())),
            "split": str(int(self.conn_row.get_value()))
        }

        custom_name = self.filename_row.get_text().strip()
        if custom_name:
            options["out"] = custom_name

        try:
            gid = self.engine.add_uri(url, options)
            if self.on_added_cb:
                self.on_added_cb(gid)
            self.close()
        except Exception as e:
            alert = Adw.MessageDialog(
                transient_for=self,
                heading="Download Error",
                body=f"Failed to start download:\n{str(e)}"
            )
            alert.add_response("ok", "OK")
            alert.present()
