"""Divine Tribe logo, everything-turned-up version: per-pixel glyphs with anti-aliasing,
brushed-metal gold with scratches and specular, smooth volumetric glow, filigree.
"""
import asyncio, sys, time, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from engine import Browser
random.seed(5)
CW=int(sys.argv[1]) if len(sys.argv)>1 else 1600
CH=int(sys.argv[2]) if len(sys.argv)>2 else 1000
VISIBLE = "--hidden" not in sys.argv   # on-screen by DEFAULT; hiding must be explicit

GOLD_HI=(255,242,196); GOLD=(232,188,92); GOLD_LO=(150,98,28); DEEP=(96,58,16)
def mix(a,b,t):
    t=max(0.0,min(1.0,t)); return tuple(int(round(a[i]+(b[i]-a[i])*t)) for i in range(3))

ops=[]
def R(x,y,w,h,c): ops.append([0,int(x),int(y),int(max(1,w)),int(max(1,h)),int(c[0]),int(c[1]),int(c[2])])
def S(x1,y1,x2,y2,w,c): ops.append([1,round(x1,1),round(y1,1),round(x2,1),round(y2,1),float(w),int(c[0]),int(c[1]),int(c[2])])
def D(x,y,r,c,a=1.0): ops.append([2,round(x,1),round(y,1),int(c[0]),int(c[1]),int(c[2]),round(r,1),round(a,3)])

def font(sz):
    for p in ("/System/Library/Fonts/Supplemental/Copperplate.ttc",
              "/System/Library/Fonts/Supplemental/Futura.ttc"):
        try: return ImageFont.truetype(p,sz)
        except Exception: continue
    return ImageFont.load_default()

