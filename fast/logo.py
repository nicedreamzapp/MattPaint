"""Divine Tribe logo: cosmic ground, radiant sunburst mandala, gold engraved wordmark.
Glyphs rasterised with PIL, then painted into MattPaint through the fast engine.
"""
import asyncio, sys, time, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from engine import Browser
random.seed(3)
CW=int(sys.argv[1]) if len(sys.argv)>1 else 1500
CH=int(sys.argv[2]) if len(sys.argv)>2 else 950
VISIBLE = "--hidden" not in sys.argv   # on-screen by DEFAULT; hiding must be explicit

GOLD_HI=(255,236,178); GOLD=(228,183,86); GOLD_LO=(166,112,34)
def mix(a,b,t): return tuple(int(round(a[i]+(b[i]-a[i])*max(0,min(1,t)))) for i in range(3))

ops=[]
def R(x,y,w,h,c): ops.append([0,int(x),int(y),int(max(1,w)),int(max(1,h)),int(c[0]),int(c[1]),int(c[2])])
def S(x1,y1,x2,y2,w,c): ops.append([1,round(x1,1),round(y1,1),round(x2,1),round(y2,1),float(w),int(c[0]),int(c[1]),int(c[2])])
def D(x,y,r,c,a=1.0): ops.append([2,round(x,1),round(y,1),int(c[0]),int(c[1]),int(c[2]),round(r,1),round(a,3)])

def font(sz):
    for p in ("/System/Library/Fonts/Supplemental/Copperplate.ttc",
              "/System/Library/Fonts/Supplemental/Futura.ttc",
              "/System/Library/Fonts/Supplemental/Impact.ttf"):
        try: return ImageFont.truetype(p, sz)
        except Exception: continue
    return ImageFont.load_default()

def tracked_mask(text, sz, tracking):
    """render text with letterspacing to a 1-bit mask + its bbox"""
    f=font(sz)
    widths=[]
    tmp=Image.new("L",(10,10)); d=ImageDraw.Draw(tmp)
    for ch in text:
        widths.append(d.textlength(ch,font=f))
    total=sum(widths)+tracking*(len(text)-1)
    H=int(sz*1.7)
    img=Image.new("L",(int(total)+40,H),0); dr=ImageDraw.Draw(img)
    x=20
    for ch,w in zip(text,widths):
        dr.text((x,H*0.18),ch,font=f,fill=255); x+=w+tracking
    return np.asarray(img), int(total)+40, H

def paint_text(text, cx, cy, sz, tracking, top_c, bot_c, cell=2, shadow=True):
    m,W,H=tracked_mask(text,sz,tracking)
    x0=int(cx-W/2); y0=int(cy-H/2)
    ys,xs=np.nonzero(m>90)
    if len(ys)==0: return
    ymin,ymax=ys.min(),ys.max()
    if shadow:
        for yy,xx in zip(ys[::3],xs[::3]):
            R(x0+xx+3,y0+yy+4,cell,cell,(18,14,26))
    for yy,xx in zip(ys,xs):
        t=(yy-ymin)/max(1,(ymax-ymin))
        c=mix(top_c,bot_c,t)
        # bright bevel along the upper edge of each glyph
        if m[max(0,yy-3),xx]<90: c=mix(c,(255,250,225),0.55)
        R(x0+xx,y0+yy,cell,cell,c)

