"""
patterns.py
Candlestick pattern detection using pure OHLC math.
No TA-Lib, no pandas-ta cdl_pattern dependency.
Detects 16 patterns reliably on the last 1-3 candles.
"""

import pandas as pd
import numpy as np


# ── Pattern Icons ──────────────────────────────────────────────────────────

PATTERN_ICONS = {
    # Bullish
    "hammer":           "🔨 Hammer",
    "inverted_hammer":  "🔁 Inverted Hammer",
    "bullish_engulfing":"🟢 Bullish Engulfing",
    "morning_star":     "⭐ Morning Star",
    "bullish_marubozu": "📊 Bullish Marubozu",
    "piercing_line":    "🔪 Piercing Line",
    "bullish_harami":   "🤝 Bullish Harami",
    "three_white":      "🏳️ Three White Soldiers",
    "tweezer_bottom":   "🔧 Tweezer Bottom",
    "dragonfly_doji":   "🐉 Dragonfly Doji",
    # Bearish
    "shooting_star":    "🌠 Shooting Star",
    "evening_star":     "🌇 Evening Star",
    "bearish_engulfing":"🔴 Bearish Engulfing",
    "dark_cloud":       "☁️ Dark Cloud Cover",
    "hanging_man":      "🪢 Hanging Man",
    "three_black":      "⬛ Three Black Crows",
}

BULLISH_PATTERNS = {
    "hammer", "inverted_hammer", "bullish_engulfing", "morning_star",
    "bullish_marubozu", "piercing_line", "bullish_harami",
    "three_white", "tweezer_bottom", "dragonfly_doji",
}

BEARISH_PATTERNS = {
    "shooting_star", "evening_star", "bearish_engulfing",
    "dark_cloud", "hanging_man", "three_black",
}

# Strong patterns get more score bonus
STRONG_BULLISH = {
    "bullish_engulfing", "morning_star", "three_white",
    "piercing_line", "bullish_marubozu",
}

MODERATE_BULLISH = {
    "hammer", "inverted_hammer", "bullish_harami",
    "tweezer_bottom", "dragonfly_doji",
}

# How many candles each pattern spans (for chart highlighting)
PATTERN_CANDLES = {
    "hammer": 1, "inverted_hammer": 1, "bullish_marubozu": 1, "dragonfly_doji": 1,
    "shooting_star": 1, "hanging_man": 1,
    "bullish_engulfing": 2, "bearish_engulfing": 2, "piercing_line": 2,
    "dark_cloud": 2, "bullish_harami": 2, "tweezer_bottom": 2,
    "morning_star": 3, "evening_star": 3, "three_white": 3, "three_black": 3,
}

# Short descriptions for chart annotations
PATTERN_DESCRIPTIONS = {
    "hammer":           "Small body at top, long lower shadow signals buyers stepping in at support",
    "inverted_hammer":  "Small body at bottom, long upper shadow hints at buying pressure emerging",
    "bullish_engulfing":"Current bullish candle fully engulfs previous bearish candle — strong reversal",
    "morning_star":     "3-candle reversal: bearish → indecision star → bullish close above midpoint",
    "bullish_marubozu": "Full-bodied bullish candle with almost no shadows — pure buying pressure",
    "piercing_line":    "Opens below prior low, closes above 50% of prior body — bulls fighting back",
    "bullish_harami":   "Small bullish body inside prior large bearish body — selling momentum fading",
    "three_white":      "Three consecutive strong bullish candles — powerful uptrend confirmation",
    "tweezer_bottom":   "Two candles with matching lows — strong support level identified",
    "dragonfly_doji":   "Open = Close = High with long lower shadow — rejection of lower prices",
    "shooting_star":    "Small body at bottom, long upper shadow after uptrend — bearish reversal",
    "evening_star":     "3-candle reversal: bullish → star → bearish close below midpoint",
    "bearish_engulfing":"Current bearish candle fully engulfs prior bullish — distribution signal",
    "dark_cloud":       "Opens above prior high, closes below 50% of prior body — sellers in control",
    "hanging_man":      "Hammer-shaped candle after uptrend — potential trend exhaustion",
    "three_black":      "Three consecutive strong bearish candles — powerful downtrend confirmation",
}


# ── Helpers ────────────────────────────────────────────────────────────────

def _body(o, c):
    """Absolute body size."""
    return abs(c - o)

def _range(h, l):
    """Full candle range."""
    return h - l

