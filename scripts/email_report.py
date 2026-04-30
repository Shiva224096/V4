"""
email_report.py
Sends the daily swing trading signals email via Gmail SMTP.
Reads signals.json and builds a rich HTML email.
"""

import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


# ---------------------------------------------------------------------------
# Load signals
# ---------------------------------------------------------------------------

def load_signals() -> dict:
    path = os.path.join(DATA_DIR, "signals.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"signals.json not found at {path}")
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def score_color(badge: str) -> str:
    return {"Strong": "#22c55e", "Moderate": "#eab308", "Weak": "#ef4444"}.get(badge, "#94a3b8")


def score_emoji(badge: str) -> str:
    return {"Strong": "🟢", "Moderate": "🟡", "Weak": "🔴"}.get(badge, "⚪")


def build_html_table(data: dict) -> str:
    signals = data.get("signals", [])
    generated_at = data.get("generated_at", "N/A")
    total = data.get("total", 0)

    # Top 3 high-confidence picks
    top3 = signals[:3]
    top3_html = "".join(
        f'<span style="display:inline-block;background:#1e293b;border:1px solid #334155;'
        f'border-radius:8px;padding:8px 14px;margin:4px;font-size:13px;">'
        f'<b style="color:#f1f5f9">{s["symbol"]}</b> '
        f'<span style="color:{score_color(s["badge"])}">●</span> '
        f'{s["strategy"]} — Score: {s["score"]}</span>'
        for s in top3
    )

    rows_html = ""
    for s in signals:
        badge_color = score_color(s["badge"])
        rows_html += f"""
        <tr style="border-bottom:1px solid #1e293b;">
          <td style="padding:10px 8px;font-weight:600;color:#f1f5f9">{s['symbol']}</td>
          <td style="padding:10px 8px;color:#94a3b8">{s.get('exchange','NSE')}</td>
          <td style="padding:10px 8px;color:#60a5fa">{s['strategy']}</td>
          <td style="padding:10px 8px;color:#c4b5fd">{s.get('pattern','—')}</td>
          <td style="padding:10px 8px;color:#4ade80">₹{s.get('entry','—')}</td>
          <td style="padding:10px 8px;color:#34d399">₹{s.get('target','—')}</td>
          <td style="padding:10px 8px;color:#f87171">₹{s.get('stop_loss','—')}</td>
          <td style="padding:10px 8px;color:#fbbf24">{s.get('rr','—')}:1</td>
          <td style="padding:10px 8px;text-align:center;">
            <span style="background:{badge_color}22;color:{badge_color};border:1px solid {badge_color};
                   border-radius:20px;padding:3px 10px;font-size:12px;font-weight:600;">
              {score_emoji(s['badge'])} {s['score']}
            </span>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;color:#e2e8f0;">
  <div style="max-width:900px;margin:0 auto;padding:24px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1e3a5f,#0f172a);border:1px solid #1e3a8a;
                border-radius:16px;padding:28px;margin-bottom:24px;text-align:center;">
      <h1 style="margin:0 0 8px;font-size:28px;color:#f1f5f9;">
        📈 Swing Trading Signals
      </h1>
      <p style="margin:0;color:#60a5fa;font-size:15px;">
        {date.today().strftime('%A, %d %B %Y')} · Indian Stock Market · NSE
      </p>
    </div>

    <!-- Summary -->
    <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;
                padding:20px;margin-bottom:20px;">
      <h2 style="margin:0 0 12px;font-size:16px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">
        📊 Summary
      </h2>
      <p style="margin:0 0 6px;font-size:14px;">
        <b style="color:#f1f5f9">Total Signals:</b>
        <span style="color:#60a5fa"> {total}</span>
      </p>
      <p style="margin:0 0 12px;font-size:14px;">
        <b style="color:#f1f5f9">Generated At:</b>
        <span style="color:#94a3b8"> {generated_at}</span>
      </p>
      <p style="margin:0 0 6px;font-size:13px;color:#94a3b8;">🔥 Top Picks:</p>
      <div>{top3_html}</div>
    </div>

    <!-- Signals Table -->
    <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;overflow:hidden;">
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#0f172a;color:#64748b;text-transform:uppercase;font-size:11px;letter-spacing:0.5px;">
            <th style="padding:12px 8px;text-align:left;">Symbol</th>
            <th style="padding:12px 8px;text-align:left;">Exch</th>
            <th style="padding:12px 8px;text-align:left;">Strategy</th>
            <th style="padding:12px 8px;text-align:left;">Pattern</th>
            <th style="padding:12px 8px;text-align:left;">Entry</th>
            <th style="padding:12px 8px;text-align:left;">Target</th>
            <th style="padding:12px 8px;text-align:left;">Stop Loss</th>
            <th style="padding:12px 8px;text-align:left;">R:R</th>
            <th style="padding:12px 8px;text-align:center;">Score</th>
          </tr>
        </thead>
        <tbody>
          {rows_html if rows_html else '<tr><td colspan="9" style="padding:20px;text-align:center;color:#64748b;">No signals today</td></tr>'}
        </tbody>
      </table>
    </div>

    <!-- Footer -->
    <div style="margin-top:20px;text-align:center;color:#475569;font-size:12px;">
      <p>Generated by GitHub Actions at 9:00 AM IST ·
         <a href="#" style="color:#3b82f6;text-decoration:none;">View Dashboard</a>
      </p>
      <p style="margin-top:4px;color:#334155;">
        ⚠️ This is for educational purposes only. Not financial advice.
      </p>
    </div>
  </div>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# Send email
# ---------------------------------------------------------------------------

def send_email(data: dict):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_PASS")
    recipient  = os.environ.get("RECIPIENT_EMAIL", gmail_user)

    if not gmail_user or not gmail_pass:
        raise EnvironmentError("GMAIL_USER and GMAIL_PASS must be set in environment/secrets.")

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = f"📈 Swing Signals — {date.today().strftime('%d %b %Y')} | {data.get('total', 0)} picks"
    msg["From"]    = gmail_user
    msg["To"]      = recipient

    html_body = build_html_table(data)
    msg.attach(MIMEText(html_body, "html"))

    print(f"[Email] Sending to {recipient}...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, gmail_pass)
        smtp.sendmail(gmail_user, recipient, msg.as_string())
    print("[Email] Sent successfully.")


if __name__ == "__main__":
    data = load_signals()
    send_email(data)
