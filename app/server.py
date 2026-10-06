"""
Blink Downloader - Local HTTP API Server
Bridges Google Chrome extension and other clients to Blink Engine.
Runs on 127.0.0.1:9632
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


class BlinkAPIHandler(BaseHTTPRequestHandler):
    engine = None
    notifier = None
    ui_callback = None

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def log_message(self, format, *args):
        # Silence default noisy access logs to terminal
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/api/status", "/status"):
            try:
                active = self.engine.tell_active() if self.engine else []
                stats = self.engine.get_global_stat() if self.engine else {}
                resp = {
                    "status": "online",
                    "app": "Blink Downloader",
                    "version": "1.0.0",
                    "active_downloads": active,
                    "download_speed": int(stats.get("downloadSpeed", 0)),
                    "upload_speed": int(stats.get("uploadSpeed", 0)),
                    "num_active": int(stats.get("numActive", 0)),
                    "num_waiting": int(stats.get("numWaiting", 0)),
                    "num_stopped": int(stats.get("numStopped", 0))
                }
                self._set_headers(200)
                self.wfile.write(json.dumps(resp).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        elif path == "/api/all":
            try:
                all_dl = self.engine.get_all_downloads() if self.engine else []
                self._set_headers(200)
                self.wfile.write(json.dumps({"downloads": all_dl}).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if path in ("/api/download", "/add"):
            url = payload.get("url", "").strip()
            if not url:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "No URL provided"}).encode("utf-8"))
                return

            try:
                options = {}
                if payload.get("referrer"):
                    options["referer"] = payload["referrer"]

                gid = self.engine.add_uri(url, options)
                
                # Extract filename preview for notification
                filename = url.split("?")[0].split("/")[-1] or "file"
                if self.notifier:
                    self.notifier.notify_started(filename, url)

                if self.ui_callback:
                    self.ui_callback("download_added", gid)

                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "gid": gid}).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif path in ("/api/pause", "/pause"):
            gid = payload.get("gid")
            if not gid:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Missing gid"}).encode("utf-8"))
                return
            try:
                res = self.engine.pause(gid)
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "result": res}).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif path in ("/api/unpause", "/unpause", "/api/resume", "/resume"):
            gid = payload.get("gid")
            if not gid:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Missing gid"}).encode("utf-8"))
                return
            try:
                res = self.engine.unpause(gid)
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "result": res}).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif path in ("/api/remove", "/remove", "/cancel"):
            gid = payload.get("gid")
            if not gid:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Missing gid"}).encode("utf-8"))
                return
            try:
                res = self.engine.remove(gid)
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "result": res}).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))


class BlinkAPIServer:
    def __init__(self, engine, notifier=None, host="127.0.0.1", port=9632, ui_callback=None):
        self.host = host
        self.port = port
        self.engine = engine
        self.notifier = notifier
        self.ui_callback = ui_callback
        self.httpd = None
        self.thread = None

    def start(self):
        BlinkAPIHandler.engine = self.engine
        BlinkAPIHandler.notifier = self.notifier
        BlinkAPIHandler.ui_callback = self.ui_callback

        try:
            self.httpd = HTTPServer((self.host, self.port), BlinkAPIHandler)
            self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.thread.start()
            print(f"[API Server] Listening on http://{self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[API Server] Failed to start on http://{self.host}:{self.port}: {e}")
            return False

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
            print("[API Server] Stopped.")
