import pandas as pd
import config


def to_server_time(df):
    """Convert index to Exness server time."""
    df = df.copy()
    df.index = df.index.tz_convert(config.SERVER_TZ)
    return df


def resample(df, rule, offset_minutes=0):
    """Build OHLC candles. Only closed candles are returned."""
    df = to_server_time(df)
    out = df.resample(
        rule,
        offset=pd.Timedelta(minutes=offset_minutes),
        label="left",
        closed="left",
    ).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
    }).dropna()

    # Drop the running candle: keep only candles whose period has ended.
    step = pd.Timedelta(rule)
    now = pd.Timestamp.now(tz=config.SERVER_TZ)
    out = out[out.index + step <= now]
    return out


def h4(df):
    # offset 90 minutes gives 01:30, 05:30, 09:30, 13:30, 17:30, 21:30
    return resample(df, "4h", config.H4_OFFSET_MINUTES)


def m15(df):
    return resample(df, "15min")


def m5(df):
    return resample(df, "5min")


def body_top(c):
    return max(c["open"], c["close"])


def body_bottom(c):
    return min(c["open"], c["close"])


def is_green(c):
    return c["close"] > c["open"]


def is_red(c):
    return c["close"] < c["open"]
