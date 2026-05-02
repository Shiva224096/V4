@echo off
echo ========================================
echo  SwingEdge - Fundamental Analysis Engine
echo  Running weekly scan...
echo ========================================

cd /d "%~dp0"

echo.
echo [1/3] Running Fundamental Engine (yfinance)...
python scripts/fundamental_engine.py --max 500
if errorlevel 1 (
    echo [ERROR] Fundamental engine failed!
    pause
    exit /b 1
)

echo.
echo [2/3] Adding fundamentals.json to git...
git add -f data/fundamentals.json

echo.
echo [3/3] Committing and pushing...
git commit -m "Update fundamentals data %date% %time:~0,5%"
git push

echo.
echo ========================================
echo  Done! Fundamentals updated.
echo ========================================
timeout /t 5
