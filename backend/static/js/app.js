/* ===== app.js — CoAutomate v2.1 Frontend Logic ===== */

const API = '';  // Same origin; backend serves the frontend

// ─── SVG Icon System (Zero Emojis) ───────────────────────────
const Icons = {
  success: `<svg class="lucide-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"></path></svg>`,
  error:   `<svg class="lucide-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`,
  info:    `<svg class="lucide-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`,
  moon:    `<svg class="lucide-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path></svg>`,
  sun:     `<svg class="lucide-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="m4.93 4.93 1.41 1.41"></path><path d="m17.66 17.66 1.41 1.41"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="m6.34 17.66-1.41 1.41"></path><path d="m19.07 4.93-1.41 1.41"></path></svg>`,
  save:    `<svg class="lucide-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>`,
  download:`<svg class="lucide-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" x2="12" y1="15" y2="3"></line></svg>`,
  trash:   `<svg class="lucide-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`,
};

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

// ─── Toast Notifications (Restrained Design) ────────────────
function toast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${Icons[type] || Icons.info}</span><span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add('leaving');
    setTimeout(() => el.remove(), 250);
  }, duration);
}

// ─── Page Navigation ────────────────────────────────────────
function showPage(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const target = document.getElementById(pageId);
  if (target) target.classList.add('active');
}

function showApp() {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('app-page').classList.add('active');
  loadApp();
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

// ─── Term & School Year Parser/Formatter Helpers ─────────────
function parseTermSchoolYear(raw) {
  let sy = '2526';
  let term = '1ST SEM';
  if (!raw) return { sy, term };

  // Common pattern: "AY 2526 1ST SEM" or "AY 2025-2026 2ND SEM" or "2526 1ST SEM"
  let clean = raw.trim();
  if (clean.toUpperCase().startsWith('AY')) {
    clean = clean.substring(2).trim();
  }

  if (clean.includes('MIDYEAR')) {
    term = 'MIDYEAR';
    sy = clean.replace('MIDYEAR', '').trim();
  } else if (clean.includes('2ND SEM')) {
    term = '2ND SEM';
    sy = clean.replace('2ND SEM', '').trim();
  } else if (clean.includes('1ST SEM')) {
    term = '1ST SEM';
    sy = clean.replace('1ST SEM', '').trim();
  } else {
    sy = clean;
  }
  return { sy, term };
}

function formatTermSchoolYear(sy, term) {
  const cleanSy = (sy || '').trim().replace(/^AY\s*/i, '');
  return `AY ${cleanSy} ${term}`.trim();
}

// ─── Auth Handlers ───────────────────────────────────────────
document.getElementById('login-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const email    = document.getElementById('login-email').value;
  const password = document.getElementById('login-password').value;
  const btn      = document.getElementById('login-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader"></span> Authenticating…';
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
    toast('Authenticated as ' + data.user.full_name.split(' ')[0], 'success');
    showApp();
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Authenticate';
  }
});

document.getElementById('register-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('register-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader"></span> Creating profile…';
  try {
    const syVal   = document.getElementById('reg-sy').value;
    const termVal = document.getElementById('reg-term-select').value;
    const termSchoolYear = formatTermSchoolYear(syVal, termVal);

    const payload = {
      email:               document.getElementById('reg-email').value,
      password:            document.getElementById('reg-password').value,
      full_name:           document.getElementById('reg-fullname').value,
      department:          document.getElementById('reg-dept').value,
      college:             document.getElementById('reg-college').value,
      total_teaching_load: document.getElementById('reg-load').value,
      term_school_year:    termSchoolYear,
    };
    const data = await apiFetch('/api/auth/register', {
      method: 'POST', body: JSON.stringify(payload),
    });
    Auth.setToken(data.access_token);
    Auth.setUser(data.user);
    toast('Profile registered successfully', 'success');
    showApp();
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Create Profile';
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
  toast('Signed out.', 'info');
});

// ─── App Load ────────────────────────────────────────────────
async function loadApp() {
  try {
    const user = await apiFetch('/api/me');
    Auth.setUser(user);
    renderNavUser(user);
    renderProfileForm(user);
    renderPreviewCard(user);
    if (user.signature_filename) {
      loadSignaturePreview();
    }
    const reports = await apiFetch('/api/reports');
    renderHistoryTable(reports);
    updateHistorySubtitle(reports.length);
  } catch (err) {
    toast('Session error: ' + err.message, 'error');
    if (err.message.includes('401') || err.message.includes('credentials')) {
      Auth.clear();
      showPage('login-page');
    }
  }
}

