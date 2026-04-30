/**
 * app.js — SwingEdge Trading Dashboard
 * Fetches signals.json from GitHub raw URL (or local fallback)
 * and renders interactive signal cards with sparklines.
 */

'use strict';

/* ═══════════════════════════════════════════════════════════
   CONFIG — Update GITHUB_USER and GITHUB_REPO after pushing
   ═══════════════════════════════════════════════════════════ */
const CONFIG = {
  // Swap these with your actual GitHub username and repo name:
  GITHUB_USER:    'Shiva224096',
  GITHUB_REPO:    'V4',
  // Local path used when opening index.html directly or via local HTTP server
  LOCAL_JSON:     './data/signals.json',      // served from project root
  LOCAL_JSON_ALT: '../data/signals.json',     // file:// fallback
  LOCAL_UPDATED:  './data/last_updated.txt',
  REFRESH_MS:     60_000,     // Auto-refresh every 60 s
  ANIMATION_STAGGER: 60,      // ms between card animations
};

// Derived URLs
const RAW_BASE    = `https://raw.githubusercontent.com/${CONFIG.GITHUB_USER}/${CONFIG.GITHUB_REPO}/main`;
const SIGNALS_URL = `${RAW_BASE}/data/signals.json`;
const UPDATED_URL = `${RAW_BASE}/data/last_updated.txt`;

/* ═══════════════════════════════════════════════════════════
   STATE
   ═══════════════════════════════════════════════════════════ */
let allSignals  = [];
let filteredSig = [];
let refreshTimer = null;
const sparklineCharts = new Map();   // canvas id → Chart instance

/* ═══════════════════════════════════════════════════════════
   FETCH + RENDER PIPELINE
   ═══════════════════════════════════════════════════════════ */

async function fetchSignals() {
  setLoading(true);
  setRefreshSpinning(true);

  try {
    /* Try GitHub raw first, then local root, then local alt (file://) */
    let data;
    const sources = [
      SIGNALS_URL + `?t=${Date.now()}`,
      CONFIG.LOCAL_JSON,
      CONFIG.LOCAL_JSON_ALT,
    ];
    let lastErr;
    for (const src of sources) {
      try {
        const resp = await fetch(src);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        data = await resp.json();
        break;
      } catch (e) { lastErr = e; }
    }
    if (!data) throw new Error(`All sources failed. Run: python scripts/generate_json.py --demo`);

    allSignals = data.signals || [];
    updateStats(allSignals);
    applyFilters();
    updateLastUpdated(data.generated_at);
    updateMarketStatus();
    hideError();
    startAutoRefresh();
  } catch (err) {
    showError(err.message);
    console.error('[SwingEdge] Fetch error:', err);
  } finally {
    setLoading(false);
    setRefreshSpinning(false);
  }
}

async function fetchLastUpdated() {
  try {
    let ts;
    try {
      const r = await fetch(UPDATED_URL + `?t=${Date.now()}`);
      ts = await r.text();
    } catch (_) {
      const r = await fetch(CONFIG.LOCAL_UPDATED + `?t=${Date.now()}`);
      ts = await r.text();
    }
    updateLastUpdated(ts.trim());
  } catch (_) { /* silent */ }
}

/* ═══════════════════════════════════════════════════════════
   FILTERS
   ═══════════════════════════════════════════════════════════ */

function applyFilters() {
  const exchange  = document.getElementById('filter-exchange').value;
  const strategy  = document.getElementById('filter-strategy').value;
  const badge     = document.getElementById('filter-badge').value;
  const minScore  = parseInt(document.getElementById('filter-min-score').value, 10) || 0;
  const pattern   = document.getElementById('filter-pattern').value;
  const search    = document.getElementById('filter-search').value.trim().toUpperCase();

  filteredSig = allSignals.filter(s => {
    if (exchange && s.exchange !== exchange) return false;
    if (strategy && s.strategy !== strategy) return false;
    if (badge    && s.badge    !== badge)    return false;
    if (s.score < minScore)                  return false;
    if (pattern  && !s.pattern.includes(pattern.replace(/[🔨🟢⭐🌠➕📊🌇🤝]/gu, '').trim())) return false;
    if (search   && !s.symbol.includes(search)) return false;
    return true;
  });

  document.getElementById('results-count').textContent =
    `${filteredSig.length} of ${allSignals.length} signals`;

  renderCards(filteredSig);
}

