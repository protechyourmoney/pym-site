#!/usr/bin/env python3
# 每朝喺雲端(GitHub Actions)寄 PYM 每日避險新聞摘要。
# 來源:直接讀網站 index.html 最新 PYMNEWS(與網站一致,免再 call API)。
# 寄信:Gmail SMTP(需 GMAIL_USER / GMAIL_APP_PASSWORD 兩個 secret)。
import os, re, sys, json, ssl, smtplib, subprocess, datetime, html, base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

TODAY = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).date()
TODAY_S = TODAY.strftime('%Y-%m-%d')
RECIPIENTS = ["chchoy@gmail.com", "alex.shum.1992@gmail.com",
              "enochhuenhk@gmail.com", "cchong0965@gmail.com"]
SITE = "https://protectyourmoney.co"

GU = os.environ.get("GMAIL_USER"); GP = os.environ.get("GMAIL_APP_PASSWORD")
if not GU or not GP:
    print("ERROR: 缺少 GMAIL_USER / GMAIL_APP_PASSWORD secret"); sys.exit(1)

html_src = open("index.html", encoding="utf-8").read()
m = re.search(r'const PYMNEWS = \[(.*?)\n\];', html_src, re.S)
if not m:
    print("ERROR: 搵唔到 PYMNEWS"); sys.exit(1)
pat = re.compile(r'\{risk:(\d+),\s*tag:"([^"]*)",\s*region:"([^"]*)",\s*date:"([^"]*)",\s*source:"([^"]*)",\s*title:"([^"]*)",\s*url:"([^"]*)",\s*summary:"([^"]*)"\}', re.S)
items = [dict(risk=int(a), tag=b, region=c, date=d, source=e, title=f, url=g, summary=h)
         for a,b,c,d,e,f,g,h in pat.findall(m.group(1))]
print(f"parsed {len(items)} PYMNEWS items")

def age(d):
    try: return (TODAY - datetime.date.fromisoformat(d)).days
    except Exception: return 999
recent = [it for it in items if age(it['date']) <= 2][:4]
picked = recent if recent else items[:3]
label = "今日" if recent else "近期"
print(f"picked {len(picked)} items ({'recent' if recent else 'fallback newest'})")

# 生成標題圖
poster_ok = False
try:
    json.dump([{"title":p["title"],"region":p["region"],"risk":p["risk"]} for p in picked],
              open("/tmp/news.json","w",encoding="utf-8"), ensure_ascii=False)
    subprocess.run([sys.executable, "scripts/email_poster.py", "/tmp/news.json", "/tmp/poster.png"], check=True)
    poster_ok = os.path.exists("/tmp/poster.png")
except Exception as ex:
    print("poster 生成失敗(照寄無圖版):", ex)

def esc(s): return html.escape(str(s))
rows_html, rows_txt = [], []
for p in picked:
    rows_html.append(
        f'<div style="margin:0 0 18px;padding:14px 16px;border:1px solid #e4ddcf;border-radius:10px;background:#fff">'
        f'<div style="font-size:12px;color:#a67c00;font-weight:700;margin-bottom:4px">{esc(p["region"])} · 風險 {p["risk"]} · {esc(p["source"])} · {esc(p["date"])}</div>'
        f'<div style="font-size:16px;font-weight:700;color:#2b2b2b;margin-bottom:6px">{esc(p["title"])}</div>'
        f'<div style="font-size:14px;color:#4a4a4a;line-height:1.6">{esc(p["summary"])}</div>'
        f'<div style="margin-top:8px"><a href="{esc(p["url"])}" style="color:#a67c00;font-size:13px">原文 →</a></div></div>')
    rows_txt.append(f"[{p['region']}·風險{p['risk']}] {p['title']}\n{p['summary']}\n原文:{p['url']}\n")

html_body = (
    f'<div style="max-width:640px;margin:0 auto;font-family:sans-serif">'
    + ('<img src="cid:poster" style="width:100%;border-radius:12px;margin-bottom:18px">' if poster_ok else '')
    + f'<h2 style="color:#2b2b2b">PYM {label}避險新聞摘要 — {TODAY_S}</h2>'
    + ''.join(rows_html)
    + f'<div style="text-align:center;margin:24px 0"><a href="{SITE}" style="background:#a67c00;color:#fff;padding:12px 26px;border-radius:8px;text-decoration:none;font-weight:700">睇更多 → protectyourmoney.co</a></div>'
    + '<div style="color:#999;font-size:12px;text-align:center">要增值，先避險 · protectyourmoney.co</div></div>')
txt_body = f"PYM {label}避險新聞摘要 — {TODAY_S}\n\n" + "\n".join(rows_txt) + f"\n睇更多:{SITE}\n"

msg = MIMEMultipart('related')
msg['Subject'] = f"PYM 每日避險新聞摘要 — {TODAY_S}"
msg['From'] = GU
msg['To'] = ", ".join(RECIPIENTS)
alt = MIMEMultipart('alternative'); msg.attach(alt)
alt.attach(MIMEText(txt_body, 'plain', 'utf-8'))
alt.attach(MIMEText(html_body, 'html', 'utf-8'))
if poster_ok:
    img = MIMEImage(open("/tmp/poster.png","rb").read()); img.add_header('Content-ID','<poster>')
    img.add_header('Content-Disposition','inline', filename='pym-daily.png'); msg.attach(img)

ctx = ssl.create_default_context()
with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
    s.login(GU, GP); s.sendmail(GU, RECIPIENTS, msg.as_string())
print(f"email sent to {len(RECIPIENTS)} recipients; poster={'yes' if poster_ok else 'no'}")
