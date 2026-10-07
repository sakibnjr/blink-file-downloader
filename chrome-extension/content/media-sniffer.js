// Blink Media Sniffer - In-Page Video Grabber
(function () {
  'use strict';

  const ATTACHED_ATTR = 'data-blink-grabber-attached';

  function getMediaUrl(mediaEl) {
    if (mediaEl.currentSrc && (mediaEl.currentSrc.startsWith('http://') || mediaEl.currentSrc.startsWith('https://'))) {
      return mediaEl.currentSrc;
    }
    if (mediaEl.src && (mediaEl.src.startsWith('http://') || mediaEl.src.startsWith('https://'))) {
      return mediaEl.src;
    }

    // Check <source> children
    const sources = mediaEl.querySelectorAll('source');
    for (const source of sources) {
      const src = source.src || source.getAttribute('src');
      if (src && (src.startsWith('http://') || src.startsWith('https://'))) {
        return src;
      }
    }

    return null;
  }

  function attachGrabber(mediaEl) {
    if (mediaEl.hasAttribute(ATTACHED_ATTR)) return;

    // Small or hidden elements don't get a button
    const rect = mediaEl.getBoundingClientRect();
    if (rect.width < 140 || rect.height < 90) return;

    const mediaUrl = getMediaUrl(mediaEl);
    if (!mediaUrl) {
      // Listen for when video metadata or source loads
      const onSourceLoaded = () => {
        if (getMediaUrl(mediaEl)) {
          mediaEl.removeEventListener('loadeddata', onSourceLoaded);
          mediaEl.removeEventListener('play', onSourceLoaded);
          attachGrabber(mediaEl);
        }
      };
      mediaEl.addEventListener('loadeddata', onSourceLoaded, { once: true });
      mediaEl.addEventListener('play', onSourceLoaded, { once: true });
      return;
    }

    mediaEl.setAttribute(ATTACHED_ATTR, 'true');

    // Find suitable parent to anchor button
    let container = mediaEl.parentElement;
    if (!container) return;

    // Ensure parent has position relative or absolute
    const computedStyle = window.getComputedStyle(container);
    if (computedStyle.position === 'static') {
      container.style.position = 'relative';
    }

    // Create floating grabber button
    const btn = document.createElement('div');
    btn.className = 'blink-video-grabber-btn';
    btn.title = `Download with Blink ⚡ (${mediaUrl})`;

    const isAudio = mediaEl.tagName.toLowerCase() === 'audio';
    const labelText = isAudio ? 'Download Audio' : 'Download Video';

    btn.innerHTML = `
      <span class="blink-video-grabber-icon">⚡</span>
      <span class="blink-video-grabber-text">${labelText}</span>
      <span class="blink-video-grabber-dismiss" title="Dismiss">✕</span>
    `;

    // Click handler for download
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      e.preventDefault();

      if (e.target.classList.contains('blink-video-grabber-dismiss')) {
        btn.remove();
        return;
      }

      const activeUrl = getMediaUrl(mediaEl) || mediaUrl;
      const title = document.title || 'Video';

      // Send to background service worker
      chrome.runtime.sendMessage({
        action: 'download_media',
        url: activeUrl,
        title: title
      }, (response) => {
        const textSpan = btn.querySelector('.blink-video-grabber-text');
        if (response && response.success) {
          btn.classList.add('blink-grabber-success');
          if (textSpan) textSpan.textContent = '✓ Queued in Blink!';
        } else {
          if (textSpan) textSpan.textContent = '⚠️ Check Blink App';
        }

        setTimeout(() => {
          btn.classList.remove('blink-grabber-success');
          if (textSpan) textSpan.textContent = labelText;
        }, 3000);
      });
    });

    container.appendChild(btn);
  }

  function scanMedia() {
    const videos = document.querySelectorAll('video');
    const audios = document.querySelectorAll('audio');

    videos.forEach(attachGrabber);
    audios.forEach(attachGrabber);
  }

  // Initial scan
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scanMedia);
  } else {
    scanMedia();
  }

  // Periodic scan & MutationObserver for dynamic players
  const observer = new MutationObserver(() => {
    scanMedia();
  });

  observer.observe(document.body || document.documentElement, {
    childList: true,
    subtree: true
  });

  // Re-scan periodically on scroll / play
  document.addEventListener('play', (e) => {
    if (e.target && (e.target.tagName === 'VIDEO' || e.target.tagName === 'AUDIO')) {
      attachGrabber(e.target);
    }
  }, true);
})();
