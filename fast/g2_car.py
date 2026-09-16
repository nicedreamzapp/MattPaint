"""2ND GEN — NIGHT RUN. Wet asphalt = broken, stretched, displaced reflections.
Rain varies in focus. Headlights scatter through the air."""
import asyncio, math, random
import art as A
from art import Art, mix, paint, TOPBAR
A.GEN="2ND GEN"
random.seed(505)
W,H=1380,880
a=Art(W,H,"NIGHT RUN")
R,L,D=a.R,a.L,a.D
ROAD=H*0.66

def build():
    for y in range(TOPBAR,int(ROAD),2):
        t=(y-TOPBAR)/(ROAD-TOPBAR)
        R(0,y,W,3, mix((8,10,24),(48,30,50), t**1.15))
    for k in range(80):
        u=k/80.0
        D(W*0.74, ROAD-70, 460*(1-u)+20, (130,74,116), 0.011*(u**1.3))
    # city: RULE 3, far buildings hazier
    for i in range(52):
        bx=random.uniform(-30,W); bw=random.uniform(28,92); bh=random.uniform(70,260)
        depth=random.random()
        by=ROAD-bh
        R(bx,by,bw,bh, mix((10,12,26),(34,34,56), depth))
        for wy in range(int(by)+8, int(ROAD)-6, 12):
            for wx in range(int(bx)+5, int(bx+bw)-5, 10):
                if random.random()<0.30:
                    c=random.choice([(255,214,140),(196,218,255),(255,176,116)])
                    D(wx,wy,2.0+depth, mix(c,(60,60,90), 1-depth), (0.30+0.6*depth))
    for i in range(240):
        D(random.uniform(0,W), ROAD-random.uniform(0,220), random.uniform(40,110), (44,40,66), 0.020)
    # wet asphalt
    for y in range(int(ROAD),H,2):
        t=max(0.0,(y-ROAD)/(H-ROAD))
        R(0,y,W,3, mix((30,30,44),(8,8,14), t**0.85))
    for i in range(700):
        D(random.uniform(0,W), random.uniform(ROAD,H), random.uniform(8,26), (64,64,92), 0.022)

    # ---------- the car ----------
    cx,cy=W*0.43, ROAD-4
    RED=(168,22,30); RED_D=(34,6,10); RED_L=(232,108,98)
    def panel(pts, top_c, bot_c):
        xs=[p[0] for p in pts]; x0,x1=int(min(xs)),int(max(xs))
        for x in range(x0,x1):
            ys=[]
            for i in range(len(pts)):
                ax,ay=pts[i]; bx,by=pts[(i+1)%len(pts)]
                if (ax<=x<bx) or (bx<=x<ax):
                    t=(x-ax)/(bx-ax); ys.append(ay+(by-ay)*t)
            if len(ys)<2: continue
            ys.sort(); yt,yb=ys[0],ys[-1]
            n=int((yb-yt)/2)+1
            for k in range(n):
                v=k/max(1,n-1)
                R(x, yt+(yb-yt)*v, 2, 3, mix(top_c,bot_c, v**0.72))
    body=[(cx-216,cy-20),(cx-182,cy-60),(cx-100,cy-90),(cx-18,cy-116),(cx+74,cy-116),
          (cx+154,cy-86),(cx+210,cy-54),(cx+228,cy-22),(cx+210,cy-2),(cx-202,cy-2)]
    panel(body, RED_L, RED_D)
    panel([(cx-72,cy-90),(cx-18,cy-112),(cx+68,cy-112),(cx+120,cy-88),(cx-62,cy-88)], (110,140,175),(10,16,30))
    # panel seams + handles (RULE 5: a few, not many)
    L(cx-92,cy-88, cx-84,cy-14, 1.4, (70,14,20)); L(cx+64,cy-92, cx+58,cy-14, 1.4, (70,14,20))
    D(cx-56,cy-58, 3.0,(240,180,176),0.8); D(cx+96,cy-56, 3.0,(240,180,176),0.8)
    for k in range(150):                                       # shoulder highlight
        t=k/150.0; x=cx-206+t*430; y=cy-58-math.sin(t*3.1)*20
        D(x,y, 2.6*(0.35+0.85*math.sin(t*3.14)), (255,214,206), 0.55)
    for wx in (cx-132, cx+128):                                # wheels with sidewalls
        for r in range(48,0,-1): D(wx, cy-16, r, mix((6,6,8),(38,38,44), r/48.0))
        for r in range(27,0,-1): D(wx, cy-16, r, mix((160,160,170),(58,58,68), r/27.0))
        for sp in range(10):
            ang=sp*(6.2832/10); L(wx,cy-16, wx+math.cos(ang)*25, cy-16+math.sin(ang)*25, 2.2, (24,24,30))
        D(wx, cy-16, 7, (30,30,36))
    # lights
    D(cx+226,cy-58, 9,(255,250,226),1.0); D(cx+226,cy-58, 22,(255,238,196),0.35)
    for s in (0,1):
        D(cx-212, cy-48+s*13, 6,(255,58,48),0.95); D(cx-212, cy-48+s*13, 17,(255,58,48),0.20)
    # headlight beam scattering through rain
    for i in range(60):
        ang=random.uniform(-0.12,0.20)
        for k in range(110):
            u=k/110.0
            x=cx+232+math.cos(ang)*700*u; y=cy-58+math.sin(ang)*700*u+u*70
            if x>W+40: break
            D(x,y, 8+u*66, (255,240,200), 0.0045*(1-u*0.92))

    # ---------- RULE 4: wet asphalt reflection — flipped, stretched, displaced, BROKEN ----------
    def reflect(src_x, src_y, col, width, length, jitter):
        for k in range(length):
            t=k/length
            y=cy+6+t*(H-cy-6)*0.92
            if y>H: break
            dx=math.sin(y*0.06+src_x*0.01)*jitter*(0.4+t*1.6)      # horizontal displacement
            w=width*(0.6+t*1.8)
            c=mix(col,(12,12,18), t*0.92)
            if random.random()<0.50: continue                      # broken by road texture
            L(src_x+dx-w/2, y, src_x+dx+w/2, y, random.uniform(0.9,2.4), c)
    for i in range(40): reflect(cx+random.uniform(-190,200), cy, mix(RED,(40,10,14),0.35), random.uniform(20,70), 150, 18)
    for i in range(26): reflect(cx+226+random.uniform(-30,70), cy, (206,188,148), random.uniform(16,52), 150, 13)
    for i in range(30): reflect(cx-212+random.uniform(-24,24), cy, (255,60,50), random.uniform(14,50), 130, 10)
    for i in range(26): reflect(random.uniform(0,W), cy, (150,160,220), random.uniform(8,28), 120, 18)
    # ---------- rain: varied length, focus and brightness ----------
    for i in range(900):                                          # distant rain: faint, low alpha
        x=random.uniform(-40,W+40); y=random.uniform(TOPBAR,H)
        ln=random.uniform(6,18)
        for k in range(4):
            p=k/4.0
            D(x-ln*0.30*p, y+ln*p, random.uniform(0.5,0.9), (150,162,196), 0.16)
    for i in range(90):                                           # mid rain
        x=random.uniform(-40,W+40); y=random.uniform(TOPBAR,H)
        ln=random.uniform(16,30)
        for k in range(6):
            p=k/6.0
            D(x-ln*0.30*p, y+ln*p, 0.9, (190,202,232), 0.32)
    for i in range(22):                                           # a few sharp foreground drops
        x=random.uniform(0,W); y=random.uniform(TOPBAR,H)
        L(x,y, x-13, y+40, 1.8, (218,228,248))
    # spray kicked up behind the wheels (RULE 2: contact)
    for wx in (cx-132, cx+128):
        for i in range(160):
            D(wx-random.uniform(0,120), cy-random.uniform(0,40), random.uniform(2,8), (190,200,225), 0.10)

build()
asyncio.run(paint(a))
