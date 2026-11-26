import config
from candles import body_top, body_bottom, is_green, is_red


def h4_bias(h4):
    """Setup one, step one. Returns 'UP', 'DOWN' or None.
    Upside: a green H4 candle closes above the body top of the previous red H4 candle.
    Downside: a red H4 candle closes below the body bottom of the previous green H4 candle.
    """
    if len(h4) < 2:
        return None
    prev, last = h4.iloc[-2], h4.iloc[-1]
    if is_red(prev) and is_green(last) and last["close"] > body_top(prev):
        return "UP"
    if is_green(prev) and is_red(last) and last["close"] < body_bottom(prev):
        return "DOWN"
    return None


def find_range(df, min_inside=config.MIN_INSIDE, max_inside=config.MAX_INSIDE_5M):
    """Find the latest mother candle whose body contains the bodies of the next
    min_inside to max_inside candles. Wicks may go outside.
    Returns (index_position, high, low, count) or None.
    """
    n = len(df)
    for i in range(n - 2, -1, -1):
        mother = df.iloc[i]
        top, bottom = body_top(mother), body_bottom(mother)
        count = 0
        for j in range(i + 1, n):
            c = df.iloc[j]
            if body_top(c) <= top and body_bottom(c) >= bottom:
                count += 1
            else:
                break
        if count >= min_inside:
            return i, mother["high"], mother["low"], count
    return None


def pick_timeframe(m5, m15):
    """Use 5m if the inside count is within limit, else switch to 15m."""
    r5 = find_range(m5, max_inside=config.MAX_INSIDE_5M)
    if r5 and r5[3] <= config.MAX_INSIDE_5M:
        return "5m", m5, r5
    r15 = find_range(m15, max_inside=config.MAX_INSIDE_15M)
    if r15:
        return "15m", m15, r15
    return None, None, None


def breakout_after_range(df, rng):
    """First closed candle after the range whose BODY closes outside it.
    Returns ('UP' or 'DOWN', candle_time, close_price) or None.
    """
    i, high, low, count = rng
    for j in range(i + count + 1, len(df)):
        c = df.iloc[j]
        if c["close"] > high and body_bottom(c) >= low:
            return "UP", df.index[j], c["close"]
        if c["close"] < low and body_top(c) <= high:
            return "DOWN", df.index[j], c["close"]
    return None


def setup_one(h4, m5, m15):
    """H4 bias, then a 5m or 15m range break in the SAME direction."""
    bias = h4_bias(h4)
    if not bias:
        return None
    tf, df, rng = pick_timeframe(m5, m15)
    if not rng:
        return None
    result = breakout_after_range(df, rng)
    if not result:
        return None
    direction, when, price = result
    if direction != bias:
        return None
    return {
        "setup": "Setup 1: H4 break + range break",
        "direction": "BUY" if direction == "UP" else "SELL",
        "timeframe": tf,
        "time": when,
        "price": price,
        "range_high": rng[1],
        "range_low": rng[2],
    }


def setup_two(h4, m5, m15):
    """Inside range of one big H4 candle, then break of its high or low."""
    rng = find_range(h4, min_inside=3, max_inside=4)
    if not rng:
        return None
    i, high, low, count = rng
    after = h4.iloc[i + count + 1:]
    if after.empty:
        return None
    for t, c in after.iterrows():
        if c["close"] > high:
            return _entry_from_lower_tf("UP", t, high, low, m5, m15)
        if c["close"] < low:
            return _entry_from_lower_tf("DOWN", t, high, low, m5, m15)
    return None


def _entry_from_lower_tf(direction, t, high, low, m5, m15):
    tf, df, rng = pick_timeframe(m5, m15)
    if not rng:
        return None
    result = breakout_after_range(df, rng)
    if not result or result[0] != direction:
        return None
    d, when, price = result
    return {
        "setup": "Setup 2: H4 inside range break",
        "direction": "BUY" if d == "UP" else "SELL",
        "timeframe": tf,
        "time": when,
        "price": price,
        "range_high": high,
        "range_low": low,
    }


def swing_target(m15, direction, before_time):
    """Previous swing high (for buys) or swing low (for sells) on 15m before the signal."""
    df = m15[m15.index < before_time]
    if len(df) < 5:
        return None
    highs, lows = df["high"].values, df["low"].values
    for k in range(len(df) - 3, 1, -1):
        if direction == "BUY" and highs[k] == max(highs[k - 2:k + 3]):
            return float(highs[k])
        if direction == "SELL" and lows[k] == min(lows[k - 2:k + 3]):
            return float(lows[k])
    return None


def add_levels(signal, symbol, m15):
    """Attach stop loss and target to a signal."""
    sl_points = config.STOP_LOSS.get(symbol)
    price = signal["price"]
    if signal["direction"] == "BUY":
        signal["stop_loss"] = price - sl_points if sl_points else None
    else:
        signal["stop_loss"] = price + sl_points if sl_points else None
    signal["target"] = swing_target(m15, signal["direction"], signal["time"])
    return signal