def tracked(text,sz,tracking,sup=3):
    """supersampled mask for anti-aliasing"""
    f=font(sz*sup)
    tmp=Image.new("L",(8,8)); d=ImageDraw.Draw(tmp)
    ws=[d.textlength(ch,font=f) for ch in text]
    total=sum(ws)+tracking*sup*(len(text)-1)
    H=int(sz*sup*1.75)
    img=Image.new("L",(int(total)+60,H),0); dr=ImageDraw.Draw(img)
    x=30
    for ch,w in zip(text,ws):
        dr.text((x,H*0.16),ch,font=f,fill=255); x+=w+tracking*sup
    img=img.resize((img.width//sup,img.height//sup),Image.LANCZOS)
    return np.asarray(img).astype(np.float32)/255.0

def metal(t, u, seed=0):
    """brushed gold: vertical gradient t plus fine horizontal grain u"""
    base=mix(GOLD_HI,GOLD,t*1.6) if t<0.45 else mix(GOLD,GOLD_LO,(t-0.45)/0.55)
    grain=math.sin(u*260.0+seed)*0.5+math.sin(u*71.0+seed*2.3)*0.5
    return mix(base,(255,252,232) if grain>0 else DEEP, abs(grain)*0.10)

def paint_text(text,cx,cy,sz,tracking,bevel=True):
    m=tracked(text,sz,tracking)
    H,W=m.shape
    x0=int(cx-W/2); y0=int(cy-H/2)
    ys,xs=np.nonzero(m>0.02)
    ymin,ymax=ys.min(),ys.max()
    # cast shadow (soft, offset)
    for yy,xx in zip(ys[::2],xs[::2]):
        a=float(m[yy,xx])
        if a>0.35: R(x0+xx+4,y0+yy+6,1,1,(12,9,20))
    # body, per pixel, metal shaded, edge anti-aliased against the ground
    for yy,xx in zip(ys,xs):
        a=float(m[yy,xx])
        t=(yy-ymin)/max(1,(ymax-ymin))
        c=metal(t, (x0+xx)/CW, seed=(yy*0.013))
        if bevel:
            up=float(m[max(0,yy-4),xx]); dn=float(m[min(H-1,yy+4),xx])
            if up<0.5: c=mix(c,(255,253,240),0.60)      # lit top edge
            if dn<0.5: c=mix(c,DEEP,0.55)               # dark bottom edge
            # engraved inner line
            if 0.42<t<0.50 and m[yy,xx]>0.9: c=mix(c,DEEP,0.35)
        if a<0.98:
            c=mix((22,16,34),c,a)                        # blend to ground = smooth edge
        R(x0+xx,y0+yy,1,1,c)

def build():
    ecx,ecy=CW/2, CH*0.395
    # ---- ground: smooth vertical + radial falloff, per 1px row bands, dithered ----
    for y in range(CH):
        t=y/CH
        base=mix((14,10,28),(38,22,50),t)
        R(0,y,CW,1,base)
    # smooth volumetric glow (many low-alpha steps -> no banding)
    for k in range(90):
        r=520*(1-k/90.0)+40
        a=0.016*(k/90.0)**1.4+0.004
        D(ecx,ecy,r,(168,96,42),a)
    for k in range(40):
        r=190*(1-k/40.0)+30
        D(ecx,ecy,r,(228,150,70),0.012)
    # star field with size/brightness variation + a few flares
    for i in range(520):
        x=random.uniform(0,CW); y=random.uniform(0,CH)
        b=random.random()
        D(x,y,0.5+b*1.6,(232,228,250),0.15+b*0.7)
        if b>0.985:
            S(x-6,y,x+6,y,1.0,(255,255,255)); S(x,y-6,x,y+6,1.0,(255,255,255))
    # ---- sunburst: every ray shaded along its length, tapered ----
    NR=96
    for i in range(NR):
        a=i*(2*math.pi/NR)
        kind=i%8
        long_ray = (kind==0); mid_ray=(kind==4)
        r0=126
        r1= 340 if long_ray else (272 if mid_ray else 226)
        w0= 7.0 if long_ray else (4.4 if mid_ray else 2.4)
        steps=44
        for s in range(steps):
            u=s/steps; v=(s+1)/steps
            rr0=r0+(r1-r0)*u; rr1=r0+(r1-r0)*v
            w=w0*(1-u*0.82)
            c=mix(GOLD_HI,GOLD_LO, u*1.15)
            S(ecx+math.cos(a)*rr0, ecy+math.sin(a)*rr0, ecx+math.cos(a)*rr1, ecy+math.sin(a)*rr1, max(0.7,w), c)
        # specular sparkle at the base of long rays
        if long_ray: D(ecx+math.cos(a)*r0, ecy+math.sin(a)*r0, 3.2,(255,252,235),0.9)
    # ---- rings with metal shading + filigree ----
    def ring(rad,w,step=1.0,hi=0.0):
        n=int(2*math.pi*rad/step)
        for i in range(n):
            a=i*(2*math.pi/n)
            lit=0.5+0.5*math.cos(a+2.2)      # light from upper-left
            c=mix(GOLD_LO,GOLD_HI,lit*0.9+hi)
            D(ecx+math.cos(a)*rad, ecy+math.sin(a)*rad, w, c, 1.0)
    ring(120,3.4,0.8,0.05); ring(112,1.5,0.9); ring(158,1.6,0.9); ring(163,0.9,1.0)
    # beaded outer ring
    for i in range(60):
        a=i*(2*math.pi/60)
        lit=0.5+0.5*math.cos(a+2.2)
        D(ecx+math.cos(a)*158, ecy+math.sin(a)*158, 3.6, mix(GOLD_LO,GOLD_HI,lit), 1.0)
        D(ecx+math.cos(a)*158-0.8, ecy+math.sin(a)*158-0.8, 1.5, (255,250,228), 0.8*lit)
    # filigree scrollwork between rings
    for i in range(24):
        a=i*(2*math.pi/24)+math.pi/24
        for s in range(26):
            u=s/26
            rr=124+ (34*u)
            sway=math.sin(u*math.pi*2)*0.085
            aa=a+sway
            lit=0.5+0.5*math.cos(aa+2.2)
            D(ecx+math.cos(aa)*rr, ecy+math.sin(aa)*rr, 1.5*(1-u*0.5), mix(GOLD_LO,GOLD_HI,lit*0.95), 0.95)
    # arrowheads on the outer band
    for i in range(12):
        a=i*(2*math.pi/12)+math.pi/12
        px,py=ecx+math.cos(a)*186, ecy+math.sin(a)*186
        ux,uy=math.cos(a),math.sin(a); vx,vy=-uy,ux
        for k in range(22):
            t=k/22; w=15*(1-t)
            lit=0.5+0.5*math.cos(a+2.2)
            c=mix(GOLD_LO,GOLD_HI,(1-t)*lit+0.15)
            S(px+ux*t*30-vx*w/2, py+uy*t*30-vy*w/2, px+ux*t*30+vx*w/2, py+uy*t*30+vy*w/2, 1.8, c)
    # ---- sacred triangle, beveled ----
    for k in range(3):
        a1=-math.pi/2+k*2*math.pi/3; a2=-math.pi/2+(k+1)*2*math.pi/3
        x1,y1=ecx+math.cos(a1)*84, ecy+math.sin(a1)*84
        x2,y2=ecx+math.cos(a2)*84, ecy+math.sin(a2)*84
        for s in range(60):
            u=s/60; v=(s+1)/60
            lit=0.5+0.5*math.cos(math.atan2((y1+(y2-y1)*u)-ecy,(x1+(x2-x1)*u)-ecx)+2.2)
            S(x1+(x2-x1)*u, y1+(y2-y1)*u, x1+(x2-x1)*v, y1+(y2-y1)*v, 4.0, mix(GOLD_LO,GOLD_HI,lit))
            S(x1+(x2-x1)*u-1, y1+(y2-y1)*u-1.6, x1+(x2-x1)*v-1, y1+(y2-y1)*v-1.6, 1.2, (255,252,236))
    # glowing core with smooth falloff
    for r in range(52,0,-1):
        t=r/52
        D(ecx,ecy,r, mix((255,253,240),(246,206,126), t), 0.10 if t>0.55 else 0.22)
    D(ecx,ecy,10,(255,255,250),1.0)
    # ---- wordmark + rule + tagline ----
    paint_text("DIVINE TRIBE", CW/2, CH*0.775, 112, 18)
    ry=CH*0.876
    for side in (-1,1):
        for s in range(120):
            u=s/120
            x=CW/2+side*(74+ (272*u))
            c=mix(GOLD_HI,GOLD_LO,u)
            S(x,ry,x+side*3,ry,2.0,c)
        D(CW/2+side*352, ry, 3.4, GOLD_HI)
        D(CW/2+side*352, ry, 1.4, (255,255,246))
    for k in range(26):
        t=k/25; w=18*(1-abs(t-0.5)*2)
        S(CW/2-w, ry-18+t*36, CW/2+w, ry-18+t*36, 1.6, mix(GOLD_HI,GOLD_LO,abs(t-0.5)*1.6))
    paint_text("HANDCRAFTED  ·  HUMBOLDT", CW/2, CH*0.945, 32, 14, bevel=False)
    # fine print grain over everything
    for i in range(2600):
        x=random.uniform(0,CW); y=random.uniform(0,CH)
        D(x,y,0.6,(255,255,255) if random.random()<0.5 else (0,0,0),0.025)

async def main():
    t_build=time.time(); build()
    print(f"{len(ops)} ops (built in {time.time()-t_build:.1f}s)",flush=True)
    if VISIBLE:
        from engine import launch_brave
        import urllib.request
        try: urllib.request.urlopen("http://localhost:9231/json/version",timeout=1); up=True
        except Exception: up=False
        if not up: launch_brave(9231,size=(1660,1050)); await asyncio.sleep(2.0)
        br=Browser(9231); await br.connect(); tab=await br.existing_page("replay") or await br.new_tab("replay")
    else:
        br=Browser(9222); await br.connect(); tab=await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r="+str(int(time.time())))
    await tab.measure_canvas(); t0=time.time(); await tab.resize_canvas(CW,CH)
    for i in range(0,len(ops),9000):
        tab.fast(ops[i:i+9000])
        if i%45000==0: await tab.sync()
    tab.fast_commit(); await tab.sync()
    dt=time.time()-t0
    print(f"DONE {len(ops)} ops in {dt:.2f}s = {len(ops)/dt:,.0f} ops/s",flush=True)
    await tab.png("logo_hd.png")
    if not VISIBLE: await tab.close()
    await br.close()
asyncio.run(main())
