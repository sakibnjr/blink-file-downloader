// Blink Downloader - Popup Script
const BLINK_API_BASE = 'http://127.0.0.1:9632';

let pollTimer = null;

// Format bytes into human readable form
function formatBytes(bytes, decimals = 1) {
  if (!bytes || bytes === 0 || isNaN(bytes)) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

// Format download speed
function formatSpeed(bytesPerSec) {
  if (!bytesPerSec || bytesPerSec === 0 || isNaN(bytesPerSec)) return '0 KB/s';
  return `${formatBytes(bytesPerSec)}/s`;
}

// Check desktop app status and update UI
async function fetchStatus() {
  const statusBadge = document.getElementById('statusBadge');
  const statusText = document.getElementById('statusText');
  const statsBanner = document.getElementById('statsBanner');
  const totalSpeedEl = document.getElementById('totalSpeed');
  const activeCountEl = document.getElementById('activeCount');
  const downloadsList = document.getElementById('downloadsList');

  try {
    const response = await fetch(`${BLINK_API_BASE}/api/status`, {
      method: 'GET',
      mode: 'cors',
      cache: 'no-store'
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();

    // App is connected
    statusBadge.className = 'status-badge connected';
    statusText.textContent = 'Connected';

    const activeList = data.active_downloads || [];
    const globalSpeed = data.download_speed || 0;

    if (activeList.length > 0) {
      statsBanner.classList.remove('hidden');
      totalSpeedEl.textContent = formatSpeed(globalSpeed);
      activeCountEl.textContent = String(activeList.length);
      renderDownloadsList(activeList);
    } else {
      statsBanner.classList.add('hidden');
      downloadsList.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">⚡</span>
          <p>No active downloads in Blink</p>
          <small>Right-click any link in Chrome to download</small>
        </div>
      `;
    }
  } catch (err) {
    console.warn('Blink status check:', err);
    // App is offline
    statusBadge.className = 'status-badge disconnected';
    statusText.textContent = 'Offline';
    statsBanner.classList.add('hidden');
    downloadsList.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">⚠️</span>
        <p>Blink Desktop App is not running</p>
        <small>Please launch Blink on Fedora Linux</small>
      </div>
    `;
  }
}

// Render active downloads list
function renderDownloadsList(downloads) {
  const container = document.getElementById('downloadsList');
  container.innerHTML = '';

  downloads.forEach(dl => {
    const card = document.createElement('div');
    card.className = 'download-card';

    const completed = parseInt(dl.completedLength || 0, 10);
    const total = parseInt(dl.totalLength || 0, 10);
    const percent = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0;
    const speed = parseInt(dl.downloadSpeed || 0, 10);
    const isPaused = dl.status === 'paused';

    // Extract human-friendly name
    let filename = dl.name;
    if (!filename && dl.files && dl.files[0] && dl.files[0].path) {
      filename = dl.files[0].path.split('/').pop();
    }
    if (!filename) filename = dl.gid || 'Download';

    card.innerHTML = `
      <div class="card-top">
        <span class="file-name" title="${filename}">${filename}</span>
        <div class="card-controls">
          <button class="card-btn toggle-btn" data-gid="${dl.gid}" data-action="${isPaused ? 'resume' : 'pause'}">
            ${isPaused ? '▶' : '⏸'}
          </button>
          <button class="card-btn cancel-btn" data-gid="${dl.gid}" data-action="remove" title="Cancel">✕</button>
        </div>
      </div>
      <div class="card-progress-bar">
        <div class="progress-fill" style="width: ${percent}%;"></div>
      </div>
      <div class="card-meta">
        <span>${isPaused ? 'Paused' : formatSpeed(speed)} (${percent}%)</span>
        <span>${formatBytes(completed)} / ${total > 0 ? formatBytes(total) : 'Unknown'}</span>
      </div>
    `;

    // Attach button listeners
    const toggleBtn = card.querySelector('.toggle-btn');
    toggleBtn.addEventListener('click', async () => {
      const gid = toggleBtn.getAttribute('data-gid');
      const action = toggleBtn.getAttribute('data-action');
      await controlDownload(gid, action);
    });

    const cancelBtn = card.querySelector('.cancel-btn');
    cancelBtn.addEventListener('click', async () => {
      const gid = cancelBtn.getAttribute('data-gid');
      await controlDownload(gid, 'remove');
    });

    container.appendChild(card);
  });
}

// Send control commands (pause / resume / remove)
async function controlDownload(gid, action) {
  try {
    const endpoint = action === 'resume' ? 'unpause' : action;
    await fetch(`${BLINK_API_BASE}/api/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gid })
    });
    fetchStatus();
  } catch (err) {
    console.error(`Failed to ${action} download:`, err);
  }
}

// Add download trigger
async function triggerDownload(url) {
  if (!url || !url.trim()) return;

  const addBtn = document.getElementById('addBtn');
  const originalText = addBtn.innerHTML;
  addBtn.disabled = true;
  addBtn.textContent = 'Adding...';

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const response = await fetch(`${BLINK_API_BASE}/api/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: url.trim(),
        referrer: tab ? tab.url : '',
        title: tab ? tab.title : ''
      })
    });

    if (!response.ok) throw new Error('Server returned error');

    document.getElementById('urlInput').value = '';
    fetchStatus();
  } catch (err) {
    alert('Error connecting to Blink. Make sure Blink desktop app is running on Fedora!');
  } finally {
    addBtn.disabled = false;
    addBtn.innerHTML = originalText;
  }
}

// Initial setup
document.addEventListener('DOMContentLoaded', () => {
  const addBtn = document.getElementById('addBtn');
  const urlInput = document.getElementById('urlInput');
  const refreshBtn = document.getElementById('refreshBtn');
  const pasteTabBtn = document.getElementById('pasteTabBtn');

  // Trigger download on button or Enter
  addBtn.addEventListener('click', () => triggerDownload(urlInput.value));
  urlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') triggerDownload(urlInput.value);
  });

  // Manual refresh
  refreshBtn.addEventListener('click', () => fetchStatus());

  // Download active tab
  pasteTabBtn.addEventListener('click', async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url && !tab.url.startsWith('chrome://')) {
        urlInput.value = tab.url;
        triggerDownload(tab.url);
      }
    } catch (e) {
      console.warn('Could not read tab URL:', e);
    }
  });

  // Load and sync auto-intercept toggle
  const autoInterceptToggle = document.getElementById('autoInterceptToggle');
  const { autoIntercept } = await chrome.storage.local.get('autoIntercept');
  autoInterceptToggle.checked = autoIntercept !== false;
  autoInterceptToggle.addEventListener('change', async () => {
    await chrome.storage.local.set({ autoIntercept: autoInterceptToggle.checked });
  });

  // Initial fetch and polling
  fetchStatus();
  pollTimer = setInterval(fetchStatus, 1500);
});

window.addEventListener('unload', () => {
  if (pollTimer) clearInterval(pollTimer);
});
