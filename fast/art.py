"""Shared painting harness: ops helpers, title bar, and an on-screen painter."""
import asyncio, time, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from engine import Browser, launch_brave

TOPBAR=58
class Art:
    def __init__(self, W, H, title):
        self.W=W; self.H=H; self.title=title; self.ops=[]
    def R(self,x,y,w,h,c): self.ops.append([0,int(x),int(y),int(max(1,w)),int(max(1,h)),int(c[0]),int(c[1]),int(c[2])])
    def L(self,x1,y1,x2,y2,w,c): self.ops.append([1,round(x1,1),round(y1,1),round(x2,1),round(y2,1),float(w),int(c[0]),int(c[1]),int(c[2])])
    def D(self,x,y,r,c,a=1.0):
        if r<=0: return
        self.ops.append([2,round(x,1),round(y,1),int(c[0]),int(c[1]),int(c[2]),round(max(0.4,r),1),round(a,3)])

def silhouette_rim(art, parts, lx, ly, col, w=2.2, dens=140, spread=1.25, alpha=0.85, fuzz=False):
    """rim light on a multi-part silhouette: only points on the TRUE outer edge are drawn.
    parts = [(cx,cy,rx,ry), ...]  lx,ly = light position"""
    import math
    for (cx,cy,rx,ry) in parts:
        a0=math.atan2(ly-cy, lx-cx)
        for i in range(dens):
            ang=a0-spread+2*spread*i/dens
            x=cx+math.cos(ang)*rx; y=cy+math.sin(ang)*ry
            inside=False
            for (ox,oy,orx,ory) in parts:
                if (ox,oy,orx,ory)==(cx,cy,rx,ry): continue
                if ((x-ox)/orx)**2 + ((y-oy)/ory)**2 < 1.06:
                    inside=True; break
            if inside: continue
            art.D(x,y,w,col,alpha)
            if fuzz:
                import random as _r
                ln=_r.uniform(2,6)
                art.L(x,y, x+math.cos(ang)*ln, y+math.sin(ang)*ln, 0.7, col)

def canopy(art, cx, cy, rx, ry, col, n=260, jitter=0.35, shade=(0,0,0)):
    """an irregular leafy mass: overlapping dabs, varied size and tone, with gaps"""
    import math, random
    for i in range(n):
        ang=random.uniform(0,6.2832)
        rr=random.random()**0.55
        x=cx+math.cos(ang)*rx*rr
        y=cy+math.sin(ang)*ry*rr
        if random.random()<0.16: continue                 # gaps let light through
        t=random.uniform(-jitter,jitter)
        c=mix(col, shade if t<0 else (255,255,255), abs(t)*0.5)
        r=random.uniform(2.2,6.5)*(1.15-0.45*rr)
        art.D(x,y,r,c,1.0)
        if random.random()<0.30:                          # a few crisp leaf edges
            a2=random.uniform(0,6.2832)
            art.L(x,y, x+math.cos(a2)*r*2.0, y+math.sin(a2)*r*2.0, 1.1, mix(c,shade,0.45))

def branch_with_leaves(art, x0, y0, ang, length, col, shade=(0,0,0), depth=0, tip=6.0):
    """a tapering branch that forks, with leaf clusters at the ends"""
    import math, random
    x1=x0+math.cos(ang)*length
    y1=y0+math.sin(ang)*length+length*0.10
    w=max(1.0, tip*(1.0-depth*0.22))
    art.L(x0,y0,x1,y1,w,mix(col,shade,0.55))
    if depth>=3 or length<26:
        canopy(art,x1,y1,length*0.85,length*0.7,col,n=int(length*3.2),shade=shade)
        return
    for k in range(random.randint(2,3)):
        branch_with_leaves(art,x1,y1, ang+random.uniform(-0.75,0.75), length*random.uniform(0.55,0.75),
                           col, shade, depth+1, tip)

def mix(a,b,t):
    t=max(0.0,min(1.0,t)); return tuple(int(round(a[i]+(b[i]-a[i])*t)) for i in range(3))

def _font(px):
    for p in ("/System/Library/Fonts/Supplemental/Copperplate.ttc",
              "/System/Library/Fonts/Supplemental/Futura.ttc"):
        try: return ImageFont.truetype(p,px)
        except Exception: pass
    return ImageFont.load_default()

def text(art, s, cx, cy, size, tracking, col, bg=(18,20,18), sup=3):
    f=_font(size*sup)
    tmp=Image.new("L",(8,8)); d=ImageDraw.Draw(tmp)
    ws=[d.textlength(ch,font=f) for ch in s]
    total=sum(ws)+tracking*sup*(len(s)-1)
    H=int(size*sup*1.6)
    img=Image.new("L",(int(total)+40,H),0); dr=ImageDraw.Draw(img)
    x=20
    for ch,w in zip(s,ws):
        dr.text((x,H*0.2),ch,font=f,fill=255); x+=w+tracking*sup
    img=img.resize((max(1,img.width//sup),max(1,img.height//sup)),Image.LANCZOS)
    m=np.asarray(img)
    x0=int(cx-img.width/2); y0=int(cy-img.height/2)
    ys,xs=np.nonzero(m>40)
    for yy,xx in zip(ys,xs):
        a=m[yy,xx]/255.0
        art.R(x0+xx,y0+yy,1,1, mix(bg,col,a))

GEN=""
def stamp(art):
    n=len(art.ops)
    art.R(0,0,art.W,TOPBAR,(18,20,18))
    art.L(0,TOPBAR,art.W,TOPBAR,1.5,(120,118,96))
    text(art, art.title, art.W*0.5, TOPBAR*0.42, 21, 7, (232,226,196))
    sub=f"{n:,} STROKES" + (f"   ·   {GEN}" if GEN else "")
    text(art, sub, art.W*0.5, TOPBAR*0.78, 11, 5, (150,146,120))
    return n

async def paint(art, pace=0.03, chunk=7000, out=None):
    n=stamp(art)
    print(f"{art.title}: {n:,} strokes ({len(art.ops):,} total ops)",flush=True)
    import urllib.request
    try: urllib.request.urlopen("http://localhost:9231/json/version",timeout=1); up=True
    except Exception: up=False
    if not up: launch_brave(9231,size=(1560,1010)); await asyncio.sleep(2.0)
    br=Browser(9231); await br.connect()
    tab=await br.existing_page("replay") or await br.new_tab("replay")
    from engine import paint_url
    await tab.goto(paint_url())
    await tab.measure_canvas(); await tab.resize_canvas(art.W,art.H)
    t=time.time()
    for i in range(0,len(art.ops),chunk):
        tab.fast(art.ops[i:i+chunk]); await tab.sync()
        if pace: await asyncio.sleep(pace)
    await tab.sync()
    print(f"painted in {time.time()-t:.2f}s",flush=True)
    await tab.png(out or (art.title.lower().replace(' ','_')[:28]+".png"))
    await br.close()
