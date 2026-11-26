import os
import smtplib
from email.message import EmailMessage
import config


def send_email(subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = config.ALERT_EMAIL
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_APP_PASSWORD"])
        s.send_message(msg)


def format_signal(symbol, sig, stats):
    st = stats.get(sig["setup"]) if stats else None
    lines = [
        f"{symbol} {sig['direction']} signal",
        f"Setup: {sig['setup']} on {sig['timeframe']}",
        f"Entry near: {sig['price']:.2f}",
        f"Stop loss: {sig['stop_loss']}",
        f"Target: {sig['target']}",
    ]
    if st:
        lines.append(
            f"Past record: {st['total']} trades, win {st['win_rate']} percent, loss {st['loss_rate']} percent"
        )
    return "\n".join(lines)