def _upper_shadow(o, h, c):
    return h - max(o, c)

def _lower_shadow(o, l, c):
    return min(o, c) - l

def _is_bullish(o, c):
    return c > o

def _is_bearish(o, c):
    return c < o

def _body_pct(o, h, l, c):
    """Body as percentage of total range."""
    r = _range(h, l)
    if r == 0:
        return 0
    return _body(o, c) / r


# ── Individual Pattern Detectors ───────────────────────────────────────────
# Each returns True/False for the LAST candle(s) in the arrays.
# o, h, l, c are numpy arrays of the last N candles.

def _detect_hammer(o, h, l, c):
    """Hammer: small body at top, long lower shadow (≥2x body), small upper shadow."""
    if len(o) < 1:
        return False
    body = _body(o[-1], c[-1])
    rng = _range(h[-1], l[-1])
    if rng == 0:
        return False
    lower = _lower_shadow(o[-1], l[-1], c[-1])
    upper = _upper_shadow(o[-1], h[-1], c[-1])
    return (
        lower >= 2 * body
        and upper <= body * 0.5
        and body > 0
        and _body_pct(o[-1], h[-1], l[-1], c[-1]) < 0.4
    )

def _detect_inverted_hammer(o, h, l, c):
    """Inverted Hammer: small body at bottom, long upper shadow, small lower shadow."""
    if len(o) < 1:
        return False
    body = _body(o[-1], c[-1])
    rng = _range(h[-1], l[-1])
    if rng == 0:
        return False
    lower = _lower_shadow(o[-1], l[-1], c[-1])
    upper = _upper_shadow(o[-1], h[-1], c[-1])
    return (
        upper >= 2 * body
        and lower <= body * 0.5
        and body > 0
        and _body_pct(o[-1], h[-1], l[-1], c[-1]) < 0.4
    )

def _detect_bullish_engulfing(o, h, l, c):
    """Bullish Engulfing: prev bearish candle fully engulfed by current bullish candle."""
    if len(o) < 2:
        return False
    return (
        _is_bearish(o[-2], c[-2])
        and _is_bullish(o[-1], c[-1])
        and o[-1] <= c[-2]      # current open <= prev close
        and c[-1] >= o[-2]      # current close >= prev open
        and _body(o[-1], c[-1]) > _body(o[-2], c[-2])
    )

def _detect_bearish_engulfing(o, h, l, c):
    """Bearish Engulfing: prev bullish candle fully engulfed by current bearish candle."""
    if len(o) < 2:
        return False
    return (
        _is_bullish(o[-2], c[-2])
        and _is_bearish(o[-1], c[-1])
        and o[-1] >= c[-2]
        and c[-1] <= o[-2]
        and _body(o[-1], c[-1]) > _body(o[-2], c[-2])
    )

def _detect_morning_star(o, h, l, c):
    """Morning Star: 3-candle pattern — bearish, small body (star), bullish."""
    if len(o) < 3:
        return False
    body0 = _body(o[-3], c[-3])
    body1 = _body(o[-2], c[-2])
    body2 = _body(o[-1], c[-1])
    return (
        _is_bearish(o[-3], c[-3])
        and body1 < body0 * 0.5          # star has small body
        and _is_bullish(o[-1], c[-1])
        and c[-1] > (o[-3] + c[-3]) / 2  # closes above midpoint of first candle
        and body2 > body1
    )

def _detect_evening_star(o, h, l, c):
    """Evening Star: bullish, small body (star), bearish."""
    if len(o) < 3:
        return False
    body0 = _body(o[-3], c[-3])
    body1 = _body(o[-2], c[-2])
    body2 = _body(o[-1], c[-1])
    return (
        _is_bullish(o[-3], c[-3])
        and body1 < body0 * 0.5
        and _is_bearish(o[-1], c[-1])
        and c[-1] < (o[-3] + c[-3]) / 2
        and body2 > body1
    )

def _detect_bullish_marubozu(o, h, l, c):
    """Bullish Marubozu: strong bullish candle, almost no shadows (body > 90% of range)."""
    if len(o) < 1:
        return False
    return (
        _is_bullish(o[-1], c[-1])
        and _body_pct(o[-1], h[-1], l[-1], c[-1]) >= 0.90
        and _range(h[-1], l[-1]) > 0
    )

