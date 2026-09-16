"""Redwood grove in fog with light shafts. Titled and stroke-stamped."""
import asyncio, sys, time, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from engine import Browser
random.seed(17)
CW=int(sys.argv[1]) if len(sys.argv)>1 else 1320
CH=int(sys.argv[2]) if len(sys.argv)>2 else 880
TITLE="FIRST LIGHT IN THE GROVE"
ops=[]
def R(x,y,w,h,c): ops.append([0,int(x),int(y),int(max(1,w)),int(max(1,h)),int(c[0]),int(c[1]),int(c[2])])
def L(x1,y1,x2,y2,w,c): ops.append([1,round(x1,1),round(y1,1),round(x2,1),round(y2,1),float(w),int(c[0]),int(c[1]),int(c[2])])
def D(x,y,r,c,a=1.0): ops.append([2,round(x,1),round(y,1),int(c[0]),int(c[1]),int(c[2]),round(max(0.4,r),1),round(a,3)])
def mix(a,b,t):
    t=max(0.0,min(1.0,t)); return tuple(int(round(a[i]+(b[i]-a[i])*t)) for i in range(3))

TOPBAR=58
def build():
    # ---- fog: brightest up where the light enters, deepening to the floor ----
    for y in range(TOPBAR,CH,2):
        t=(y-TOPBAR)/(CH-TOPBAR)
        R(0,y,CW,3, mix((196,196,178),(38,44,38), t**1.25))
    # a warm pool of light high on the left
    for k in range(80):
        u=k/80.0
        D(CW*0.30, CH*0.10, 560*(1-u)+30, (236,220,168), 0.055*(u**1.4))
    # ---- trunks, far to near ----
    def trunk(x, wdt, depth, lean=0.0):
        """depth 0 = far/faint, 1 = near/dark"""
        base=mix((150,152,140),(34,30,26), depth)
        lit =mix((198,196,176),(96,80,62), depth)
        top_y=TOPBAR-20
        for yy in range(int(top_y), CH, 3):
            t=(yy-top_y)/(CH-top_y)
            w=wdt*(0.72+0.5*t)
            xc=x+lean*t*90
            n=int(w/2.2)+1
            for k in range(n):
                v=k/max(1,n-1)
                # cylinder shading: lit on the left, falling to dark on the right
                shade=1.0-abs(v-0.28)*1.55
                c=mix(base, lit, max(0.0,shade)*0.85)
                c=mix(c, (206,206,190), (1-depth)*0.55*(1-t*0.35))   # fog wash
                R(xc-w/2+w*v, yy, 3, 4, c)
            # bark striations
            if depth>0.45 and yy%9==0:
                for b in range(4):
                    bx=xc-w/2+w*random.uniform(0.08,0.92)
                    L(bx,yy,bx+random.uniform(-1.5,1.5),yy+random.uniform(7,18), 1.1,
                      mix(base,(12,10,8),0.55))
    far=[(CW*0.06,16,0.12),(CW*0.19,13,0.10),(CW*0.33,18,0.16),(CW*0.46,14,0.11),
         (CW*0.58,20,0.18),(CW*0.71,15,0.12),(CW*0.84,17,0.15),(CW*0.95,13,0.10)]
    mid=[(CW*0.12,40,0.42,-0.05),(CW*0.40,46,0.46,0.04),(CW*0.66,42,0.44,-0.03),(CW*0.90,38,0.40,0.05)]
    near=[(CW*0.02,104,0.88,0.03),(CW*0.52,118,0.92,-0.02),(CW*0.99,110,0.90,0.02)]
    for x,w,d in far: trunk(x,w,d)
    # fog layer between depths
    for i in range(700):
        D(random.uniform(0,CW), random.uniform(TOPBAR,CH), random.uniform(40,120), (204,204,188), 0.013)
    for x,w,d,l in mid: trunk(x,w,d,l)
    for i in range(500):
        D(random.uniform(0,CW), random.uniform(TOPBAR,CH), random.uniform(30,90), (196,198,182), 0.011)
    for x,w,d,l in near: trunk(x,w,d,l)
    # ---- light shafts angling down from the upper left ----
    for i in range(20):
        x0=random.uniform(-CW*0.1, CW*0.75); ang=1.02+random.uniform(-0.10,0.10)
        wdt=random.uniform(16,54)
        for k in range(110):
            u=k/110.0
            x=x0+math.cos(ang-0.35)*1500*u*0.55
            y=TOPBAR+math.sin(ang)*1500*u*0.62
            if y>CH: break
            D(x,y, wdt*(0.35+u*1.25), (250,238,190), 0.013*(1-u*0.88))
    # dust motes drifting in the light
    for i in range(420):
        x=random.uniform(0,CW); y=random.uniform(TOPBAR,CH*0.88)
        b=random.random()
        D(x,y, 0.7+b*1.5, (255,248,214), 0.10+0.45*b)
    # ---- forest floor + ferns ----
    for y in range(int(CH*0.84),CH,2):
        t=(y-CH*0.84)/(CH*0.16)
        R(0,y,CW,3, mix((54,54,44),(16,18,14), t))
    for i in range(150):
        fx=random.uniform(0,CW); fy=CH*random.uniform(0.85,1.0)
        fl=random.uniform(26,74); a=random.uniform(-1.2,-1.9)
        col=mix((30,48,30),(84,112,62), random.random()*0.8)
        ex,ey=fx+math.cos(a)*fl, fy+math.sin(a)*fl
        L(fx,fy,ex,ey,1.6,col)
        for k in range(7):
            t=k/7.0
            px=fx+(ex-fx)*t; py=fy+(ey-fy)*t
            lw=fl*0.22*(1-t)
            L(px,py,px-lw,py-lw*0.5,1.0,col); L(px,py,px+lw,py-lw*0.5,1.0,col)

