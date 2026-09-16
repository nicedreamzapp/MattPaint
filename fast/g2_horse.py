"""2ND GEN — MORNING FIELD. Rebuilt on: believable light, physical contact, 3 depth levels,
material response, subtle imperfection. Horse built from rib cage/pelvis/spine, not a blob."""
import asyncio, math, random
import art as A
from art import Art, mix, paint, TOPBAR, silhouette_rim
A.GEN="2ND GEN"
random.seed(8)
W,H=1380,880
a=Art(W,H,"MORNING FIELD")
R,L,D=a.R,a.L,a.D
HOR=H*0.70
SX,SY=W*0.21, HOR-176          # low sun, behind-left

def build():
    # ---------- sky: value first ----------
    keys=[(0.0,(74,104,146)),(0.34,(150,166,186)),(0.62,(222,200,178)),(0.86,(250,222,180)),(1.0,(255,240,212))]
    def sky(t):
        for (p,ca),(q,cb) in zip(keys,keys[1:]):
            if p<=t<=q: return mix(ca,cb,(t-p)/(q-p))
        return keys[-1][1]
    for y in range(TOPBAR,int(HOR),2):
        R(0,y,W,3, sky((y-TOPBAR)/(HOR-TOPBAR)))
    # sun: tight core, falloff to zero (learned)
    for k in range(90):
        u=k/90.0
        D(SX,SY, 185*(1-u)+7, mix(sky((SY-TOPBAR)/(HOR-TOPBAR)),(255,250,238),0.22+0.72*(u**2)), 0.050*((u**2)**1.25))
    D(SX,SY,14,(255,254,248),1.0)
    # clouds catching the low light on their undersides
    for j in range(10):
        cy=TOPBAR+random.uniform(6,(HOR-TOPBAR)*0.62); cx=random.uniform(-120,W+120)
        wd=random.uniform(240,660); ht=random.uniform(10,28)
        for k in range(260):
            u=random.random(); env=math.sin(max(0,min(1,u))*math.pi)**1.35
            px=cx-wd/2+wd*u+random.uniform(-12,12)
            py=cy+math.sin(u*4+j)*ht*0.4+random.gauss(0,ht*0.42)
            under=max(0.0,(py-cy)/ (ht*1.2))
            base=mix((214,206,206),(255,226,186), 1-under)
            D(px,py, ht*env*random.uniform(0.25,0.95), base, 0.026)

    # ---------- RULE 3: three ground planes ----------
    # far: hedgerow + trees, bleached into the haze
    for i in range(150):
        x=random.uniform(-40,W+40); h=random.uniform(16,74)
        for k in range(int(h*1.5)):
            ang=random.uniform(0,6.2832); rr=random.random()**0.6
            D(x+math.cos(ang)*h*0.44*rr, HOR-6-h*0.55+math.sin(ang)*h*0.34*rr,
              random.uniform(2.0,5.0), mix((168,176,168),(214,214,200), random.random()*0.6), 0.45)
    for i in range(26):
        D(random.uniform(0,W), HOR-random.uniform(0,40), random.uniform(60,150), (226,224,212), 0.030)
    # field
    for y in range(int(HOR),H,2):
        t=max(0.0,(y-HOR)/(H-HOR))
        R(0,y,W,3, mix((168,166,120),(56,60,38), t**0.85))
    # mid + foreground grass: gets larger and sharper toward the camera
    for i in range(5200):
        x=random.uniform(-20,W+20); y=random.uniform(HOR,H)
        t=max(0.0,(y-HOR)/(H-HOR))
        ln=4+22*t; w=0.5+1.1*t
        c=mix((214,204,142),(46,52,32), t*1.05)
        if random.random()<0.35: c=mix(c,(255,238,190), (1-t)*0.5)     # backlit tips
        L(x,y, x+random.uniform(-3,3)*(1+t), y-ln*random.uniform(0.6,1.3), w, c)

    # ---------- the horse: skeleton first ----------
    GND=HOR+118
    hx=W*0.60
    DARK=(18,17,16); MID=(30,29,27); RIM=(255,232,186)
    parts=[]
    def blob(cx,cy,rx,ry,col):
        yy=-ry
        while yy<=ry:
            w=rx*math.sqrt(max(0.0,1-(yy/ry)**2))
            R(cx-w, cy+yy, 2*w, 2.4, col); yy+=2
    def part(cx,cy,rx,ry,col=None):
        blob(cx,cy,rx,ry, col or DARK); parts.append((cx,cy,rx,ry))
    WTH=330                                  # withers height
    SPINE=GND-WTH*0.70
    # RULE 5: not 100% black — subtle internal value so form reads
    part(hx-4,  SPINE+8,  86, 46, DARK)       # rib cage (deep, long)
    part(hx-80, SPINE+16, 42, 44, DARK)      # chest/shoulder mass
    part(hx+74, SPINE+8, 48, 48, DARK)       # pelvis/croup
    part(hx+18, SPINE-22, 72, 18, DARK)
    part(hx-58, SPINE-28, 26, 16, DARK)      # withers
    part(hx+70, SPINE-26, 30, 16, DARK)      # croup      # topline: withers -> loin -> croup
    # neck: base thick at the chest, tapering, carried forward ~40°
    nk=[]
    for k in range(120):
        t=k/120.0
        nx=hx-88-t*102; ny=SPINE-10-t*66 - math.sin(t*3.14)*9
        rr=27-14*t
        blob(nx,ny, rr, rr*0.92, DARK)
        nk.append((nx,ny,rr,rr*0.92))

    part(hx-212, SPINE-74, 36, 20, DARK)     # head
    part(hx-250, SPINE-66, 21, 13, DARK)     # muzzle
    part(hx-202, SPINE-98, 5.5, 13); part(hx-189, SPINE-96, 5.5, 12)   # ears
    # legs with real joints; weight carried on the near foreleg
    def leg(x0, kx, cx2, w0, planted):
        knee=(x0+kx, SPINE+40+(GND-(SPINE+40))*0.44)
        hoof=(x0+cx2, GND-4)
        for (ax,ay),(bx,by),seg in [((x0,SPINE+40),knee,0),(knee,hoof,1)]:
            for k in range(30):
                t=k/30.0
                D(ax+(bx-ax)*t, ay+(by-ay)*t, w0*(1-0.46*(seg*0.5+t*0.5)), DARK)
        D(hoof[0], GND-3, w0*0.60, DARK)
        if planted:                           # RULE 2: contact — grass rises over the hoof
            for q in range(60):
                gx=hoof[0]+random.uniform(-16,16); gy=GND-random.uniform(0,12)
                L(gx,gy, gx+random.uniform(-3,3), gy-random.uniform(6,18), 1.0, (72,78,46))
    leg(hx-56, -14,  -4, 13, True)
    leg(hx-32,  10,  22, 11, False)
    leg(hx+66,  16,   2, 14, True)
    leg(hx+92, -10,  14, 12, False)
    # mane in strands, gravity + a little wind
    for i in range(90):
        t=random.random()
        x=hx-88-t*102; y=SPINE-12-t*66-math.sin(t*3.14)*9
        ln=random.uniform(14,40)
        L(x,y, x-random.uniform(4,16), y+ln, random.uniform(0.9,2.0), DARK)
    # tail, several strand groups
    for g in range(7):
        gx=hx+116+g*2.4
        for i in range(150):
            t=i/150.0
            x=gx+math.sin(t*1.9+g*0.7)*16
            y=SPINE+12+t*158
            D(x+random.uniform(-1.2,1.2), y, 5.6*(1-t*0.62), DARK)
    # ---------- light: warm rim on the sun side, cool fill opposite ----------
    silhouette_rim(a, parts, SX, SY, RIM, w=2.2, dens=200, spread=1.22, alpha=0.85, fuzz=True)
    # neck: light its own upper/sun-side edge, following the tube
    for i,(nx,ny,rx,ry) in enumerate(nk):
        if i%2: continue
        ang=math.atan2(SY-ny, SX-nx)
        x=nx+math.cos(ang)*rx*0.98; y=ny+math.sin(ang)*ry*0.98
        ok=True
        for (ox,oy,orx,ory) in parts:
            if ((x-ox)/orx)**2+((y-oy)/ory)**2 < 1.02: ok=False; break
        if not ok: continue
        D(x,y, 2.1, RIM, 0.85)
        L(x,y, x+math.cos(ang)*random.uniform(2,5), y+math.sin(ang)*random.uniform(2,5), 0.7, RIM)
    def outside(x,y,skip):
        for (ox,oy,orx,ory) in parts:
            if (ox,oy,orx,ory)==skip: continue
            if ((x-ox)/orx)**2 + ((y-oy)/ory)**2 < 1.06: return False
        return True
    for prt in parts:                                # cool sky fill, outer silhouette only
        cx,cy,rx,ry=prt
        a0=math.atan2(SY-cy, SX-cx)+math.pi
        for i in range(70):
            ang=a0-0.95+1.9*i/70
            x=cx+math.cos(ang)*rx*0.97; y=cy+math.sin(ang)*ry*0.97
            if not outside(x,y,prt): continue
            D(x,y, 2.0, (96,108,130), 0.20)
    # ---------- RULE 2: contact shadow + haze around the legs ----------
    for i in range(700):
        D(hx+random.uniform(-190,190), GND+random.uniform(-6,26), random.uniform(6,18), (44,48,30), 0.030)
    for i in range(160):
        D(hx+random.uniform(-230,230), GND-random.uniform(0,34), random.uniform(14,34), (222,220,206), 0.013)
    # airborne seed/dust in the light
    for i in range(420):
        D(random.uniform(0,W), random.uniform(TOPBAR,H*0.95), random.uniform(0.6,1.9), (255,246,214), random.uniform(0.12,0.55))

build()
asyncio.run(paint(a))