def _detect_piercing_line(o, h, l, c):
    """Piercing Line: prev bearish, current opens below prev low, closes above midpoint of prev body."""
    if len(o) < 2:
        return False
    mid_prev = (o[-2] + c[-2]) / 2
    return (
        _is_bearish(o[-2], c[-2])
        and _is_bullish(o[-1], c[-1])
        and o[-1] < l[-2]
        and c[-1] > mid_prev
        and c[-1] < o[-2]
    )

def _detect_dark_cloud(o, h, l, c):
    """Dark Cloud Cover: prev bullish, current opens above prev high, closes below midpoint of prev body."""
    if len(o) < 2:
        return False
    mid_prev = (o[-2] + c[-2]) / 2
    return (
        _is_bullish(o[-2], c[-2])
        and _is_bearish(o[-1], c[-1])
        and o[-1] > h[-2]
        and c[-1] < mid_prev
        and c[-1] > o[-2]
    )

def _detect_bullish_harami(o, h, l, c):
    """Bullish Harami: prev bearish with large body, current bullish with body inside prev body."""
    if len(o) < 2:
        return False
    return (
        _is_bearish(o[-2], c[-2])
        and _is_bullish(o[-1], c[-1])
        and c[-1] <= o[-2]     # current close within prev body
        and o[-1] >= c[-2]     # current open within prev body
        and _body(o[-1], c[-1]) < _body(o[-2], c[-2])
    )

def _detect_shooting_star(o, h, l, c):
    """Shooting Star: small body at bottom, long upper shadow, small lower shadow (after an uptrend)."""
    if len(o) < 2:
        return False
    body = _body(o[-1], c[-1])
    rng = _range(h[-1], l[-1])
    if rng == 0:
        return False
    upper = _upper_shadow(o[-1], h[-1], c[-1])
    lower = _lower_shadow(o[-1], l[-1], c[-1])
    # Verify prior uptrend: previous close > close 2 back
    prior_up = c[-2] > c[-3] if len(o) >= 3 else True
    return (
        upper >= 2 * body
        and lower <= body * 0.5
        and body > 0
        and _body_pct(o[-1], h[-1], l[-1], c[-1]) < 0.4
        and prior_up
    )

def _detect_hanging_man(o, h, l, c):
    """Hanging Man: hammer shape but after an uptrend."""
    if len(o) < 3:
        return False
    # Verify prior uptrend
    prior_up = c[-2] > c[-3]
    body = _body(o[-1], c[-1])
    rng = _range(h[-1], l[-1])
    if rng == 0:
        return False
    lower = _lower_shadow(o[-1], l[-1], c[-1])
    upper = _upper_shadow(o[-1], h[-1], c[-1])
    return (
        lower >= 2 * body
        and upper <= body * 0.5
        and body > 0
        and _body_pct(o[-1], h[-1], l[-1], c[-1]) < 0.4
        and prior_up
    )

def _detect_three_white(o, h, l, c):
    """Three White Soldiers: 3 consecutive bullish candles, each closing higher with big bodies."""
    if len(o) < 3:
        return False
    return (
        _is_bullish(o[-3], c[-3])
        and _is_bullish(o[-2], c[-2])
        and _is_bullish(o[-1], c[-1])
        and c[-1] > c[-2] > c[-3]
        and o[-2] > o[-3] and o[-1] > o[-2]
        and _body_pct(o[-3], h[-3], l[-3], c[-3]) > 0.5
        and _body_pct(o[-2], h[-2], l[-2], c[-2]) > 0.5
        and _body_pct(o[-1], h[-1], l[-1], c[-1]) > 0.5
    )

def _detect_three_black(o, h, l, c):
    """Three Black Crows: 3 consecutive bearish candles, each closing lower with big bodies."""
    if len(o) < 3:
        return False
    return (
        _is_bearish(o[-3], c[-3])
        and _is_bearish(o[-2], c[-2])
        and _is_bearish(o[-1], c[-1])
        and c[-1] < c[-2] < c[-3]
        and o[-2] < o[-3] and o[-1] < o[-2]
        and _body_pct(o[-3], h[-3], l[-3], c[-3]) > 0.5
        and _body_pct(o[-2], h[-2], l[-2], c[-2]) > 0.5
        and _body_pct(o[-1], h[-1], l[-1], c[-1]) > 0.5
    )

