'use strict';

const CONFIG = {
  GITHUB_USER: 'Shiva224096', GITHUB_REPO: 'V4',
  LOCAL_JSON: './data/signals.json', LOCAL_JSON_ALT: '../data/signals.json',
  LOCAL_UPDATED: './data/last_updated.txt',
  REFRESH_MS: 60_000, ANIMATION_STAGGER: 60, PAGE_SIZE: 50,
};
const RAW_BASE = `https://raw.githubusercontent.com/${CONFIG.GITHUB_USER}/${CONFIG.GITHUB_REPO}/main`;
const SIGNALS_URL = `${RAW_BASE}/data/signals.json`;
const UPDATED_URL = `${RAW_BASE}/data/last_updated.txt`;

let allSignals = [], filteredSig = [], refreshTimer = null, currentView = 'cards';
let currentPage = 1, sortCol = 'score', sortDir = 'desc', modalSignal = null;
const sparklineCharts = new Map();

// ═══ FETCH ═══
async function fetchSignals() {
  setLoading(true); setRefreshSpinning(true);
  try {
    let data;
    const sources = [SIGNALS_URL+`?t=${Date.now()}`, CONFIG.LOCAL_JSON, CONFIG.LOCAL_JSON_ALT];
    for (const src of sources) {
      try { const r = await fetch(src); if(!r.ok) throw 0; data = await r.json(); break; } catch(_){}
    }
    if (!data) throw new Error('All sources failed.');
    allSignals = data.signals || [];
    updateStats(allSignals); applyFilters();
    updateLastUpdated(data.generated_at); updateMarketStatus(); hideError(); startAutoRefresh();
  } catch (err) { showError(err.message); } finally { setLoading(false); setRefreshSpinning(false); }
}

// ═══ FILTERS ═══
function applyFilters() {
  const exchange = document.getElementById('filter-exchange').value;
  const strategy = document.getElementById('filter-strategy').value;
  const badge = document.getElementById('filter-badge').value;
  const minScore = parseInt(document.getElementById('filter-min-score').value,10)||0;
  const pattern = document.getElementById('filter-pattern').value;
  const search = document.getElementById('filter-search').value.trim().toUpperCase();
  filteredSig = allSignals.filter(s => {
    if (exchange && s.exchange !== exchange) return false;
    if (strategy && s.strategy !== strategy) return false;
    if (badge && s.badge !== badge) return false;
    if (s.score < minScore) return false;
    if (pattern && !(s.pattern||'').includes(pattern)) return false;
    if (search && !s.symbol.includes(search)) return false;
    return true;
  });
  document.getElementById('results-count').textContent = `${filteredSig.length} of ${allSignals.length} signals`;
  currentPage = 1;
  if (currentView === 'cards') renderCards(filteredSig); else renderTable(filteredSig);
}
function clearFilters() {
  ['filter-exchange','filter-strategy','filter-badge','filter-pattern'].forEach(id => document.getElementById(id).value='');
  document.getElementById('filter-min-score').value=0;
  document.getElementById('score-range-display').textContent='0';
  document.getElementById('filter-search').value='';
  applyFilters();
}

// ═══ VIEW TOGGLE ═══
function setView(v) {
  currentView = v;
  document.getElementById('btn-view-cards').classList.toggle('active', v==='cards');
  document.getElementById('btn-view-table').classList.toggle('active', v==='table');
  document.getElementById('cards-grid').hidden = v!=='cards';
  document.getElementById('table-container').hidden = v!=='table';
  if (v==='cards') renderCards(filteredSig); else renderTable(filteredSig);
}

// ═══ CARDS ═══
function renderCards(signals) {
  const grid = document.getElementById('cards-grid');
  sparklineCharts.forEach(c=>c.destroy()); sparklineCharts.clear();
  if (!signals.length) { grid.innerHTML=''; document.getElementById('empty-state').hidden=false; return; }
  document.getElementById('empty-state').hidden=true;
  const grouped = new Map();
  signals.forEach(s => { if(!grouped.has(s.symbol)) grouped.set(s.symbol,[]); grouped.get(s.symbol).push(s); });
  const groups = Array.from(grouped.values());
  grid.innerHTML = groups.map((g,i) => buildGroupCard(g,i)).join('');
  requestAnimationFrame(() => groups.forEach((g,i) => buildSparkline(`spark-${i}`, g[0].sparkline||[])));
}

