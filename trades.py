import pandas as pd
import config
import candles
import setups
import data


def _walk(sig, m15_all):
    """Walk forward from the signal on 15m candles.
    Returns (status, exit_time, exit_price). Status is OPEN, WIN or LOSS."""
    fut = m15_all[m15_all.index > pd.Timestamp(sig["time"])]
    for t, c in fut.iterrows():
        if sig["direction"] == "BUY":
            if c["low"] <= sig["stop_loss"]:
                return "LOSS", t, sig["stop_loss"]
            if c["high"] >= sig["target"]:
                return "WIN", t, sig["target"]
        else:
            if c["high"] >= sig["stop_loss"]:
                return "LOSS", t, sig["stop_loss"]
            if c["low"] <= sig["target"]:
                return "WIN", t, sig["target"]
    return "OPEN", None, None


def chart_payload(symbol, tf="15m", max_candles=300):
    """Candles plus every trade found in the loaded window, with entry, stop, target and result."""
    raw = data.fetch_history(symbol, "15m", "60d") if tf != "5m" else data.fetch_1m(symbol)
    m15_all = candles.m15(raw)
    m5_all = candles.m5(raw) if tf == "5m" else m15_all
    h4_all = candles.h4(raw)
    view = m5_all if tf == "5m" else m15_all

    trades = []
    seen = set()
    start = max(200, len(m15_all) - 1200)
    for k in range(start, len(m15_all)):
        t = m15_all.index[k]
        m15 = m15_all.iloc[:k + 1]
        h4 = h4_all[h4_all.index + pd.Timedelta(hours=4) <= t]
        for fn in (setups.setup_one, setups.setup_two):
            sig = fn(h4, m15, m15)
            if not sig:
                continue
            key = (sig["setup"], str(sig["time"]))
            if key in seen:
                continue
            seen.add(key)
            sig = setups.add_levels(sig, symbol, m15)
            if sig.get("target") is None or sig.get("stop_loss") is None:
                continue
            status, xt, xp = _walk(sig, m15_all)
            trades.append({
                "setup": sig["setup"],
                "direction": sig["direction"],
                "entry_time": int(pd.Timestamp(sig["time"]).timestamp()),
                "entry": float(sig["price"]),
                "stop": float(sig["stop_loss"]),
                "target": float(sig["target"]),
                "status": status,
                "exit_time": int(xt.timestamp()) if xt is not None else None,
                "exit": float(xp) if xp is not None else None,
            })

    view = view.iloc[-max_candles:]
    cs = [{
        "time": int(t.timestamp()),
        "open": float(r["open"]), "high": float(r["high"]),
        "low": float(r["low"]), "close": float(r["close"]),
    } for t, r in view.iterrows()]
    first = cs[0]["time"] if cs else 0
    trades = [x for x in trades if x["entry_time"] >= first]
    return {"symbol": symbol, "tf": tf, "candles": cs, "trades": trades}