function clearFilters() {
  ['filter-exchange','filter-strategy','filter-badge','filter-pattern'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('filter-min-score').value = 0;
  document.getElementById('score-range-display').textContent = '0';
  document.getElementById('filter-search').value = '';
  applyFilters();
}

/* ═══════════════════════════════════════════════════════════
   RENDER CARDS
   ═══════════════════════════════════════════════════════════ */

function renderCards(signals) {
  const grid = document.getElementById('cards-grid');

  // Destroy old sparkline charts
  sparklineCharts.forEach(chart => chart.destroy());
  sparklineCharts.clear();

  if (!signals.length) {
    grid.innerHTML = '';
    document.getElementById('empty-state').hidden = false;
    return;
  }
  document.getElementById('empty-state').hidden = true;

  grid.innerHTML = signals.map((s, i) => buildCardHTML(s, i)).join('');

  // Build sparklines after DOM is ready
  requestAnimationFrame(() => {
    signals.forEach((s, i) => {
      const canvasId = `spark-${i}`;
      buildSparkline(canvasId, s.sparkline || []);
    });
  });
}

function buildCardHTML(s, i) {
  const score     = s.score || 0;
  const pct       = score; // 0–100
  const ringColor = score >= 80 ? '#22c55e' : score >= 60 ? '#eab308' : '#ef4444';
  const ringGlow  = score >= 80 ? 'rgba(34,197,94,0.4)' : score >= 60 ? 'rgba(234,179,8,0.35)' : 'rgba(239,68,68,0.35)';

  const rr   = s.rr  ? `${s.rr}:1` : '—';
  const date = s.date ? formatDate(s.date) : '—';

  const rup = n => n != null ? `₹${Number(n).toLocaleString('en-IN', {maximumFractionDigits: 2})}` : '—';

  return `
<article
  class="signal-card badge-${escHtml(s.badge)}"
  role="listitem"
  style="animation-delay: ${i * CONFIG.ANIMATION_STAGGER}ms"
  aria-label="${escHtml(s.symbol)} — ${escHtml(s.strategy)}"
>
  <!-- Header -->
  <div class="card-header">
    <div class="card-symbol-wrap">
      <span class="card-symbol">${escHtml(s.symbol)}</span>
      <span class="card-exchange-badge">${escHtml(s.exchange || 'NSE')}</span>
      <span class="card-close">LTP ${rup(s.close)}</span>
    </div>
    <div class="score-badge">
      <div
        class="score-ring"
        style="
          --ring-color: ${ringColor};
          --ring-pct: ${pct * 3.6}deg;
          --ring-glow: ${ringGlow};
          background: conic-gradient(${ringColor} ${pct * 3.6}deg, rgba(255,255,255,0.04) 0%);
          box-shadow: 0 0 14px ${ringGlow};
        "
      >
        <span class="score-num">${score}</span>
      </div>
      <span
        class="score-label-text"
        style="color: ${ringColor}"
      >${escHtml(s.badge)}</span>
    </div>
  </div>

  <!-- Strategy + Pattern -->
  <div class="card-strategy-row">
    <span class="card-strategy">${escHtml(s.strategy)}</span>
    <span class="card-pattern">${escHtml(s.pattern || '—')}</span>
  </div>

  <!-- Prices -->
  <div class="card-prices">
    <div class="price-box">
      <div class="price-label">Entry</div>
      <div class="price-value entry">${rup(s.entry)}</div>
    </div>
    <div class="price-box">
      <div class="price-label">Target 🎯</div>
      <div class="price-value target">${rup(s.target)}</div>
    </div>
    <div class="price-box">
      <div class="price-label">Stop Loss 🛑</div>
      <div class="price-value sl">${rup(s.stop_loss)}</div>
    </div>
  </div>

  <!-- R:R + Date -->
  <div class="card-rr-row">
    <span class="rr-pill">⚖️ R:R ${escHtml(rr)}</span>
    <span class="card-date">${escHtml(date)}</span>
  </div>

  <!-- Sparkline -->
  <div class="sparkline-wrap">
    <canvas id="spark-${i}" height="44" aria-label="${escHtml(s.symbol)} 7-day price trend"></canvas>
  </div>
</article>`;
}

/* ═══════════════════════════════════════════════════════════
   SPARKLINE (Chart.js)
   ═══════════════════════════════════════════════════════════ */

function buildSparkline(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data.length) return;

  const isUp = data[data.length - 1] >= data[0];
  const lineColor  = isUp ? '#22c55e' : '#ef4444';
  const fillColor  = isUp ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)';

  const chart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: data.map((_, i) => `D-${data.length - 1 - i}`),
      datasets: [{
        data,
        borderColor:     lineColor,
        borderWidth:     1.8,
        backgroundColor: fillColor,
        fill:            true,
        tension:         0.4,
        pointRadius:     0,
        pointHoverRadius:3,
        pointHoverBackgroundColor: lineColor,
      }]
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      animation:           { duration: 600, easing: 'easeOutCubic' },
      plugins: { legend: { display: false }, tooltip: {
        mode: 'index', intersect: false,
        backgroundColor: 'rgba(13,27,46,0.95)',
        titleColor: '#7fa8d0', bodyColor: '#f0f6ff',
        borderColor: 'rgba(59,130,246,0.3)', borderWidth: 1,
        callbacks: { label: ctx => ` ${ctx.parsed.y.toFixed(1)}` }
      }},
      scales: {
        x: { display: false },
        y: { display: false, min: -5, max: 105 }
      },
      interaction: { mode: 'nearest', axis: 'x', intersect: false },
    }
  });

  sparklineCharts.set(canvasId, chart);
}