def _detect_tweezer_bottom(o, h, l, c):
    """Tweezer Bottom: two candles with nearly identical lows, first bearish second bullish."""
    if len(o) < 2:
        return False
    low_diff = abs(l[-1] - l[-2])
    avg_range = (_range(h[-2], l[-2]) + _range(h[-1], l[-1])) / 2
    if avg_range == 0:
        return False
    return (
        _is_bearish(o[-2], c[-2])
        and _is_bullish(o[-1], c[-1])
        and (low_diff / avg_range) < 0.05  # lows within 5% of avg range
    )

def _detect_dragonfly_doji(o, h, l, c):
    """Dragonfly Doji: open ≈ close ≈ high, long lower shadow."""
    if len(o) < 1:
        return False
    rng = _range(h[-1], l[-1])
    if rng == 0:
        return False
    body = _body(o[-1], c[-1])
    lower = _lower_shadow(o[-1], l[-1], c[-1])
    upper = _upper_shadow(o[-1], h[-1], c[-1])
    return (
        body / rng < 0.1       # very small body
        and lower >= rng * 0.6  # long lower shadow
        and upper < rng * 0.1   # almost no upper shadow
    )


# ── Master Detection Registry ─────────────────────────────────────────────

PATTERN_DETECTORS = {
    "hammer":           _detect_hammer,
    "inverted_hammer":  _detect_inverted_hammer,
    "bullish_engulfing":_detect_bullish_engulfing,
    "bearish_engulfing":_detect_bearish_engulfing,
    "morning_star":     _detect_morning_star,
    "evening_star":     _detect_evening_star,
    "bullish_marubozu": _detect_bullish_marubozu,
    "piercing_line":    _detect_piercing_line,
    "dark_cloud":       _detect_dark_cloud,
    "bullish_harami":   _detect_bullish_harami,
    "shooting_star":    _detect_shooting_star,
    "hanging_man":      _detect_hanging_man,
    "three_white":      _detect_three_white,
    "three_black":      _detect_three_black,
    "tweezer_bottom":   _detect_tweezer_bottom,
    "dragonfly_doji":   _detect_dragonfly_doji,
}


# ── Public API ─────────────────────────────────────────────────────────────

def detect_patterns(df: pd.DataFrame) -> dict:
    """
    Detect candlestick patterns on the last candle(s).
    Returns dict: {pattern_name: True/False, ...}
    """
    if len(df) < 5:
        return {}

    # Extract last 5 candles as numpy arrays for speed
    tail = df.tail(5)
    o = tail["open"].values.astype(float)
    h = tail["high"].values.astype(float)
    l = tail["low"].values.astype(float)
    c = tail["close"].values.astype(float)

    detected = {}
    for name, fn in PATTERN_DETECTORS.items():
        try:
            detected[name] = fn(o, h, l, c)
        except Exception:
            detected[name] = False

    return detected


def get_active_patterns(df: pd.DataFrame) -> list[str]:
    """Return list of pattern names detected on the last candle(s)."""
    raw = detect_patterns(df)
    return [k for k, v in raw.items() if v]


def get_pattern_label(patterns: list[str]) -> str:
    """Return a user-friendly label for the first detected bullish pattern, or first any pattern."""
    # Prefer bullish patterns first
    for p in patterns:
        if p in BULLISH_PATTERNS and p in PATTERN_ICONS:
            return PATTERN_ICONS[p]
    # Then any pattern
    for p in patterns:
        if p in PATTERN_ICONS:
            return PATTERN_ICONS[p]
    return "—"


def get_all_pattern_labels(patterns: list[str]) -> list[str]:
    """Return all detected pattern labels."""
    return [PATTERN_ICONS[p] for p in patterns if p in PATTERN_ICONS]


def pattern_score_bonus(patterns: list[str]) -> int:
    """
    Return score bonus based on detected patterns.
    Strong bullish = +20, Moderate bullish = +10, Bearish = -5, None = 0.
    """
    has_strong  = any(p in STRONG_BULLISH for p in patterns)
    has_moderate = any(p in MODERATE_BULLISH for p in patterns)
    has_bearish = any(p in BEARISH_PATTERNS for p in patterns)

    bonus = 0
    if has_strong:
        bonus += 20
    elif has_moderate:
        bonus += 10

    if has_bearish:
        bonus -= 5

    return max(bonus, 0)


if __name__ == "__main__":
    print("Patterns module loaded.")
    print(f"  Registered detectors: {len(PATTERN_DETECTORS)}")
    print(f"  Bullish: {len(BULLISH_PATTERNS)}")
    print(f"  Bearish: {len(BEARISH_PATTERNS)}")
