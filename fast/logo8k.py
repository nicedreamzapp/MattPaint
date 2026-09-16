"""Divine Tribe crest — designed in a 1600x900 space, scaled to any resolution (8K default).
Vector ornament as strokes/dabs (resolution-independent), lettering run-length encoded.
"""
import asyncio, sys, time, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from engine import Browser
random.seed(11)

CW=int(sys.argv[1]) if len(sys.argv)>1 else 7680
CH=int(sys.argv[2]) if len(sys.argv)>2 else 4320
VISIBLE = "--hidden" not in sys.argv   # on-screen by DEFAULT; hiding must be explicit
RECORD="--record" in sys.argv
DW,DH=1600.0,900.0                      # design space
S=CW/DW                                  # scale factor

GOLD_HI=(255,238,183); GOLD=(224,178,80); GOLD_LO=(138,92,26); DEEP=(70,48,12)
JADE_HI=(46,120,104); JADE=(16,62,58); JADE_LO=(7,28,30)
def mix(a,b,t):
    t=max(0.0,min(1.0,t)); return tuple(int(round(a[i]+(b[i]-a[i])*t)) for i in range(3))

ops=[]
def R(x,y,w,h,c): ops.append([0,int(x),int(y),int(max(1,w)),int(max(1,h)),int(c[0]),int(c[1]),int(c[2])])
def L(x1,y1,x2,y2,w,c): ops.append([1,round(x1*S,1),round(y1*S,1),round(x2*S,1),round(y2*S,1),max(0.8,w*S),int(c[0]),int(c[1]),int(c[2])])
def Dot(x,y,r,c,a=1.0): ops.append([2,round(x*S,1),round(y*S,1),int(c[0]),int(c[1]),int(c[2]),max(0.6,round(r*S,1)),round(a,3)])
def Rd(x,y,w,h,c): R(x*S,y*S,w*S,h*S,c)          # design-space rect

def font(px):
    for p in ("/System/Library/Fonts/Supplemental/Copperplate.ttc",
              "/System/Library/Fonts/Supplemental/Futura.ttc"):
        try: return ImageFont.truetype(p,int(px))
        except Exception: continue
    return ImageFont.load_default()

def text_ops(text, cx_d, cy_d, size_d, tracking_d, top_c, bot_c, bevel=True):
    """render the wordmark at full output resolution, emit as run-length rects"""
    sz=int(size_d*S); tr=tracking_d*S
    f=font(sz)
    tmp=Image.new("L",(8,8)); d=ImageDraw.Draw(tmp)
    ws=[d.textlength(ch,font=f) for ch in text]
    total=sum(ws)+tr*(len(text)-1)
    H=int(sz*1.72)
    img=Image.new("L",(int(total)+int(40*S),H),0); dr=ImageDraw.Draw(img)
    x=20*S
    for ch,w in zip(text,ws):
        dr.text((x,H*0.16),ch,font=f,fill=255); x+=w+tr
    m=np.asarray(img)
    W=img.width
    x0=int(cx_d*S-W/2); y0=int(cy_d*S-H/2)
    ysnz,_=np.nonzero(m>60)
    if len(ysnz)==0: return
    ymin,ymax=ysnz.min(),ysnz.max()
    # shadow
    for y in range(0,H,2):
        row=m[y]>120
        if not row.any(): continue
        idx=np.nonzero(row)[0]
        st=idx[0]; prev=idx[0]
        for xx in idx[1:]:
            if xx-prev>1:
                R(x0+st+int(5*S), y0+y+int(7*S), prev-st+1, 2, (10,22,20)); st=xx
            prev=xx
        R(x0+st+int(5*S), y0+y+int(7*S), prev-st+1, 2, (10,22,20))
    # body: run-length per row, colour quantised so runs stay long
    for y in range(H):
        row=m[y]
        idx=np.nonzero(row>60)[0]
        if len(idx)==0: continue
        t=(y-ymin)/max(1,(ymax-ymin))
        base=mix(top_c,bot_c,t)
        up = m[max(0,y-int(5*S))]; dn = m[min(H-1,y+int(5*S))]
        st=idx[0]; prev=idx[0]; cur=None
        def col_at(xx):
            c=base
            if bevel:
                if up[xx]<60: c=mix(c,(255,253,238),0.62)
                elif dn[xx]<60: c=mix(c,DEEP,0.55)
            a=row[xx]/255.0
            return mix((9,26,26),c,a) if a<0.95 else c
        cur=col_at(idx[0])
        for xx in idx[1:]:
            c=col_at(xx)
            if xx-prev>1 or c!=cur:
                R(x0+st,y0+y,prev-st+1,1,cur); st=xx; cur=c
            prev=xx
        R(x0+st,y0+y,prev-st+1,1,cur)

