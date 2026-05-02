'use strict';

// ═══ FUNDAMENTALS TAB ═══
const FUND_CONFIG = {
  GITHUB_USER: 'Shiva224096', GITHUB_REPO: 'V4',
  LOCAL_JSON: '../data/fundamentals.json', LOCAL_ALT: './data/fundamentals.json',
  PAGE_SIZE: 50,
};
const FUND_URL = `https://raw.githubusercontent.com/${FUND_CONFIG.GITHUB_USER}/${FUND_CONFIG.GITHUB_REPO}/main/data/fundamentals.json`;

let allFundStocks = [], filteredFund = [], fPage = 1, fSortCol = 'composite_score', fSortDir = 'desc';
let fundLoaded = false, fundModalStock = null, activeTab = 'technical';

// ═══ TAB SWITCHING ═══
function switchTab(tab) {
  activeTab = tab;
  const techPanel = document.getElementById('technical-panel');
  const fundPanel = document.getElementById('fundamentals-panel');
  const tabTech = document.getElementById('tab-technical');
  const tabFund = document.getElementById('tab-fundamentals');

  if (tab === 'technical') {
    if (techPanel) techPanel.hidden = false;
    if (fundPanel) fundPanel.hidden = true;
    tabTech.classList.add('active'); tabTech.setAttribute('aria-selected','true');
    tabFund.classList.remove('active'); tabFund.setAttribute('aria-selected','false');
  } else {
    if (techPanel) techPanel.hidden = true;
    if (fundPanel) fundPanel.hidden = false;
    tabFund.classList.add('active'); tabFund.setAttribute('aria-selected','true');
    tabTech.classList.remove('active'); tabTech.setAttribute('aria-selected','false');
    if (!fundLoaded) fetchFundamentals();
  }
}

// ═══ FETCH ═══
async function fetchFundamentals() {
  document.getElementById('f-loading').hidden = false;
  document.getElementById('f-table-container').hidden = true;
  document.getElementById('f-error').hidden = true;
  try {
    let data;
    const sources = [FUND_URL + `?t=${Date.now()}`, FUND_CONFIG.LOCAL_JSON, FUND_CONFIG.LOCAL_ALT];
    for (const src of sources) {
      try { const r = await fetch(src); if (!r.ok) throw 0; data = await r.json(); break; } catch(_){}
    }
    if (!data) throw new Error('No fundamentals data found. Run the engine locally first.');
    allFundStocks = data.stocks || [];
    fundLoaded = true;
    document.getElementById('f-updated').innerHTML = `<span class="updated-icon">🕐</span> Data as of: ${data.generated_at || 'Unknown'}`;
    populateSectors();
    updateFundStats();
    applyFundFilters();
    document.getElementById('f-loading').hidden = true;
    document.getElementById('f-table-container').hidden = false;
  } catch (err) {
    document.getElementById('f-loading').hidden = true;
    document.getElementById('f-error').hidden = false;
    document.getElementById('f-error-msg').textContent = err.message;
  }
}

// ═══ SECTORS ═══
function populateSectors() {
  const sel = document.getElementById('f-sector');
  const sectors = [...new Set(allFundStocks.map(s => s.sector).filter(Boolean))].sort();
  sel.innerHTML = '<option value="">All Sectors</option>' + sectors.map(s => `<option>${s}</option>`).join('');
}

// ═══ STATS ═══
function updateFundStats() {
  const s = allFundStocks;
  animateFundCount('fstat-total-val', s.length);
  animateFundCount('fstat-strong-val', s.filter(x => x.badge === 'Strong Buy').length);
  animateFundCount('fstat-buy-val', s.filter(x => x.badge === 'Buy').length);
  animateFundCount('fstat-hold-val', s.filter(x => x.badge === 'Hold').length);
  animateFundCount('fstat-avoid-val', s.filter(x => x.badge === 'Avoid').length);
}
function animateFundCount(id, target) {
  const el = document.getElementById(id); if (!el) return;
  let s = 0; const step = Math.ceil(target / 20);
  const iv = setInterval(() => { s = Math.min(s + step, target); el.textContent = s; if (s >= target) clearInterval(iv); }, 30);
}

