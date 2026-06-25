/* ===== app.js — CoAutomate Frontend Logic ===== */

const API = '';  // Same origin; backend serves the frontend

// ─── Token Management ───────────────────────────────────────
const Auth = {
  getToken: () => localStorage.getItem('coa_token'),
  setToken: (t) => localStorage.setItem('coa_token', t),
  clear: () => { localStorage.removeItem('coa_token'); localStorage.removeItem('coa_user'); },
  getUser: () => JSON.parse(localStorage.getItem('coa_user') || 'null'),
  setUser: (u) => localStorage.setItem('coa_user', JSON.stringify(u)),
};

// ─── HTTP Client ────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const token = Auth.getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (options.body instanceof FormData) delete headers['Content-Type'];

  const res = await fetch(API + path, { ...options, headers });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

// ─── Toast Notifications ────────────────────────────────────
function toast(message, type = 'info', duration = 4000) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type]}</span><span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add('leaving');
    setTimeout(() => el.remove(), 350);
  }, duration);
}

// ─── Page Navigation ────────────────────────────────────────
function showPage(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const target = document.getElementById(pageId);
  if (target) target.classList.add('active');
}

function showDashboard() {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('dashboard-page').classList.add('active');
  loadDashboard();
}

// ─── Tab Navigation ─────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      const group = btn.closest('[data-tab-group]')?.dataset?.tabGroup
        || btn.dataset.tabGroup;
      const target = btn.dataset.tab;
      document.querySelectorAll(`[data-tab-group="${group}"] [data-tab]`)
        .forEach(b => b.classList.remove('active'));
      document.querySelectorAll(`[data-tab-content][data-tab-group="${group}"]`)
        .forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.querySelector(`[data-tab-content="${target}"][data-tab-group="${group}"]`)
        ?.classList.add('active');
    });
  });
}

// ─── Auth ────────────────────────────────────────────────────
document.getElementById('login-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const email    = document.getElementById('login-email').value;
  const password = document.getElementById('login-password').value;
  const btn      = document.getElementById('login-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader"></span> Signing in…';
  try {
    const form = new URLSearchParams({ username: email, password });
    const res  = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form.toString(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    Auth.setToken(data.access_token);
    Auth.setUser(data.user);
    toast('Welcome back, ' + data.user.full_name.split(' ')[0] + '!', 'success');
    showDashboard();
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Sign In';
  }
});

document.getElementById('register-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('register-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader"></span> Creating account…';
  try {
    const payload = {
      email:               document.getElementById('reg-email').value,
      password:            document.getElementById('reg-password').value,
      full_name:           document.getElementById('reg-fullname').value,
      department:          document.getElementById('reg-dept').value,
      college:             document.getElementById('reg-college').value,
      total_teaching_load: document.getElementById('reg-load').value,
      term_school_year:    document.getElementById('reg-term').value,
    };
    const data = await apiFetch('/api/auth/register', {
      method: 'POST', body: JSON.stringify(payload),
    });
    Auth.setToken(data.access_token);
    Auth.setUser(data.user);
    toast('Account created! Welcome, ' + data.user.full_name.split(' ')[0] + '!', 'success');
    showDashboard();
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Create Account';
  }
});

document.getElementById('go-register')?.addEventListener('click', (e) => {
  e.preventDefault();
  showPage('register-page');
});
document.getElementById('go-login')?.addEventListener('click', (e) => {
  e.preventDefault();
  showPage('login-page');
});
document.getElementById('logout-btn')?.addEventListener('click', () => {
  Auth.clear();
  showPage('login-page');
  toast('Signed out successfully.', 'info');
});

// ─── Dashboard ───────────────────────────────────────────────
async function loadDashboard() {
  try {
    const user = await apiFetch('/api/me');
    Auth.setUser(user);
    renderUserInfo(user);

    const reports = await apiFetch('/api/reports');
    renderReportsTable(reports);
    renderStats(reports);

    const smtpStatus = await apiFetch('/api/settings/smtp-status');
    renderSmtpStatus(smtpStatus);
  } catch (err) {
    toast('Error loading dashboard: ' + err.message, 'error');
    if (err.message.includes('401') || err.message.includes('credentials')) {
      Auth.clear();
      showPage('login-page');
    }
  }
}

