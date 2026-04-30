# SwingEdge — Indian Stock Market Swing Trading Signals 📈

> Fully automated swing trading signal engine for **NSE & BSE**.
> Runs daily at **9:00 AM IST** via GitHub Actions. Zero Yahoo Finance.

[![Daily Signals](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/daily_signals.yml/badge.svg)](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/daily_signals.yml)

---

## 🌐 Live Dashboard

**[https://YOUR_USERNAME.github.io/YOUR_REPO](https://YOUR_USERNAME.github.io/YOUR_REPO)**

---

## ⚡ Features

| Feature | Details |
|---|---|
| 📡 Data Sources | jugaad-data → NSE Direct API → Twelve Data → BSE Bhavcopy |
| 📊 Strategies | 10 swing trading strategies (EMA, MACD, RSI, Bollinger, Supertrend, etc.) |
| 🕯️ Patterns | 12 candlestick patterns via pandas-ta |
| 💯 Scoring | 0–100 confidence score per signal |
| 📧 Email | Daily HTML email at 9:00 AM IST via Gmail SMTP |
| 🌐 Dashboard | Dark-mode GitHub Pages UI with sparklines & filters |
| ⏱️ Schedule | GitHub Actions cron: Mon–Fri 9:00 AM IST |

---

## 📁 Project Structure

```
swing-trading-app/
├── .github/workflows/
│   ├── daily_signals.yml       # Main job — 9 AM IST Mon–Fri
│   └── weekly_tickers.yml      # Refreshes NSE ticker list Sunday
├── scripts/
│   ├── fetch_tickers.py        # NSE 500 + BSE ticker lists
│   ├── fetch_ohlcv.py          # 4-source waterfall data fetcher
│   ├── strategies.py           # 10 strategy functions
│   ├── patterns.py             # Candlestick detection (pandas-ta)
│   ├── signals_engine.py       # Main orchestrator
│   ├── email_report.py         # Gmail SMTP sender
│   └── generate_json.py        # Writes signals.json + demo mode
├── data/
│   ├── signals.json            # Auto-updated daily by Actions
│   ├── last_updated.txt        # Timestamp string
│   └── nse_tickers.csv         # NSE 500 symbols
├── frontend/
│   ├── index.html              # Dashboard
│   ├── style.css               # Dark-mode design system
│   └── app.js                  # Vanilla JS, Chart.js sparklines
├── requirements.txt
└── README.md
```

---

## 🚀 Setup Guide

### 1. Fork / Clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### 2. Install Python dependencies (local testing)

```bash
pip install -r requirements.txt
```

### 3. Generate demo signals for frontend dev

```bash
python scripts/generate_json.py --demo
```

### 4. Add GitHub Secrets

Go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value |
|---|---|
| `GMAIL_USER` | `yourgmail@gmail.com` |
| `GMAIL_PASS` | 16-char Gmail App Password |
| `RECIPIENT_EMAIL` | Email to receive signals |
| `TWELVE_DATA_KEY` | Free key from [twelvedata.com](https://twelvedata.com) |

#### How to get Gmail App Password:
1. Enable **2-Step Verification** on your Google Account
2. Go to **Google Account → Security → App Passwords**
3. Create password for "Mail"
4. Use the 16-character code as `GMAIL_PASS`

### 5. Enable GitHub Pages

- Go to **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: `main` | Folder: `/frontend`
- Save → Dashboard live at `https://YOUR_USERNAME.github.io/YOUR_REPO`

### 6. Update `app.js` with your GitHub details

Edit `frontend/app.js` lines 14–15:
```js
GITHUB_USER: 'YOUR_GITHUB_USERNAME',
GITHUB_REPO: 'YOUR_GITHUB_REPO',
```

### 7. Trigger the workflow manually to test

Go to **Actions → Daily Swing Signals → Run workflow**

---

## 📡 Data Source Waterfall

```
1. jugaad-data      ← Native NSE library, most reliable
2. NSE Direct API   ← Official NSE with session headers
3. Twelve Data      ← Free 800 req/day (no card needed)
4. BSE Bhavcopy     ← Full daily OHLCV dump (last resort)
```

---

## 📊 Strategies Implemented

| # | Strategy | Signal Condition |
|---|---|---|
| 1 | EMA Crossover | 9 EMA crosses above 21 EMA |
| 2 | MACD Crossover | MACD crosses above signal (below zero) |
| 3 | RSI Reversal | RSI dips below 30, crosses back above |
| 4 | Bollinger Squeeze | Price breaks upper band after squeeze |
| 5 | Supertrend Breakout | Trend flips bullish (ATR 10, Factor 3) |
| 6 | Volume Breakout | Resistance break with 2× avg volume |
| 7 | Inside Bar Breakout | Breakout above mother bar high |
| 8 | Golden Cross | 50 SMA crosses above 200 SMA |
| 9 | EMA Pullback | Bounce from 21 EMA in uptrend |
| 10 | 52-Week High Break | All-time high break with volume |

---

## 💯 Scoring Logic

| Condition | Points |
|---|---|
| Volume > 2× 20-day average | +25 |
| Strong candlestick pattern | +20 |
| 52-week high breakout | +20 |
| Multiple strategy confluence | +15 |
| RSI in ideal zone (40–60) | +10 |
| Price above 50 SMA | +10 |

**Badges:** 🟢 Strong (80–100) · 🟡 Moderate (60–79) · 🔴 Weak (<60)

---

## ⚠️ Disclaimer

> This tool is for **educational and research purposes only**.
> It does **not** constitute financial advice.
> Always do your own research before making any investment decisions.
> The authors are not responsible for any trading losses.

---

## 📜 License

MIT — free to use and modify.