def build():
    # ---- cosmic ground ----
    for y in range(0,CH,2):
        t=y/CH
        R(0,y,CW,3, mix((16,12,30), (34,20,44), t))
    ecx,ecy=CW/2, CH*0.40
    # warm divine glow behind the emblem
    for r,a in [(430,0.10),(340,0.12),(260,0.14),(190,0.16),(130,0.20),(80,0.28)]:
        D(ecx,ecy,r,(150,86,40),a)
    # stars
    for i in range(160):
        x=random.uniform(0,CW); y=random.uniform(0,CH*0.8)
        D(x,y,random.uniform(0.6,1.8),(230,225,245),random.uniform(0.25,0.8))
    # ---- sunburst rays ----
    for i in range(48):
        a=i*(2*math.pi/48)
        long_ray = (i%4==0)
        r0,r1=(118, 300) if long_ray else (118, 232)
        w=6.5 if long_ray else 3.0
        x1,y1=ecx+math.cos(a)*r0, ecy+math.sin(a)*r0
        x2,y2=ecx+math.cos(a)*r1, ecy+math.sin(a)*r1
        S(x1,y1,x2,y2,w, mix(GOLD,GOLD_LO,0.35))
        S(x1,y1,(x1+x2)/2,(y1+y2)/2, w*0.8, GOLD_HI)
    # ---- mandala rings ----
    def ring(rad,w,c,step=2.0):
        n=int(2*math.pi*rad/step)
        for i in range(n):
            a=i*(2*math.pi/n)
            D(ecx+math.cos(a)*rad, ecy+math.sin(a)*rad, w, c, 1.0)
    ring(112,3.2,GOLD_HI); ring(104,1.6,mix(GOLD,GOLD_LO,0.5))
    ring(150,1.4,mix(GOLD,GOLD_LO,0.6))
    # tribal dots + triangles on the outer ring
    for i in range(24):
        a=i*(2*math.pi/24)
        D(ecx+math.cos(a)*150, ecy+math.sin(a)*150, 4.2, GOLD_HI)
    for i in range(12):
        a=i*(2*math.pi/12)+math.pi/12
        px,py=ecx+math.cos(a)*178, ecy+math.sin(a)*178
        ux,uy=math.cos(a),math.sin(a); vx,vy=-uy,ux
        for k in range(10):
            t=k/10; w=13*(1-t)
            S(px+ux*t*22 - vx*w/2, py+uy*t*22 - vy*w/2, px+ux*t*22 + vx*w/2, py+uy*t*22 + vy*w/2, 2.0, mix(GOLD,GOLD_HI,1-t))
    # inner sacred triangle + core
    for k in range(3):
        a1=-math.pi/2+k*2*math.pi/3; a2=-math.pi/2+(k+1)*2*math.pi/3
        S(ecx+math.cos(a1)*78, ecy+math.sin(a1)*78, ecx+math.cos(a2)*78, ecy+math.sin(a2)*78, 3.4, GOLD_HI)
    for r in range(40,0,-2):
        D(ecx,ecy,r, mix(GOLD_HI,(255,252,236), 1-r/40), 0.5)
    # ---- wordmark ----
    paint_text("DIVINE TRIBE", CW/2, CH*0.775, 104, 16, GOLD_HI, mix(GOLD_LO,(120,70,18),0.4))
    # rule with diamond
    ry=CH*0.875
    for side in (-1,1):
        S(CW/2+side*70, ry, CW/2+side*330, ry, 2.2, mix(GOLD,GOLD_LO,0.4))
        D(CW/2+side*340, ry, 3.0, GOLD_HI)
    for k in range(11):
        t=k/10; w=16*(1-abs(t-0.5)*2)
        S(CW/2-w, ry-16+t*32, CW/2+w, ry-16+t*32, 2.0, GOLD_HI)
    paint_text("HANDCRAFTED  ·  HUMBOLDT", CW/2, CH*0.945, 30, 12, mix(GOLD,(210,180,140),0.4), mix(GOLD_LO,(140,100,50),0.3), shadow=False)

async def main():
    build()
    print(f"{len(ops)} ops",flush=True)
    if VISIBLE:
        from engine import launch_brave
        import urllib.request
        try: urllib.request.urlopen("http://localhost:9231/json/version",timeout=1); up=True
        except Exception: up=False
        if not up: launch_brave(9231,size=(1560,1010)); await asyncio.sleep(2.0)
        br=Browser(9231); await br.connect(); tab=await br.existing_page("replay") or await br.new_tab("replay")
    else:
        br=Browser(9222); await br.connect(); tab=await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r="+str(int(time.time())))
    await tab.measure_canvas(); t0=time.time(); await tab.resize_canvas(CW,CH)
    for i in range(0,len(ops),6000):
        tab.fast(ops[i:i+6000])
        if i%30000==0: await tab.sync()
    tab.fast_commit(); await tab.sync()
    print(f"DONE {len(ops)} ops in {time.time()-t0:.2f}s",flush=True)
    await tab.png("logo.png")
    if not VISIBLE: await tab.close()
    await br.close()
asyncio.run(main())
