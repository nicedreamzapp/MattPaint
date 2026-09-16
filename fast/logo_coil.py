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
    ecx,ecy=DW/2, DH*0.435
    # ---- ground: near-black, warm ember bloom behind the coil ----
    rows=int(CH)
    for y in range(0,rows,3):
        t=y/rows
        R(0,y,CW,4, mix((14,11,12),(26,17,14), t))
    for k in range(110):
        r=DW*0.52*(1-k/110.0)+30
        Dot(ecx,ecy,r,(190,72,18),0.009)
    for k in range(60):
        r=200*(1-k/60.0)+20
        Dot(ecx,ecy,r,(255,150,50),0.012)
    for i in range(9000):
        Dot(random.uniform(0,DW),random.uniform(0,DH),0.7,(255,255,255) if random.random()<0.5 else (0,0,0),0.016)

    # ---- THE COIL: flat archimedean spiral, white-hot core -> deep red outer ----
    TURNS=5.6; R_IN=26.0; R_OUT=178.0
    steps=int(TURNS*2*math.pi/0.012)
    prev=None
    # heat bloom first, so the wire sits on top of its own glow
    for k in range(steps//40):
        th=(k/(steps//40))*TURNS*2*math.pi
        rr=R_IN+(R_OUT-R_IN)*(th/(TURNS*2*math.pi))
        t=rr/R_OUT
        glow=mix((255,246,224),(196,44,8), t)
        Dot(ecx+math.cos(th)*rr, ecy+math.sin(th)*rr, 14*(1-t*0.45), glow, 0.05)
    for k in range(steps):
        th=(k/steps)*TURNS*2*math.pi
        rr=R_IN+(R_OUT-R_IN)*(th/(TURNS*2*math.pi))
        x=ecx+math.cos(th)*rr; y=ecy+math.sin(th)*rr
        if prev:
            t=rr/R_OUT                                  # 0 centre .. 1 outer
            # heat ramp: white -> yellow -> orange -> red -> dark cherry
            if t<0.22:   c=mix((255,253,244),(255,232,150), t/0.22)
            elif t<0.45: c=mix((255,232,150),(255,166,48), (t-0.22)/0.23)
            elif t<0.72: c=mix((255,166,48),(214,64,14), (t-0.45)/0.27)
            else:        c=mix((214,64,14),(120,22,10), (t-0.72)/0.28)
            w=5.4*(1-t*0.30)
            L(prev[0],prev[1],x,y,w,c)
            # specular highlight along the top-left of the wire
            lit=0.5+0.5*math.cos(th+2.3)
            if lit>0.45:
                L(prev[0]-0.9,prev[1]-1.1,x-0.9,y-1.1, w*0.34, mix(c,(255,255,245),0.55*lit))
            # dark underside so the wire reads round
            L(prev[0]+0.8,prev[1]+1.2,x+0.8,y+1.2, w*0.26, mix(c,(40,8,4),0.45))
        prev=(x,y)
    # incandescent core
    for r in range(30,0,-1):
        Dot(ecx,ecy,r, mix((255,255,252),(255,214,140), r/30.0), 0.22)

    # ---- vapour rising off the coil ----
    for j in range(9):
        bx=ecx-150+j*38; by=ecy-R_OUT*0.55
        amp=10+random.uniform(0,16); ph=random.uniform(0,6.28)
        for s in range(70):
            u=s/70
            x=bx+math.sin(u*5.2+ph)*amp*(0.35+u*1.25)
            y=by-u*230
            c=mix((230,206,180),(120,150,160),u)
            Dot(x,y, 3.4*(1-u*0.55), c, 0.20*(1-u)*(0.5+0.5*math.sin(u*9+ph)))

    # ---- restrained tribal ring: notches + a thin double rule ----
    RR=222
    def ring(rad,w,step=0.7,lo=(92,58,22),hi=(240,196,120),phase=2.3):
        n=int(2*math.pi*rad/step)
        for i in range(n):
            a=i*(2*math.pi/n); lit=0.5+0.5*math.cos(a+phase)
            Dot(ecx+math.cos(a)*rad, ecy+math.sin(a)*rad, w, mix(lo,hi,lit))
    ring(RR,1.6); ring(RR+7,0.9)
    for i in range(36):
        a=i*(2*math.pi/36); lit=0.5+0.5*math.cos(a+2.3)
        c=mix((92,58,22),(240,196,120),lit)
        x0=ecx+math.cos(a)*(RR+7); y0=ecy+math.sin(a)*(RR+7)
        x1=ecx+math.cos(a)*(RR+ (19 if i%3==0 else 13)); y1=ecy+math.sin(a)*(RR+(19 if i%3==0 else 13))
        L(x0,y0,x1,y1, 2.2 if i%3==0 else 1.3, c)

    # ---- wordmark ----
    text_ops("DIVINE TRIBE", ecx, DH*0.775, 60, 12, (255,238,196), (150,86,26))
    ry=DH*0.858
    for e in (-1,1):
        L(ecx+e*66, ry, ecx+e*258, ry, 1.6, (168,110,40))
        Dot(ecx+e*270, ry, 2.4, (250,214,150))
    for k in range(14):
        t=k/13; w=10*(1-abs(t-0.5)*2)
        L(ecx-w, ry-10+t*20, ecx+w, ry-10+t*20, 1.2, (250,214,150))
    text_ops("HUMBOLDT COUNTY, CALIFORNIA", ecx, DH*0.915, 18, 9, (226,186,132), (132,86,34), bevel=False)

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
