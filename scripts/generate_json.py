"""
generate_json.py
Standalone script to regenerate signals.json from last engine run.
Useful for local testing without running the full engine.
"""

import os
import json
from datetime import datetime
import pytz

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)


def load_and_validate_signals() -> dict:
    path = os.path.join(DATA_DIR, "signals.json")
    if not os.path.exists(path):
        print("[generate_json] signals.json not found — creating empty placeholder")
        return {
            "generated_at": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M IST"),
            "total": 0,
            "signals": []
        }

    with open(path) as f:
        data = json.load(f)

    # Validate required fields in each signal
    required = ["symbol", "strategy", "entry", "target", "stop_loss", "score"]
    clean_signals = []
    for sig in data.get("signals", []):
        if all(sig.get(k) is not None for k in required):
            clean_signals.append(sig)

    data["signals"] = clean_signals
    data["total"]   = len(clean_signals)
    return data


def write_signals(data: dict):
    path = os.path.join(DATA_DIR, "signals.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"[generate_json] Written {data['total']} signals to {path}")


def write_last_updated(data: dict):
    path = os.path.join(DATA_DIR, "last_updated.txt")
    ts = data.get("generated_at", datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M IST"))
    with open(path, "w") as f:
        f.write(ts)
    print(f"[generate_json] last_updated.txt: {ts}")


def generate_demo_signals() -> dict:
    """Generate sample signals for frontend development / GitHub Pages demo."""
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    sample = [
        {"symbol":"RELIANCE","exchange":"NSE","strategy":"EMA Crossover","pattern":"🟢 Engulfing","entry":2850.50,"target":3050.50,"stop_loss":2750.50,"rr":2.0,"score":88,"badge":"Strong","sparkline":[40,45,42,55,60,72,85],"date":today,"close":2850.50},
        {"symbol":"TCS","exchange":"NSE","strategy":"MACD Crossover","pattern":"⭐ Morning Star","entry":4120.00,"target":4500.00,"stop_loss":3930.00,"rr":2.0,"score":82,"badge":"Strong","sparkline":[30,35,38,40,55,65,78],"date":today,"close":4120.00},
        {"symbol":"HDFCBANK","exchange":"NSE","strategy":"RSI Reversal","pattern":"🔨 Hammer","entry":1720.00,"target":1900.00,"stop_loss":1630.00,"rr":2.0,"score":75,"badge":"Moderate","sparkline":[50,45,38,35,40,55,62],"date":today,"close":1720.00},
        {"symbol":"INFY","exchange":"NSE","strategy":"Volume Breakout","pattern":"📊 Marubozu","entry":1890.00,"target":2090.00,"stop_loss":1790.00,"rr":2.0,"score":79,"badge":"Moderate","sparkline":[60,62,58,65,70,75,80],"date":today,"close":1890.00},
        {"symbol":"ICICIBANK","exchange":"NSE","strategy":"Supertrend Breakout","pattern":"—","entry":1340.00,"target":1540.00,"stop_loss":1240.00,"rr":2.0,"score":68,"badge":"Moderate","sparkline":[45,48,50,55,58,62,68],"date":today,"close":1340.00},
        {"symbol":"BHARTIARTL","exchange":"NSE","strategy":"52-Week High Break","pattern":"🟢 Engulfing","entry":1650.00,"target":1850.00,"stop_loss":1550.00,"rr":2.0,"score":92,"badge":"Strong","sparkline":[55,60,65,70,75,85,95],"date":today,"close":1650.00},
        {"symbol":"LT","exchange":"NSE","strategy":"Bollinger Squeeze","pattern":"➕ Doji","entry":3750.00,"target":4150.00,"stop_loss":3550.00,"rr":2.0,"score":65,"badge":"Moderate","sparkline":[40,42,45,48,50,55,60],"date":today,"close":3750.00},
        {"symbol":"BAJFINANCE","exchange":"NSE","strategy":"EMA Pullback","pattern":"🤝 Harami","entry":7100.00,"target":7900.00,"stop_loss":6700.00,"rr":2.0,"score":58,"badge":"Weak","sparkline":[70,65,60,58,62,65,68],"date":today,"close":7100.00},
        {"symbol":"SBIN","exchange":"NSE","strategy":"Golden Cross","pattern":"⭐ Morning Star","entry":810.00,"target":910.00,"stop_loss":760.00,"rr":2.0,"score":85,"badge":"Strong","sparkline":[30,35,40,48,58,68,80],"date":today,"close":810.00},
        {"symbol":"MARUTI","exchange":"NSE","strategy":"Inside Bar Breakout","pattern":"🔨 Hammer","entry":12800.00,"target":14000.00,"stop_loss":12200.00,"rr":2.0,"score":72,"badge":"Moderate","sparkline":[50,52,48,55,58,65,70],"date":today,"close":12800.00},
    ]
    return {
        "generated_at": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M IST"),
        "total": len(sample),
        "signals": sample,
    }


if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        data = generate_demo_signals()
        write_signals(data)
        write_last_updated(data)
        print("[generate_json] Demo signals written.")
    else:
        data = load_and_validate_signals()
        write_signals(data)
        write_last_updated(data)
        print("[generate_json] Done.")
