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
    ecx,ecy=DW/2, DH*0.42
    # ---- ground: deep dark, warm bloom behind the crucible ----
    rows=int(CH)
    for y in range(0,rows,3):
        t=y/rows
        R(0,y,CW,4, mix((16,15,17),(27,24,26), t))
    for k in range(90):
        r=DW*0.30*(1-k/90.0)+24
        Dot(ecx,ecy+18,r,(188,92,30),0.009)
    for i in range(9000):
        Dot(random.uniform(0,DW),random.uniform(0,DH),0.7,(255,255,255) if random.random()<0.5 else (0,0,0),0.015)

    # ================= THE CRUCIBLE =================
    RX, RY   = 156.0, 54.0        # rim ellipse
    BX, BY   = 116.0, 40.0        # base ellipse
    DEPTH    = 128.0              # rim -> base
    WALL     = 15.0               # wall thickness at the rim
    rim_y    = ecy - 26
    base_y   = rim_y + DEPTH

    CER_LIT=(242,238,232); CER=(198,192,188); CER_DK=(86,82,82); CER_WARM=(232,150,78)
    HOT_CORE=(255,253,246); HOT_1=(255,226,150); HOT_2=(255,158,52); HOT_3=(206,58,14)

    # --- radiance thrown up out of the cup ---
    for k in range(70):
        r=170*(1-k/70.0)+16
        Dot(ecx, rim_y-8, r, mix(HOT_CORE,HOT_2,k/70.0), 0.018)

    # --- inner cavity: back wall dark, floor glowing ---
    IRX,IRY = RX-WALL, RY-WALL*0.36
    yy=-IRY
    while yy<=IRY:
        w=IRX*math.sqrt(max(0.0,1-(yy/IRY)**2))
        t=(yy+IRY)/(2*IRY)                      # 0 = far rim (back), 1 = near rim (front)
        # back of the cavity is shadowed wall; toward the front we look down onto the glowing floor
        c = mix(mix(CER_DK,(44,24,20),0.55), HOT_2, max(0.0,(t-0.18)/0.82)**1.5)
        Rd(ecx-w, rim_y+yy, 2*w, 2.4, c)
        yy+=2
    # molten pool on the floor
    for k in range(46):
        u=k/46
        prx=IRX*0.62*(1-u*0.75); pry=IRY*0.62*(1-u*0.75)
        c=mix(HOT_2,HOT_CORE,u)
        y2=-pry
        while y2<=pry:
            w=prx*math.sqrt(max(0.0,1-(y2/pry)**2))
            Rd(ecx-w, rim_y+IRY*0.34+y2, 2*w, 2.0, c)
            y2+=2
    for k in range(26):
        Dot(ecx, rim_y+IRY*0.34, 40-k*1.4, mix(HOT_CORE,HOT_1,k/26.0), 0.14)

    # --- outer body: true frustum (rim ellipse -> slanted sides -> base ellipse) ---
    x=-RX
    while x<=RX:
        u=x/RX
        top = rim_y + RY*math.sqrt(max(0.0,1-u*u))
        if abs(x)<=BX:
            bot = base_y + BY*math.sqrt(max(0.0,1-(x/BX)**2))
        else:
            bot = rim_y + (base_y-rim_y)*((RX-abs(x))/max(1e-6,(RX-BX)))
        if bot<=top: x+=0.9; continue
        lit = 0.5+0.5*math.cos(u*1.45 + 2.5)
        n=int((bot-top)/2.0)+1
        for k in range(n):
            v=k/max(1,n-1)
            base_c = mix(mix(CER_DK,CER,lit), CER_LIT, max(0.0,lit-0.55)*1.7)
            c = mix(base_c, CER_WARM, (v**2.3)*0.5)
            Rd(x+ecx, top+(bot-top)*v, 2.2, 2.3, c)
        x+=0.9
    # base contact glow
    for k in range(22):
        Dot(ecx, base_y+BY*0.6, 90-k*3.2, (196,86,30), 0.03)

    # --- the rim itself: a ceramic ring with a bright specular ---
    n=int(2*math.pi*RX/0.5)
    for i in range(n):
        a=i*(2*math.pi/n)
        lit=0.5+0.5*math.cos(a+2.5)
        px=ecx+math.cos(a)*((RX+IRX)/2); py=rim_y+math.sin(a)*((RY+IRY)/2)
        c=mix(mix(CER_DK,CER,lit),CER_LIT,max(0.0,lit-0.6)*2.2)
        Dot(px,py, WALL*0.5, c)
        if lit>0.80: Dot(px-0.8,py-1.0, WALL*0.20, (255,255,252), 0.9)
        # warm bounce on the inner lip
        Dot(ecx+math.cos(a)*IRX, rim_y+math.sin(a)*IRY, 2.0, mix(c,HOT_2,0.45), 0.85)

    # --- vapour rising ---
    for j in range(16):
        bx=ecx-110+j*14.5; by=rim_y-14
        amp=7+random.uniform(0,18); ph=random.uniform(0,6.28); drift=random.uniform(-0.5,0.5)
        for s2 in range(96):
            u=s2/96
            xv=bx+math.sin(u*4.2+ph)*amp*(0.25+u*1.5)+drift*u*60
            yv=by-u*250
            c=mix((240,214,186),(132,158,170),u)
            for o in range(2):
                Dot(xv+o*2.0,yv, 5.0*(1-u*0.5), c, 0.075*(1-u)*(0.45+0.55*math.sin(u*7+ph)))

    # ---- restrained tribal ring around it ----
    RR=250
    def ring(rad,w,step=0.7,lo=(92,58,22),hi=(240,196,120),phase=2.4):
        m=int(2*math.pi*rad/step)
        for i in range(m):
            a=i*(2*math.pi/m); lit=0.5+0.5*math.cos(a+phase)
            Dot(ecx+math.cos(a)*rad, ecy+math.sin(a)*rad, w, mix(lo,hi,lit))
    ring(RR,1.5); ring(RR+7,0.85)
    for i in range(36):
        a=i*(2*math.pi/36); lit=0.5+0.5*math.cos(a+2.4)
        c=mix((92,58,22),(240,196,120),lit)
        x0=ecx+math.cos(a)*(RR+7); y0=ecy+math.sin(a)*(RR+7)
        ln=19 if i%3==0 else 12
        x1=ecx+math.cos(a)*(RR+ln); y1=ecy+math.sin(a)*(RR+ln)
        L(x0,y0,x1,y1, 2.1 if i%3==0 else 1.2, c)

    # ---- wordmark ----
    text_ops("DIVINE TRIBE", ecx, DH*0.788, 60, 12, (255,238,196), (150,86,26))
    ry=DH*0.868
    for e in (-1,1):
        L(ecx+e*66, ry, ecx+e*258, ry, 1.6, (168,110,40))
        Dot(ecx+e*270, ry, 2.4, (250,214,150))
    for k in range(14):
        t=k/13; w=10*(1-abs(t-0.5)*2)
        L(ecx-w, ry-10+t*20, ecx+w, ry-10+t*20, 1.2, (250,214,150))
    text_ops("HUMBOLDT COUNTY, CALIFORNIA", ecx, DH*0.925, 18, 9, (226,186,132), (132,86,34), bevel=False)

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
