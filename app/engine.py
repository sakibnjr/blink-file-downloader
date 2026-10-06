"""
Download Engine for Blink
Manages aria2c daemon lifecycle and provides JSON-RPC interface.
"""

import os
import time
import json
import socket
import urllib.request
import subprocess
from pathlib import Path


class DownloadEngine:
    def __init__(self, rpc_port=6800, download_dir=None):
        self.rpc_port = rpc_port
        self.download_dir = download_dir or str(Path.home() / "Downloads")
        self.rpc_url = f"http://127.0.0.1:{self.rpc_port}/jsonrpc"
        self.process = None
        self.rpc_secret = None
        self._notified_completed = set()
        self._notified_failed = set()

        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)

    def is_port_in_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def start(self):
        """Starts aria2c daemon if not already running on port."""
        if self.is_port_in_use(self.rpc_port):
            print(f"[Engine] Port {self.rpc_port} already in use; assuming existing aria2c instance.")
            return True

        cmd = [
            "aria2c",
            "--enable-rpc=true",
            f"--rpc-listen-port={self.rpc_port}",
            "--rpc-listen-all=false",
            "--rpc-allow-origin-all=true",
            f"--dir={self.download_dir}",
            "--max-connection-per-server=16",
            "--split=16",
            "--min-split-size=1M",
            "--continue=true",
            "--auto-file-renaming=true",
            "--allow-overwrite=false",
            "--max-concurrent-downloads=5",
            "--file-allocation=none",
            "--summary-interval=0",
            "--quiet=true"
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Give aria2c a moment to bind port
            time.sleep(0.4)
            print(f"[Engine] aria2c daemon started on port {self.rpc_port} (PID: {self.process.pid})")
            return True
        except Exception as e:
            print(f"[Engine] Error starting aria2c: {e}")
            return False

    def stop(self):
        """Stops the aria2c daemon process if we started it."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
                print("[Engine] aria2c daemon stopped.")
            except Exception as e:
                print(f"[Engine] Error stopping aria2c: {e}")
            self.process = None

    def _call(self, method, params=None):
        """Executes a JSON-RPC call against aria2."""
        if params is None:
            params = []
        payload = {
            "jsonrpc": "2.0",
            "id": f"blink-{int(time.time()*1000)}",
            "method": f"aria2.{method}",
            "params": params
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.rpc_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if "error" in result:
                    raise RuntimeError(result["error"].get("message", "Aria2 RPC error"))
                return result.get("result")
        except Exception as e:
            # Re-raise with clean message
            raise RuntimeError(f"Aria2 RPC failed: {e}")

    def add_uri(self, uris, options=None):
        """Adds a new download URI (or list of URIs) with optional download options."""
        if isinstance(uris, str):
            uris = [uris]
        opts = {
            "dir": self.download_dir,
            "max-connection-per-server": "16",
            "split": "16"
        }
        if options:
            opts.update(options)

        return self._call("addUri", [uris, opts])

    def pause(self, gid):
        return self._call("pause", [gid])

    def unpause(self, gid):
        return self._call("unpause", [gid])

    def remove(self, gid):
        try:
            return self._call("remove", [gid])
        except Exception:
            # If already stopped/complete, remove download result
            try:
                return self._call("removeDownloadResult", [gid])
            except Exception:
                return None

    def tell_active(self):
        try:
            return self._call("tellActive") or []
        except Exception:
            return []

    def tell_waiting(self, offset=0, num=100):
        try:
            return self._call("tellWaiting", [offset, num]) or []
        except Exception:
            return []

    def tell_stopped(self, offset=0, num=100):
        try:
            return self._call("tellStopped", [offset, num]) or []
        except Exception:
            return []

    def tell_status(self, gid):
        try:
            return self._call("tellStatus", [gid])
        except Exception:
            return None

    def get_global_stat(self):
        try:
            return self._call("getGlobalStat") or {}
        except Exception:
            return {}

    def get_all_downloads(self):
        """Retrieves combined list of active, waiting, and stopped downloads."""
        active = self.tell_active()
        waiting = self.tell_waiting(0, 100)
        stopped = self.tell_stopped(0, 100)
        
        for item in active:
            item["_category"] = "active"
        for item in waiting:
            item["_category"] = "waiting"
        for item in stopped:
            item["_category"] = "stopped"

        return active + waiting + stopped

    def purge_completed(self):
        try:
            return self._call("purgeDownloadResult")
        except Exception:
            return None
