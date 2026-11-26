import pandas as pd
import requests
import config


def fetch_1m(symbol_key, days=7):
    """Fetch recent 1-minute candles from the public Yahoo chart feed.
    Free feeds limit 1-minute history to about 7 days."""
    ticker = config.SYMBOLS[symbol_key]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": "1m", "range": f"{days}d"}
    r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True)
    df = pd.DataFrame(q, index=idx)[["open", "high", "low", "close"]].dropna()
    return df


def fetch_history(symbol_key, interval="15m", range_="60d"):
    """Longer history for backtesting, coarser candles."""
    ticker = config.SYMBOLS[symbol_key]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": interval, "range": range_}
    r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True)
    return pd.DataFrame(q, index=idx)[["open", "high", "low", "close"]].dropna()