/* ═══════════════════════════════════════════════════════════
   STATS BAR
   ═══════════════════════════════════════════════════════════ */

function updateStats(signals) {
  const strong   = signals.filter(s => s.badge === 'Strong').length;
  const moderate = signals.filter(s => s.badge === 'Moderate').length;
  const weak     = signals.filter(s => s.badge === 'Weak').length;
  const strategies = new Set(signals.map(s => s.strategy)).size;

  animateCount('stat-total-val',      signals.length);
  animateCount('stat-strong-val',     strong);
  animateCount('stat-moderate-val',   moderate);
  animateCount('stat-weak-val',       weak);
  animateCount('stat-strategies-val', strategies);
}

function animateCount(elId, target) {
  const el = document.getElementById(elId);
  if (!el) return;
  let start = 0;
  const step = Math.ceil(target / 20);
  const interval = setInterval(() => {
    start = Math.min(start + step, target);
    el.textContent = start;
    if (start >= target) clearInterval(interval);
  }, 30);
}

/* ═══════════════════════════════════════════════════════════
   MARKET STATUS (IST 9:15 AM – 3:30 PM)
   ═══════════════════════════════════════════════════════════ */

function updateMarketStatus() {
  const now  = new Date();
  const ist  = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const h    = ist.getHours();
  const m    = ist.getMinutes();
  const dow  = ist.getDay(); // 0=Sun 6=Sat
  const mins = h * 60 + m;

  const isWeekday = dow >= 1 && dow <= 5;
  const isOpen    = isWeekday && mins >= 9 * 60 + 15 && mins < 15 * 60 + 30;

  const dot  = document.getElementById('status-dot');
  const text = document.getElementById('status-text');

  if (isOpen) {
    dot.className  = 'status-dot open';
    text.textContent = 'Market Open';
    text.style.color = '#22c55e';
  } else {
    dot.className  = 'status-dot closed';
    const reason = !isWeekday ? 'Weekend' : mins < 9 * 60 + 15 ? 'Pre-Market' : 'Market Closed';
    text.textContent = reason;
    text.style.color = '#ef4444';
  }
}

/* ═══════════════════════════════════════════════════════════
   UI HELPERS
   ═══════════════════════════════════════════════════════════ */

function setLoading(show) {
  document.getElementById('loading-state').hidden  = !show;
  document.getElementById('cards-grid').hidden     = show;
}

function showError(msg) {
  document.getElementById('error-state').hidden = false;
  document.getElementById('error-msg').textContent = msg;
  document.getElementById('loading-state').hidden = true;
}

function hideError() {
  document.getElementById('error-state').hidden = true;
}

function updateLastUpdated(ts) {
  if (!ts) return;
  document.getElementById('updated-text').textContent = `Updated: ${ts.trim()}`;
}

function setRefreshSpinning(on) {
  const icon = document.getElementById('refresh-icon');
  if (on) icon.classList.add('spinning');
  else    icon.classList.remove('spinning');
}

function startAutoRefresh() {
  clearInterval(refreshTimer);
  refreshTimer = setInterval(fetchSignals, CONFIG.REFRESH_MS);
}

function formatDate(str) {
  try {
    const d = new Date(str);
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch (_) { return str; }
}

function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ═══════════════════════════════════════════════════════════
   EVENT LISTENERS
   ═══════════════════════════════════════════════════════════ */

function bindFilters() {
  const filterIds = [
    'filter-exchange', 'filter-strategy', 'filter-badge',
    'filter-pattern',  'filter-search',
  ];
  filterIds.forEach(id => {
    document.getElementById(id)?.addEventListener('input', applyFilters);
    document.getElementById(id)?.addEventListener('change', applyFilters);
  });

  const rangeEl = document.getElementById('filter-min-score');
  const display = document.getElementById('score-range-display');
  rangeEl?.addEventListener('input', () => {
    display.textContent = rangeEl.value;
    applyFilters();
  });
}

/* ═══════════════════════════════════════════════════════════
   BOOT
   ═══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  bindFilters();
  updateMarketStatus();
  setInterval(updateMarketStatus, 60_000);
  fetchSignals();
});
