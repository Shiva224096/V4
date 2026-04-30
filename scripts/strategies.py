"""
strategies.py
10 swing trading strategy detectors.
All use pandas-ta only (no TA-Lib C compiler dependency).
Each function returns a dict with signal details or None.
"""

import pandas as pd
import pandas_ta as ta
import numpy as np


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _last(series: pd.Series):
    """Return the last non-NaN value of a series."""
    s = series.dropna()
    return s.iloc[-1] if len(s) else None


def _prev(series: pd.Series):
    """Return the second-to-last non-NaN value."""
    s = series.dropna()
    return s.iloc[-2] if len(s) >= 2 else None


# ---------------------------------------------------------------------------
# Strategy 1 — EMA Crossover (9 EMA crosses above 21 EMA)
# ---------------------------------------------------------------------------

def strategy_ema_crossover(df: pd.DataFrame) -> dict | None:
    if len(df) < 30:
        return None
    ema9  = ta.ema(df["close"], length=9)
    ema21 = ta.ema(df["close"], length=21)

    prev9, prev21 = _prev(ema9), _prev(ema21)
    last9, last21 = _last(ema9), _last(ema21)

    if None in (prev9, prev21, last9, last21):
        return None

    # Golden cross: was below, now above
    if prev9 <= prev21 and last9 > last21:
        entry = float(df["close"].iloc[-1])
        sl    = float(df["low"].iloc[-3:].min())
        tgt   = entry + 2 * (entry - sl)
        return {
            "strategy": "EMA Crossover",
            "entry":    round(entry, 2),
            "target":   round(tgt, 2),
            "stop_loss": round(sl, 2),
            "rr":       round((tgt - entry) / max(entry - sl, 0.01), 2),
        }
    return None


# ---------------------------------------------------------------------------
# Strategy 2 — MACD Crossover
# ---------------------------------------------------------------------------

def strategy_macd(df: pd.DataFrame) -> dict | None:
    if len(df) < 40:
        return None
    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd_df is None or macd_df.empty:
        return None

    macd_col   = [c for c in macd_df.columns if "MACD_" in c and "MACDs" not in c and "MACDh" not in c]
    signal_col = [c for c in macd_df.columns if "MACDs_" in c]
    hist_col   = [c for c in macd_df.columns if "MACDh_" in c]

    if not macd_col or not signal_col:
        return None

    macd_line   = macd_df[macd_col[0]]
    signal_line = macd_df[signal_col[0]]

    prev_m, prev_s = _prev(macd_line), _prev(signal_line)
    last_m, last_s = _last(macd_line), _last(signal_line)

    if None in (prev_m, prev_s, last_m, last_s):
        return None

    if prev_m <= prev_s and last_m > last_s and last_m < 0:
        entry = float(df["close"].iloc[-1])
        sl    = float(df["low"].iloc[-5:].min())
        tgt   = entry + 2 * (entry - sl)
        return {
            "strategy":  "MACD Crossover",
            "entry":     round(entry, 2),
            "target":    round(tgt, 2),
            "stop_loss": round(sl, 2),
            "rr":        round((tgt - entry) / max(entry - sl, 0.01), 2),
        }
    return None


# ---------------------------------------------------------------------------
# Strategy 3 — RSI Reversal (dip below 30, then crosses back above 30)
# ---------------------------------------------------------------------------

def strategy_rsi_reversal(df: pd.DataFrame) -> dict | None:
    if len(df) < 20:
        return None
    rsi = ta.rsi(df["close"], length=14)
    if rsi is None:
        return None

    prev_rsi = _prev(rsi)
    last_rsi = _last(rsi)

    if None in (prev_rsi, last_rsi):
        return None

    if prev_rsi < 30 and last_rsi >= 30:
        entry = float(df["close"].iloc[-1])
        sl    = float(df["low"].iloc[-3:].min())
        tgt   = entry + 2 * (entry - sl)
        return {
            "strategy":  "RSI Reversal",
            "entry":     round(entry, 2),
            "target":    round(tgt, 2),
            "stop_loss": round(sl, 2),
            "rr":        round((tgt - entry) / max(entry - sl, 0.01), 2),
            "rsi":       round(float(last_rsi), 1),
        }
    return None


# ---------------------------------------------------------------------------
# Strategy 4 — Bollinger Squeeze Breakout
# ---------------------------------------------------------------------------

