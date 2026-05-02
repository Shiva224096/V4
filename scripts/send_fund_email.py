"""Send email notification after fundamental scan completes."""
import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

user = os.environ.get("GMAIL_USER", "")
pw = os.environ.get("GMAIL_PASS", "")
to = os.environ.get("RECIPIENT_EMAIL", "")

if not all([user, pw, to]):
    print("Email credentials not set, skipping...")
    exit(0)

# Load results
try:
    data = json.load(open("data/fundamentals.json"))
    total = data.get("total", 0)
    stocks = data.get("stocks", [])
    strong = [s for s in stocks if s.get("badge") == "Strong Buy"]
    buy = [s for s in stocks if s.get("badge") == "Buy"]
except Exception:
    total, strong, buy = 0, [], []

html = "<h2>Fundamental Scan Complete</h2>"
html += f"<p><b>{total}</b> stocks screened | <b>{len(strong)}</b> Strong Buy | <b>{len(buy)}</b> Buy</p>"

if strong:
    html += "<h3>Top Strong Buy Picks:</h3>"
    html += '<table border="1" cellpadding="5"><tr><th>Symbol</th><th>Name</th><th>Score</th><th>PE</th><th>ROE%</th><th>F-Score</th></tr>'
    for s in strong[:15]:
        sym = s.get("symbol", "")
        name = s.get("name", "")
        score = s.get("composite_score", "")
        pe = s.get("pe", "-")
        roe = s.get("roe", "-")
        fs = s.get("fscore", "-")
        html += f"<tr><td><b>{sym}</b></td><td>{name}</td><td>{score}</td><td>{pe}</td><td>{roe}</td><td>{fs}/9</td></tr>"
    html += "</table>"

html += '<br><p><a href="https://shiva224096.github.io/V4/frontend/">Open Dashboard</a></p>'

msg = MIMEMultipart("alternative")
msg["Subject"] = f"SwingEdge: Fundamental Scan Done - {len(strong)} Strong Buys"
msg["From"] = user
msg["To"] = to
msg.attach(MIMEText(html, "html"))

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login(user, pw)
    s.sendmail(user, to, msg.as_string())

print("Email sent!")