function renderUserInfo(user) {
  const initials = user.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  document.getElementById('nav-user-name').textContent = user.full_name;
  document.getElementById('nav-user-initials').textContent = initials;

  // Populate profile form
  document.getElementById('pf-fullname').value = user.full_name;
  document.getElementById('pf-dept').value     = user.department;
  document.getElementById('pf-college').value  = user.college;
  document.getElementById('pf-load').value     = user.total_teaching_load;
  document.getElementById('pf-term').value     = user.term_school_year;

  // Load signature preview (must go through authenticated fetch)
  if (user.signature_filename) {
    loadSignaturePreview();
  }
}

async function loadSignaturePreview() {
  try {
    const token = Auth.getToken();
    const res = await fetch('/api/me/signature', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const preview = document.getElementById('sig-preview');
    if (preview._blobUrl) URL.revokeObjectURL(preview._blobUrl);
    preview._blobUrl  = url;
    preview.src       = url;
    preview.style.display = 'block';
    document.getElementById('sig-placeholder').style.display = 'none';
  } catch (_) { /* no signature yet */ }
}

function renderStats(reports) {
  const total = reports.length;
  const sent  = reports.filter(r => r.email_sent).length;
  const thisMonth = new Date().toLocaleString('default', { month: 'long' });
  const thisMonthCount = reports.filter(r => r.month === thisMonth).length;

  document.getElementById('stat-total').textContent = total;
  document.getElementById('stat-sent').textContent = sent;
  document.getElementById('stat-month').textContent = thisMonthCount;

  // Next run calculation
  const today = new Date();
  let nextRun;
  if (today.getDate() < 16) {
    nextRun = new Date(today.getFullYear(), today.getMonth(), 16);
  } else {
    nextRun = new Date(today.getFullYear(), today.getMonth() + 1, 1);
  }
  const daysLeft = Math.ceil((nextRun - today) / (1000 * 60 * 60 * 24));
  document.getElementById('next-run-date').textContent =
    nextRun.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
  document.getElementById('next-run-sub').textContent =
    daysLeft === 0 ? 'Today!' : `In ${daysLeft} day${daysLeft !== 1 ? 's' : ''}`;
}

// Shared HTML builder for a single report row
function buildReportRow(r, showDelete = false) {
  const date = r.created_at
    ? new Date(r.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '—';
  const emailBadge = r.email_sent
    ? '<span class="badge badge-success">✉ Sent</span>'
    : '<span class="badge badge-muted">Not sent</span>';
  const emailBtn = !r.email_sent
    ? `<button class="btn btn-ghost btn-sm" onclick="resendEmail(${r.id})">✉ Email</button>`
    : '';
  const deleteBtn = showDelete
    ? `<button class="btn btn-danger btn-sm" style="margin-left:auto;" onclick="deleteReport(${r.id})" title="Delete report">🗑 Delete</button>`
    : '';
  return `
    <tr id="report-row-${r.id}">
      <td class="td-main">${r.month} ${r.year}</td>
      <td>${r.period}</td>
      <td>${date}</td>
      <td>${emailBadge}</td>
      <td class="td-actions">
        <button class="btn btn-secondary btn-sm" onclick="downloadReport(${r.id})">⬇ Download</button>
        ${emailBtn}
        ${deleteBtn}
      </td>
    </tr>`;
}

const EMPTY_ROW = (colspan) => `
  <tr><td colspan="${colspan}">
    <div class="empty-state">
      <img class="empty-state-icon" src="/static/img/logo.png" style="width: 48px; height: 48px; object-fit: contain; margin: 0 auto; opacity: 0.6;" alt="No reports" />
      <div class="empty-state-title">No reports yet</div>
      <div class="empty-state-desc">Click "Generate Now" to create your first CoA report.</div>
    </div>
  </td></tr>`;

function renderReportsTable(reports) {
  // Overview tab (recent 5, no delete button)
  const overview = document.getElementById('reports-tbody');
  if (overview) {
    if (!reports.length) {
      overview.innerHTML = EMPTY_ROW(5);
    } else {
      overview.innerHTML = reports.slice(0, 5).map(r => buildReportRow(r, false)).join('');
    }
  }

  // Reports tab (full list, with delete button)
  const full = document.getElementById('reports-tbody-full');
  if (full) {
    if (!reports.length) {
      full.innerHTML = EMPTY_ROW(5);
    } else {
      full.innerHTML = reports.map(r => buildReportRow(r, true)).join('');
    }
  }
}

function renderSmtpStatus(status) {
  const dot = document.getElementById('smtp-status-dot');
  const label = document.getElementById('smtp-status-label');
  if (status.configured) {
    dot.className = 'smtp-status-dot online';
    label.textContent = 'Connected (' + status.smtp_username + ')';
  } else {
    dot.className = 'smtp-status-dot offline';
    label.textContent = 'Not configured';
  }
  if (status.smtp_host) document.getElementById('smtp-host').value = status.smtp_host;
  if (status.smtp_port) document.getElementById('smtp-port').value = status.smtp_port;
  if (status.smtp_username) document.getElementById('smtp-user').value = status.smtp_username;
  if (status.smtp_password) document.getElementById('smtp-pass').value = status.smtp_password;
  if (status.smtp_from_name) document.getElementById('smtp-name').value = status.smtp_from_name;
}

// ─── Profile Save ────────────────────────────────────────────
document.getElementById('profile-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('save-profile-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader"></span>';
  try {
    const payload = {
      full_name:           document.getElementById('pf-fullname').value,
      department:          document.getElementById('pf-dept').value,
      college:             document.getElementById('pf-college').value,
      total_teaching_load: document.getElementById('pf-load').value,
      term_school_year:    document.getElementById('pf-term').value,
    };
    const user = await apiFetch('/api/me', { method: 'PATCH', body: JSON.stringify(payload) });
    Auth.setUser(user);
    renderUserInfo(user);
    toast('Profile updated successfully!', 'success');
  } catch (err) {
    toast('Failed to save profile: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '💾 Save Changes';
  }
});

// ─── Signature Upload ────────────────────────────────────────
document.getElementById('sig-input')?.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const user = await apiFetch('/api/me/signature', { method: 'POST', body: formData, headers: {} });
    Auth.setUser(user);
    await loadSignaturePreview();
    toast('E-signature uploaded!', 'success');
  } catch (err) {
    toast('Failed to upload signature: ' + err.message, 'error');
  }
});