def strategy_bollinger_squeeze(df: pd.DataFrame) -> dict | None:
    if len(df) < 30:
        return None
    bb = ta.bbands(df["close"], length=20, std=2)
    if bb is None or bb.empty:
        return None

    upper_col = [c for c in bb.columns if "BBU_" in c]
    lower_col = [c for c in bb.columns if "BBL_" in c]
    bw_col    = [c for c in bb.columns if "BBB_" in c]

    if not upper_col or not lower_col:
        return None

    upper = bb[upper_col[0]]
    bw    = bb[bw_col[0]] if bw_col else None

    last_close = float(df["close"].iloc[-1])
    prev_close = float(df["close"].iloc[-2])
    last_upper = float(_last(upper))
    prev_upper = float(_prev(upper))

    # Squeeze: bandwidth was at 20-period low, now price breaks upper band
    if bw is not None:
        bw_vals = bw.dropna().tail(20)
        is_squeeze = float(_last(bw)) <= float(bw_vals.min()) * 1.1
    else:
        is_squeeze = True

    if is_squeeze and prev_close <= prev_upper and last_close > last_upper:
        entry = last_close
        sl    = float(df["close"].iloc[-5:].min())
        tgt   = entry + 2 * (entry - sl)
        return {
            "strategy":  "Bollinger Squeeze",
            "entry":     round(entry, 2),
            "target":    round(tgt, 2),
            "stop_loss": round(sl, 2),
            "rr":        round((tgt - entry) / max(entry - sl, 0.01), 2),
        }
    return None


# ---------------------------------------------------------------------------
# Strategy 5 — Supertrend Breakout (ATR 10, Factor 3)
# ---------------------------------------------------------------------------

def strategy_supertrend(df: pd.DataFrame) -> dict | None:
    if len(df) < 20:
        return None
    try:
        st = ta.supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3)
        if st is None or st.empty:
            return None

        trend_col = [c for c in st.columns if "SUPERTd_" in c]
        sup_col   = [c for c in st.columns if c.startswith("SUPERT_") and "SUPERTd" not in c and "SUPERTl" not in c and "SUPERTs" not in c]

        if not trend_col:
            return None

        trend = st[trend_col[0]]
        prev_trend = _prev(trend)
        last_trend = _last(trend)

        # Trend flipped from -1 (bearish) to 1 (bullish) → breakout
        if prev_trend == -1 and last_trend == 1:
            entry = float(df["close"].iloc[-1])
            sl    = float(df["low"].iloc[-5:].min())
            tgt   = entry + 2 * (entry - sl)
            return {
                "strategy":  "Supertrend Breakout",
                "entry":     round(entry, 2),
                "target":    round(tgt, 2),
                "stop_loss": round(sl, 2),
                "rr":        round((tgt - entry) / max(entry - sl, 0.01), 2),
            }
    except Exception as e:
        print(f"    [Supertrend] Error: {e}")
    return None


# ---------------------------------------------------------------------------
# Strategy 6 — Volume Breakout
# ---------------------------------------------------------------------------

def strategy_volume_breakout(df: pd.DataFrame) -> dict | None:
    if len(df) < 25:
        return None
    vol_avg = df["volume"].rolling(20).mean()
    last_vol  = float(df["volume"].iloc[-1])
    avg_vol   = float(_last(vol_avg))

    # Price breaks recent resistance
    resistance = float(df["high"].iloc[-20:-1].max())
    last_close = float(df["close"].iloc[-1])
    prev_close = float(df["close"].iloc[-2])

    if last_vol > 2 * avg_vol and prev_close <= resistance and last_close > resistance:
        entry = last_close
        sl    = float(df["low"].iloc[-3:].min())
        tgt   = entry + 2 * (entry - sl)
        return {
            "strategy":    "Volume Breakout",
            "entry":       round(entry, 2),
            "target":      round(tgt, 2),
            "stop_loss":   round(sl, 2),
            "rr":          round((tgt - entry) / max(entry - sl, 0.01), 2),
            "vol_ratio":   round(last_vol / max(avg_vol, 1), 1),
        }
    return None


# ---------------------------------------------------------------------------
# Strategy 7 — Inside Bar Breakout
# ---------------------------------------------------------------------------

def strategy_inside_bar(df: pd.DataFrame) -> dict | None:
    if len(df) < 5:
        return None
    # Inside bar: today's range is fully within yesterday's range
    h  = df["high"].values
    l  = df["low"].values
    c  = df["close"].values

    # Day -2 is the "mother bar", day -1 is the inside bar, day 0 is breakout
    if len(h) < 3:
        return None

    mother_h, mother_l = h[-3], l[-3]
    inside_h, inside_l = h[-2], l[-2]
    today_c = c[-1]
    today_h = h[-1]

    is_inside = inside_h <= mother_h and inside_l >= mother_l
    breakout  = today_h > mother_h  # breakout above mother bar high

    if is_inside and breakout:
        entry = float(today_c)
        sl    = float(inside_l)
        tgt   = entry + 2 * (entry - sl)
        return {
            "strategy":  "Inside Bar Breakout",
            "entry":     round(entry, 2),
            "target":    round(tgt, 2),
            "stop_loss": round(sl, 2),
            "rr":        round((tgt - entry) / max(entry - sl, 0.01), 2),
        }
    return None


