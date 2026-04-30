"""
build_standalone.py — Creates a self-contained frontend/standalone.html
for offline preview and browser-subagent testing.
Inlines CSS, JS, and signals data into one HTML file.
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# Load files
with open(os.path.join(BASE, 'data', 'signals.json'), encoding='utf-8') as f:
    data = json.load(f)
with open(os.path.join(BASE, 'frontend', 'index.html'), encoding='utf-8') as f:
    html = f.read()
with open(os.path.join(BASE, 'frontend', 'style.css'), encoding='utf-8') as f:
    css = f.read()
with open(os.path.join(BASE, 'frontend', 'app.js'), encoding='utf-8') as f:
    js = f.read()

signals_json = json.dumps(data, ensure_ascii=False)

# Shim that bypasses all network fetches and uses inline data
shim = f"""
window.__INLINE__ = {signals_json};
const _origFetchSignals = typeof fetchSignals !== 'undefined' ? fetchSignals : null;
function fetchSignals() {{
  setLoading(true);
  setRefreshSpinning(true);
  try {{
    const d = window.__INLINE__;
    allSignals = d.signals || [];
    updateStats(allSignals);
    applyFilters();
    updateLastUpdated(d.generated_at);
    updateMarketStatus();
    hideError();
    startAutoRefresh();
  }} catch(e) {{
    showError(e.message);
  }} finally {{
    setLoading(false);
    setRefreshSpinning(false);
  }}
}}
"""

# Replace external CSS and JS with inline versions
out = html
out = out.replace(
    '<link rel="stylesheet" href="style.css" />',
    f'<style>\n{css}\n</style>'
)
out = out.replace(
    '<script src="app.js"></script>',
    f'<script>\n{js}\n</script>\n<script>\n{shim}\n</script>'
)

dest = os.path.join(BASE, 'frontend', 'standalone.html')
with open(dest, 'w', encoding='utf-8') as f:
    f.write(out)

print(f"[build_standalone] Written to {dest}")
