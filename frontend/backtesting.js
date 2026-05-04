'use strict';

// ═══ BACKTESTING TAB ═══
const BT_CONFIG = {
  GITHUB_USER: 'Shiva224096', GITHUB_REPO: 'V4',
  LOCAL_JSON: '../data/backtest_results.json', LOCAL_ALT: './data/backtest_results.json',
};
const BT_URL = `https://raw.githubusercontent.com/${BT_CONFIG.GITHUB_USER}/${BT_CONFIG.GITHUB_REPO}/main/data/backtest_results.json`;

let btLoaded = false;

async function fetchBacktesting() {
  if (btLoaded) return;
  document.getElementById('bt-loading').hidden = false;
  document.getElementById('bt-table-container').hidden = true;
  document.getElementById('bt-error').hidden = true;

  try {
    let data;
    const sources = [BT_URL + `?t=${Date.now()}`, BT_CONFIG.LOCAL_JSON, BT_CONFIG.LOCAL_ALT];
    for (const src of sources) {
      try { const r = await fetch(src); if (!r.ok) throw 0; data = await r.json(); break; } catch(_){}
    }
    if (!data) throw new Error('No backtesting data found. Run backtester.py locally first.');
    
    btLoaded = true;
    if (data.generated_at) {
      document.getElementById('bt-updated').innerHTML = `<span class="updated-icon">🕐</span> Last run: ${data.generated_at}`;
    }

    renderBtStats(data.strategies || {});
    renderBtTable(data.strategies || {});
    renderBtPatternTable(data.patterns || {});

    document.getElementById('bt-loading').hidden = true;
    document.getElementById('bt-table-container').hidden = false;
  } catch (err) {
    document.getElementById('bt-loading').hidden = true;
    document.getElementById('bt-error').hidden = false;
    document.getElementById('bt-error-msg').textContent = err.message;
  }
}

function renderBtStats(strats) {
  const keys = Object.keys(strats);
  document.getElementById('bt-total-strats').textContent = keys.length;
  
  if (keys.length === 0) return;

  let bestStrat = keys[0];
  let bestWinRate = -1;

  for (const k of keys) {
    const s = strats[k];
    if (s.win_rate > bestWinRate && s.total >= 10) {
      bestWinRate = s.win_rate;
      bestStrat = k;
    }
  }

  document.getElementById('bt-best-strat').textContent = bestStrat;
  document.getElementById('bt-best-winrate').textContent = (bestWinRate > -1 ? bestWinRate + '%' : '—');
}

function renderBtTable(strats) {
  const tbody = document.getElementById('bt-tbody');
  const keys = Object.keys(strats).sort((a, b) => strats[b].win_rate - strats[a].win_rate);
  
  tbody.innerHTML = keys.map(k => {
    const s = strats[k];
    const wr = s.win_rate;
    const bc = wr >= 60 ? 'badge-strong' : wr >= 50 ? 'badge-moderate' : 'badge-weak';
    return `<tr class="table-row">
      <td><span class="strategy-pill">${escBt(k)}</span></td>
      <td class="num"><span class="score-pill ${bc}">${wr}%</span></td>
      <td class="num">${s.total}</td>
      <td class="num col-target">${s.wins}</td>
      <td class="num col-sl">${s.losses}</td>
      <td class="num ${s.avg_gain > 0 ? 'col-target' : ''}">${s.avg_gain > 0 ? '+' : ''}${s.avg_gain}%</td>
      <td class="num col-sl">${s.avg_loss}%</td>
      <td class="num">${s.weight > 0 ? '+' : ''}${s.weight}</td>
    </tr>`;
  }).join('');
}

function renderBtPatternTable(patterns) {
  const tbody = document.getElementById('bt-pattern-tbody');
  const keys = Object.keys(patterns).sort((a, b) => patterns[b].win_rate - patterns[a].win_rate);
  
  tbody.innerHTML = keys.map(k => {
    const p = patterns[k];
    const wr = p.win_rate;
    const bc = wr >= 60 ? 'badge-strong' : wr >= 50 ? 'badge-moderate' : 'badge-weak';
    return `<tr class="table-row">
      <td><span class="strategy-pill" style="background:var(--bg-lighter)">${escBt(k)}</span></td>
      <td class="num"><span class="score-pill ${bc}">${wr}%</span></td>
      <td class="num">${p.total}</td>
      <td class="num col-target">${p.wins}</td>
      <td class="num col-sl">${p.losses}</td>
    </tr>`;
  }).join('');
}

function escBt(s) { return s == null ? '' : String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
