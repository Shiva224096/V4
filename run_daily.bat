@echo off
REM =======================================================================
REM SwingEdge - Daily Signal Runner
REM Runs the trading engine locally to bypass NSE IP blocking.
REM =======================================================================

cd /d "%~dp0"

echo [SwingEdge] Starting daily signal generation...
python scripts/fetch_tickers.py
python scripts/signals_engine.py
python scripts/generate_json.py

echo [SwingEdge] Pushing to GitHub...
git add -f data/signals.json data/last_updated.txt data/nse_tickers.csv
git commit -m "data: automated daily local run"
git push

echo [SwingEdge] Done!
