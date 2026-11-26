ALERT_EMAIL = "devilstocktrader@gmail.com"

# Symbols the app watches. Data comes from a public feed.
SYMBOLS = {
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "EURUSD": "EURUSD=X",
}

# Backtest only for these.
BACKTEST_SYMBOLS = ["GOLD", "BTC"]

# Stop loss in price points.
STOP_LOSS = {"GOLD": 3.5, "BTC": 200.0}

# Exness four-hour candles open at these server hours and minute 30.
# 01:30, 05:30, 09:30, 13:30, 17:30, 21:30
H4_OFFSET_MINUTES = 90  # 1 hour 30 minutes after midnight

# Exness chart timezone set by Dev: UTC+5:30 (Kolkata).
SERVER_TZ = "Asia/Kolkata"

# Mother candle rules.
MIN_INSIDE = 3
MAX_INSIDE_5M = 5   # more than this on 5m means switch to 15m
MAX_INSIDE_15M = 5