function buildGroupCard(group, i) {
  const m = group.reduce((a,b) => a.score>b.score?a:b);
  const sc = m.score||0, rc = sc>=80?'#22c55e':sc>=60?'#eab308':'#ef4444';
  const rg = sc>=80?'rgba(34,197,94,0.4)':sc>=60?'rgba(234,179,8,0.35)':'rgba(239,68,68,0.35)';
  const rup = n => n!=null?`₹${Number(n).toLocaleString('en-IN',{maximumFractionDigits:2})}`:'—';
  const sigs = group.map((s,idx) => {
    const rr = s.rr?`${s.rr}:1`:'—', dt = s.date?formatDate(s.date):'—';
    return `${idx>0?'<hr class="signal-divider"/>':''}
    <div class="signal-item">
      <div class="card-strategy-row"><span class="card-strategy">${esc(s.strategy)}</span><span class="card-pattern">${esc(s.pattern||'—')}</span></div>
      <div class="card-prices"><div class="price-box"><div class="price-label">Entry</div><div class="price-value entry">${rup(s.entry)}</div></div><div class="price-box"><div class="price-label">Target 🎯</div><div class="price-value target">${rup(s.target)}</div></div><div class="price-box"><div class="price-label">Stop Loss 🛑</div><div class="price-value sl">${rup(s.stop_loss)}</div></div></div>
      <div class="card-rr-row" style="margin-bottom:0"><span class="rr-pill">⚖️ R:R ${esc(rr)}</span><span class="card-date">${esc(dt)}</span></div>
    </div>`;
  }).join('');
  return `<article class="signal-card badge-${esc(m.badge)}" role="listitem" style="animation-delay:${i*CONFIG.ANIMATION_STAGGER}ms" onclick="openModal(${JSON.stringify(m).replace(/"/g,'&quot;')})">
  <div class="card-header"><div class="card-symbol-wrap"><span class="card-symbol">${esc(m.symbol)}</span><span class="card-exchange-badge">${esc(m.exchange||'NSE')}</span><span class="card-close">LTP ${rup(m.close)}</span></div>
  <div class="score-badge"><div class="score-ring" style="--ring-color:${rc};background:conic-gradient(${rc} ${sc*3.6}deg,rgba(255,255,255,0.04) 0%);box-shadow:0 0 14px ${rg}"><span class="score-num">${sc}</span></div><span class="score-label-text" style="color:${rc}">${esc(m.badge)}</span></div></div>
  <div class="group-signals">${sigs}</div>
  <div class="sparkline-wrap"><canvas id="spark-${i}" height="44"></canvas></div></article>`;
}

// ═══ TABLE ═══
function renderTable(signals) {
  document.getElementById('empty-state').hidden = signals.length > 0;
  if (!signals.length) { document.getElementById('table-body').innerHTML=''; document.getElementById('pagination').innerHTML=''; return; }
  // Sort
  const sorted = [...signals].sort((a,b) => {
    let va=a[sortCol], vb=b[sortCol];
    if (typeof va==='string') { va=va.toLowerCase(); vb=(vb||'').toLowerCase(); }
    if (va<vb) return sortDir==='asc'?-1:1;
    if (va>vb) return sortDir==='asc'?1:-1;
    return 0;
  });
  const totalPages = Math.ceil(sorted.length/CONFIG.PAGE_SIZE);
  if (currentPage>totalPages) currentPage=totalPages;
  const start = (currentPage-1)*CONFIG.PAGE_SIZE, pageData = sorted.slice(start, start+CONFIG.PAGE_SIZE);
  const rup = n => n!=null?`₹${Number(n).toLocaleString('en-IN',{maximumFractionDigits:2})}`:'—';
  const tbody = document.getElementById('table-body');
  tbody.innerHTML = pageData.map(s => {
    const bc = s.badge==='Strong'?'badge-strong':s.badge==='Moderate'?'badge-moderate':'badge-weak';
    return `<tr class="table-row ${bc}" onclick="openModal(${JSON.stringify(s).replace(/"/g,'&quot;')})">
      <td class="col-symbol">${esc(s.symbol)}</td>
      <td><span class="strategy-pill">${esc(s.strategy)}</span></td>
      <td>${esc(s.pattern||'—')}</td>
      <td class="num">${rup(s.entry)}</td>
      <td class="num col-target">${rup(s.target)}</td>
      <td class="num col-sl">${rup(s.stop_loss)}</td>
      <td class="num">${s.rr?s.rr+':1':'—'}</td>
      <td class="num"><span class="score-pill ${bc}">${s.score}</span></td>
      <td><span class="badge-label ${bc}">${esc(s.badge)}</span></td>
      <td class="num">${s.date?formatDate(s.date):'—'}</td>
      <td><button class="btn-mini" onclick="event.stopPropagation();openModal(${JSON.stringify(s).replace(/"/g,'&quot;')})">📊</button></td>
    </tr>`;
  }).join('');
  // Sort indicators
  document.querySelectorAll('.signals-table th.sortable').forEach(th => {
    const icon = th.querySelector('.sort-icon');
    if (th.dataset.sort===sortCol) icon.textContent = sortDir==='asc'?'↑':'↓';
    else icon.textContent = '⇅';
  });
  // Pagination
  renderPagination(totalPages);
}
function sortTable(col) {
  if (sortCol===col) sortDir = sortDir==='asc'?'desc':'asc';
  else { sortCol=col; sortDir='desc'; }
  renderTable(filteredSig);
}
function renderPagination(total) {
  if (total<=1) { document.getElementById('pagination').innerHTML=''; return; }
  let html = `<button class="page-btn" ${currentPage<=1?'disabled':''} onclick="goPage(${currentPage-1})">‹</button>`;
  const range = 2;
  for (let p=1;p<=total;p++) {
    if (p===1||p===total||Math.abs(p-currentPage)<=range)
      html += `<button class="page-btn ${p===currentPage?'active':''}" onclick="goPage(${p})">${p}</button>`;
    else if (Math.abs(p-currentPage)===range+1) html += `<span class="page-dots">…</span>`;
  }
  html += `<button class="page-btn" ${currentPage>=total?'disabled':''} onclick="goPage(${currentPage+1})">›</button>`;
  document.getElementById('pagination').innerHTML = html;
}
function goPage(p) { currentPage=p; renderTable(filteredSig); document.getElementById('table-container').scrollIntoView({behavior:'smooth'}); }

