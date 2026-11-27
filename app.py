import os
import time
import feedparser
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
NEWS = []            # latest headlines

NEWS_FEEDS = [
    ("ForexLive", "https://investinglive.com/rss/news"),
    ("Investing.com Forex", "https://www.investing.com/rss/news_1.rss"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("crypto.news", "https://crypto.news/feed/"),
]


def refresh_news():
    items = []
    for name, url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:12]:
                ts = time.mktime(e.published_parsed) if getattr(e, "published_parsed", None) else 0
                items.append({"source": name, "title": e.get("title", ""), "link": e.get("link", ""), "ts": ts})
        except Exception as ex:
            print("news failed", name, ex)
    items.sort(key=lambda x: x["ts"], reverse=True)
    NEWS[:] = items[:50]


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
<!doctype html>
<html><head>
<meta charset=utf-8>
<title>My Setups</title>
<meta name=viewport content="width=device-width, initial-scale=1">
<meta name=theme-color content="#03060f">
<style>
:root{--bg:#03060f;--card:#0b1224;--line:#1a2542;--text:#e6ecff;--mute:#8a96b8;--buy:#22d39a;--sell:#ff5c6c;--glow:#4f7cff}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(1200px 600px at 70% -10%,#0d1a3d 0%,var(--bg) 60%);color:var(--text);font-family:Inter,system-ui,sans-serif}
header{padding:22px 20px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center}
header b{font-size:20px;letter-spacing:.5px}
header span{color:var(--mute);font-size:13px}
main{display:grid;grid-template-columns:1.2fr 1fr;gap:18px;padding:18px;max-width:1300px;margin:auto}
@media(max-width:900px){main{grid-template-columns:1fr}}
h2{font-size:13px;letter-spacing:2px;text-transform:uppercase;color:var(--mute);margin:6px 0 12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px;box-shadow:0 0 24px rgba(79,124,255,.06)}
.BUY{border-left:4px solid var(--buy)}
.SELL{border-left:4px solid var(--sell)}
.tag{display:inline-block;padding:2px 10px;border-radius:99px;font-size:12px;font-weight:700}
.tag.BUY{background:rgba(34,211,154,.15);color:var(--buy);border:0}
.tag.SELL{background:rgba(255,92,108,.15);color:var(--sell);border:0}
.row{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:14px}
.row div small{display:block;color:var(--mute);font-size:11px}
.mute{color:var(--mute);font-size:12px}
.bar{height:6px;border-radius:9px;background:var(--sell);overflow:hidden;margin:6px 0}
.bar i{display:block;height:100%;background:var(--buy)}
.news a{color:var(--text);text-decoration:none;font-size:14px;line-height:1.4}
.news a:hover{color:var(--glow)}
.news .src{font-size:11px;color:var(--glow);letter-spacing:1px;text-transform:uppercase}
.news .item{padding:10px 0;border-bottom:1px solid var(--line)}
.news .item:last-child{border:0}
.empty{color:var(--mute);font-size:14px}
</style></head><body>
<header><b>MY SETUPS</b><span id=clock></span></header>
<main>
<section>
  <h2>Live setups</h2><div id=list class=empty>No setups yet</div>
  <h2 style="margin-top:22px">Backtest: gold and BTC</h2><div id=bt class=empty>Backtest is still running, refresh in a few minutes</div>
</section>
<section class=news>
  <h2>Market news</h2><div id=news class="card empty">Loading news</div>
</section>
</main>
<script>
let last = 0;
function bar(w){return `<div class=bar><i style="width:${w}%"></i></div>`}
function side(label, v){
  return `<div class=mute>${label}: ${v.total} trades | Win ${v.win_rate}% | Loss ${v.loss_rate}%</div>${bar(v.win_rate)}`;
}
async function load(){
  const s = await (await fetch('/api/signals')).json();
  if (s.length) document.getElementById('list').innerHTML = s.map(x =>
    `<div class="card ${x.direction}"><span class="tag ${x.direction}">${x.direction}</span> <b>${x.symbol}</b> <span class=mute>${x.setup} (${x.timeframe})</span>`+
    `<div class=row><div><small>Entry</small>${x.price.toFixed(2)}</div><div><small>Stop loss</small>${x.stop_loss}</div><div><small>Target</small>${x.target}</div></div>`+
    `<div class=mute style="margin-top:8px">${x.time}</div></div>`).join('');
  if (s.length > last && last !== 0 && Notification.permission === 'granted') {
    new Notification('New setup: ' + s[0].symbol + ' ' + s[0].direction);
  }
  last = s.length;
  const b = await (await fetch('/api/backtest')).json();
  const html = Object.entries(b).map(([sym, st]) =>
    Object.entries(st).map(([name, v]) =>
      `<div class=card><b>${sym}</b> <span class=mute>${name}</span>`+
      side('All', v.ALL)+side('BUY', v.BUY)+side('SELL', v.SELL)+`</div>`).join('')).join('');
  if (html) document.getElementById('bt').innerHTML = html;
  const n = await (await fetch('/api/news')).json();
  if (n.length) document.getElementById('news').innerHTML = n.map(x =>
    `<div class=item><div class=src>${x.source}</div><a href="${x.link}" target=_blank rel=noopener>${x.title}</a></div>`).join('');
  document.getElementById('clock').textContent = new Date().toLocaleString();
}
Notification.requestPermission();
load(); setInterval(load, 60000);
</script>
</body></html>
"""


@app.route("/")
def home():
    return render_template_string(PAGE)


@app.route("/api/signals")
def api_signals():
    return jsonify(LATEST[:50])


@app.route("/api/news")
def api_news():
    return jsonify(NEWS)


@app.route("/test-email")
def test_email():
    fake = {
        "setup": "Setup 1: H4 break + range break",
        "direction": "BUY",
        "timeframe": "5m",
        "price": 4000.00,
        "stop_loss": 3996.50,
        "target": 4010.00,
    }
    try:
        alerts.send_email("TEST: GOLD BUY setup", alerts.format_signal("GOLD", fake, STATS.get("GOLD")))
        return "Test email sent. Check your Gmail inbox and spam."
    except Exception as e:
        return f"Email failed: {e}", 500


@app.route("/api/backtest")
def api_backtest():
    return jsonify(STATS)


if __name__ == "__main__":
    sched = BackgroundScheduler()
    sched.add_job(refresh_stats, "date")
    sched.add_job(refresh_news, "date")
    sched.add_job(scan, "interval", minutes=5)
    sched.add_job(refresh_news, "interval", minutes=10)
    sched.add_job(refresh_stats, "interval", hours=6)
    sched.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