// ═══ FILTERS ═══
function applyFundFilters() {
  const sector = document.getElementById('f-sector').value;
  const badge = document.getElementById('f-badge').value;
  const minScore = parseInt(document.getElementById('f-min-score').value, 10) || 0;
  const peMax = parseFloat(document.getElementById('f-pe-max').value) || Infinity;
  const search = document.getElementById('f-search').value.trim().toUpperCase();

  filteredFund = allFundStocks.filter(s => {
    if (sector && s.sector !== sector) return false;
    if (badge && s.badge !== badge) return false;
    if (s.composite_score < minScore) return false;
    if (s.pe && s.pe > peMax) return false;
    if (search && !s.symbol.includes(search)) return false;
    return true;
  });
  document.getElementById('f-results-count').textContent = `${filteredFund.length} of ${allFundStocks.length} stocks`;
  fPage = 1;
  renderFundTable();
}

function clearFundFilters() {
  document.getElementById('f-sector').value = '';
  document.getElementById('f-badge').value = '';
  document.getElementById('f-min-score').value = 0;
  document.getElementById('f-score-display').textContent = '0';
  document.getElementById('f-pe-max').value = '';
  document.getElementById('f-search').value = '';
  applyFundFilters();
}

// ═══ PRESETS ═══
function applyPreset(name) {
  clearFundFilters();
  switch (name) {
    case 'value':
      document.getElementById('f-pe-max').value = '20';
      document.getElementById('f-min-score').value = 50;
      document.getElementById('f-score-display').textContent = '50';
      break;
    case 'quality':
      document.getElementById('f-min-score').value = 60;
      document.getElementById('f-score-display').textContent = '60';
      break;
    case 'safe':
      document.getElementById('f-min-score').value = 40;
      document.getElementById('f-score-display').textContent = '40';
      break;
    case 'undervalued':
      document.getElementById('f-min-score').value = 0;
      break;
  }
  if (name === 'undervalued') {
    filteredFund = allFundStocks.filter(s => s.margin_of_safety && s.margin_of_safety > 0).sort((a, b) => (b.margin_of_safety || 0) - (a.margin_of_safety || 0));
    document.getElementById('f-results-count').textContent = `${filteredFund.length} undervalued stocks`;
    fPage = 1;
    renderFundTable();
  } else {
    applyFundFilters();
  }
}

// ═══ TABLE ═══
function renderFundTable() {
  const sorted = [...filteredFund].sort((a, b) => {
    let va = a[fSortCol], vb = b[fSortCol];
    if (va == null) va = fSortDir === 'asc' ? Infinity : -Infinity;
    if (vb == null) vb = fSortDir === 'asc' ? Infinity : -Infinity;
    if (typeof va === 'string') { va = va.toLowerCase(); vb = (vb || '').toLowerCase(); }
    return fSortDir === 'asc' ? (va < vb ? -1 : va > vb ? 1 : 0) : (va > vb ? -1 : va < vb ? 1 : 0);
  });

  const totalPages = Math.ceil(sorted.length / FUND_CONFIG.PAGE_SIZE);
  if (fPage > totalPages) fPage = totalPages || 1;
  const start = (fPage - 1) * FUND_CONFIG.PAGE_SIZE;
  const pageData = sorted.slice(start, start + FUND_CONFIG.PAGE_SIZE);
  const rup = n => n != null ? n.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '—';
  const fmt = (n, suffix) => n != null ? `${rup(n)}${suffix || ''}` : '—';

  const tbody = document.getElementById('f-tbody');
  tbody.innerHTML = pageData.map(s => {
    const bc = badgeClass(s.badge);
    const sc = s.composite_score || 0;
    return `<tr class="table-row ${bc}" onclick='openFundModal(${JSON.stringify(s).replace(/'/g,"&#39;")})'>
      <td class="col-symbol">${esc(s.symbol)}</td>
      <td><span class="strategy-pill" style="font-size:10px">${esc(s.sector||'')}</span></td>
      <td class="num">${rup(s.price)}</td>
      <td class="num">${fmt(s.pe)}</td>
      <td class="num">${fmt(s.pb)}</td>
      <td class="num">${fmt(s.roe, '%')}</td>
      <td class="num">${fmt(s.de_ratio)}</td>
      <td class="num">${fmt(s.profit_margin, '%')}</td>
      <td class="num ${s.rev_growth > 0 ? 'col-target' : s.rev_growth < 0 ? 'col-sl' : ''}">${fmt(s.rev_growth, '%')}</td>
      <td class="num"><span class="fscore-pill fscore-${fscoreClass(s.fscore)}">${s.fscore}/9</span></td>
      <td class="num"><span class="zscore-pill zscore-${zscoreClass(s.zscore)}">${s.zscore || '—'}</span></td>
      <td class="num ${s.margin_of_safety > 0 ? 'col-target' : 'col-sl'}">${fmt(s.margin_of_safety, '%')}</td>
      <td class="num"><span class="score-pill ${bc}">${sc}</span></td>
      <td><span class="badge-label ${bc}">${esc(s.badge)}</span></td>
    </tr>`;
  }).join('');

  // Sort indicators
  document.querySelectorAll('#f-table th.sortable').forEach(th => {
    const col = th.getAttribute('onclick')?.match(/fSort\('(.+?)'\)/)?.[1];
    const icon = th.querySelector('.sort-icon');
    if (col === fSortCol) icon.textContent = fSortDir === 'asc' ? '↑' : '↓';
    else icon.textContent = '⇅';
  });

  renderFundPagination(totalPages);
}