// ═══ MODAL + CHART ═══
let modalChart = null;

function openModal(signal) {
  modalSignal = signal;
  const m = document.getElementById('chart-modal');
  document.getElementById('modal-title').textContent = signal.symbol;
  document.getElementById('modal-subtitle').textContent = `${signal.strategy} · Score ${signal.score} · ${signal.badge}`;
  const rup = n => n!=null?`₹${Number(n).toLocaleString('en-IN',{maximumFractionDigits:2})}`:'—';
  document.getElementById('modal-signal-info').innerHTML = `
    <div class="modal-info-grid">
      <div class="modal-info-item"><span class="mil">Strategy</span><span class="miv strategy-pill">${esc(signal.strategy)}</span></div>
      <div class="modal-info-item"><span class="mil">Pattern</span><span class="miv">${esc(signal.pattern||'—')}</span></div>
      <div class="modal-info-item"><span class="mil">Entry</span><span class="miv">${rup(signal.entry)}</span></div>
      <div class="modal-info-item"><span class="mil">Target 🎯</span><span class="miv col-target">${rup(signal.target)}</span></div>
      <div class="modal-info-item"><span class="mil">Stop Loss 🛑</span><span class="miv col-sl">${rup(signal.stop_loss)}</span></div>
      <div class="modal-info-item"><span class="mil">R:R</span><span class="miv">${signal.rr?signal.rr+':1':'—'}</span></div>
    </div>`;

  // Build candlestick chart
  renderCandlestickChart(signal);

  // Build pattern explanation
  renderPatternExplanation(signal);

  m.hidden = false; document.body.style.overflow = 'hidden';
}

