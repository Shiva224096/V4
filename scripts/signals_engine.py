"""
signals_engine.py
Main orchestrator — runs all strategies across NSE 500 tickers.
Writes results to data/signals.json and data/last_updated.txt
"""

import os
import sys
import json
import time
import pandas as pd
from datetime import date, datetime
import pytz

# Allow imports from scripts/
sys.path.insert(0, os.path.dirname(__file__))
from bhavcopy_bulk import build_bhavcopy_history
from strategies import run_all_strategies
from patterns import get_active_patterns, get_pattern_label, pattern_score_bonus

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

MAX_STOCKS = 300   # GitHub Actions 6-hour limit safety cap
SLEEP_SEC  = 1.5   # Respect NSE rate limits


# ---------------------------------------------------------------------------
# Scoring logic (0–100)
# ---------------------------------------------------------------------------

def compute_score(df: pd.DataFrame, signal: dict, patterns: list[str]) -> int:
    score = 0

    # Volume > 2× 20-day average → +25
    try:
        vol_avg  = df["volume"].rolling(20).mean().iloc[-1]
        last_vol = df["volume"].iloc[-1]
        if last_vol > 2 * vol_avg:
            score += 25
    except Exception:
        pass

    # Strong candlestick pattern → +20
    score += pattern_score_bonus(patterns)

    # 52-week high breakout → +20
    if signal.get("strategy") == "52-Week High Break":
        score += 20
    elif "52w_high" in signal:
        score += 20

    # Multiple strategy confluence → +15 (handled at caller level)
    # RSI in ideal zone 40–60 → +10
    try:
        import pandas_ta as ta
        rsi = ta.rsi(df["close"], length=14)
        last_rsi = rsi.dropna().iloc[-1]
        if 40 <= last_rsi <= 60:
            score += 10
    except Exception:
        pass

    # Price above 50 SMA → +10
    try:
        import pandas_ta as ta
        sma50 = ta.sma(df["close"], length=50)
        if sma50 is not None:
            last_sma50 = sma50.dropna().iloc[-1]
            if df["close"].iloc[-1] > last_sma50:
                score += 10
    except Exception:
        pass

    return min(score, 100)


def score_badge(score: int) -> str:
    if score >= 80:
        return "Strong"
    elif score >= 60:
        return "Moderate"
    else:
        return "Weak"


# ---------------------------------------------------------------------------
# Sparkline — last 7 closes (normalised 0–100)
# ---------------------------------------------------------------------------

def build_sparkline(df: pd.DataFrame, n: int = 7) -> list[float]:
    closes = df["close"].tail(n).tolist()
    if not closes:
        return []
    mn, mx = min(closes), max(closes)
    rng = mx - mn or 1
    return [round((v - mn) / rng * 100, 1) for v in closes]


# ---------------------------------------------------------------------------
# Holiday check (NSE market holidays — simplified weekend check)
# ---------------------------------------------------------------------------

def is_market_day(d: date = None) -> bool:
    if d is None:
        d = date.today()
    # Skip weekends
    if d.weekday() in (5, 6):
        return False
    return True


# ---------------------------------------------------------------------------
# Load tickers
# ---------------------------------------------------------------------------

def load_tickers() -> list[str]:
    path = os.path.join(DATA_DIR, "nse_tickers.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        return df["symbol"].dropna().tolist()[:MAX_STOCKS]
    # Fallback: hardcoded top 20 blue chips
    return [
        "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK",
        "BHARTIARTL","KOTAKBANK","HINDUNILVR","ITC","LT",
        "AXISBANK","BAJFINANCE","SBIN","MARUTI","NESTLEIND",
        "TATAMOTORS","SUNPHARMA","WIPRO","ONGC","NTPC"
    ]


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

def run_engine():
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)

    if not is_market_day():
        print(f"[Engine] {now_ist.strftime('%A')} is a non-trading day. Generating report anyway for demo purposes.")

    tickers = load_tickers()
    print(f"[Engine] Processing {len(tickers)} tickers...")

    # 1. Fetch entire market history in bulk (takes 1-2 mins)
    print(f"[Engine] Downloading Bulk Bhavcopy History (this takes a minute)...")
    history_dict = build_bhavcopy_history(days=200)

    all_signals = []

    for i, symbol in enumerate(tickers):
        print(f"\n[{i+1}/{len(tickers)}] {symbol}")
        try:
            df = history_dict.get(symbol)
            if df is None or len(df) < 20:
                print(f"  Skipping {symbol} — insufficient data")
                continue

            signals = run_all_strategies(df)
            if not signals:
                continue

            # Detect patterns once per ticker
            patterns = get_active_patterns(df)
            pattern_label = get_pattern_label(patterns)

            # Compute confluence bonus
            confluence_bonus = 15 if len(signals) > 1 else 0

            # Aggregate: one record per strategy triggered
            for sig in signals:
                score = compute_score(df, sig, patterns) + confluence_bonus
                score = min(score, 100)
                record = {
                    "symbol":        symbol,
                    "exchange":      "NSE",
                    "strategy":      sig["strategy"],
                    "pattern":       pattern_label,
                    "entry":         sig.get("entry"),
                    "target":        sig.get("target"),
                    "stop_loss":     sig.get("stop_loss"),
                    "rr":            sig.get("rr"),
                    "score":         score,
                    "badge":         score_badge(score),
                    "sparkline":     build_sparkline(df),
                    "date":          df["date"].iloc[-1].strftime("%Y-%m-%d") if hasattr(df["date"].iloc[-1], "strftime") else str(df["date"].iloc[-1]),
                    "close":         round(float(df["close"].iloc[-1]), 2),
                }
                all_signals.append(record)

        except Exception as e:
            print(f"  [!] Error processing {symbol}: {e}")

    # Sort by score descending
    all_signals.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n[Engine] Total signals generated: {len(all_signals)}")
    return all_signals


# ---------------------------------------------------------------------------
# Save outputs
# ---------------------------------------------------------------------------

def save_signals(signals: list[dict]):
    path = os.path.join(DATA_DIR, "signals.json")
    with open(path, "w") as f:
        json.dump({
            "generated_at": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M IST"),
            "total":        len(signals),
            "signals":      signals,
        }, f, indent=2)
    print(f"[Engine] signals.json written: {path}")


def save_last_updated():
    path = os.path.join(DATA_DIR, "last_updated.txt")
    ts = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M IST")
    with open(path, "w") as f:
        f.write(ts)
    print(f"[Engine] last_updated.txt: {ts}")


if __name__ == "__main__":
    signals = run_engine()
    save_signals(signals)
    save_last_updated()
    print("[Engine] Done.")