def text_ops(text, cx, cy, size, tracking, col, sup=3):
    for p in ("/System/Library/Fonts/Supplemental/Copperplate.ttc",
              "/System/Library/Fonts/Supplemental/Futura.ttc"):
        try: f=ImageFont.truetype(p,size*sup); break
        except Exception: f=None
    if f is None: f=ImageFont.load_default()
    tmp=Image.new("L",(8,8)); d=ImageDraw.Draw(tmp)
    ws=[d.textlength(ch,font=f) for ch in text]
    total=sum(ws)+tracking*sup*(len(text)-1)
    H=int(size*sup*1.6)
    img=Image.new("L",(int(total)+40,H),0); dr=ImageDraw.Draw(img)
    x=20
    for ch,w in zip(text,ws):
        dr.text((x,H*0.2),ch,font=f,fill=255); x+=w+tracking*sup
    img=img.resize((img.width//sup,img.height//sup),Image.LANCZOS)
    m=np.asarray(img)
    x0=int(cx-img.width/2); y0=int(cy-img.height/2)
    ys,xs=np.nonzero(m>40)
    for yy,xx in zip(ys,xs):
        a=m[yy,xx]/255.0
        R(x0+xx,y0+yy,1,1, mix((18,20,18), col, a))

async def main():
    build()
    art=len(ops)
    # ---- title bar: name + stroke count ----
    R(0,0,CW,TOPBAR,(18,20,18))
    L(0,TOPBAR,CW,TOPBAR,1.5,(120,118,96))
    text_ops(TITLE, CW*0.5, TOPBAR*0.42, 21, 7, (232,226,196))
    text_ops(f"{art:,} STROKES", CW*0.5, TOPBAR*0.78, 11, 5, (150,146,120))
    print(f"art strokes {art}, total ops {len(ops)}",flush=True)
    from engine import launch_brave
    import urllib.request
    try: urllib.request.urlopen("http://localhost:9231/json/version",timeout=1); up=True
    except Exception: up=False
    if not up: launch_brave(9231,size=(1560,1010)); await asyncio.sleep(2.0)
    br=Browser(9231); await br.connect(); tab=await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r="+str(int(time.time())))
    await tab.measure_canvas(); await tab.resize_canvas(CW,CH)
    t1=time.time()
    for i in range(0,len(ops),7000):
        tab.fast(ops[i:i+7000]); await tab.sync(); await asyncio.sleep(0.03)
    await tab.sync()
    print(f"painted in {time.time()-t1:.2f}s",flush=True)
    await tab.png("forest.png")
    await br.close()
asyncio.run(main())
