"""
backtester.py
Backtesting engine that replays historical strategy signals forward
to measure which strategies actually perform well.

For each strategy, it:
1. Scans the historical data looking for entry signals
2. Simulates holding for N days after each signal
3. Checks if Target or Stop-Loss was hit first
4. Computes win rate, avg gain, avg loss per strategy
5. Saves results to data/backtest_results.json

The signals_engine then uses these weights to boost or penalize strategies
in the confidence score.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(__file__))
from strategies import ALL_STRATEGIES
from patterns import get_active_patterns, BULLISH_PATTERNS, BEARISH_PATTERNS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Maximum holding period (trading days) after signal entry
MAX_HOLD_DAYS = 10


# ---------------------------------------------------------------------------
# Core: simulate a single trade
# ---------------------------------------------------------------------------

def simulate_trade(df: pd.DataFrame, signal_bar_idx: int, entry: float,
                   target: float, stop_loss: float,
                   hold_days: int = MAX_HOLD_DAYS) -> dict:
    """
    Simulate a trade starting from signal_bar_idx + 1.
    Check each subsequent bar to see if target or stop_loss is hit first.

    Returns:
        dict with keys: outcome ('win'|'loss'|'timeout'), pnl_pct, bars_held
    """
    start = signal_bar_idx + 1
    end   = min(start + hold_days, len(df))

    if start >= len(df):
        return {"outcome": "timeout", "pnl_pct": 0.0, "bars_held": 0}

    for i in range(start, end):
        high_i = float(df["high"].iloc[i])
        low_i  = float(df["low"].iloc[i])
        close_i = float(df["close"].iloc[i])

        # Stop loss hit
        if low_i <= stop_loss:
            pnl = (stop_loss - entry) / entry * 100
            return {"outcome": "loss", "pnl_pct": round(pnl, 2), "bars_held": i - signal_bar_idx}

        # Target hit
        if high_i >= target:
            pnl = (target - entry) / entry * 100
            return {"outcome": "win", "pnl_pct": round(pnl, 2), "bars_held": i - signal_bar_idx}

    # Timeout: exit at last close
    exit_price = float(df["close"].iloc[end - 1])
    pnl = (exit_price - entry) / entry * 100
    outcome = "win" if pnl > 0 else "loss"
    return {"outcome": outcome, "pnl_pct": round(pnl, 2), "bars_held": end - start}


# ---------------------------------------------------------------------------
# Walk-forward backtester for a single symbol
# ---------------------------------------------------------------------------

def backtest_symbol(df: pd.DataFrame, symbol: str,
                    lookback_start: int = 50,
                    step: int = 1) -> list[dict]:
    """
    Walk through the DataFrame and at each bar, check all strategies.
    When a strategy fires, simulate the trade forward.

    Args:
        df:              full OHLCV DataFrame for the symbol
        symbol:          ticker name for labeling
        lookback_start:  minimum bars needed before we start scanning
        step:            check every N-th bar (1 = every bar, 5 = weekly)

    Returns:
        List of trade result dicts
    """
    if len(df) < lookback_start + MAX_HOLD_DAYS + 5:
        return []

    trades = []
    # Walk from bar 'lookback_start' to len(df) - MAX_HOLD_DAYS
    scan_end = len(df) - MAX_HOLD_DAYS - 1

    for bar_idx in range(lookback_start, scan_end, step):
        # Slice df up to current bar (simulate "we only know data up to here")
        df_slice = df.iloc[:bar_idx + 1].copy()

        if len(df_slice) < 20:
            continue

        for fn in ALL_STRATEGIES:
            try:
                sig = fn(df_slice)
                if sig is None:
                    continue

                entry = sig["entry"]
                target = sig["target"]
                sl     = sig["stop_loss"]

                # Sanity: entry must be between sl and target
                if not (sl < entry < target):
                    continue

                # Simulate forward using full df
                result = simulate_trade(df, bar_idx, entry, target, sl)

                trades.append({
                    "symbol":    symbol,
                    "strategy":  sig["strategy"],
                    "bar_idx":   bar_idx,
                    "date":      str(df["date"].iloc[bar_idx]) if "date" in df.columns else str(bar_idx),
                    "entry":     entry,
                    "target":    target,
                    "stop_loss": sl,
                    "outcome":   result["outcome"],
                    "pnl_pct":   result["pnl_pct"],
                    "bars_held": result["bars_held"],
                })
            except Exception:
                continue

    return trades


# ---------------------------------------------------------------------------
# Backtest patterns too
# ---------------------------------------------------------------------------

def backtest_patterns_symbol(df: pd.DataFrame, symbol: str,
                             lookback_start: int = 50,
                             step: int = 5) -> list[dict]:
    """
    Walk through and check if bullish/bearish patterns had predictive power.
    A 'win' means price moved >1% in the expected direction within 5 days.
    """
    if len(df) < lookback_start + 10:
        return []

    results = []
    scan_end = len(df) - 6

    for bar_idx in range(lookback_start, scan_end, step):
        df_slice = df.iloc[:bar_idx + 1].copy()
        if len(df_slice) < 5:
            continue

        patterns = get_active_patterns(df_slice)
        if not patterns:
            continue

        entry = float(df["close"].iloc[bar_idx])
        # Check next 5 bars
        future_highs = df["high"].iloc[bar_idx + 1:bar_idx + 6].max()
        future_lows  = df["low"].iloc[bar_idx + 1:bar_idx + 6].min()

        up_pct   = (float(future_highs) - entry) / entry * 100
        down_pct = (entry - float(future_lows)) / entry * 100

        for p in patterns:
            if p in BULLISH_PATTERNS:
                outcome = "win" if up_pct > 1.0 else "loss"
                results.append({
                    "symbol":  symbol,
                    "pattern": p,
                    "type":    "bullish",
                    "outcome": outcome,
                    "up_pct":  round(up_pct, 2),
                    "down_pct": round(down_pct, 2),
                })
            elif p in BEARISH_PATTERNS:
                outcome = "win" if down_pct > 1.0 else "loss"
                results.append({
                    "symbol":  symbol,
                    "pattern": p,
                    "type":    "bearish",
                    "outcome": outcome,
                    "up_pct":  round(up_pct, 2),
                    "down_pct": round(down_pct, 2),
                })

    return results


# ---------------------------------------------------------------------------
# Aggregate results per strategy
# ---------------------------------------------------------------------------

def aggregate_results(all_trades: list[dict]) -> dict:
    """
    Aggregate individual trades into per-strategy statistics.
    Returns dict: { strategy_name: { wins, losses, total, win_rate, avg_gain, avg_loss, weight } }
    """
    from collections import defaultdict
    strat_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "gains": [], "losses_list": []})

    for t in all_trades:
        strat = t["strategy"]
        if t["outcome"] == "win":
            strat_stats[strat]["wins"] += 1
            strat_stats[strat]["gains"].append(t["pnl_pct"])
        else:
            strat_stats[strat]["losses"] += 1
            strat_stats[strat]["losses_list"].append(t["pnl_pct"])

    results = {}
    for strat, stats in strat_stats.items():
        total = stats["wins"] + stats["losses"]
        win_rate = stats["wins"] / total if total > 0 else 0
        avg_gain = sum(stats["gains"]) / len(stats["gains"]) if stats["gains"] else 0
        avg_loss = sum(stats["losses_list"]) / len(stats["losses_list"]) if stats["losses_list"] else 0

        # Dynamic weight: based on win rate and sample size
        # Minimum 10 trades for reliable weighting
        if total >= 10:
            if win_rate >= 0.60:
                weight = 15    # Bonus for proven strategies
            elif win_rate >= 0.50:
                weight = 5     # Slight bonus
            elif win_rate < 0.40:
                weight = -10   # Penalty for poor performers
            else:
                weight = 0
        else:
            weight = 0  # Not enough data to judge

        results[strat] = {
            "wins":     stats["wins"],
            "losses":   stats["losses"],
            "total":    total,
            "win_rate": round(win_rate * 100, 1),
            "avg_gain": round(avg_gain, 2),
            "avg_loss": round(avg_loss, 2),
            "weight":   weight,
        }

    return results


def aggregate_pattern_results(pattern_trades: list[dict]) -> dict:
    """Aggregate pattern backtest results."""
    from collections import defaultdict
    stats = defaultdict(lambda: {"wins": 0, "losses": 0})

    for t in pattern_trades:
        p = t["pattern"]
        if t["outcome"] == "win":
            stats[p]["wins"] += 1
        else:
            stats[p]["losses"] += 1

    results = {}
    for p, s in stats.items():
        total = s["wins"] + s["losses"]
        win_rate = s["wins"] / total if total > 0 else 0
        results[p] = {
            "wins": s["wins"],
            "losses": s["losses"],
            "total": total,
            "win_rate": round(win_rate * 100, 1),
        }
    return results


# ---------------------------------------------------------------------------
# Save / Load backtest results
# ---------------------------------------------------------------------------

def save_backtest_results(strategy_results: dict, pattern_results: dict):
    path = os.path.join(DATA_DIR, "backtest_results.json")
    payload = {
        "generated_at": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M IST"),
        "strategies": strategy_results,
        "patterns":   pattern_results,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[Backtester] Results saved to {path}")


def load_backtest_weights() -> dict:
    """
    Load strategy weights from backtest_results.json.
    Returns dict: { strategy_name: weight_int }
    Falls back to empty dict if file doesn't exist.
    """
    path = os.path.join(DATA_DIR, "backtest_results.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        return {
            strat: info.get("weight", 0)
            for strat, info in data.get("strategies", {}).items()
        }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Main: run backtest across all symbols with available data
# ---------------------------------------------------------------------------

def run_backtest(history_dict: dict, sample_size: int = 50, step: int = 3):
    """
    Run backtest on a sample of symbols from the history dict.
    Uses step=3 (check every 3rd bar) for speed.

    Args:
        history_dict:  { symbol: pd.DataFrame } from bhavcopy_bulk
        sample_size:   max number of symbols to test (for speed)
        step:          bar step for walk-forward scanning
    """
    # Pick symbols with enough data
    eligible = {
        sym: df for sym, df in history_dict.items()
        if len(df) >= 100
    }

    # Sample for speed
    symbols = list(eligible.keys())[:sample_size]
    print(f"[Backtester] Running backtest on {len(symbols)} symbols (step={step})...")

    all_trades = []
    all_pattern_trades = []

    for i, sym in enumerate(symbols):
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(symbols)}] Backtesting {sym}...")
        df = eligible[sym]
        trades = backtest_symbol(df, sym, lookback_start=50, step=step)
        all_trades.extend(trades)

        pat_trades = backtest_patterns_symbol(df, sym, lookback_start=50, step=step * 2)
        all_pattern_trades.extend(pat_trades)

    print(f"[Backtester] Total strategy trades simulated: {len(all_trades)}")
    print(f"[Backtester] Total pattern checks simulated: {len(all_pattern_trades)}")

    strategy_results = aggregate_results(all_trades)
    pattern_results  = aggregate_pattern_results(all_pattern_trades)

    # Print summary
    print("\n[Backtester] ═══ Strategy Performance ═══")
    for strat, info in sorted(strategy_results.items(), key=lambda x: x[1]["win_rate"], reverse=True):
        print(f"  {strat:25s}  WR: {info['win_rate']:5.1f}%  |  W:{info['wins']:3d}  L:{info['losses']:3d}  |  AvgG: {info['avg_gain']:+.2f}%  AvgL: {info['avg_loss']:+.2f}%  |  Wt: {info['weight']:+d}")

    print("\n[Backtester] ═══ Pattern Performance ═══")
    for pat, info in sorted(pattern_results.items(), key=lambda x: x[1]["win_rate"], reverse=True):
        print(f"  {pat:25s}  WR: {info['win_rate']:5.1f}%  |  W:{info['wins']:3d}  L:{info['losses']:3d}")

    save_backtest_results(strategy_results, pattern_results)
    return strategy_results, pattern_results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from bhavcopy_bulk import build_bhavcopy_history

    print("[Backtester] Downloading Bhavcopy history...")
    history = build_bhavcopy_history(days=200)

    if not history:
        print("[Backtester] No history data available. Exiting.")
        sys.exit(1)

    run_backtest(history, sample_size=50, step=3)
    print("[Backtester] Done.")