function renderCandlestickChart(signal) {
  const container = document.getElementById('candlestick-chart');
  container.innerHTML = '';

  const ohlcv = signal.ohlcv;
  if (!ohlcv || !ohlcv.length || typeof LightweightCharts === 'undefined') {
    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:350px;color:var(--text-muted)">No chart data available. Run the engine locally to generate OHLCV data.</div>';
    return;
  }

  // Destroy previous chart
  if (modalChart) { modalChart.remove(); modalChart = null; }

  const chart = LightweightCharts.createChart(container, {
    width: container.clientWidth, height: 350,
    layout: { background: { type: 'solid', color: '#0a1628' }, textColor: '#7fa8d0', fontSize: 12 },
    grid: { vertLines: { color: 'rgba(59,130,246,0.06)' }, horzLines: { color: 'rgba(59,130,246,0.06)' } },
    crosshair: { mode: 0 },
    rightPriceScale: { borderColor: 'rgba(59,130,246,0.2)' },
    timeScale: { borderColor: 'rgba(59,130,246,0.2)', timeVisible: false },
  });
  modalChart = chart;

  // Candlestick series
  const candleSeries = chart.addCandlestickSeries({
    upColor: '#22c55e', downColor: '#ef4444',
    borderUpColor: '#22c55e', borderDownColor: '#ef4444',
    wickUpColor: '#22c55e', wickDownColor: '#ef4444',
  });
  candleSeries.setData(ohlcv);

  // Entry / Target / SL price lines
  if (signal.entry) candleSeries.createPriceLine({ price: signal.entry, color: '#3b82f6', lineWidth: 2, lineStyle: 2, title: 'Entry' });
  if (signal.target) candleSeries.createPriceLine({ price: signal.target, color: '#22c55e', lineWidth: 1, lineStyle: 1, title: 'Target 🎯' });
  if (signal.stop_loss) candleSeries.createPriceLine({ price: signal.stop_loss, color: '#ef4444', lineWidth: 1, lineStyle: 1, title: 'Stop Loss 🛑' });

  // Pattern markers on the last N candles
  const patterns = signal.pattern_info || [];
  if (patterns.length > 0) {
    const markers = [];
    patterns.forEach(p => {
      const nCandles = p.candles || 1;
      const isBullish = p.type === 'bullish';
      // Mark the last candle of the pattern
      const lastIdx = ohlcv.length - 1;
      const markerIdx = lastIdx; // Pattern detected on last candle(s)

      markers.push({
        time: ohlcv[markerIdx].time,
        position: isBullish ? 'belowBar' : 'aboveBar',
        color: isBullish ? '#22c55e' : '#ef4444',
        shape: isBullish ? 'arrowUp' : 'arrowDown',
        text: p.name,
      });

      // For multi-candle patterns, also mark the starting candle
      if (nCandles > 1) {
        const startIdx = Math.max(0, lastIdx - nCandles + 1);
        if (startIdx !== markerIdx) {
          markers.push({
            time: ohlcv[startIdx].time,
            position: 'belowBar',
            color: isBullish ? 'rgba(34,197,94,0.5)' : 'rgba(239,68,68,0.5)',
            shape: 'circle',
            text: `← ${nCandles}-candle pattern starts`,
          });
        }
      }
    });
    // Sort markers by time
    markers.sort((a, b) => a.time < b.time ? -1 : 1);
    candleSeries.setMarkers(markers);
  }

  chart.timeScale().fitContent();

  // Resize handler
  const ro = new ResizeObserver(() => { chart.applyOptions({ width: container.clientWidth }); });
  ro.observe(container);
  container._ro = ro;
}

function renderPatternExplanation(signal) {
  const el = document.getElementById('modal-pattern-explain');
  const patterns = signal.pattern_info || [];
  if (!patterns.length) { el.innerHTML = ''; return; }

  el.innerHTML = `
    <div class="pattern-explain-header">📖 Pattern Analysis</div>
    <div class="pattern-explain-list">
      ${patterns.map(p => `
        <div class="pattern-explain-item ${p.type}">
          <div class="pattern-explain-name">${esc(p.name)}</div>
          <div class="pattern-explain-meta">
            <span class="pattern-type-badge ${p.type}">${p.type === 'bullish' ? '🟢 Bullish' : '🔴 Bearish'}</span>
            <span class="pattern-candle-count">${p.candles}-candle pattern</span>
          </div>
          <div class="pattern-explain-desc">${esc(p.description)}</div>
        </div>
      `).join('')}
    </div>`;
}

function closeModal() {
  document.getElementById('chart-modal').hidden = true;
  document.body.style.overflow = '';
  if (modalChart) { modalChart.remove(); modalChart = null; }
  const container = document.getElementById('candlestick-chart');
  if (container._ro) container._ro.disconnect();
  modalSignal = null;
}
function openTradingViewChart() {
  if (!modalSignal) return;
  const url = `https://www.tradingview.com/chart/?symbol=NSE:${modalSignal.symbol}&interval=D`;
  window.open(url, '_blank');
}
function openTradingViewLink() {
  if (!modalSignal) return;
  const url = `https://www.tradingview.com/symbols/NSE-${modalSignal.symbol}/`;
  window.open(url, '_blank');
}

