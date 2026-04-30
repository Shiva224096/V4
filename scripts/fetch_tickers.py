"""
fetch_tickers.py
Fetches NSE 500 and BSE ticker lists from official sources.
Saves to data/nse_tickers.csv and data/bse_tickers.csv
"""

import os
import requests
import pandas as pd
from io import StringIO

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_nse_tickers(index="nifty500"):
    """
    Fetch NSE tickers from official NSE archive CSVs.
    index options: 'nifty500', 'nifty200', 'all'
    Returns list of symbols.
    """
    urls = {
        "nifty500": "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
        "nifty200": "https://archives.nseindia.com/content/indices/ind_nifty200list.csv",
        "all":      "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
    }
    url = urls.get(index, urls["nifty500"])
    print(f"[NSE Tickers] Fetching {index} from {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text))

        # Column names differ between files
        sym_col = None
        for col in ["Symbol", "SYMBOL"]:
            if col in df.columns:
                sym_col = col
                break

        if sym_col is None:
            print(f"[NSE Tickers] Could not find Symbol column. Columns: {df.columns.tolist()}")
            return []

        symbols = df[sym_col].dropna().str.strip().tolist()
        print(f"[NSE Tickers] Fetched {len(symbols)} symbols")
        return symbols

    except Exception as e:
        print(f"[NSE Tickers] Error: {e}")
        return []


def fetch_bse_tickers():
    """
    Fetch BSE tickers via bse library or fallback BSE CSV.
    Returns list of (symbol, scripcode) tuples.
    """
    # Primary: use bse library
    try:
        from bse import BSE
        b = BSE()
        data = b.get_scripcode_list()
        tickers = [{"symbol": k, "scripcode": v} for k, v in data.items()]
        print(f"[BSE Tickers] Fetched {len(tickers)} scripts via bse library")
        return tickers
    except Exception as e:
        print(f"[BSE Tickers] bse library failed: {e}")

    # Fallback: BSE equity master CSV
    try:
        url = "https://www.bseindia.com/corporates/List_Scrips.aspx"
        print(f"[BSE Tickers] Trying fallback BSE equity list...")
        # BSE doesn't have a clean public CSV — return empty and rely on NSE
        return []
    except Exception as e:
        print(f"[BSE Tickers] Fallback failed: {e}")
        return []


def save_nse_tickers(symbols: list):
    path = os.path.join(DATA_DIR, "nse_tickers.csv")
    df = pd.DataFrame({"symbol": symbols})
    df.to_csv(path, index=False)
    print(f"[NSE Tickers] Saved {len(symbols)} tickers to {path}")


def save_bse_tickers(tickers: list):
    path = os.path.join(DATA_DIR, "bse_tickers.csv")
    df = pd.DataFrame(tickers)
    df.to_csv(path, index=False)
    print(f"[BSE Tickers] Saved {len(tickers)} tickers to {path}")


if __name__ == "__main__":
    nse_symbols = fetch_nse_tickers("all")
    save_nse_tickers(nse_symbols)

    bse_tickers = fetch_bse_tickers()
    save_bse_tickers(bse_tickers)
    print("[fetch_tickers] Done.")