const sigZone = document.getElementById('sig-zone');
sigZone?.addEventListener('dragover', (e) => { e.preventDefault(); sigZone.classList.add('drag-over'); });
sigZone?.addEventListener('dragleave', () => sigZone.classList.remove('drag-over'));
sigZone?.addEventListener('drop', (e) => {
  e.preventDefault();
  sigZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) {
    const input = document.getElementById('sig-input');
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    input.dispatchEvent(new Event('change'));
  }
});

// ─── Generate Report ─────────────────────────────────────────
document.getElementById('generate-btn')?.addEventListener('click', async () => {
  const btn = document.getElementById('generate-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader"></span> Generating…';
  try {
    const res = await apiFetch('/api/reports/generate', { method: 'POST' });
    toast('Report generated: ' + res.report.month + ' ' + res.report.year + ' (' + res.report.period + ')', 'success');
    const reports = await apiFetch('/api/reports');
    renderReportsTable(reports);
    renderStats(reports);
  } catch (err) {
    toast('Generation failed: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '⚡ Generate Now';
  }
});

// ─── Download Report ─────────────────────────────────────────
async function downloadReport(reportId) {
  const token = Auth.getToken();
  const a = document.createElement('a');
  a.href = `/api/reports/${reportId}/download`;
  a.setAttribute('download', '');
  // We need to fetch with auth header
  try {
    const res = await fetch(a.href, { headers: { 'Authorization': `Bearer ${token}` } });
    if (!res.ok) throw new Error('Download failed');
    const blob = await res.blob();
    const cd = res.headers.get('content-disposition') || '';
    const match = cd.match(/filename="(.+?)"/);
    const filename = match ? match[1] : 'report.xlsx';
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    toast('Downloading report…', 'info');
  } catch (err) {
    toast('Download error: ' + err.message, 'error');
  }
}

// ─── Delete Modal ────────────────────────────────────────────
const DeleteModal = {
  _pendingId: null,
  _overlay: null,
  _confirmBtn: null,
  _cancelBtn: null,

  init() {
    this._overlay    = document.getElementById('delete-modal');
    this._confirmBtn = document.getElementById('modal-confirm-btn');
    this._cancelBtn  = document.getElementById('modal-cancel-btn');

    if (!this._overlay || !this._confirmBtn || !this._cancelBtn) {
      console.warn('DeleteModal: elements not found in DOM');
      return;
    }

    this._confirmBtn.addEventListener('click', () => this._confirm());
    this._cancelBtn.addEventListener('click', ()  => this.close());
    this._overlay.addEventListener('click', (e) => {
      if (e.target === this._overlay) this.close();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.close();
    });
  },

  open(reportId) {
    this._pendingId = reportId;
    this._overlay.classList.add('visible');
    this._confirmBtn.focus();
  },

  close() {
    this._pendingId = null;
    this._overlay.classList.remove('visible');
  },

  async _confirm() {
    const id = this._pendingId;
    if (!id) return;
    this.close();
    try {
      await apiFetch(`/api/reports/${id}`, { method: 'DELETE' });
      const row = document.getElementById(`report-row-${id}`);
      if (row) {
        row.style.transition = 'opacity 0.3s';
        row.style.opacity = '0';
        setTimeout(() => row.remove(), 320);
      }
      toast('Report deleted.', 'info');
      const reports = await apiFetch('/api/reports');
      renderReportsTable(reports);
      renderStats(reports);
    } catch (err) {
      toast('Delete failed: ' + err.message, 'error');
    }
  },
};

function deleteReport(reportId) {
  DeleteModal.open(reportId);
}

// ─── Resend Email ────────────────────────────────────────────
async function resendEmail(reportId) {
  try {
    const res = await apiFetch(`/api/reports/${reportId}/send-email`, { method: 'POST' });
    toast(res.message, 'success');
    const reports = await apiFetch('/api/reports');
    renderReportsTable(reports);
    renderStats(reports);
  } catch (err) {
    toast('Email error: ' + err.message, 'error');
  }
}

// ─── Theme Toggle ─────────────────────────────────────────────
const Theme = {
  _html: document.documentElement,
  _btn:  null,
  ICONS: { dark: '🌙', light: '☀️' },

  init() {
    this._btn = document.getElementById('theme-toggle-btn');
    const saved = localStorage.getItem('coa_theme') || 'dark';
    this._apply(saved);
    if (this._btn) {
      this._btn.addEventListener('click', () => this.toggle());
    } else {
      console.warn('Theme: toggle button not found');
    }
  },

  toggle() {
    const next = this._html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    this._apply(next);
    localStorage.setItem('coa_theme', next);
  },

  _apply(theme) {
    this._html.setAttribute('data-theme', theme);
    if (this._btn) {
      this._btn.textContent = theme === 'dark' ? this.ICONS.dark : this.ICONS.light;
      this._btn.title = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
    }
  },
};

// ─── SMTP Save ───────────────────────────────────────────────
document.getElementById('smtp-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('save-smtp-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader"></span>';
  try {
    const payload = {
      smtp_host:      document.getElementById('smtp-host').value,
      smtp_port:      parseInt(document.getElementById('smtp-port').value),
      smtp_username:  document.getElementById('smtp-user').value,
      smtp_password:  document.getElementById('smtp-pass').value,
      smtp_from_name: document.getElementById('smtp-name').value,
    };
    await apiFetch('/api/settings/smtp', { method: 'POST', body: JSON.stringify(payload) });
    toast('SMTP settings saved!', 'success');
    const status = await apiFetch('/api/settings/smtp-status');
    renderSmtpStatus(status);
  } catch (err) {
    toast('Failed to save SMTP: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '💾 Save Settings';
  }
});

// ─── Startup (script is at end of <body>, DOM is ready) ───────
Theme.init();
DeleteModal.init();
initTabs();

const _token = Auth.getToken();
if (_token) {
  showDashboard();
} else {
  showPage('login-page');
}
