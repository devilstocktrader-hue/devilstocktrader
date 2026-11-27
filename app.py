import os
from flask import Flask, jsonify, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
import config
import candles
import setups
import data
import backtest
import alerts

app = Flask(__name__)
LATEST = []          # signals shown on the site
SENT = set()         # signals already emailed, so only the first per range is sent
STATS = {}           # backtest results per symbol


def refresh_stats():
    for sym in config.BACKTEST_SYMBOLS:
        try:
            STATS[sym] = backtest.run_backtest(sym)
        except Exception as e:
            print("backtest failed", sym, e)


def scan():
    for sym in config.SYMBOLS:
        try:
            raw = data.fetch_1m(sym)
            m5, m15, h4 = candles.m5(raw), candles.m15(raw), candles.h4(raw)
            for fn in (setups.setup_one, setups.setup_two):
                sig = fn(h4, m5, m15)
                if not sig:
                    continue
                sig = setups.add_levels(sig, sym, m15)
                key = (sym, sig["setup"], str(sig["time"]), sig["direction"])
                if key in SENT:
                    continue
                SENT.add(key)
                sig["symbol"] = sym
                sig["time"] = str(sig["time"])
                LATEST.insert(0, sig)
                alerts.send_email(
                    f"{sym} {sig['direction']} setup",
                    alerts.format_signal(sym, sig, STATS.get(sym)),
                )
        except Exception as e:
            print("scan failed", sym, e)


PAGE = """
<!doctype html><title>My Setups</title>
<meta name=viewport content="width=device-width, initial-scale=1">
<style>body{font-family:sans-serif;margin:16px}.c{border:1px solid #ccc;border-radius:8px;padding:10px;margin:8px 0}
.BUY{border-left:6px solid green}.SELL{border-left:6px solid red}</style>
<h2>Live setups</h2><div id=list></div>
<h2>Backtest (gold and BTC)</h2><div id=bt></div>
<script>
let last = 0;
async function load(){
  const s = await (await fetch('/api/signals')).json();
  document.getElementById('list').innerHTML = s.map(x =>
    `<div class="c ${x.direction}"><b>${x.symbol} ${x.direction}</b> ${x.setup} (${x.timeframe})<br>`+
    `Entry ${x.price.toFixed(2)} | SL ${x.stop_loss} | TP ${x.target}<br>${x.time}</div>`).join('') || 'No setups yet';
  if (s.length > last && last !== 0 && Notification.permission === 'granted') {
    new Notification('New setup: ' + s[0].symbol + ' ' + s[0].direction);
  }
  last = s.length;
  const b = await (await fetch('/api/backtest')).json();
  document.getElementById('bt').innerHTML = Object.entries(b).map(([sym, st]) =>
    Object.entries(st).map(([name, v]) =>
      `<div class=c><b>${sym}</b> ${name}<br>Trades ${v.total} | Win ${v.win_rate}% | Loss ${v.loss_rate}%</div>`).join('')).join('');
}
Notification.requestPermission();
load(); setInterval(load, 60000);
</script>
"""


@app.route("/")
def home():
    return render_template_string(PAGE)


@app.route("/api/signals")
def api_signals():
    return jsonify(LATEST[:50])


@app.route("/api/backtest")
def api_backtest():
    return jsonify(STATS)


if __name__ == "__main__":
    sched = BackgroundScheduler()
    sched.add_job(refresh_stats, "date")
    sched.add_job(scan, "interval", minutes=5)
    sched.add_job(refresh_stats, "interval", hours=6)
    sched.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
