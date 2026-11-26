import pandas as pd
import config
import candles
import setups
import data


def simulate(symbol, signal, m15):
    """Walk forward from the signal. Win if target hit before stop loss."""
    if signal.get("target") is None or signal.get("stop_loss") is None:
        return None
    fut = m15[m15.index > signal["time"]]
    for _, c in fut.iterrows():
        if signal["direction"] == "BUY":
            if c["low"] <= signal["stop_loss"]:
                return "LOSS"
            if c["high"] >= signal["target"]:
                return "WIN"
        else:
            if c["high"] >= signal["stop_loss"]:
                return "LOSS"
            if c["low"] <= signal["target"]:
                return "WIN"
    return None  # still open, not counted


def run_backtest(symbol):
    """Replay history candle by candle. Returns stats per setup."""
    raw = data.fetch_history(symbol, "15m", "60d")
    m15_all = candles.m15(raw)
    h4_all = candles.h4(raw)
    stats = {}
    seen = set()
    # Walk through time in steps of one 15m candle, after warm-up.
    for k in range(200, len(m15_all)):
        t = m15_all.index[k]
        m15 = m15_all.iloc[:k + 1]
        h4 = h4_all[h4_all.index + pd.Timedelta(hours=4) <= t]
        for fn in (setups.setup_one, setups.setup_two):
            sig = fn(h4, m15, m15)  # 15m used for both lower frames in history
            if not sig:
                continue
            key = (sig["setup"], str(sig["time"]))
            if key in seen:
                continue  # only the first signal per range
            seen.add(key)
            sig = setups.add_levels(sig, symbol, m15)
            outcome = simulate(symbol, sig, m15_all)
            if outcome:
                s = stats.setdefault(sig["setup"], {"WIN": 0, "LOSS": 0})
                s[outcome] += 1
    for name, s in stats.items():
        total = s["WIN"] + s["LOSS"]
        s["total"] = total
        s["win_rate"] = round(100 * s["WIN"] / total, 1) if total else 0
        s["loss_rate"] = round(100 * s["LOSS"] / total, 1) if total else 0
    return stats