// ─── Nav User ───────────────────────────────────────────────
function renderNavUser(user) {
  const initials = user.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  document.getElementById('nav-user-name').textContent = user.full_name;
  document.getElementById('nav-user-initials').textContent = initials;
}

// ─── Profile Preview Card ────────────────────────────────────
function renderPreviewCard(user) {
  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val || '—';
  };
  set('prev-name',    user.full_name);
  set('prev-dept',    user.department);
  set('prev-college', user.college);
  set('prev-load',    user.total_teaching_load ? user.total_teaching_load + ' units' : '');
  set('prev-term',    user.term_school_year);
}

// ─── Signature Preview (Fixed Overflow Layout) ───────────────
async function loadSignaturePreview() {
  try {
    const token = Auth.getToken();
    const res = await fetch('/api/me/signature', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);

    // Profile tab active asset box
    const activeBox = document.getElementById('sig-active-asset-box');
    const preview = document.getElementById('sig-preview');
    if (preview) {
      if (preview._blobUrl) URL.revokeObjectURL(preview._blobUrl);
      preview._blobUrl  = url;
      preview.src       = url;
      preview.style.display = 'block';
    }
    if (activeBox) {
      activeBox.style.display = 'flex';
    }

    // Generator tab preview card
    const previewImg = document.getElementById('preview-sig-img');
    const previewPh  = document.getElementById('preview-sig-placeholder');
    if (previewImg) {
      previewImg.src = url;
      previewImg.style.display = 'block';
    }
    if (previewPh) previewPh.style.display = 'none';
  } catch (_) { /* no signature yet */ }
}

// ─── Profile Form Render & Submit ────────────────────────────
function renderProfileForm(user) {
  document.getElementById('pf-fullname').value = user.full_name;
  document.getElementById('pf-dept').value     = user.department;
  document.getElementById('pf-college').value  = user.college;
  document.getElementById('pf-load').value     = user.total_teaching_load;

  const parsed = parseTermSchoolYear(user.term_school_year);
  const pfSy = document.getElementById('pf-sy');
  const pfTerm = document.getElementById('pf-term-select');
  if (pfSy) pfSy.value = parsed.sy;
  if (pfTerm) pfTerm.value = parsed.term;
}

document.getElementById('profile-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('save-profile-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader"></span> Saving…';
  try {
    const syVal   = document.getElementById('pf-sy').value;
    const termVal = document.getElementById('pf-term-select').value;
    const combinedTermSY = formatTermSchoolYear(syVal, termVal);

    const payload = {
      full_name:           document.getElementById('pf-fullname').value,
      department:          document.getElementById('pf-dept').value,
      college:             document.getElementById('pf-college').value,
      total_teaching_load: document.getElementById('pf-load').value,
      term_school_year:    combinedTermSY,
    };
    const user = await apiFetch('/api/me', { method: 'PATCH', body: JSON.stringify(payload) });
    Auth.setUser(user);
    renderNavUser(user);
    renderProfileForm(user);
    renderPreviewCard(user);
    toast('Faculty profile updated', 'success');
  } catch (err) {
    toast('Save error: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `${Icons.save} Save Changes`;
  }
});

