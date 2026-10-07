// Blink Downloader - Chrome Extension Service Worker (Manifest V3)
const BLINK_API_BASE = 'http://127.0.0.1:9632';

// Set up context menus and defaults on extension installation
chrome.runtime.onInstalled.addListener(async () => {
  // Enable auto interception by default
  const { autoIntercept } = await chrome.storage.local.get('autoIntercept');
  if (autoIntercept === undefined) {
    await chrome.storage.local.set({ autoIntercept: true });
  }

  chrome.contextMenus.create({
    id: 'blink-download-link',
    title: 'Download with Blink ⚡',
    contexts: ['link']
  });

  chrome.contextMenus.create({
    id: 'blink-download-media',
    title: 'Download Media with Blink ⚡',
    contexts: ['image', 'video', 'audio']
  });

  chrome.contextMenus.create({
    id: 'blink-download-page',
    title: 'Download Current Page / Selection with Blink ⚡',
    contexts: ['selection', 'page']
  });
});

// Automatic Chrome Download Interception
chrome.downloads.onCreated.addListener(async (downloadItem) => {
  const { autoIntercept = true } = await chrome.storage.local.get('autoIntercept');
  if (!autoIntercept) return;

  const url = downloadItem.finalUrl || downloadItem.url;
  if (!url || url.startsWith('chrome:') || url.startsWith('chrome-extension:') || url.startsWith('blob:') || url.startsWith('data:')) {
    return;
  }

  // Check if Blink API server is running before cancelling Chrome's download
  try {
    const res = await fetch(`${BLINK_API_BASE}/api/status`, { cache: 'no-store' });
    if (!res.ok) return;
  } catch (err) {
    // Blink app is offline: let Chrome download normally
    return;
  }

  // Cancel and erase from Chrome's default download manager
  try {
    await chrome.downloads.cancel(downloadItem.id);
    await chrome.downloads.erase({ id: downloadItem.id });
  } catch (err) {
    console.warn('Could not cancel Chrome download:', err);
  }

  // Send download to Blink
  const result = await sendToBlink(url, downloadItem.referrer, downloadItem.filename);
  if (result.success) {
    await flashBadge('⚡', '#10b981');
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.id) {
      await showTabNotification(tab.id, `Intercepted & sent to Blink Downloader ⚡`, 'success');
    }
  }
});

// Helper: send download URL to Blink native app
async function sendToBlink(url, referrer, title) {
  try {
    const response = await fetch(`${BLINK_API_BASE}/api/download`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        url: url.trim(),
        referrer: referrer || '',
        title: title || ''
      })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `HTTP ${response.status}`);
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    console.error('Failed to send download to Blink:', error);
    return { success: false, error: error.message };
  }
}

// Helper: inject toast message into active tab
async function showTabNotification(tabId, message, type = 'success') {
  if (!tabId) return;
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      func: (msg, toastType) => {
        // Remove existing toast if any
        const existing = document.getElementById('blink-notification-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.id = 'blink-notification-toast';
        toast.style.position = 'fixed';
        toast.style.bottom = '24px';
        toast.style.right = '24px';
        toast.style.zIndex = '2147483647';
        toast.style.backgroundColor = toastType === 'success' ? '#1e293b' : '#7f1d1d';
        toast.style.color = '#ffffff';
        toast.style.padding = '14px 20px';
        toast.style.borderRadius = '12px';
        toast.style.boxShadow = '0 10px 30px rgba(0,0,0,0.4), 0 0 1px rgba(255,255,255,0.2)';
        toast.style.border = toastType === 'success' ? '1px solid rgba(59,130,246,0.5)' : '1px solid rgba(239,68,68,0.5)';
        toast.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        toast.style.fontSize = '14px';
        toast.style.fontWeight = '500';
        toast.style.display = 'flex';
        toast.style.alignItems = 'center';
        toast.style.gap = '10px';
        toast.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
        toast.style.transform = 'translateY(20px)';
        toast.style.opacity = '0';

        const icon = document.createElement('span');
        icon.style.fontSize = '18px';
        icon.textContent = toastType === 'success' ? '⚡' : '⚠️';

        const text = document.createElement('span');
        text.textContent = msg;

        toast.appendChild(icon);
        toast.appendChild(text);
        document.body.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
          toast.style.transform = 'translateY(0)';
          toast.style.opacity = '1';
        });

        // Remove after 3.5s
        setTimeout(() => {
          toast.style.transform = 'translateY(20px)';
          toast.style.opacity = '0';
          setTimeout(() => toast.remove(), 350);
        }, 3500);
      },
      args: [message, type]
    });
  } catch (err) {
    // Some tabs (e.g., chrome://, edge://, about:blank) don't allow scripting
    console.warn('Could not inject toast notification into tab:', err);
  }
}

// Flash extension badge
async function flashBadge(text, color = '#2563eb') {
  await chrome.action.setBadgeBackgroundColor({ color });
  await chrome.action.setBadgeText({ text });
  setTimeout(async () => {
    // Refresh badge with active downloads count or clear
    await updateBadgeStatus();
  }, 3000);
}

// Check Blink server status and update badge
async function updateBadgeStatus() {
  try {
    const res = await fetch(`${BLINK_API_BASE}/api/status`, { cache: 'no-store' });
    if (res.ok) {
      const data = await res.json();
      const activeCount = (data.active_downloads || []).length;
      if (activeCount > 0) {
        await chrome.action.setBadgeBackgroundColor({ color: '#2563eb' });
        await chrome.action.setBadgeText({ text: String(activeCount) });
      } else {
        await chrome.action.setBadgeText({ text: '' });
      }
    } else {
      await chrome.action.setBadgeText({ text: '' });
    }
  } catch {
    await chrome.action.setBadgeText({ text: '' });
  }
}

// Handle Context Menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  let downloadUrl = '';

  if (info.menuItemId === 'blink-download-link') {
    downloadUrl = info.linkUrl;
  } else if (info.menuItemId === 'blink-download-media') {
    downloadUrl = info.srcUrl;
  } else if (info.menuItemId === 'blink-download-page') {
    if (info.selectionText && (info.selectionText.startsWith('http://') || info.selectionText.startsWith('https://') || info.selectionText.startsWith('magnet:'))) {
      downloadUrl = info.selectionText.trim();
    } else {
      downloadUrl = info.pageUrl;
    }
  }

  if (!downloadUrl) return;

  const result = await sendToBlink(downloadUrl, tab?.url, tab?.title);
  if (result.success) {
    await flashBadge('✓', '#10b981');
    await showTabNotification(tab?.id, 'Sent to Blink Downloader!', 'success');
  } else {
    await flashBadge('!', '#ef4444');
    await showTabNotification(tab?.id, 'Cannot connect to Blink app. Is it running on Fedora?', 'error');
  }
});

// Periodic badge update alarm
chrome.alarms.create('check-blink-status', { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'check-blink-status') {
    updateBadgeStatus();
  }
});

// Handle messages from content scripts (like media sniffer)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'download_media') {
    (async () => {
      const result = await sendToBlink(request.url, sender.tab?.url, request.title);
      if (result.success) {
        await flashBadge('⚡', '#10b981');
        if (sender.tab?.id) {
          await showTabNotification(sender.tab.id, `Queued media in Blink: ${request.title || 'Video'}`, 'success');
        }
      }
      sendResponse(result);
    })();
    return true; // Keep channel open for async response
  }
});
