"""
fundamental_engine.py
Fundamental Analysis Screener for NSE stocks.
Uses yfinance for financial data + 5 proven quantitative models.
Outputs data/fundamentals.json for the frontend dashboard.
"""

import os
import sys
import json
import math
import time
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

IST = pytz.timezone("Asia/Kolkata")


# ---------------------------------------------------------------------------
# 1. Load tickers (reuse existing nse_tickers.csv)
# ---------------------------------------------------------------------------

def load_tickers(max_count=500):
    """Load NSE tickers, limited to max_count for performance."""
    path = os.path.join(DATA_DIR, "nse_tickers.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        return df["symbol"].dropna().tolist()[:max_count]
    # Fallback: top blue chips
    return [
        "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","BHARTIARTL",
        "KOTAKBANK","HINDUNILVR","ITC","LT","AXISBANK","BAJFINANCE",
        "SBIN","MARUTI","NESTLEIND","TATAMOTORS","SUNPHARMA","WIPRO",
        "ONGC","NTPC","ADANIENT","TITAN","ULTRACEMCO","BAJAJFINSV",
        "POWERGRID","TECHM","HCLTECH","JSWSTEEL","TATASTEEL","INDUSINDBK",
    ]


# ---------------------------------------------------------------------------
# 2. Fetch fundamental data from yfinance
# ---------------------------------------------------------------------------

def fetch_fundamentals(symbol):
    """Fetch all fundamental data for a single NSE stock."""
    ticker = yf.Ticker(f"{symbol}.NS")
    info = ticker.info or {}

    if not info.get("currentPrice") and not info.get("regularMarketPrice"):
        return None

    # --- Basic Info ---
    price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
    company_name = info.get("shortName") or info.get("longName") or symbol
    about = info.get("longBusinessSummary", "")
    pe = info.get("trailingPE")
    forward_pe = info.get("forwardPE")
    pb = info.get("priceToBook")
    eps = info.get("trailingEps")
    bvps = info.get("bookValue")
    mktcap = info.get("marketCap", 0)
    ev = info.get("enterpriseValue", 0)
    div_yield = info.get("dividendYield")
    sector = info.get("sector", "Unknown")
    industry = info.get("industry", "Unknown")

    # --- Profitability ---
    roe = info.get("returnOnEquity")
    roa = info.get("returnOnAssets")
    gross_margin = info.get("grossMargins")
    op_margin = info.get("operatingMargins")
    profit_margin = info.get("profitMargins")
    rev_growth = info.get("revenueGrowth")

    # --- Financial Health ---
    de_ratio = info.get("debtToEquity")
    total_debt = info.get("totalDebt", 0)
    total_cash = info.get("totalCash", 0)
    fcf = info.get("freeCashflow")
    ebitda = info.get("ebitda")
    revenue = info.get("totalRevenue", 0)

    # --- Financial Statements (for Piotroski & Altman) ---
    stmt = {}
    try:
        fin = ticker.financials
        if fin is not None and not fin.empty:
            stmt["revenue"] = _safe_list(fin, "Total Revenue", 2)
            stmt["net_income"] = _safe_list(fin, "Net Income", 2)
            stmt["gross_profit"] = _safe_list(fin, "Gross Profit", 2)
            stmt["op_income"] = _safe_list(fin, "Operating Income", 2)
    except Exception:
        pass

    try:
        bs = ticker.balance_sheet
        if bs is not None and not bs.empty:
            stmt["total_assets"] = _safe_list(bs, "Total Assets", 2)
            stmt["total_debt_bs"] = _safe_list(bs, "Total Debt", 2)
            stmt["equity"] = _safe_list(bs, "Stockholders Equity", 2)
            stmt["current_assets"] = _safe_list(bs, "Total Current Assets", 2)
            stmt["current_liab"] = _safe_list(bs, "Total Current Liabilities", 2)
            stmt["retained_earnings"] = _safe_list(bs, "Retained Earnings", 2)
            stmt["shares"] = _safe_list(bs, "Share Issued", 2)
    except Exception:
        pass

    try:
        cf = ticker.cashflow
        if cf is not None and not cf.empty:
            stmt["op_cashflow"] = _safe_list(cf, "Operating Cash Flow", 2)
    except Exception:
        pass

    return {
        "symbol": symbol,
        "company_name": company_name,
        "about": about[:500] if about else "",  # Truncate to save JSON size
        "price": price,
        "pe": pe,
        "forward_pe": forward_pe,
        "pb": pb,
        "eps": eps,
        "bvps": bvps,
        "mktcap": mktcap,
        "ev": ev,
        "div_yield": div_yield,
        "sector": sector,
        "industry": industry,
        "roe": roe,
        "roa": roa,
        "gross_margin": gross_margin,
        "op_margin": op_margin,
        "profit_margin": profit_margin,
        "rev_growth": rev_growth,
        "de_ratio": de_ratio,
        "total_debt": total_debt,
        "total_cash": total_cash,
        "fcf": fcf,
        "ebitda": ebitda,
        "revenue": revenue,
        "stmt": stmt,
    }


def _safe_list(df, row_name, n):
    """Extract up to n values from a DataFrame row, returning floats."""
    if row_name not in df.index:
        return []
    vals = df.loc[row_name].head(n).tolist()
    return [float(v) if pd.notna(v) else None for v in vals]


# ---------------------------------------------------------------------------
# 3. Scoring Models
# ---------------------------------------------------------------------------

def piotroski_fscore(data):
    """Piotroski F-Score (0-9): measures financial health."""
    score = 0
    s = data.get("stmt", {})

    # --- Profitability (4 points) ---
    # 1. ROA > 0
    if data.get("roa") and data["roa"] > 0:
        score += 1
    # 2. Operating Cash Flow > 0
    ocf = _first(s.get("op_cashflow", []))
    if ocf and ocf > 0:
        score += 1
    # 3. ROA increasing (net income / total assets YoY)
    ni = s.get("net_income", [])
    ta = s.get("total_assets", [])
    if len(ni) >= 2 and len(ta) >= 2 and ni[0] and ni[1] and ta[0] and ta[1]:
        roa_curr = ni[0] / ta[0] if ta[0] else 0
        roa_prev = ni[1] / ta[1] if ta[1] else 0
        if roa_curr > roa_prev:
            score += 1
    # 4. Cash Flow > Net Income (accruals quality)
    ni_curr = _first(ni)
    if ocf and ni_curr and ocf > ni_curr:
        score += 1

    # --- Leverage / Liquidity (3 points) ---
    # 5. Long-term debt ratio decreasing
    debt = s.get("total_debt_bs", [])
    if len(debt) >= 2 and len(ta) >= 2:
        if debt[0] and debt[1] and ta[0] and ta[1]:
            dr_curr = debt[0] / ta[0] if ta[0] else 0
            dr_prev = debt[1] / ta[1] if ta[1] else 0
            if dr_curr < dr_prev:
                score += 1
    # 6. Current ratio increasing
    ca = s.get("current_assets", [])
    cl = s.get("current_liab", [])
    if len(ca) >= 2 and len(cl) >= 2:
        if ca[0] and cl[0] and ca[1] and cl[1] and cl[0] > 0 and cl[1] > 0:
            cr_curr = ca[0] / cl[0]
            cr_prev = ca[1] / cl[1]
            if cr_curr > cr_prev:
                score += 1
    # 7. No new shares issued
    shares = s.get("shares", [])
    if len(shares) >= 2 and shares[0] and shares[1]:
        if shares[0] <= shares[1]:
            score += 1
    elif not shares:
        score += 1  # Assume no dilution if data missing

    # --- Operating Efficiency (2 points) ---
    # 8. Gross margin increasing
    gp = s.get("gross_profit", [])
    rev = s.get("revenue", [])
    if len(gp) >= 2 and len(rev) >= 2:
        if gp[0] and gp[1] and rev[0] and rev[1] and rev[0] > 0 and rev[1] > 0:
            gm_curr = gp[0] / rev[0]
            gm_prev = gp[1] / rev[1]
            if gm_curr > gm_prev:
                score += 1
    # 9. Asset turnover increasing
    if len(rev) >= 2 and len(ta) >= 2:
        if rev[0] and rev[1] and ta[0] and ta[1] and ta[0] > 0 and ta[1] > 0:
            at_curr = rev[0] / ta[0]
            at_prev = rev[1] / ta[1]
            if at_curr > at_prev:
                score += 1

    return score


def graham_number(data):
    """Calculate Graham Number and Margin of Safety."""
    eps = data.get("eps")
    bvps = data.get("bvps")
    price = data.get("price", 0)

    if not eps or not bvps or eps <= 0 or bvps <= 0:
        return None, None

    gn = math.sqrt(22.5 * eps * bvps)
    mos = ((gn - price) / gn * 100) if gn > 0 else None
    return round(gn, 2), round(mos, 2) if mos else None


def magic_formula_metrics(data):
    """Greenblatt's Magic Formula: Earnings Yield + Return on Capital."""
    # Earnings Yield = EBIT / Enterprise Value
    ebitda = data.get("ebitda")
    ev = data.get("ev")
    earnings_yield = None
    if ebitda and ev and ev > 0:
        earnings_yield = round((ebitda / ev) * 100, 2)

    # Return on Capital = EBIT / (Net Fixed Assets + Working Capital)
    # Simplified: use ROE as proxy since we have it
    roc = None
    if data.get("roe"):
        roc = round(data["roe"] * 100, 2)

    return earnings_yield, roc


def altman_zscore(data):
    """Altman Z-Score: bankruptcy prediction. >2.99 safe, <1.8 distress."""
    s = data.get("stmt", {})
    ta_list = s.get("total_assets", [])
    ta = _first(ta_list)
    if not ta or ta <= 0:
        return None

    mktcap = data.get("mktcap", 0)
    revenue = data.get("revenue", 0)

    # A = Working Capital / Total Assets
    ca = _first(s.get("current_assets", []))
    cl = _first(s.get("current_liab", []))
    wc = (ca - cl) if ca and cl else 0
    A = wc / ta

    # B = Retained Earnings / Total Assets
    re = _first(s.get("retained_earnings", []))
    B = (re / ta) if re else 0

    # C = EBIT / Total Assets (use operating income)
    ebit = _first(s.get("op_income", []))
    C = (ebit / ta) if ebit else 0

    # D = Market Cap / Total Liabilities
    equity = _first(s.get("equity", []))
    total_liab = ta - equity if equity else ta * 0.5
    D = (mktcap / total_liab) if total_liab and total_liab > 0 else 0

    # E = Revenue / Total Assets
    E = (revenue / ta) if revenue else 0

    z = 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1.0 * E
    return round(z, 2)


def compute_composite_score(data, fscore, gn, mos, ey, roc, zscore):
    """Compute final composite score (0-100) from all models."""
    score = 0

    # --- Piotroski F-Score (max 25 pts) ---
    # Scale 0-9 to 0-25
    if fscore is not None:
        score += round((fscore / 9) * 25)

    # --- Graham Undervaluation (max 20 pts) ---
    if mos is not None:
        if mos > 50:
            score += 20
        elif mos > 30:
            score += 15
        elif mos > 10:
            score += 10
        elif mos > 0:
            score += 5

    # --- Magic Formula (max 20 pts) ---
    if ey is not None:
        if ey > 15:
            score += 10
        elif ey > 10:
            score += 7
        elif ey > 5:
            score += 4
    if roc is not None:
        if roc > 25:
            score += 10
        elif roc > 15:
            score += 7
        elif roc > 10:
            score += 4

    # --- Altman Z-Score (max 15 pts) ---
    if zscore is not None:
        if zscore > 2.99:
            score += 15
        elif zscore > 1.8:
            score += 8
        else:
            score -= 5  # Penalty for distress

    # --- Key Ratios (max 20 pts) ---
    pe = data.get("pe")
    de = data.get("de_ratio")
    pm = data.get("profit_margin")
    rg = data.get("rev_growth")

    if pe and 0 < pe < 20:
        score += 5
    elif pe and 0 < pe < 30:
        score += 2

    if de is not None and de < 50:
        score += 5
    elif de is not None and de < 100:
        score += 2

    if pm and pm > 0.15:
        score += 5
    elif pm and pm > 0.05:
        score += 2

    if rg and rg > 0.10:
        score += 5
    elif rg and rg > 0:
        score += 2

    return max(min(score, 100), 0)


def score_badge(score):
    if score >= 75:
        return "Strong Buy"
    elif score >= 60:
        return "Buy"
    elif score >= 40:
        return "Hold"
    else:
        return "Avoid"


def _first(lst):
    """Return first non-None value from a list."""
    for v in (lst or []):
        if v is not None:
            return v
    return None


# ---------------------------------------------------------------------------
# 4. Main Engine
# ---------------------------------------------------------------------------

def run_engine(max_stocks=500):
    print(f"[Fundamentals] Starting engine...")
    tickers = load_tickers(max_stocks)
    print(f"[Fundamentals] Processing {len(tickers)} tickers...")

    results = []
    errors = 0

    for i, symbol in enumerate(tickers):
        if (i + 1) % 25 == 0:
            print(f"  [{i+1}/{len(tickers)}] Processing {symbol}...")

        try:
            data = fetch_fundamentals(symbol)
            if not data or not data.get("price"):
                continue

            # Run all 5 models
            fscore = piotroski_fscore(data)
            gn, mos = graham_number(data)
            ey, roc = magic_formula_metrics(data)
            zscore = altman_zscore(data)
            composite = compute_composite_score(data, fscore, gn, mos, ey, roc, zscore)

            # Format for frontend
            record = {
                "symbol": symbol,
                "company_name": data.get("company_name", symbol),
                "about": data.get("about", ""),
                "sector": data["sector"],
                "industry": data["industry"],
                "price": round(data["price"], 2),
                "pe": round(data["pe"], 2) if data.get("pe") else None,
                "forward_pe": round(data["forward_pe"], 2) if data.get("forward_pe") else None,
                "pb": round(data["pb"], 2) if data.get("pb") else None,
                "eps": round(data["eps"], 2) if data.get("eps") else None,
                "bvps": round(data["bvps"], 2) if data.get("bvps") else None,
                "roe": round(data["roe"] * 100, 2) if data.get("roe") else None,
                "roa": round(data["roa"] * 100, 2) if data.get("roa") else None,
                "de_ratio": round(data["de_ratio"], 2) if data.get("de_ratio") else None,
                "mktcap_cr": round(data["mktcap"] / 1e7, 0) if data.get("mktcap") else None,
                "revenue_cr": round(data["revenue"] / 1e7, 0) if data.get("revenue") else None,
                "rev_growth": round(data["rev_growth"] * 100, 2) if data.get("rev_growth") else None,
                "profit_margin": round(data["profit_margin"] * 100, 2) if data.get("profit_margin") else None,
                "op_margin": round(data["op_margin"] * 100, 2) if data.get("op_margin") else None,
                "gross_margin": round(data["gross_margin"] * 100, 2) if data.get("gross_margin") else None,
                "div_yield": round(data["div_yield"] * 100, 2) if data.get("div_yield") else None,
                "fcf_cr": round(data["fcf"] / 1e7, 0) if data.get("fcf") else None,
                "ebitda_cr": round(data["ebitda"] / 1e7, 0) if data.get("ebitda") else None,
                "debt_cr": round(data["total_debt"] / 1e7, 0) if data.get("total_debt") else None,
                "cash_cr": round(data["total_cash"] / 1e7, 0) if data.get("total_cash") else None,
                # Scores
                "fscore": fscore,
                "graham_number": gn,
                "margin_of_safety": mos,
                "earnings_yield": ey,
                "return_on_capital": roc,
                "zscore": zscore,
                "composite_score": composite,
                "badge": score_badge(composite),
            }
            results.append(record)

        except Exception as e:
            errors += 1
            if errors < 10:
                print(f"  [!] Error {symbol}: {e}")

        # Rate limit: small delay every request
        time.sleep(0.3)

        # Re-init session every 100 stocks to avoid stale cookies
        if (i + 1) % 100 == 0:
            time.sleep(2)

    # Sort by composite score
    results.sort(key=lambda x: x["composite_score"], reverse=True)

    print(f"\n[Fundamentals] Scored {len(results)} stocks ({errors} errors)")
    return results


# ---------------------------------------------------------------------------
# 5. Save outputs
# ---------------------------------------------------------------------------

def save_results(results):
    path = os.path.join(DATA_DIR, "fundamentals.json")
    payload = {
        "generated_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
        "total": len(results),
        "stocks": results,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"[Fundamentals] Saved {len(results)} stocks to {path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=500, help="Max stocks to scan")
    args = parser.parse_args()

    results = run_engine(max_stocks=args.max)
    save_results(results)
    print("[Fundamentals] Done.")
