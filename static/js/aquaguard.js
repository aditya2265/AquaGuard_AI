/**
 * AquaGuard AI — Core Utilities
 */

/* ─── CSRF token helper ─────────────────────────────────── */
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) return meta.getAttribute('content');
  const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
  return cookie ? cookie.trim().split('=')[1] : '';
}

function fetchWithCsrf(url, options = {}) {
  return fetch(url, {
    ...options,
    headers: {
      'X-CSRFToken': getCsrfToken(),
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    credentials: 'same-origin',
  });
}

/* ─── Notification badge ────────────────────────────────── */
function updateNotificationBadge() {
  fetch('/api/alerts/unread-count/', { credentials: 'same-origin' })
    .then(r => r.json())
    .then(data => {
      const count = data.unread_count || 0;
      document.querySelectorAll('.aq-notif-badge').forEach(el => {
        if (count > 0) {
          el.textContent = count > 99 ? '99+' : count;
          el.style.display = '';
        } else {
          el.style.display = 'none';
        }
      });
      // sidebar nav badge
      const navBadge = document.getElementById('alerts-nav-badge');
      if (navBadge) {
        navBadge.textContent = count > 0 ? count : '';
        navBadge.style.display = count > 0 ? '' : 'none';
      }
    })
    .catch(() => {});
}

/* ─── Bootstrap tooltip init ────────────────────────────── */
function initTooltips() {
  if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
      new bootstrap.Tooltip(el);
    });
  }
}

/* ─── Toast notifications ───────────────────────────────── */
function showToast(message, type = 'info') {
  let wrap = document.getElementById('aq-toast-container');
  if (!wrap) {
    wrap = document.createElement('div');
    wrap.id = 'aq-toast-container';
    wrap.className = 'aq-toast-wrap';
    document.body.appendChild(wrap);
  }

  const icons = { success: 'bi-check-circle-fill', error: 'bi-x-circle-fill', warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill' };
  const icon = icons[type] || icons.info;

  const toast = document.createElement('div');
  toast.className = `aq-toast ${type}`;
  toast.innerHTML = `<i class="bi ${icon}"></i><span>${message}</span>`;
  wrap.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

/* ─── Risk level badge HTML ─────────────────────────────── */
function formatRiskLevel(level) {
  if (!level) return '<span class="badge-risk badge-info">N/A</span>';
  const map = {
    'LOW':      'badge-low',
    'MODERATE': 'badge-moderate',
    'HIGH':     'badge-high',
    'CRITICAL': 'badge-critical',
  };
  const cls = map[level.toUpperCase()] || 'badge-info';
  return `<span class="badge-risk ${cls}"><span class="dot"></span>${level}</span>`;
}

/* ─── Number formatter ──────────────────────────────────── */
function formatNumber(n, decimals = 1) {
  if (n === null || n === undefined) return '—';
  const num = parseFloat(n);
  if (isNaN(num)) return '—';
  return num.toFixed(decimals);
}

/* ─── Relative time ─────────────────────────────────────── */
function timeAgo(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now - date) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/* ─── Sidebar toggle (mobile) ───────────────────────────── */
function initSidebar() {
  const toggle = document.getElementById('aq-sidebar-toggle');
  const sidebar = document.querySelector('.aq-sidebar');
  if (toggle && sidebar) {
    toggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
    document.addEventListener('click', (e) => {
      if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }
}

/* ─── Mark all alerts read ──────────────────────────────── */
function markAllAlertsRead() {
  fetchWithCsrf('/alerts/mark-read/', { method: 'POST' })
    .then(r => r.json())
    .then(() => {
      showToast('All alerts marked as read.', 'success');
      setTimeout(() => location.reload(), 800);
    })
    .catch(() => showToast('Failed to mark alerts.', 'error'));
}

function markAlertRead(pk) {
  fetchWithCsrf(`/alerts/${pk}/mark-read/`, { method: 'POST' })
    .then(r => r.json())
    .then(() => {
      const row = document.querySelector(`[data-alert-id="${pk}"]`);
      if (row) {
        row.classList.remove('unread');
        row.classList.add('read');
        const btn = row.querySelector('.btn-mark-read');
        if (btn) btn.remove();
      }
      updateNotificationBadge();
    })
    .catch(() => showToast('Failed to mark alert.', 'error'));
}

/* ─── Auto-init on DOMContentLoaded ─────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initTooltips();
  initSidebar();
  updateNotificationBadge();
  // refresh badge every 60 s
  setInterval(updateNotificationBadge, 60000);

  // Highlight active nav link
  const currentPath = window.location.pathname;
  document.querySelectorAll('.aq-nav-item').forEach(item => {
    const href = item.getAttribute('href');
    if (href && currentPath.startsWith(href) && href !== '/') {
      item.classList.add('active');
    }
  });
});
