#!/usr/bin/env python3
# 每日自動搵 PYM 相關新聞 → AI 揀選/寫簡介/標風險+地區 → 插入 index.html
import os, re, sys, json, datetime, urllib.parse
import feedparser
from anthropic import Anthropic

TODAY = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d')

QUERIES = [
    '香港 樓市 銀主盤', '香港 樓價 蝕讓', '香港 零售 經濟', '香港 保險 監管',
    '中國 資本管制 走資', '人民幣 匯率', '中國 追稅 境外 資產', '中國 房地產 恒大',
    '中美 金融 制裁', '美國 中概股 除牌', '香港 移民 資產', '中國 通縮 銀行',
]

def fetch():
    items, seen = [], set()
    for q in QUERIES:
        url = 'https://news.google.com/rss/search?q=' + urllib.parse.quote(q) + '&hl=zh-HK&gl=HK&ceid=HK:zh-Hant'
        try:
            d = feedparser.parse(url)
        except Exception:
            continue
        for e in d.entries[:6]:
            title = re.sub(r'\s*-\s*[^-]+$', '', e.get('title', '')).strip()
            if not title:
                continue
            k = title[:30]
            if k in seen:
                continue
            seen.add(k)
            src = ''
            if e.get('source'):
                src = e.source.get('title', '') if hasattr(e.source, 'get') else getattr(e.source, 'title', '')
            items.append({'title': title, 'link': e.get('link', ''), 'source': src})
    return items

html = open('index.html', encoding='utf-8').read()
existing_titles = set(re.findall(r'title:"([^"]+)"', html))
existing_urls = set(re.findall(r'url:"([^"]+)"', html))

cands = [it for it in fetch() if it['title'] not in existing_titles and it['link'] not in existing_urls][:40]
if not cands:
    print('no candidates'); sys.exit(0)

listing = '\n'.join(f"{i+1}. {c['title']} | 來源:{c['source']} | {c['link']}" for i, c in enumerate(cands))

RULES = """風險編號:
1 格價 2 流動性 3 平台(券商/銀行/保險) 4 貨幣(聯匯/人民幣/港元) 5 政策(跨境資金/走資/離岸稅/外匯管制) 6 地緣中美(金融戰/制裁/關稅/FCC) 7 中國因素(經濟/通縮/政局/房地產/銀行) 8 香港本地經濟(樓市/零售/就業/營商)
地區只三揀一:香港 / 中國 / 美國"""

prompt = f"""你係 PYM(Protect Your Money)避險新聞編輯。以下係今日候選新聞標題。揀出最多 4 條同「香港/中國/美國 資產避險、金融風險」真正相關嘅(其餘唔好),為每條輸出 JSON。

{RULES}

今日日期:{TODAY}

候選:
{listing}

只輸出一個 JSON array,每個 object 欄位:
risk(1-8 整數), tag(短標籤,例 "樓市 · 銀主盤"), region("香港"/"中國"/"美國"), date("{TODAY}"), source(媒體名), title(乾淨中文標題), url(用候選提供嘅連結), summary(2-3 句客觀中文,唔好作數字)。
如果冇一條相關,輸出 []。唔好有其他文字。"""

client = Anthropic()
msg = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=2000,
                             messages=[{"role": "user", "content": prompt}])
txt = msg.content[0].text.strip()
m = re.search(r'\[.*\]', txt, re.S)
if not m:
    print('no json returned'); sys.exit(0)
try:
    entries = json.loads(m.group(0))
except Exception as ex:
    print('json parse fail:', ex); sys.exit(0)

entries = [e for e in entries if e.get('title') and e['title'] not in existing_titles][:4]
if not entries:
    print('nothing new'); sys.exit(0)

def esc(s):
    return str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')

def risk(e):
    try:
        r = int(e.get('risk', 8))
        return r if 1 <= r <= 8 else 8
    except Exception:
        return 8

block = ''
for e in entries:
    block += (f'  {{risk:{risk(e)}, tag:"{esc(e.get("tag",""))}", region:"{esc(e.get("region","香港"))}", date:"{esc(e.get("date",TODAY))}", source:"{esc(e.get("source",""))}",\n'
              f'   title:"{esc(e.get("title"))}",\n'
              f'   url:"{esc(e.get("url",""))}",\n'
              f'   summary:"{esc(e.get("summary",""))}"}},\n')

html = html.replace('const PYMNEWS = [\n', 'const PYMNEWS = [\n' + block, 1)
open('index.html', 'w', encoding='utf-8').write(html)
print(f'added {len(entries)} entries for {TODAY}')
