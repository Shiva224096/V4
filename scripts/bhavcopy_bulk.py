import os
import time
import pandas as pd
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor

try:
    from jugaad_data.nse import bhavcopy_save
except ImportError:
    pass

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bhavcopies")

def _download_day(dt):
    try:
        bhavcopy_save(dt, DATA_DIR)
        return True
    except Exception:
        return False

def build_bhavcopy_history(days=200) -> dict[str, pd.DataFrame]:
    """
    Downloads bulk Bhavcopy archives for the last N trading days.
    Returns a dictionary mapping 'SYMBOL' -> Pandas DataFrame of historical OHLCV.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Cleanup corrupted/404 bhavcopies (files < 10KB)
    try:
        for f in os.listdir(DATA_DIR):
            if f.endswith('.csv'):
                path = os.path.join(DATA_DIR, f)
                if os.path.getsize(path) < 10000:
                    os.remove(path)
    except Exception as e:
        print(f"[Bhavcopy Bulk] Cleanup error: {e}")
        
    # 1. Generate past dates
    dts = []
    curr = date.today()
    for _ in range(days + int(days * 0.5)): # Add 50% buffer for weekends/holidays
        if len(dts) >= days:
            break
        if curr.weekday() < 5:
            dts.append(curr)
        curr -= timedelta(days=1)
        
    print(f"[Bhavcopy Bulk] Downloading {len(dts)} days of Bhavcopies...")
    
    # 2. Download in parallel
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(_download_day, dts))
        
    success = sum(results)
    print(f"[Bhavcopy Bulk] Successfully downloaded/found {success} files.")
    
    # 3. Process all CSVs in the folder
    print("[Bhavcopy Bulk] Merging files into memory...")
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    dfs = []
    
    # Handle both old and new bhavcopy column formats
    for f in files:
        path = os.path.join(DATA_DIR, f)
        try:
            # Read all columns first to strip whitespace
            temp = pd.read_csv(path)
            temp.columns = temp.columns.str.strip()
            
            # Normalize to standard columns
            col_map = {
                'TradDt': 'date', 'TIMESTAMP': 'date', 'DATE1': 'date',
                'TckrSymb': 'symbol', 'SYMBOL': 'symbol',
                'SctySrs': 'series', 'SERIES': 'series',
                'OpnPric': 'open', 'OPEN': 'open', 'OPEN_PRICE': 'open',
                'HghPric': 'high', 'HIGH': 'high', 'HIGH_PRICE': 'high',
                'LwPric': 'low', 'LOW': 'low', 'LOW_PRICE': 'low',
                'ClsPric': 'close', 'CLOSE': 'close', 'CLOSE_PRICE': 'close',
                'TtlTradgVol': 'volume', 'TOTTRDQTY': 'volume', 'TTL_TRD_QNTY': 'volume'
            }
            temp.rename(columns=col_map, inplace=True)
            
            # Filter for Equity only
            if 'series' in temp.columns:
                temp = temp[temp['series'].astype(str).str.strip() == 'EQ']
            
            # Keep required columns
            required_cols = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            missing = [c for c in required_cols if c not in temp.columns]
            if not missing:
                temp = temp[required_cols]
                dfs.append(temp)
        except Exception as e:
            pass # Skip malformed files

    if not dfs:
        return {}
        
    master_df = pd.concat(dfs, ignore_index=True)
    master_df['date'] = pd.to_datetime(master_df['date'], errors='coerce')
    master_df.dropna(subset=['date'], inplace=True)
    master_df.sort_values('date', inplace=True)
    
    # 4. Group by symbol into a dictionary
    print("[Bhavcopy Bulk] Grouping by symbol...")
    history_dict = {}
    for symbol, group in master_df.groupby('symbol'):
        df = group.drop(columns=['symbol']).reset_index(drop=True)
        # Sort again just in case
        df.sort_values('date', inplace=True)
        # Convert numeric columns safely
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        history_dict[symbol] = df
        
    print(f"[Bhavcopy Bulk] Built history for {len(history_dict)} symbols.")
    return history_dict

if __name__ == "__main__":
    h = build_bhavcopy_history(10)
    print("RELIANCE:", h.get("RELIANCE"))