// ─── Signature Upload Handler ────────────────────────────────
document.getElementById('sig-input')?.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const user = await apiFetch('/api/me/signature', { method: 'POST', body: formData, headers: {} });
    Auth.setUser(user);
    await loadSignaturePreview();
    toast('Signature image uploaded', 'success');
  } catch (err) {
    toast('Upload failed: ' + err.message, 'error');
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

// ─── Generator Form Setup ────────────────────────────────────
(function initGeneratorDefaults() {
  const today = new Date();
  const monthSel = document.getElementById('gen-month');
  const yearInp  = document.getElementById('gen-year');
  const dateInp  = document.getElementById('gen-date');

  if (monthSel) monthSel.value = today.getMonth() + 1; // 1-indexed
  if (yearInp)  yearInp.value  = today.getFullYear();
  if (dateInp)  dateInp.value  = today.toISOString().slice(0, 10);

  updatePeriodEndLabel();
})();

function updatePeriodEndLabel() {
  const month = parseInt(document.getElementById('gen-month')?.value || 0);
  const year  = parseInt(document.getElementById('gen-year')?.value  || new Date().getFullYear());
  const label = document.getElementById('period-end-label');
  if (!label || !month || !year) return;

  const lastDay = new Date(year, month, 0).getDate();
  label.textContent = `Days 16 through ${lastDay}`;
}

document.getElementById('gen-month')?.addEventListener('change', updatePeriodEndLabel);
document.getElementById('gen-year')?.addEventListener('input', updatePeriodEndLabel);

// ─── Generate & Download ─────────────────────────────────────
document.getElementById('generator-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('generate-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader"></span> Generating Spreadsheet…';

  try {
    const month  = parseInt(document.getElementById('gen-month').value);
    const year   = parseInt(document.getElementById('gen-year').value);
    const period = document.querySelector('input[name="gen-period"]:checked')?.value || '1-15';
    const dateAcc = document.getElementById('gen-date').value;

    if (!dateAcc) throw new Error('Please specify a Date Accomplished.');

    const payload = { month, year, period, date_accomplished: dateAcc };

    const token = Auth.getToken();
    const res = await fetch('/api/reports/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const cd = res.headers.get('content-disposition') || '';
    const fnMatch = cd.match(/filename="(.+?)"/);
    const xFilename = res.headers.get('X-Filename');
    const filename = fnMatch ? fnMatch[1] : (xFilename || 'CoA_report.xlsx');

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    toast(`Downloaded: ${filename}`, 'success', 5000);

    const reports = await apiFetch('/api/reports');
    renderHistoryTable(reports);
    updateHistorySubtitle(reports.length);

  } catch (err) {
    toast('Generation failed: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `${Icons.download} Generate &amp; Download Spreadsheet`;
  }
});

// ─── History Table ───────────────────────────────────────────
function buildHistoryRow(r) {
  const genDate = r.created_at
    ? new Date(r.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '—';
  return `
    <tr id="report-row-${r.id}">
      <td class="td-bold">${r.month} ${r.year}</td>
      <td class="td-mono">${r.period}</td>
      <td class="td-mono">${genDate}</td>
      <td class="td-actions">
        <button class="btn btn-secondary btn-sm" onclick="downloadReport(${r.id})">
          ${Icons.download} Download
        </button>
        <button class="btn btn-danger btn-sm" onclick="deleteReport(${r.id})" title="Delete report" style="margin-left:6px;">
          ${Icons.trash} Delete
        </button>
      </td>
    </tr>`;
}

const HISTORY_EMPTY = `
  <tr><td colspan="4">
    <div class="empty-notice">
      <p class="empty-notice-title">No archived reports</p>
      <p class="empty-notice-sub">Generated documents will appear here for audit and re-download.</p>
    </div>
  </td></tr>`;

function renderHistoryTable(reports) {
  const tbody = document.getElementById('history-tbody');
  if (!tbody) return;
  tbody.innerHTML = reports.length
    ? reports.map(buildHistoryRow).join('')
    : HISTORY_EMPTY;
}

function updateHistorySubtitle(count) {
  const el = document.getElementById('history-subtitle');
  if (!el) return;
  el.textContent = count === 0
    ? 'Record of all previously compiled and exported documents.'
    : `${count} document${count !== 1 ? 's' : ''} stored in local archive.`;
}

// ─── Download Report ─────────────────────────────────────────
async function downloadReport(reportId) {
  const token = Auth.getToken();
  try {
    const res = await fetch(`/api/reports/${reportId}/download`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
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
    toast('Downloading report archive…', 'info');
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
        row.style.transition = 'opacity 0.2s';
        row.style.opacity = '0';
        setTimeout(() => row.remove(), 210);
      }
      toast('Report deleted from archive', 'info');
      setTimeout(async () => {
        const reports = await apiFetch('/api/reports');
        renderHistoryTable(reports);
        updateHistorySubtitle(reports.length);
      }, 250);
    } catch (err) {
      toast('Delete failed: ' + err.message, 'error');
    }
  },
};

function deleteReport(reportId) {
  DeleteModal.open(reportId);
}

// ─── Theme Toggle ─────────────────────────────────────────────
const Theme = {
  _html: document.documentElement,
  _btn:  null,

  init() {
    this._btn = document.getElementById('theme-toggle-btn');
    const saved = localStorage.getItem('coa_theme') || 'dark';
    this._apply(saved);
    if (this._btn) {
      this._btn.addEventListener('click', () => this.toggle());
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
      this._btn.innerHTML = theme === 'dark' ? Icons.sun : Icons.moon;
      this._btn.title = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
    }
  },
};

// ─── Startup ─────────────────────────────────────────────────
Theme.init();
DeleteModal.init();
initTabs();

const _token = Auth.getToken();
if (_token) {
  showApp();
} else {
  showPage('login-page');
}