def build():
    ecx,ecy=DW/2, DH*0.415
    # ---- ground: jade gradient + vignette ----
    rows=int(CH)
    for y in range(0,rows,3):
        t=y/rows
        R(0,y,CW,4, mix(mix(JADE_LO,JADE,0.55), mix(JADE,(4,18,20),0.8), t))
    for k in range(70):
        r=DW*0.62*(1-k/70.0)+40
        Dot(ecx,ecy,r,(40,150,124),0.010)
    # corner vignette
    for k in range(90):
        a=0.006
        Dot(-40+ (k*2), -40+(k*1.2), 520-k*4, (0,0,0), a)
        Dot(DW+40-(k*2), DH+40-(k*1.2), 520-k*4, (0,0,0), a)
    # fine grain
    for i in range(9000):
        Dot(random.uniform(0,DW),random.uniform(0,DH),0.7,(255,255,255) if random.random()<0.5 else (0,0,0),0.018)

    # ---- outer tribal border ----
    M=46
    for side in range(4):
        pass
    def border_run(x0,y0,x1,y1,n):
        for i in range(n):
            u=i/n; v=(i+0.5)/n
            x=x0+(x1-x0)*u; y=y0+(y1-y0)*u
            xm=x0+(x1-x0)*v; ym=y0+(y1-y0)*v
            c=mix(GOLD_LO,GOLD_HI, 0.5+0.5*math.sin(i*0.5))
            L(x,y,xm,ym,2.0,c)
    for (x0,y0,x1,y1) in [(M,M,DW-M,M),(DW-M,M,DW-M,DH-M),(DW-M,DH-M,M,DH-M),(M,DH-M,M,M)]:
        L(x0,y0,x1,y1,2.6,mix(GOLD,GOLD_LO,0.35))
        L(x0+ (6 if x0<x1 else -6 if x0>x1 else 0), y0, x1, y1, 0.0+1.2, mix(GOLD_HI,GOLD,0.5))
    # chevron pattern inside the border
    for i in range(78):
        u=i/78
        for (ax,ay,bx,by,nx,ny) in [(M,M,DW-M,M,0,1),(M,DH-M,DW-M,DH-M,0,-1)]:
            x=ax+(bx-ax)*u; y=ay
            s=8
            L(x-s,y+ny*4, x, y+ny*13, 1.6, mix(GOLD,GOLD_LO,0.3))
            L(x, y+ny*13, x+s, y+ny*4, 1.6, mix(GOLD,GOLD_LO,0.3))
    for i in range(44):
        u=i/44
        for (ax,ay,by,nx) in [(M,M,DH-M,1),(DW-M,M,DH-M,-1)]:
            y=ay+(by-ay)*u; x=ax
            s=8
            L(x+nx*4,y-s, x+nx*13, y, 1.6, mix(GOLD,GOLD_LO,0.3))
            L(x+nx*13, y, x+nx*4, y+s, 1.6, mix(GOLD,GOLD_LO,0.3))
    # corner diamonds
    for (cx,cy) in [(M,M),(DW-M,M),(M,DH-M),(DW-M,DH-M)]:
        for k in range(16):
            t=k/15; w=14*(1-abs(t-0.5)*2)
            L(cx-w,cy-14+t*28,cx+w,cy-14+t*28,1.4,mix(GOLD_HI,GOLD_LO,abs(t-0.5)*1.8))

    # ---- crest: outer ring, beading, filigree ----
    RAD=196
    def ring(rad,w,step=0.7,lo=GOLD_LO,hi=GOLD_HI,phase=2.2):
        n=int(2*math.pi*rad/step)
        for i in range(n):
            a=i*(2*math.pi/n)
            lit=0.5+0.5*math.cos(a+phase)
            Dot(ecx+math.cos(a)*rad, ecy+math.sin(a)*rad, w, mix(lo,hi,lit))
    ring(RAD,3.0); ring(RAD-9,1.3); ring(RAD-15,0.9); ring(RAD+11,1.1)
    for i in range(72):
        a=i*(2*math.pi/72); lit=0.5+0.5*math.cos(a+2.2)
        Dot(ecx+math.cos(a)*(RAD+11), ecy+math.sin(a)*(RAD+11), 3.0, mix(GOLD_LO,GOLD_HI,lit))
        Dot(ecx+math.cos(a)*(RAD+11)-0.7, ecy+math.sin(a)*(RAD+11)-0.7, 1.2, (255,250,226),0.85*lit)
    # filigree scrolls between rings
    for i in range(36):
        a0=i*(2*math.pi/36)+math.pi/36
        for s in range(30):
            u=s/30
            rr=RAD-15-(0)+ (11*math.sin(u*math.pi))
            aa=a0+ (u-0.5)*(2*math.pi/36)*0.92
            lit=0.5+0.5*math.cos(aa+2.2)
            Dot(ecx+math.cos(aa)*rr, ecy+math.sin(aa)*rr, 1.2, mix(GOLD_LO,GOLD_HI,lit*0.95))
    # ---- inner scene: sky disc, sun, mountains ----
    for r in range(int(RAD-18),0,-1):
        t=r/(RAD-18)
        Dot(ecx,ecy, r, mix((250,206,128),(26,74,78), t*1.05), 0.16 if r> (RAD-24) else 0.5)
    sun_y=ecy+18
    for k in range(60):
        r=96*(1-k/60.0)+8
        Dot(ecx,sun_y,r,(255,236,176),0.035)
    Dot(ecx,sun_y,44,(255,248,214),1.0)
    for i in range(64):
        a=i*(2*math.pi/64)
        r0,r1=(50,(118 if i%4==0 else 86))
        L(ecx+math.cos(a)*r0, sun_y+math.sin(a)*r0, ecx+math.cos(a)*r1, sun_y+math.sin(a)*r1,
          2.4 if i%4==0 else 1.1, mix(GOLD_HI,GOLD,0.4))
    # mountains (clipped to the disc)
    def mtn(peaks, base_y, col_top, col_bot, seed):
        rnd=random.Random(seed)
        for x in range(int(ecx-RAD+20), int(ecx+RAD-20)):
            dx=x-ecx
            lim=math.sqrt(max(0.0,(RAD-20)**2-dx*dx))
            ytop=base_y
            for (px,py,sl,sr) in peaks:
                yy=py+((px-x)*sl if x<px else (x-px)*sr)
                ytop=min(ytop,yy)
            ytop+= math.sin(x*0.4+seed)*1.2
            y0=max(ecy-lim,ytop); y1=min(ecy+lim, base_y)
            if y1<=y0: continue
            n=int((y1-y0)/2)+1
            for k in range(n):
                t=k/max(1,n-1)
                Rd(x, y0+ (y1-y0)*t, 1.2, 2.4, mix(col_top,col_bot,t))
    mtn([(ecx-96,ecy-42,0.62,0.5),(ecx-18,ecy-86,0.55,0.52),(ecx+78,ecy-50,0.5,0.6)],
        ecy+92, (86,120,120),(16,44,50), 3)
    mtn([(ecx-140,ecy+4,0.7,0.6),(ecx-40,ecy-24,0.6,0.6),(ecx+70,ecy+6,0.6,0.68),(ecx+152,ecy-10,0.6,0.7)],
        ecy+96, (34,70,70),(8,26,32), 9)
    # snow caps
    for (px,py) in [(ecx-18,ecy-86),(ecx-96,ecy-42),(ecx+78,ecy-50)]:
        for k in range(16):
            w=13*(1-k/16.0)
            Rd(px-w, py+k*1.6, w*2, 1.8, mix((235,244,246),(150,180,190),k/16.0))
    # ---- third eye above the peaks ----
    eyx,eyy=ecx, ecy-118
    for k in range(26):
        Dot(eyx,eyy, 30-k*0.9, mix((255,246,214),(250,206,128), k/26.0), 0.12)
    for s in range(42):
        u=s/42; ang=-math.pi*u
        Dot(eyx+math.cos(ang)*26, eyy+math.sin(ang)*13, 1.6, GOLD_HI)
        Dot(eyx+math.cos(ang)*26, eyy-math.sin(ang)*13, 1.6, GOLD_HI)
    Dot(eyx,eyy,9,(18,44,46)); Dot(eyx,eyy,5.5,(6,18,20)); Dot(eyx-1.8,eyy-2.2,1.8,(255,252,238))
    for i in range(14):
        a=-math.pi/2 + (i-6.5)*0.17
        L(eyx+math.cos(a)*30, eyy+math.sin(a)*18, eyx+math.cos(a)*44, eyy+math.sin(a)*30, 1.4, mix(GOLD,GOLD_HI,0.5))
    # vapour curls rising from the disc
    for j in range(5):
        bx=ecx-70+j*35; by=ecy-RAD+6
        for s in range(46):
            u=s/46
            x=bx+math.sin(u*6.0+j)*14*(0.4+u)
            y=by-u*84
            Dot(x,y,2.4*(1-u*0.7), mix((190,226,220),(60,110,110),u), 0.30*(1-u))

    # ---- banner ribbon + wordmark ----
    by=DH*0.735
    Rd(ecx-430, by-42, 860, 84, mix(JADE_HI,JADE,0.55))
    for e in (-1,1):
        L(ecx+e*430, by-42, ecx+e*470, by-16, 2.4, GOLD)
        L(ecx+e*470, by-16, ecx+e*470, by+16, 2.4, GOLD)
        L(ecx+e*470, by+16, ecx+e*430, by+42, 2.4, GOLD)
        L(ecx+e*430, by-42, ecx+e*430, by+42, 1.6, mix(GOLD,GOLD_LO,0.5))
    L(ecx-430,by-42,ecx+430,by-42,2.6,GOLD_HI)
    L(ecx-430,by+42,ecx+430,by+42,2.6,mix(GOLD,GOLD_LO,0.4))
    text_ops("DIVINE TRIBE", ecx, by, 56, 11, GOLD_HI, mix(GOLD_LO,DEEP,0.35))
    # rule + tagline
    ry=DH*0.845
    for e in (-1,1):
        L(ecx+e*60, ry, ecx+e*250, ry, 1.8, mix(GOLD,GOLD_LO,0.4))
        Dot(ecx+e*262, ry, 2.6, GOLD_HI)
    for k in range(14):
        t=k/13; w=11*(1-abs(t-0.5)*2)
        L(ecx-w, ry-11+t*22, ecx+w, ry-11+t*22, 1.3, GOLD_HI)
    text_ops("HANDCRAFTED IN HUMBOLDT", ecx, DH*0.905, 19, 9, mix(GOLD,(226,200,150),0.4), GOLD_LO, bevel=False)

async def main():
    t0=time.time(); build()
    print(f"{len(ops)} ops built in {time.time()-t0:.1f}s for {CW}x{CH}",flush=True)
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
    await tab.measure_canvas()
    await tab.resize_canvas(CW,CH)
    ok=await tab.eval("(()=>{const c=document.getElementById('main-canvas');return c.width+'x'+c.height;})()")
    print("canvas:",ok,flush=True)
    t1=time.time()
    CHUNK= max(1,len(ops)//150) if RECORD else 9000
    for i in range(0,len(ops),CHUNK):
        tab.fast(ops[i:i+CHUNK])
        if RECORD:
            await tab.sync(); await asyncio.sleep(0.06)
        elif i % (CHUNK*6)==0:
            await tab.sync()
    await tab.sync()
    dt=time.time()-t1
    print(f"DONE {len(ops)} ops in {dt:.2f}s = {len(ops)/dt:,.0f} ops/s",flush=True)
    try: await tab.png("logo8k.png")
    except Exception as e: print("png skipped:",str(e)[:80])
    if not VISIBLE: await tab.close()
    await br.close()
asyncio.run(main())
