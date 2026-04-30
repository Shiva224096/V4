"""
patterns.py
Candlestick pattern detection using pandas-ta.
No TA-Lib. No C compiler required.
"""

import pandas as pd
import pandas_ta as ta

PATTERN_ICONS = {
    "hammer":       "🔨 Hammer",
    "engulfing":    "🟢 Engulfing",
    "morningstar":  "⭐ Morning Star",
    "shootingstar": "🌠 Shooting Star",
    "doji":         "➕ Doji",
    "marubozu":     "📊 Marubozu",
    "eveningstar":  "🌇 Evening Star",
    "harami":       "🤝 Harami",
    "invertedhammer": "🔁 Inverted Hammer",
    "hangingman":   "🪢 Hanging Man",
    "piercingline": "🔪 Piercing Line",
    "darkcloudcover":"☁️ Dark Cloud",
}

BULLISH_PATTERNS = {
    "hammer", "engulfing", "morningstar", "doji",
    "invertedhammer", "piercingline", "marubozu", "harami"
}

BEARISH_PATTERNS = {
    "shootingstar", "eveningstar", "hangingman", "darkcloudcover"
}


def detect_patterns(df: pd.DataFrame) -> dict:
    """
    Detect candlestick patterns on the last candle.
    Returns dict: {pattern_name: True/False/value, ...}
    """
    if len(df) < 5:
        return {}

    o = df["open"]
    h = df["high"]
    l = df["low"]
    c = df["close"]

    detected: dict[str, bool] = {}

    for pattern_name in PATTERN_ICONS.keys():
        try:
            result = ta.cdl_pattern(o, h, l, c, name=pattern_name)
            if result is not None and not result.empty:
                last_val = result.iloc[-1]
                detected[pattern_name] = bool(last_val != 0)
        except Exception:
            # pandas-ta may not support every pattern name
            detected[pattern_name] = False

    return detected


def get_active_patterns(df: pd.DataFrame) -> list[str]:
    """Return list of pattern names detected on the last candle."""
    raw = detect_patterns(df)
    return [k for k, v in raw.items() if v]


def get_pattern_label(patterns: list[str]) -> str:
    """Return a user-friendly label for the first detected pattern."""
    for p in patterns:
        if p in PATTERN_ICONS:
            return PATTERN_ICONS[p]
    return "—"


def pattern_score_bonus(patterns: list[str]) -> int:
    """
    Return +20 if a strong bullish pattern is detected, 0 otherwise.
    This feeds into the confidence score.
    """
    for p in patterns:
        if p in BULLISH_PATTERNS:
            return 20
    return 0


if __name__ == "__main__":
    # Quick smoke test
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scripts.fetch_ohlcv import get_ohlcv

    df = get_ohlcv("RELIANCE", days=60)
    if df is not None:
        pats = get_active_patterns(df)
        print("Detected patterns:", pats)
        print("Label:", get_pattern_label(pats))
    else:
        print("No data")