// ═══ SPARKLINE ═══
function buildSparkline(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas||!data.length) return;
  const isUp = data[data.length-1]>=data[0], lc = isUp?'#22c55e':'#ef4444', fc = isUp?'rgba(34,197,94,0.08)':'rgba(239,68,68,0.08)';
  const chart = new Chart(canvas, {
    type:'line', data:{ labels:data.map((_,i)=>`D-${data.length-1-i}`), datasets:[{data,borderColor:lc,borderWidth:1.8,backgroundColor:fc,fill:true,tension:0.4,pointRadius:0,pointHoverRadius:3,pointHoverBackgroundColor:lc}]},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:600,easing:'easeOutCubic'},plugins:{legend:{display:false},tooltip:{mode:'index',intersect:false,backgroundColor:'rgba(13,27,46,0.95)',titleColor:'#7fa8d0',bodyColor:'#f0f6ff',borderColor:'rgba(59,130,246,0.3)',borderWidth:1,callbacks:{label:ctx=>` ${ctx.parsed.y.toFixed(1)}`}}},scales:{x:{display:false},y:{display:false,min:-5,max:105}},interaction:{mode:'nearest',axis:'x',intersect:false}}
  });
  sparklineCharts.set(canvasId, chart);
}

// ═══ STATS ═══
function updateStats(signals) {
  const strong=signals.filter(s=>s.badge==='Strong').length, moderate=signals.filter(s=>s.badge==='Moderate').length;
  const weak=signals.filter(s=>s.badge==='Weak').length, strats=new Set(signals.map(s=>s.strategy)).size;
  animateCount('stat-total-val',signals.length); animateCount('stat-strong-val',strong);
  animateCount('stat-moderate-val',moderate); animateCount('stat-weak-val',weak); animateCount('stat-strategies-val',strats);
}
function animateCount(id,target) {
  const el=document.getElementById(id); if(!el) return;
  let s=0; const step=Math.ceil(target/20);
  const iv=setInterval(()=>{s=Math.min(s+step,target);el.textContent=s;if(s>=target)clearInterval(iv);},30);
}

// ═══ MARKET STATUS ═══
function updateMarketStatus() {
  const now=new Date(), ist=new Date(now.toLocaleString('en-US',{timeZone:'Asia/Kolkata'}));
  const h=ist.getHours(),m=ist.getMinutes(),dow=ist.getDay(),mins=h*60+m;
  const isWeekday=dow>=1&&dow<=5, isOpen=isWeekday&&mins>=9*60+15&&mins<15*60+30;
  const dot=document.getElementById('status-dot'), text=document.getElementById('status-text');
  if(isOpen){dot.className='status-dot open';text.textContent='Market Open';text.style.color='#22c55e';}
  else{dot.className='status-dot closed';text.textContent=!isWeekday?'Weekend':mins<9*60+15?'Pre-Market':'Market Closed';text.style.color='#ef4444';}
}

// ═══ HELPERS ═══
function setLoading(s){document.getElementById('loading-state').hidden=!s;document.getElementById('cards-grid').hidden=s;document.getElementById('table-container').hidden=s||currentView!=='table';}
function showError(msg){document.getElementById('error-state').hidden=false;document.getElementById('error-msg').textContent=msg;document.getElementById('loading-state').hidden=true;}
function hideError(){document.getElementById('error-state').hidden=true;}
function updateLastUpdated(ts){if(ts)document.getElementById('updated-text').textContent=`Updated: ${ts.trim()}`;}
function setRefreshSpinning(on){const i=document.getElementById('refresh-icon');if(on)i.classList.add('spinning');else i.classList.remove('spinning');}
function startAutoRefresh(){clearInterval(refreshTimer);refreshTimer=setInterval(fetchSignals,CONFIG.REFRESH_MS);}
function formatDate(str){try{return new Date(str).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'});}catch(_){return str;}}
function esc(s){return s==null?'':String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

// ═══ EVENTS ═══
function bindFilters() {
  ['filter-exchange','filter-strategy','filter-badge','filter-pattern','filter-search'].forEach(id=>{
    document.getElementById(id)?.addEventListener('input',applyFilters);
    document.getElementById(id)?.addEventListener('change',applyFilters);
  });
  const r=document.getElementById('filter-min-score'),d=document.getElementById('score-range-display');
  r?.addEventListener('input',()=>{d.textContent=r.value;applyFilters();});
  document.getElementById('chart-modal')?.addEventListener('click',e=>{if(e.target.id==='chart-modal')closeModal();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
}

// ═══ BOOT ═══
document.addEventListener('DOMContentLoaded',()=>{bindFilters();updateMarketStatus();setInterval(updateMarketStatus,60000);fetchSignals();});