# ---------------------------------------------------------------------------
# Strategy 8 — Golden Cross (50 SMA above 200 SMA)
# ---------------------------------------------------------------------------

def strategy_golden_cross(df: pd.DataFrame) -> dict | None:
    if len(df) < 205:
        return None
    sma50  = ta.sma(df["close"], length=50)
    sma200 = ta.sma(df["close"], length=200)

    prev50, prev200 = _prev(sma50), _prev(sma200)
    last50, last200 = _last(sma50), _last(sma200)

    if None in (prev50, prev200, last50, last200):
        return None

    if prev50 <= prev200 and last50 > last200:
        entry = float(df["close"].iloc[-1])
        sl    = float(df["low"].iloc[-10:].min())
        tgt   = entry + 2 * (entry - sl)
        return {
            "strategy":  "Golden Cross",
            "entry":     round(entry, 2),
            "target":    round(tgt, 2),
            "stop_loss": round(sl, 2),
            "rr":        round((tgt - entry) / max(entry - sl, 0.01), 2),
        }
    return None


# ---------------------------------------------------------------------------
# Strategy 9 — EMA Pullback (bounce from 21 EMA in uptrend)
# ---------------------------------------------------------------------------

def strategy_ema_pullback(df: pd.DataFrame) -> dict | None:
    if len(df) < 30:
        return None
    ema21 = ta.ema(df["close"], length=21)
    ema50 = ta.ema(df["close"], length=50)

    last21 = _last(ema21)
    last50 = _last(ema50)
    last_close = float(df["close"].iloc[-1])
    prev_close = float(df["close"].iloc[-2])

    if None in (last21, last50):
        return None

    # Uptrend: price > 50 EMA
    # Pullback: price dipped near 21 EMA then bounced
    low_recent = float(df["low"].iloc[-3:].min())
    bounced    = prev_close <= float(last21) * 1.01 and last_close > float(last21)

    if float(last_close) > float(last50) and bounced:
        entry = last_close
        sl    = low_recent
        tgt   = entry + 2 * (entry - sl)
        return {
            "strategy":  "EMA Pullback",
            "entry":     round(entry, 2),
            "target":    round(tgt, 2),
            "stop_loss": round(sl, 2),
            "rr":        round((tgt - entry) / max(entry - sl, 0.01), 2),
        }
    return None


# ---------------------------------------------------------------------------
# Strategy 10 — 52-Week High Break
# ---------------------------------------------------------------------------

def strategy_52w_high_break(df: pd.DataFrame) -> dict | None:
    if len(df) < 50:
        return None
    periods = min(252, len(df) - 1)
    high_52w = float(df["high"].iloc[-periods:-1].max())
    last_close = float(df["close"].iloc[-1])
    prev_close = float(df["close"].iloc[-2])

    vol_avg   = float(df["volume"].rolling(20).mean().iloc[-1])
    last_vol  = float(df["volume"].iloc[-1])
    vol_surge = last_vol > 1.5 * vol_avg

    if prev_close <= high_52w and last_close > high_52w and vol_surge:
        entry = last_close
        sl    = float(df["low"].iloc[-5:].min())
        tgt   = entry + 2 * (entry - sl)
        return {
            "strategy":  "52-Week High Break",
            "entry":     round(entry, 2),
            "target":    round(tgt, 2),
            "stop_loss": round(sl, 2),
            "rr":        round((tgt - entry) / max(entry - sl, 0.01), 2),
            "52w_high":  round(high_52w, 2),
        }
    return None


# ---------------------------------------------------------------------------
# Master: run all strategies on a DataFrame
# ---------------------------------------------------------------------------

ALL_STRATEGIES = [
    strategy_ema_crossover,
    strategy_macd,
    strategy_rsi_reversal,
    strategy_bollinger_squeeze,
    strategy_supertrend,
    strategy_volume_breakout,
    strategy_inside_bar,
    strategy_golden_cross,
    strategy_ema_pullback,
    strategy_52w_high_break,
]


def run_all_strategies(df: pd.DataFrame) -> list[dict]:
    """Run all 10 strategies on df. Return list of triggered signals."""
    results = []
    for fn in ALL_STRATEGIES:
        try:
            sig = fn(df)
            if sig is not None:
                results.append(sig)
        except Exception as e:
            print(f"    [Strategy Error] {fn.__name__}: {e}")
    return results