function fSort(col) {
  if (fSortCol === col) fSortDir = fSortDir === 'asc' ? 'desc' : 'asc';
  else { fSortCol = col; fSortDir = 'desc'; }
  renderFundTable();
}

function renderFundPagination(total) {
  const el = document.getElementById('f-pagination');
  if (total <= 1) { el.innerHTML = ''; return; }
  let html = `<button class="page-btn" ${fPage <= 1 ? 'disabled' : ''} onclick="fGoPage(${fPage - 1})">‹</button>`;
  for (let p = 1; p <= total; p++) {
    if (p === 1 || p === total || Math.abs(p - fPage) <= 2)
      html += `<button class="page-btn ${p === fPage ? 'active' : ''}" onclick="fGoPage(${p})">${p}</button>`;
    else if (Math.abs(p - fPage) === 3) html += '<span class="page-dots">…</span>';
  }
  html += `<button class="page-btn" ${fPage >= total ? 'disabled' : ''} onclick="fGoPage(${fPage + 1})">›</button>`;
  el.innerHTML = html;
}
function fGoPage(p) { fPage = p; renderFundTable(); }

// ═══ MODAL ═══
function openFundModal(stock) {
  fundModalStock = stock;
  document.getElementById('fm-title').textContent = stock.symbol;
  document.getElementById('fm-subtitle').textContent = `${stock.sector} · ${stock.industry} · Score ${stock.composite_score}`;

  const rup = n => n != null ? `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '—';
  const fmt = (n, s) => n != null ? `${n}${s || ''}` : '—';

  document.getElementById('fm-info').innerHTML = `
    <div class="modal-info-grid">
      <div class="modal-info-item"><span class="mil">Price</span><span class="miv">${rup(stock.price)}</span></div>
      <div class="modal-info-item"><span class="mil">Market Cap</span><span class="miv">${rup(stock.mktcap_cr)} Cr</span></div>
      <div class="modal-info-item"><span class="mil">PE Ratio</span><span class="miv">${fmt(stock.pe)}</span></div>
      <div class="modal-info-item"><span class="mil">PB Ratio</span><span class="miv">${fmt(stock.pb)}</span></div>
      <div class="modal-info-item"><span class="mil">EPS</span><span class="miv">${rup(stock.eps)}</span></div>
      <div class="modal-info-item"><span class="mil">Book Value</span><span class="miv">${rup(stock.bvps)}</span></div>
      <div class="modal-info-item"><span class="mil">ROE</span><span class="miv">${fmt(stock.roe, '%')}</span></div>
      <div class="modal-info-item"><span class="mil">ROA</span><span class="miv">${fmt(stock.roa, '%')}</span></div>
      <div class="modal-info-item"><span class="mil">Debt/Equity</span><span class="miv">${fmt(stock.de_ratio)}</span></div>
      <div class="modal-info-item"><span class="mil">Revenue</span><span class="miv">${rup(stock.revenue_cr)} Cr</span></div>
      <div class="modal-info-item"><span class="mil">Rev Growth</span><span class="miv ${stock.rev_growth > 0 ? 'col-target' : 'col-sl'}">${fmt(stock.rev_growth, '%')}</span></div>
      <div class="modal-info-item"><span class="mil">Net Margin</span><span class="miv">${fmt(stock.profit_margin, '%')}</span></div>
      <div class="modal-info-item"><span class="mil">Gross Margin</span><span class="miv">${fmt(stock.gross_margin, '%')}</span></div>
      <div class="modal-info-item"><span class="mil">Op Margin</span><span class="miv">${fmt(stock.op_margin, '%')}</span></div>
      <div class="modal-info-item"><span class="mil">Div Yield</span><span class="miv">${fmt(stock.div_yield, '%')}</span></div>
      <div class="modal-info-item"><span class="mil">EBITDA</span><span class="miv">${rup(stock.ebitda_cr)} Cr</span></div>
      <div class="modal-info-item"><span class="mil">Total Debt</span><span class="miv col-sl">${rup(stock.debt_cr)} Cr</span></div>
      <div class="modal-info-item"><span class="mil">Cash</span><span class="miv col-target">${rup(stock.cash_cr)} Cr</span></div>
    </div>`;

  const sc = stock.composite_score;
  const rc = sc >= 75 ? '#22c55e' : sc >= 60 ? '#3b82f6' : sc >= 40 ? '#eab308' : '#ef4444';
  document.getElementById('fm-scores').innerHTML = `
    <div class="fund-scores-grid">
      <div class="fund-score-card">
        <div class="fund-score-title">Composite Score</div>
        <div class="fund-score-big" style="color:${rc}">${sc}/100</div>
        <div class="fund-score-badge" style="color:${rc}">${stock.badge}</div>
      </div>
      <div class="fund-score-card">
        <div class="fund-score-title">Piotroski F-Score</div>
        <div class="fund-score-val fscore-${fscoreClass(stock.fscore)}">${stock.fscore}/9</div>
        <div class="fund-score-desc">${stock.fscore >= 7 ? 'Strong' : stock.fscore >= 4 ? 'Neutral' : 'Weak'}</div>
      </div>
      <div class="fund-score-card">
        <div class="fund-score-title">Graham Number</div>
        <div class="fund-score-val">${stock.graham_number ? '₹' + stock.graham_number : '—'}</div>
        <div class="fund-score-desc ${stock.margin_of_safety > 0 ? 'col-target' : 'col-sl'}">MoS: ${stock.margin_of_safety != null ? stock.margin_of_safety + '%' : '—'}</div>
      </div>
      <div class="fund-score-card">
        <div class="fund-score-title">Altman Z-Score</div>
        <div class="fund-score-val zscore-${zscoreClass(stock.zscore)}">${stock.zscore || '—'}</div>
        <div class="fund-score-desc">${stock.zscore > 2.99 ? 'Safe Zone' : stock.zscore > 1.8 ? 'Grey Zone' : stock.zscore ? 'Distress' : '—'}</div>
      </div>
      <div class="fund-score-card">
        <div class="fund-score-title">Earnings Yield</div>
        <div class="fund-score-val">${stock.earnings_yield ? stock.earnings_yield + '%' : '—'}</div>
        <div class="fund-score-desc">Magic Formula</div>
      </div>
      <div class="fund-score-card">
        <div class="fund-score-title">Return on Capital</div>
        <div class="fund-score-val">${stock.return_on_capital ? stock.return_on_capital + '%' : '—'}</div>
        <div class="fund-score-desc">Magic Formula</div>
      </div>
    </div>`;

  document.getElementById('fund-modal').hidden = false;
  document.body.style.overflow = 'hidden';
}

function closeFundModal() {
  document.getElementById('fund-modal').hidden = true;
  document.body.style.overflow = '';
  fundModalStock = null;
}
function openFundTV() {
  if (!fundModalStock) return;
  window.open(`https://www.tradingview.com/chart/?symbol=NSE:${fundModalStock.symbol}&interval=W`, '_blank');
}

// ═══ HELPERS ═══
function badgeClass(b) {
  if (b === 'Strong Buy') return 'badge-strong';
  if (b === 'Buy') return 'badge-buy';
  if (b === 'Hold') return 'badge-moderate';
  return 'badge-weak';
}
function fscoreClass(f) { return f >= 7 ? 'high' : f >= 4 ? 'mid' : 'low'; }
function zscoreClass(z) { return z > 2.99 ? 'safe' : z > 1.8 ? 'grey' : 'distress'; }
function esc(s) { return s == null ? '' : String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

// ═══ EVENT BINDINGS ═══
document.addEventListener('DOMContentLoaded', () => {
  ['f-sector','f-badge','f-search','f-pe-max'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', applyFundFilters);
    document.getElementById(id)?.addEventListener('change', applyFundFilters);
  });
  const r = document.getElementById('f-min-score'), d = document.getElementById('f-score-display');
  r?.addEventListener('input', () => { d.textContent = r.value; applyFundFilters(); });
  document.getElementById('fund-modal')?.addEventListener('click', e => { if (e.target.id === 'fund-modal') closeFundModal(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeFundModal(); });
});
