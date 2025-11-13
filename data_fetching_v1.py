# data_fetching.py

import os
import pandas as pd
import yfinance as yf
from pandas_datareader import data as web
from datetime import datetime, timedelta

FRED_API_KEY = os.getenv("FRED_API_KEY", None)

TICKERS = {
    "3M_TBill": "^IRX",
    "1Y_Yield": "DGS1", 
    "2Y_Yield": "^FVX",
    "10Y_Yield": "^TNX",
    "30Y_Yield": "^TYX",
    "Nasdaq": "^IXIC",
    "Gold": "GC=F",
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "XRP": "XRP-USD",
}

# ---------------------- FRED Fetch ---------------------- #
def fetch_fred_series(series: str, period: str) -> pd.DataFrame:
    """Fetch daily FRED data (e.g., DGS1)."""
    end = datetime.utcnow()
    days = int(period.replace("d", "")) if "d" in period else 365
    start = end - timedelta(days=days)

    df = web.DataReader(series, "fred", start, end, api_key=FRED_API_KEY)
    df.columns = ["1Y_Yield"]
    return df.ffill().bfill()

# ---------------------- Combined Fetch ---------------------- #
def fetch_cross_asset_data(period: str, interval: str):
    # Yahoo Finance cannot do intraday for long periods → force 1d
    if period in ["180d", "1y"]:
        interval = "1d"

    # EXCLUDE DGS1 FROM Yahoo Finance
    yahoo_tickers = {k: v for k, v in TICKERS.items() if k != "1Y_Yield"}

    # ---- Fetch Yahoo tickers only ----
    df_yahoo = yf.download(
        tickers=list(yahoo_tickers.values()),
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
    )

    # Extract close prices
    if isinstance(df_yahoo.columns, pd.MultiIndex):
        close = df_yahoo["Close"].copy()
    else:
        close = df_yahoo.copy()

    close.columns = list(yahoo_tickers.keys())

    # Yahoo yields are ×10
    for col in ["3M_TBill", "2Y_Yield", "10Y_Yield", "30Y_Yield"]:
        if col in close.columns:
            close[col] = close[col] / 10.0

    # ---- Fetch 1-Year yield from FRED ----
    df_1y = fetch_fred_series("DGS1", period)

    # ---- Merge all ----
    df = pd.concat([close, df_1y], axis=1).sort_index()
    return df.ffill().bfill()
