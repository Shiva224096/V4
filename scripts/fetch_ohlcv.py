"""
fetch_ohlcv.py
4-level waterfall fetcher for OHLCV data.
Sources: jugaad-data → NSE Direct API → Twelve Data → BSE Bhavcopy
No Yahoo Finance anywhere.
"""

import os
import io
import time
import zipfile
import requests
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "")

# ---------------------------------------------------------------------------
# Source 1 — jugaad-data (NSE native)
# ---------------------------------------------------------------------------

def fetch_jugaad(symbol: str, days: int = 180) -> pd.DataFrame | None:
    try:
        from jugaad_data.nse import stock_df
        from_date = date.today() - timedelta(days=days)
        to_date = date.today()
        df = stock_df(symbol=symbol, from_date=from_date, to_date=to_date, series="EQ")
        if df is None or len(df) < 5:
            return None

        # Normalise column names
        df.columns = [c.lower().strip() for c in df.columns]
        rename_map = {
            "ch_opening_price":   "open",
            "ch_trade_high_price": "high",
            "ch_trade_low_price":  "low",
            "ch_closing_price":   "close",
            "ch_tot_trd_qnty":    "volume",
            "ch_timestamp":       "date",
        }
        df.rename(columns=rename_map, inplace=True)
        df = _standardise(df)
        print(f"  [jugaad] {symbol}: {len(df)} rows")
        return df
    except Exception as e:
        print(f"  [jugaad] {symbol} failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Source 2 — NSE Direct API with session
# ---------------------------------------------------------------------------

_nse_session = None

def _get_nse_session():
    global _nse_session
    if _nse_session is None:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=HEADERS, timeout=15)
        _nse_session = s
    return _nse_session


def fetch_nse_direct(symbol: str, days: int = 180) -> pd.DataFrame | None:
    try:
        sess = _get_nse_session()
        from_dt = (date.today() - timedelta(days=days)).strftime("%d-%m-%Y")
        to_dt   = date.today().strftime("%d-%m-%Y")
        url = (
            f"https://www.nseindia.com/api/historical/cm/equity"
            f"?symbol={symbol}&series=[%22EQ%22]&from={from_dt}&to={to_dt}"
        )
        resp = sess.get(url, headers={**HEADERS, "Referer": "https://www.nseindia.com"}, timeout=20)
        resp.raise_for_status()
        raw = resp.json()
        if "data" not in raw or not raw["data"]:
            return None

        df = pd.DataFrame(raw["data"])
        col_map = {
            "CH_OPENING_PRICE":    "open",
            "CH_TRADE_HIGH_PRICE": "high",
            "CH_TRADE_LOW_PRICE":  "low",
            "CH_CLOSING_PRICE":    "close",
            "CH_TOT_TRD_QNTY":    "volume",
            "CH_TIMESTAMP":        "date",
        }
        df.rename(columns=col_map, inplace=True)
        df = _standardise(df)
        print(f"  [NSE direct] {symbol}: {len(df)} rows")
        return df
    except Exception as e:
        print(f"  [NSE direct] {symbol} failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Source 3 — Twelve Data (free tier: 800 req/day)
# ---------------------------------------------------------------------------

def fetch_twelve_data(symbol: str, days: int = 180) -> pd.DataFrame | None:
    if not TWELVE_DATA_KEY:
        print("  [TwelveData] No API key set — skipping")
        return None
    try:
        from twelvedata import TDClient
        td = TDClient(apikey=TWELVE_DATA_KEY)
        df = td.time_series(
            symbol=f"{symbol}:NSE",
            interval="1day",
            outputsize=days,
        ).as_pandas()
        if df is None or len(df) < 5:
            return None
        df.reset_index(inplace=True)
        df.rename(columns={"datetime": "date"}, inplace=True)
        df = _standardise(df)
        print(f"  [TwelveData] {symbol}: {len(df)} rows")
        return df
    except Exception as e:
        print(f"  [TwelveData] {symbol} failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Source 4 — BSE Bhavcopy bulk dump (today's data only — last resort)
# ---------------------------------------------------------------------------

_bse_bhavcopy_cache: dict[str, pd.DataFrame] = {}

def fetch_bse_bhavcopy(symbol: str) -> pd.DataFrame | None:
    global _bse_bhavcopy_cache
    try:
        today = date.today()
        key = today.strftime("%d%m%y")
        if key not in _bse_bhavcopy_cache:
            url = f"https://www.bseindia.com/download/BhavCopy/Equity/EQ{key}_CSV.ZIP"
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                fname = [n for n in z.namelist() if n.endswith(".csv")][0]
                with z.open(fname) as f:
                    bse_df = pd.read_csv(f)
            _bse_bhavcopy_cache[key] = bse_df
        bse_df = _bse_bhavcopy_cache[key]

        row = bse_df[bse_df["SC_CODE"].astype(str).str.strip() == symbol.strip()]
        if row.empty:
            # Try by name
            row = bse_df[bse_df.get("SC_NAME", pd.Series()).str.upper() == symbol.upper()]
        if row.empty:
            return None

        record = row.iloc[0]
        df = pd.DataFrame([{
            "date":   today,
            "open":   float(record.get("OPEN", 0)),
            "high":   float(record.get("HIGH", 0)),
            "low":    float(record.get("LOW", 0)),
            "close":  float(record.get("CLOSE", 0)),
            "volume": float(record.get("NO_OF_SHRS", 0)),
        }])
        print(f"  [BSE Bhavcopy] {symbol}: single row (today only)")
        return df
    except Exception as e:
        print(f"  [BSE Bhavcopy] {symbol} failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Public waterfall entry point
# ---------------------------------------------------------------------------

def get_ohlcv(symbol: str, days: int = 180) -> pd.DataFrame | None:
    """
    Try each data source in order. Return the first successful result.
    Adds a small sleep between calls to respect rate limits.
    """
    # 1. jugaad-data
    df = fetch_jugaad(symbol, days)
    if df is not None and len(df) > 20:
        return df
    time.sleep(1)

    # 2. NSE Direct API
    df = fetch_nse_direct(symbol, days)
    if df is not None and len(df) > 20:
        return df
    time.sleep(1)

    # 3. Twelve Data
    df = fetch_twelve_data(symbol, days)
    if df is not None and len(df) > 20:
        return df
    time.sleep(1)

    # 4. BSE Bhavcopy (today only — very limited but better than nothing)
    df = fetch_bse_bhavcopy(symbol)
    if df is not None and len(df) > 0:
        return df

    print(f"  [!] All sources failed for {symbol}")
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _standardise(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure consistent column names and types."""
    required = ["date", "open", "high", "low", "close", "volume"]
    df.columns = [c.lower().strip() for c in df.columns]

    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df.dropna(subset=["open", "high", "low", "close"], inplace=True)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df[[c for c in required if c in df.columns]]


if __name__ == "__main__":
    # Quick test
    df = get_ohlcv("RELIANCE", days=90)
    if df is not None:
        print(df.tail())
    else:
        print("No data returned.")
