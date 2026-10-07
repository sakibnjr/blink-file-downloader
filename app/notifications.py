"""
Desktop Notification Manager for Blink Downloader
Integrates with Fedora GNOME desktop notification system.
"""

import os
import subprocess
try:
    import gi
    gi.require_version('Notify', '0.7')
    from gi.repository import Notify
    HAS_NOTIFY = True
except Exception:
    HAS_NOTIFY = False


class NotificationManager:
    def __init__(self, app_name="Blink Downloader"):
        self.app_name = app_name
        self.initialized = False
        if HAS_NOTIFY:
            try:
                Notify.init(self.app_name)
                self.initialized = True
            except Exception as e:
                print(f"[Notify] Failed to initialize libnotify: {e}")

    def notify_started(self, filename: str, url: str = ""):
        if not self.initialized:
            return
        try:
            body = f"Started downloading: {filename}"
            notif = Notify.Notification.new("Download Started ⚡", body, "emblem-downloads")
            notif.show()
        except Exception as e:
            print(f"[Notify] Error showing notification: {e}")

    def notify_completed(self, filename: str, filepath: str = ""):
        if not self.initialized:
            return
        try:
            body = f"Successfully downloaded {filename}"
            notif = Notify.Notification.new("Download Complete 🎉", body, "emblem-default")
            
            # Action: Open file or folder if available
            if filepath and os.path.exists(filepath):
                def _open_file_cb(n, action):
                    try:
                        subprocess.Popen(["xdg-open", filepath])
                    except Exception as err:
                        print(f"Failed to open file: {err}")

                try:
                    notif.add_action("open_file", "Open File", _open_file_cb)
                except Exception:
                    pass

            notif.show()
        except Exception as e:
            print(f"[Notify] Error showing completion notification: {e}")

    def notify_error(self, filename: str, error_msg: str = ""):
        if not self.initialized:
            return
        try:
            body = f"Failed to download {filename}: {error_msg or 'Unknown error'}"
            notif = Notify.Notification.new("Download Failed ⚠️", body, "dialog-error")
            notif.show()
        except Exception as e:
            print(f"[Notify] Error showing error notification: {e}")

    def notify_info(self, title: str, message: str):
        if not self.initialized:
            return
        try:
            notif = Notify.Notification.new(title, message, "dialog-information")
            notif.show()
        except Exception as e:
            print(f"[Notify] Error showing info notification: {e}")

    def notify_clipboard(self, url: str, filename: str, on_download_action=None):
        if not self.initialized:
            return
        try:
            body = f"{filename}\nClick to start multi-connection download."
            notif = Notify.Notification.new("Download Link Detected 📋", body, "emblem-downloads")

            if on_download_action:
                def _download_cb(n, action):
                    on_download_action(url)

                try:
                    notif.add_action("download_now", "Download ⚡", _download_cb)
                except Exception:
                    pass

            notif.show()
        except Exception as e:
            print(f"[Notify] Error showing clipboard notification: {e}")

