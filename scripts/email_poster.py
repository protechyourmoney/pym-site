#!/usr/bin/env python3
# 用法: python email_poster.py news.json out.png  (news.json: [{"title","region","risk"}...])
import sys, json, io, base64, datetime, html
import qrcode, cairosvg

news = json.load(open(sys.argv[1], encoding='utf-8'))[:4]
OUT = sys.argv[2] if len(sys.argv) > 2 else 'poster.png'
TODAY = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d')

RISK_C = {1:'#6b7280',2:'#0ea5e9',3:'#8b5cf6',4:'#14b8a6',5:'#f59e0b',6:'#ef4444',7:'#e11d48',8:'#a67c00'}
FF = 'font-family="Noto Serif CJK TC"'
BG='#f7f4ee'; CARD='#ffffff'; LINE='#e4ddcf'; GOLD='#a67c00'; INK='#2b2b2b'; MUT='#7a7367'
W=1080; H=1080

qr = qrcode.QRCode(border=1, box_size=8); qr.add_data('https://protectyourmoney.co'); qr.make(fit=True)
qi = qr.make_image(fill_color='#2b2b2b', back_color='#ffffff').convert('RGB')
bq = io.BytesIO(); qi.save(bq,'PNG'); QR='data:image/png;base64,'+base64.b64encode(bq.getvalue()).decode()

def esc(s): return html.escape(str(s))
def wrap(t, n=20):
    t=str(t); out=[]; line=''
    for ch in t:
        line+=ch
        if len(line)>=n: out.append(line); line=''
    if line: out.append(line)
    return out[:2]

p=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
p.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
p.append(f'<rect x="0" y="0" width="{W}" height="12" fill="{GOLD}"/>')
p.append(f'<text x="60" y="110" {FF} font-size="46" font-weight="700" fill="{INK}">PYM 每日避險摘要</text>')
p.append(f'<text x="60" y="158" {FF} font-size="26" fill="{MUT}">Protect Your Money · {TODAY}</text>')
y=230
for n in news:
    c=RISK_C.get(int(n.get('risk',8)) if str(n.get('risk','8')).isdigit() else 8, GOLD)
    p.append(f'<rect x="60" y="{y}" width="{W-120}" height="170" rx="16" fill="{CARD}" stroke="{LINE}"/>')
    p.append(f'<circle cx="92" cy="{y+40}" r="11" fill="{c}"/>')
    p.append(f'<text x="118" y="{y+48}" {FF} font-size="23" fill="{MUT}">{esc(n.get("region","香港"))} · 風險 {esc(n.get("risk",8))}</text>')
    lines=wrap(n.get('title',''), 22)
    for i,ln in enumerate(lines):
        p.append(f'<text x="92" y="{y+95+i*42}" {FF} font-size="33" font-weight="700" fill="{INK}">{esc(ln)}</text>')
    y+=190
p.append(f'<rect x="{W-210}" y="{H-200}" width="150" height="150" rx="10" fill="#fff" stroke="{LINE}"/>')
p.append(f'<image x="{W-200}" y="{H-190}" width="130" height="130" href="{QR}"/>')
p.append(f'<text x="60" y="{H-120}" {FF} font-size="30" font-weight="700" fill="{GOLD}">protectyourmoney.co</text>')
p.append(f'<text x="60" y="{H-78}" {FF} font-size="22" fill="{MUT}">睇清風險 · 守住資產 · 掃碼即上 →</text>')
p.append('</svg>')
cairosvg.svg2png(bytestring=''.join(p).encode('utf-8'), write_to=OUT, output_width=W, output_height=H)
print('poster saved:', OUT)
