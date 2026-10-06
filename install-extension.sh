#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHROME_HOSTS_DIR="${HOME}/.config/google-chrome/NativeMessagingHosts"
CHROMIUM_HOSTS_DIR="${HOME}/.config/chromium/NativeMessagingHosts"
APP_DIR="${HOME}/.local/share/applications"

echo "========================================="
echo "  Blink Downloader - Fedora Setup Script"
echo "========================================="

# 1. Install Desktop Entry for GNOME / Fedora
mkdir -p "${APP_DIR}"
sed "s|/home/sakibnjr/Desktop/blink|${SCRIPT_DIR}|g" "${SCRIPT_DIR}/blink.desktop" > "${APP_DIR}/blink.desktop"
chmod +x "${APP_DIR}/blink.desktop"
echo "✓ Desktop launcher installed to ${APP_DIR}/blink.desktop"

# 2. Register Native Messaging Host
HOST_JSON='{
  "name": "com.blink.downloader",
  "description": "Blink Downloader Native Host for Google Chrome",
  "path": "'"${SCRIPT_DIR}"'/app/native_host.py",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://*/"
  ]
}'

mkdir -p "${CHROME_HOSTS_DIR}"
echo "${HOST_JSON}" > "${CHROME_HOSTS_DIR}/com.blink.downloader.json"
echo "✓ Native Messaging host registered for Google Chrome in ${CHROME_HOSTS_DIR}"

if [ -d "${HOME}/.config/chromium" ]; then
  mkdir -p "${CHROMIUM_HOSTS_DIR}"
  echo "${HOST_JSON}" > "${CHROMIUM_HOSTS_DIR}/com.blink.downloader.json"
  echo "✓ Native Messaging host registered for Chromium in ${CHROMIUM_HOSTS_DIR}"
fi

# Ensure native host is executable
chmod +x "${SCRIPT_DIR}/app/native_host.py"
chmod +x "${SCRIPT_DIR}/run.sh"

echo ""
echo "========================================="
echo "  Google Chrome Extension Setup"
echo "========================================="
echo "To enable the Blink extension in Chrome:"
echo " 1. Open Google Chrome and go to: chrome://extensions"
echo " 2. Toggle 'Developer mode' ON (top-right corner)"
echo " 3. Click 'Load unpacked' (top-left)"
echo " 4. Select the directory:"
echo "    ${SCRIPT_DIR}/chrome-extension"
echo ""
echo "Now you can right-click any link or media in Chrome and choose:"
echo "  'Download with Blink ⚡'"
echo "========================================="

# Prompt to open Chrome extensions page
if which google-chrome >/dev/null 2>&1; then
  echo "Opening Chrome Extensions page..."
  google-chrome "chrome://extensions" >/dev/null 2>&1 &
fi
