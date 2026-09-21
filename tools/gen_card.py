# -*- coding: utf-8 -*-
# PYM 每日新聞圖生成器
# 用法: python3 tools/gen_card.py <YYYY-MM-DD> <輸出png路徑> <items.json路徑>
# items.json: [{"risk":6,"tag":"地緣・中美","region":"中國","title":"...","source":"中央社／路透"}, ...]
import sys, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

date = sys.argv[1]; out = sys.argv[2]
items_path = sys.argv[3] if len(sys.argv) > 3 else "/tmp/pym_items.json"
items = json.load(open(items_path, encoding="utf-8"))[:4]
n = max(1, len(items))

W = H = 1080
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REG  = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
HK = 4
def fb(s): return ImageFont.truetype(BOLD, s, index=HK)
def fr(s): return ImageFont.truetype(REG, s, index=HK)
INK=(28,32,40); INK2=(90,96,106); GOLD=(200,133,20); GOLDB=(232,166,40)
WHITE=(255,255,255); CARDBORD=(238,228,206)
RISK={1:(14,165,233),2:(8,145,178),3:(124,58,237),4:(22,163,74),5:(217,119,6),6:(229,66,62),7:(202,138,4),8:(71,85,105)}
def rcol(r):
    try: return RISK.get(int(r), GOLD)
    except: return GOLD
def tint(c,a=0.14): return tuple(int(ci*a+255*(1-a)) for ci in c)

img=Image.new("RGB",(W,H),(255,250,236)); px=img.load()
top=(255,247,228); bot=(250,232,190)
for y in range(H):
    t=y/H; row=(int(top[0]*(1-t)+bot[0]*t),int(top[1]*(1-t)+bot[1]*t),int(top[2]*(1-t)+bot[2]*t))
    for x in range(W): px[x,y]=row
glow=Image.new("L",(W,H),0); gd=ImageDraw.Draw(glow)
gd.ellipse([-200,-220,380,360],fill=90); gd.ellipse([W-360,H-320,W+220,H+240],fill=70)
glow=glow.filter(ImageFilter.GaussianBlur(150))
img=Image.composite(Image.new("RGB",(W,H),(255,214,120)),img,glow)
d=ImageDraw.Draw(img)
M=70
def tw(t,f): return d.textbbox((0,0),t,font=f)[2]
def wrap(t,f,mw):
    L=[];c=""
    for ch in str(t):
        if ch=="\n": L.append(c);c="";continue
        if tw(c+ch,f)<=mw: c+=ch
        else: L.append(c);c=ch
    if c:L.append(c)
    return L
def clip(line,f,mw):
    if tw(line,f)<=mw: return line
    while line and tw(line+"…",f)>mw: line=line[:-1]
    return line+"…"

d.rectangle([0,0,W,10],fill=GOLDB)
# header
y=60
d.rounded_rectangle([M,y,M+98,y+98],radius=22,fill=GOLDB)
lf=fb(40); lw=tw("PYM",lf); d.text((M+49-lw/2,y+28),"PYM",font=lf,fill=WHITE)
d.text((M+122,y+12),"PYM 避險逃生門",font=fb(44),fill=INK)
d.text((M+124,y+70),"P R O T E C T   Y O U R   M O N E Y",font=fr(20),fill=GOLD)
dd=date.replace("-","."); df=fb(30); dw=tw(dd,df)
d.rounded_rectangle([W-M-dw-44,y+22,W-M,y+22+54],radius=27,fill=GOLDB)
d.text((W-M-dw-22,y+33),dd,font=df,fill=WHITE)
# title
y=176
d.text((M,y),"今日避險焦點",font=fb(68),fill=INK)
d.text((M+4,y+90),"DAILY RISK BRIEF",font=fb(24),fill=GOLD)
d.text((M+236,y+92),"· %d 則精選新聞"%n,font=fr(24),fill=INK2)

CW=W-2*M
cy0=312; footer_line=H-56-16; avail=footer_line-8-cy0; gap=18
ch=int((avail-gap*(n-1))/n); ch=min(ch,230)
tf_size = 36 if n<=2 else (32 if n==3 else 28)
tf=fb(tf_size); LH=tf_size+10
PAD=20; CHIP=42; G1=10; SRCH=24; PADB=14
title_area = ch-(PAD+CHIP+G1+8+SRCH+PADB)
maxlines=max(1, title_area//LH)
total=n*ch+gap*(n-1); cy=cy0+max(0,(avail-total)//2)

# shadows
sh=Image.new("RGBA",(W,H),(0,0,0,0)); sd=ImageDraw.Draw(sh)
for i in range(n):
    ty0=cy+i*(ch+gap)
    sd.rounded_rectangle([M+6,ty0+10,M+CW+6,ty0+ch+10],radius=24,fill=(120,90,20,60))
sh=sh.filter(ImageFilter.GaussianBlur(14))
img=Image.alpha_composite(img.convert("RGBA"),sh).convert("RGB"); d=ImageDraw.Draw(img)

for i,it in enumerate(items):
    top_y=cy+i*(ch+gap); col=rcol(it.get("risk"))
    d.rounded_rectangle([M,top_y,M+CW,top_y+ch],radius=22,fill=WHITE,outline=CARDBORD,width=1)
    d.rounded_rectangle([M,top_y,M+11,top_y+ch],radius=6,fill=col)
    px0=M+44; py0=top_y+PAD
    d.ellipse([px0,py0,px0+40,py0+40],fill=col)
    nf=fb(24); ns=str(it.get("risk","")); nw=tw(ns,nf); d.text((px0+20-nw/2,py0+6),ns,font=nf,fill=WHITE)
    d.text((px0+56,py0-1),"風險 %s"%it.get("risk",""),font=fb(22),fill=col)
    d.text((px0+56,py0+25),str(it.get("tag","")),font=fr(20),fill=INK2)
    reg=str(it.get("region","")); rf=fb(22); rw=tw(reg,rf)
    d.rounded_rectangle([M+CW-rw-54,py0+2,M+CW-26,py0+40],radius=20,fill=tint(col),outline=col,width=2)
    d.text((M+CW-rw-40,py0+8),reg,font=rf,fill=col)
    lines=wrap(it.get("title",""),tf,CW-84)
    if len(lines)>maxlines:
        lines=lines[:maxlines]; lines[-1]=clip(lines[-1]+"…",tf,CW-84)
    ty=py0+CHIP+G1
    for ln in lines: d.text((px0,ty),ln,font=tf,fill=INK); ty+=LH
    d.text((px0,top_y+ch-PADB-22),"來源："+str(it.get("source","")),font=fr(20),fill=INK2)

fy=H-56
d.line([M,fy-16,W-M,fy-16],fill=(226,210,178),width=2)
d.text((M,fy),"protectyourmoney.co",font=fb(30),fill=GOLD)
tg="避險 · 逃生 · 保護你的資產"; tf2=fr(26); twd=tw(tg,tf2)
d.text((W-M-twd,fy+3),tg,font=tf2,fill=INK2)
img.save(out,"PNG"); print("card saved:", out, "items:", n)
