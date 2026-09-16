"""2ND GEN — THE WATCHER. Branch compresses under weight, creature integrated into the
environment, three depth planes, body not pure black."""
import asyncio, math, random
import art as A
from art import Art, mix, paint, TOPBAR, canopy, silhouette_rim
A.GEN="2ND GEN"
random.seed(303)
W,H=1340,880
a=Art(W,H,"THE WATCHER")
R,L,D=a.R,a.L,a.D
SX,SY=W*0.63, H*0.30

def build():
    # golden-hour jungle haze
    for y in range(TOPBAR,H,2):
        t=(y-TOPBAR)/(H-TOPBAR)
        R(0,y,W,3, mix((252,212,140),(34,42,28), t**1.12))
    for k in range(90):
        u=k/90.0
        D(SX,SY, 330*(1-u)+10, mix((252,226,168),(255,248,220),u), 0.045*(u**1.5))
    # ---------- RULE 3: three canopy planes, contrast and saturation drop with distance ----------
    for (col,shade,cnt,rad,alpha_haze) in [
        ((186,170,110),(132,120,72), 22, (70,150), 0.030),      # far, bleached
        ((118,116,68), (66,70,38),  20, (60,130), 0.020),       # middle
        ((44,50,28),   (16,20,12),  16, (60,140), 0.0)]:        # near, dark
        for i in range(cnt):
            cx=random.uniform(-70,W+70); cy=random.uniform(TOPBAR-40, H*0.58)
            canopy(a, cx, cy, random.uniform(*rad), random.uniform(*rad)*0.65, col,
                   n=int(random.uniform(130,260)), shade=shade)
        if alpha_haze:
            for i in range(260):
                D(random.uniform(0,W), random.uniform(TOPBAR,H*0.8), random.uniform(50,130), (244,220,166), alpha_haze)

    # ---------- the branch: it SAGS under the animal (RULE 2) ----------
    MX=W*0.40                       # where the weight sits
    by0=H*0.60
    def branch_y(x):
        d=abs(x-MX)/(W*0.52)
        sag=26*max(0.0, 1.0-d*d)                      # deepest right under the animal
        return by0 + sag + math.sin(x*0.004)*7
    for x in range(0,W,2):
        yy=branch_y(x); th=30-8*abs(x-MX)/W
        for k in range(int(th)):
            v=k/th
            c=mix((78,58,38),(16,12,9), v**0.7)
            if v<0.16: c=mix(c,(226,176,110), (0.16-v)*4.0)    # top of the branch catches the sun
            R(x, yy+k*1.5, 3, 2.0, c)
        if x%9==0:                                              # bark
            L(x,yy+random.uniform(2,26), x+random.uniform(-3,3), yy+random.uniform(6,30), 1.0, (18,13,9))
    for i in range(120):                                        # moss on the upper side
        x=random.uniform(0,W); D(x, branch_y(x)+random.uniform(0,5), random.uniform(1.5,4), (92,112,58), 0.5)
    for i in range(26):                                         # small twigs, angled out and drooping
        x=random.uniform(0,W); y=branch_y(x)+random.uniform(0,8)
        side=random.choice((-1,1)); ln=random.uniform(26,90)
        px,py=x,y
        for k in range(10):
            p=(k+1)/10.0
            nx=x+side*ln*p; ny=y - ln*0.35*math.sin(p*2.0) + ln*0.5*(p*p)
            L(px,py,nx,ny, max(0.6, 1.8*(1-p)), (46,34,22))
            if p>0.3:
                for q in range(3):
                    D(nx+random.uniform(-5,5), ny+random.uniform(-2,6), random.uniform(1.6,3.4), (64,88,44), 0.75)
            px,py=nx,ny

    # ---------- the monkey ----------
    MY=branch_y(MX)+2
    BODY=(25,23,22); DEEP=(15,14,14); RIM=(255,214,146)
    parts=[]
    def blob(cx,cy,rx,ry,col):
        yy=-ry
        while yy<=ry:
            w=rx*math.sqrt(max(0.0,1-(yy/ry)**2))
            R(cx-w, cy+yy, 2*w, 2.4, col); yy+=2
    def part(cx,cy,rx,ry):
        blob(cx,cy,rx,ry,BODY); parts.append((cx,cy,rx,ry))
    part(MX,      MY-78, 60, 64)      # haunches/back
    part(MX+30,   MY-108, 38, 52)     # chest
    part(MX+12,   MY-166, 40, 40)     # head
    part(MX-16,   MY-160, 22, 17)     # muzzle
    part(MX-14,   MY-192, 12, 14); part(MX+40, MY-190, 12, 14)   # ears
    for (ax,ay,bx2,by2,wt) in [(MX+6,MY-150,MX-34,MY-16,13),(MX+46,MY-132,MX+66,MY-14,12)]:
        for k in range(40):
            t=k/40.0
            D(ax+(bx2-ax)*t, ay+(by2-ay)*t+math.sin(t*3.0)*6, wt*(1-t*0.34), BODY)
    for lx in (MX-26, MX+34):                                    # feet gripping, toes over the branch
        for k in range(26):
            t=k/26.0
            D(lx+t*10, MY-40+t*40, 12*(1-t*0.3), BODY)
        for f in range(4):
            D(lx+6+f*6, MY+4, 3.6, BODY)
    for k in range(110):                                         # tail hanging with gravity
        t=k/110.0
        D(MX+64+math.sin(t*2.6)*54*t, MY-60+t*250, 9*(1-t*0.72), BODY)
    # RULE 5: not pure black — a hint of form inside the silhouette
    for i in range(700):
        cx,cy,rx,ry=random.choice(parts)
        ang=random.uniform(0,6.2832); rr=random.random()**0.6
        D(cx+math.cos(ang)*rx*rr*0.85, cy+math.sin(ang)*ry*rr*0.85, random.uniform(1.5,4),
          mix(BODY,(58,52,46),0.55), 0.10)
    silhouette_rim(a, parts, SX, SY, RIM, w=2.2, dens=210, spread=1.30, alpha=0.85, fuzz=True)
    for s in (-1,1):                                             # eyes, catching the sun
        D(MX+12+s*15, MY-172, 4.2, (252,236,200), 0.95)
        D(MX+12+s*15, MY-172, 2.0, (30,22,16), 0.9)
    # contact shadow on the branch directly under the animal (RULE 2)
    for i in range(240):
        x=MX+random.gauss(0,44)
        D(x, branch_y(x)+random.uniform(0,10), random.uniform(4,12), (10,8,6), 0.05)

    # ---------- understory below the branch: receding shadow, not an empty wash ----------
    UB=branch_y(W*0.5)+40
    for y in range(int(UB),H,2):
        t=max(0.0,(y-UB)/(H-UB))
        R(0,y,W,3, mix((44,50,32),(12,16,11), t**0.75))
    for (col,shade,cnt,rad) in [((70,80,46),(30,38,22),14,(80,180)),((40,50,30),(14,20,12),12,(70,160))]:
        for i in range(cnt):
            canopy(a, random.uniform(-60,W+60), UB+random.uniform(0,(H-UB)*0.9),
                   random.uniform(*rad), random.uniform(*rad)*0.55, col, n=220, shade=shade)
    for i in range(700):                                        # undergrowth blades
        x=random.uniform(0,W); y=UB+random.uniform(0,H-UB)
        t=max(0.0,(y-UB)/(H-UB))
        L(x,y, x+random.uniform(-4,4), y-random.uniform(10,40)*(0.5+t), 1.0+t,
          mix((58,74,40),(20,28,18), t))
    for i in range(240):                                        # mist pooling low
        D(random.uniform(0,W), UB+random.uniform(-20,90), random.uniform(30,80), (214,198,150), 0.020)

    # ---------- near foreground leaves, dark and soft ----------
    for i in range(10):
        cx=random.choice([random.uniform(-60,W*0.10), random.uniform(W*0.92,W+60)])
        canopy(a, cx, random.uniform(TOPBAR,H), random.uniform(130,210), random.uniform(100,180),
               (12,16,11), n=420, shade=(0,0,0))
    for i in range(320):
        D(random.uniform(0,W), random.uniform(TOPBAR,H*0.92), random.uniform(0.6,1.9), (255,238,196), random.uniform(0.12,0.6))

build()
asyncio.run(paint(a))
