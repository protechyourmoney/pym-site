#!/usr/bin/env python3
# 每日自動搵 PYM 相關新聞 → AI 揀選/寫簡介/標風險+地區 → 插入 index.html
# 來源政策:近 48 小時、最新優先;同等新再按來源級別(A 權威 > B 可信 > C 聚合)排;
# A 級但付費牆(彭博/WSJ/FT/日經)可引用,但盡量揀讀者打得開嘅連結。
import os, re, sys, json, datetime, urllib.parse, calendar
import feedparser
from anthropic import Anthropic

NOW = datetime.datetime.utcnow()
TODAY = (NOW + datetime.timedelta(hours=8)).strftime('%Y-%m-%d')
MAX_AGE_HOURS = 48

QUERIES = [
    # 本地/中國/中美 主題
    '香港 樓市 銀主盤', '香港 樓價 蝕讓', '香港 零售 經濟', '香港 保險 監管',
    '中國 資本管制 走資', '人民幣 匯率', '中國 追稅 境外 資產', '中國 房地產 恒大',
    '中美 金融 制裁', '美國 中概股 除牌', '香港 移民 資產', '中國 通縮 銀行',
    # A 級權威來源導向查詢(多撈高質來源上嚟)
    '路透 香港 經濟', '路透 人民幣', '彭博 香港', '財新 走資',
    'Reuters Hong Kong economy', '日經 中國 經濟',
]

# 來源分級:A=權威/通訊社/深度, B=可信・易讀中文, C=聚合/一般。數字越細越高級。
TIER_A = ['reuters', '路透', 'bloomberg', '彭博', 'wall street', 'wsj', '華爾街日報', '华尔街日报',
          'financial times', 'ft中文', 'ft 中文', '金融時報', '金融时报',
          'nikkei', '日經', '日经', 'caixin', '財新', '财新', 'scmp', 'south china morning', '南華早報']
TIER_B = ['明報', '明报', '經濟日報', '经济日报', 'hket', '信報', '信报', '星島', '星岛',
          '中央社', 'cna', '聯合報', '联合报', '工商時報', 'rthk', '香港電台', '香港电台', 'now 新聞', 'now新聞']

def tier_of(src):
    s = (src or '').lower()
    for kw in TIER_A:
        if kw.lower() in s:
            return 1
    for kw in TIER_B:
        if kw.lower() in s:
            return 2
    return 3  # C / 未知

def age_hours(entry):
    t = entry.get('published_parsed') or entry.get('updated_parsed')
    if not t:
        return None
    try:
        dt = datetime.datetime.utcfromtimestamp(calendar.timegm(t))
        return (NOW - dt).total_seconds() / 3600.0
    except Exception:
        return None

def fetch():
    items, seen = [], set()
    for q in QUERIES:
        url = 'https://news.google.com/rss/search?q=' + urllib.parse.quote(q) + '&hl=zh-HK&gl=HK&ceid=HK:zh-Hant'
        try:
            d = feedparser.parse(url)
        except Exception:
            continue
        for e in d.entries[:8]:
            title = re.sub(r'\s*-\s*[^-]+$', '', e.get('title', '')).strip()
            if not title:
                continue
            k = title[:30]
            if k in seen:
                continue
            ah = age_hours(e)
            # 近 48 小時優先:有日期而超過 48 小時就跳過;冇日期就當未知保留
            if ah is not None and ah > MAX_AGE_HOURS:
                continue
            seen.add(k)
            src = ''
            if e.get('source'):
                src = e.source.get('title', '') if hasattr(e.source, 'get') else getattr(e.source, 'title', '')
            items.append({'title': title, 'link': e.get('link', ''), 'source': src,
                          'tier': tier_of(src), 'age': ah if ah is not None else 999})
    return items

html = open('index.html', encoding='utf-8').read()
existing_titles = set(re.findall(r'title:"([^"]+)"', html))
existing_urls = set(re.findall(r'url:"([^"]+)"', html))

raw = [it for it in fetch() if it['title'] not in existing_titles and it['link'] not in existing_urls]
# 排序:最新優先(以「幾多個 12 小時區間」分桶) → 同桶內 A 級行先 → 再按新到舊
def sort_key(it):
    bucket = int(it['age'] // 12) if it['age'] != 999 else 99   # 0=最新 12h, 1=12-24h ...
    return (bucket, it['tier'], it['age'])
raw.sort(key=sort_key)
cands = raw[:40]
if not cands:
    print('no candidates'); sys.exit(0)

TIER_NAME = {1: 'A權威', 2: 'B可信', 3: 'C一般'}
def agestr(a):
    return '未知' if a == 999 else (f'{a:.0f}h前')
listing = '\n'.join(
    f"{i+1}. [{TIER_NAME[c['tier']]}|{agestr(c['age'])}] {c['title']} | 來源:{c['source']} | {c['link']}"
    for i, c in enumerate(cands))

RULES = """風險編號:
1 格價 2 流動性 3 平台(券商/銀行/保險) 4 貨幣(聯匯/人民幣/港元) 5 政策(跨境資金/走資/離岸稅/外匯管制) 6 地緣中美(金融戰/制裁/關稅/FCC) 7 中國因素(經濟/通縮/政局/房地產/銀行) 8 香港本地經濟(樓市/零售/就業/營商)
地區只三揀一:香港 / 中國 / 美國"""

SOURCE_POLICY = """來源優先次序(重要):
1) 最新優先:揀近 1-2 日嘅新聞,越新越好(候選已標示「幾多小時前」)。
2) 同等新,揀來源級別高嘅:A權威(路透/彭博/WSJ中文/FT中文/日經中文/財新/SCMP)> B可信(明報/經濟日報/信報/星島/中央社/RTHK)> C一般(聚合/其他)。
3) 彭博/WSJ/FT/日經等 A 級常有付費牆:可引用,但如果有同一單新聞嘅可免費閱讀版本(中文或其他可信媒體),優先畀讀者打得開嗰條連結。
4) 寧揀 1 條 A 級新鮮、過 1 條 C 級舊聞;同一單新聞唔好重覆揀。"""

prompt = f"""你係 PYM(Protect Your Money)避險新聞編輯。以下係今日候選新聞標題(已標來源級別同新鮮度)。揀出最多 4 條同「香港/中國/美國 資產避險、金融風險」真正相關嘅(其餘唔好),為每條輸出 JSON。

{RULES}

{SOURCE_POLICY}

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
