# data_fetching.py
import os
import pandas as pd
import yfinance as yf
from pandas_datareader import data as web
from datetime import datetime, timedelta

FRED_API_KEY = os.getenv("FRED_API_KEY", None)

# -------------------------------------------------------------------
# All yields from FRED (consistent, daily, long history)
# -------------------------------------------------------------------
FRED_TICKERS = {
    "3M_Yield": "DGS3MO",
    "1Y_Yield": "DGS1",
    "2Y_Yield": "DGS2",
    "10Y_Yield": "DGS10",
    "30Y_Yield": "DGS30",
}

# -------------------------------------------------------------------
# Yahoo tickers (non-FRED assets)
# -------------------------------------------------------------------
YAHOO_TICKERS = {
    "Nasdaq": "^IXIC",
    "Gold": "GC=F",
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "XRP": "XRP-USD",
}

# -------------------------------------------------------------------
# FRED fetch helper
# -------------------------------------------------------------------
def fetch_fred_series(series: str, period: str) -> pd.DataFrame:
    """Fetch daily FRED series like DGS1, DGS2, DGS10."""
    end = datetime.utcnow()
    days = int(period.replace("d", "")) if "d" in period else 365
    start = end - timedelta(days=days)

    df = web.DataReader(series, "fred", start, end, api_key=FRED_API_KEY)
    return df.ffill().bfill()

# -------------------------------------------------------------------
# Main fetcher
# -------------------------------------------------------------------
def fetch_cross_asset_data(period: str, interval: str):
    # Yahoo intraday not available for long ranges → force 1d
    if period in ["180d", "1y"]:
        interval = "1d"

    # ---- Fetch Yahoo assets ----
    df_yahoo = yf.download(
        tickers=list(YAHOO_TICKERS.values()),
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
    )

    if isinstance(df_yahoo.columns, pd.MultiIndex):
        close = df_yahoo["Close"].copy()
    else:
        close = df_yahoo.copy()

    close.columns = list(YAHOO_TICKERS.keys())

    # ---- Fetch FRED yields ----
    fred_frames = []
    for label, series in FRED_TICKERS.items():
        df_fred = fetch_fred_series(series, period)
        df_fred.columns = [label]
        fred_frames.append(df_fred)

    df_fred_all = pd.concat(fred_frames, axis=1)

    # ---- Merge all ----
    df = pd.concat([df_fred_all, close], axis=1)
    df = df.sort_index().ffill().bfill()

    return df
