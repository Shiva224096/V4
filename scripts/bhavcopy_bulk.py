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
            temp = pd.read_csv(path, usecols=lambda c: c in [
                'TradDt', 'TckrSymb', 'SctySrs', 'OpnPric', 'HghPric', 'LwPric', 'ClsPric', 'TtlTradgVol', # New format
                'TIMESTAMP', 'SYMBOL', 'SERIES', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'TOTTRDQTY'               # Old format
            ])
            # Normalize to standard columns
            col_map = {
                'TradDt': 'date', 'TIMESTAMP': 'date',
                'TckrSymb': 'symbol', 'SYMBOL': 'symbol',
                'SctySrs': 'series', 'SERIES': 'series',
                'OpnPric': 'open', 'OPEN': 'open',
                'HghPric': 'high', 'HIGH': 'high',
                'LwPric': 'low', 'LOW': 'low',
                'ClsPric': 'close', 'CLOSE': 'close',
                'TtlTradgVol': 'volume', 'TOTTRDQTY': 'volume'
            }
            temp.rename(columns=col_map, inplace=True)
            
            # Filter for Equity only
            temp = temp[temp['series'] == 'EQ']
            
            # Keep required columns
            temp = temp[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
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
