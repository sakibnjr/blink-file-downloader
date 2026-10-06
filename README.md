# Blink Downloader ⚡

A high-speed, multi-threaded file downloader for **Fedora Linux** built with **Python 3, GTK 4, and Libadwaita**, powered by the **aria2c** acceleration engine and integrated seamlessly with **Google Chrome**.

![Blink Downloader](app/icons/icon-128.png)

---

## Features

- 🚀 **Multi-Connection Acceleration**: Splits downloads into up to 16–32 parallel streams per file for maximum bandwidth utilization.
- 🎨 **Native Fedora / GNOME Experience**: Built with GTK 4 and Libadwaita following modern GNOME design patterns (responsive cards, rounded squircle styling, dark/light theme adaptation).
- 🌐 **Seamless Google Chrome Companion**:
  - **Right-Click Context Menus**: Download any link, media (image, audio, video), or highlighted text with `"Download with Blink ⚡"`.
  - **Extension Popup**: Real-time download progress, current transfer speed, pause/resume controls, and one-click `"Download Current Tab"`.
  - **On-Page Toasts**: Sleek floating notifications right inside Chrome when a download is queued.
  - **Chrome Native Messaging**: Native host bridge registered in `~/.config/google-chrome/NativeMessagingHosts/`.
- ⏯ **Full Transfer Control**: Pause, resume, cancel, and clear completed downloads.
- 🔔 **Desktop Notifications**: Native Fedora notifications on download completion with direct `"Open File"` and `"Show in Folder"` buttons.
- 🗂 **Folder Management**: Automatically places downloads in `~/Downloads` (customizable via Preferences).
- 🔍 **Real-Time Filtering & Search**: Instant search by file name or URL, plus quick tabs for *All*, *Downloading*, *Completed*, and *Paused*.

---

## Architecture Overview

```
Google Chrome (Manifest V3)
 ├── Context Menu ("Download with Blink ⚡")
 ├── Extension Popup (Active status, speeds, quick add)
 └── Content Script (On-page toast feedback)
       │
       │ HTTP REST API (127.0.0.1:9632)
       │ & Native Messaging Host
       ▼
 Blink Desktop App (GTK 4 / Libadwaita)
 ├── App Window (Adw.ApplicationWindow, live speed badge, filters)
 ├── Preferences (Bandwidth limits, parallel connections, download dir)
 ├── Desktop Notifications (libnotify / Notify)
 └── Aria2 Engine Supervisor (JSON-RPC on 127.0.0.1:6800)
       ▼
   Aria2c (16-thread multi-segmented acceleration engine)
```

---

## Quick Start Guide

### 1. Launch Blink on Fedora
You can start Blink immediately using the runner script:
```bash
./run.sh
```
Or launch it from your GNOME Application Menu (`Blink Downloader`).

### 2. Set Up the Google Chrome Extension
Run the automated installation helper:
```bash
./install-extension.sh
```
This script automatically:
1. Registers the Native Messaging Host manifest in `~/.config/google-chrome/NativeMessagingHosts/com.blink.downloader.json`.
2. Installs the desktop application launcher to `~/.local/share/applications/blink.desktop`.
3. Opens Google Chrome to `chrome://extensions`.

Then follow these 3 quick steps in Google Chrome:
1. Turn **ON** the **"Developer mode"** toggle in the top-right corner of `chrome://extensions`.
2. Click the **"Load unpacked"** button in the top-left corner.
3. Select the `chrome-extension` folder located inside this project:
   ```
   /home/sakibnjr/Desktop/blink/chrome-extension
   ```

---

## How to Use with Google Chrome

1. **Right-Click Any Link**:
   Right-click any downloadable link, image, or video in Google Chrome and click:
   > **Download with Blink ⚡**
   A floating toast will appear on the webpage and the download will immediately start in Blink.

2. **Extension Popup**:
   Click the Blink icon in the Chrome extension bar:
   - Paste any URL or Magnet link to start downloading.
   - Click **"⚡ Download Current Tab URL"** to download the active page.
   - Monitor real-time download speeds and pause/resume active tasks.

3. **Command Line & Magnet Links**:
   You can also trigger downloads from terminal:
   ```bash
   ./run.sh "https://example.com/file.zip"
   ```

---

## Project Structure

```
blink/
├── app/
│   ├── main.py                # Main application entry point & lifecycle
│   ├── engine.py              # Aria2c process supervisor & JSON-RPC client
│   ├── server.py              # HTTP REST API server (127.0.0.1:9632)
│   ├── native_host.py         # Chrome Native Messaging Host script
│   ├── notifications.py       # Desktop notifications via libnotify
│   ├── ui/
│   │   ├── window.py          # Main Libadwaita window with list & filters
│   │   ├── download_row.py    # Custom GTK4 download card row widget
│   │   ├── add_dialog.py      # Modal dialog to add downloads manually
│   │   └── preferences.py     # Settings window (speed limits, connections)
│   └── icons/                 # Crisp app icons (16px to 512px)
├── chrome-extension/
│   ├── manifest.json          # Manifest V3 configuration
│   ├── background.js          # Service worker for context menus & badge
│   ├── popup/
│   │   ├── popup.html         # Modern glassmorphism popup UI
│   │   ├── popup.css          # Dark-mode styling
│   │   └── popup.js           # Live polling & control logic
│   └── icons/                 # Extension icons
├── install-extension.sh       # Setup script for Chrome native host & desktop entry
├── run.sh                     # Launcher script
├── blink.desktop              # GNOME desktop launcher
└── README.md                  # Documentation
```

---

## License

GPL-3.0
