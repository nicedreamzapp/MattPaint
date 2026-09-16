import asyncio, math, random
from art import Art, mix, paint, TOPBAR
random.seed(31)
W,H=1340,860
a=Art(W,H,"NIGHT RUN")
R,L,D=a.R,a.L,a.D

ROAD=H*0.68
def build():
    # night sky + city glow
    for y in range(TOPBAR,int(ROAD),2):
        t=(y-TOPBAR)/(ROAD-TOPBAR)
        R(0,y,W,3, mix((10,12,26),(42,30,46), t**1.2))
    for k in range(70):
        u=k/70.0
        D(W*0.74, ROAD-40, 420*(1-u)+20, (120,70,110), 0.012*(u**1.2))
    # distant city: lit windows
    for i in range(46):
        bx=random.uniform(-20,W); bw=random.uniform(26,86); bh=random.uniform(60,230)
        by=ROAD-bh
        R(bx,by,bw,bh,(16,16,30))
        for wy in range(int(by)+8, int(ROAD)-6, 12):
            for wx in range(int(bx)+5, int(bx+bw)-5, 10):
                if random.random()<0.34:
                    D(wx,wy,2.2, random.choice([(255,214,140),(200,220,255),(255,180,120)]), random.uniform(0.4,0.95))
    # wet road
    for y in range(int(ROAD),H,2):
        t=(y-ROAD)/(H-ROAD)
        R(0,y,W,3, mix((26,26,38),(8,8,14), t))
    # ---- the car: low sports coupe, side-on, lit from behind-left ----
    cx,cy=W*0.44, ROAD-6
    BODY=(178,26,34); BODY_D=(58,10,16); BODY_L=(255,150,140)
    def body_panel(pts, top_c, bot_c):
        xs=[p[0] for p in pts]
        x0,x1=int(min(xs)),int(max(xs))
        for x in range(x0,x1):
            ys=[]
            for i in range(len(pts)):
                ax,ay=pts[i]; bx,by=pts[(i+1)%len(pts)]
                if (ax<=x<bx) or (bx<=x<ax):
                    t=(x-ax)/(bx-ax)
                    ys.append(ay+(by-ay)*t)
            if len(ys)<2: continue
            ys.sort(); ytop,ybot=ys[0],ys[-1]
            n=int((ybot-ytop)/2)+1
            for k in range(n):
                v=k/max(1,n-1)
                R(x, ytop+(ybot-ytop)*v, 2, 3, mix(top_c,bot_c, v**0.75))
    # main body silhouette
    body=[(cx-210,cy-18),(cx-176,cy-58),(cx-96,cy-86),(cx-16,cy-112),(cx+72,cy-112),
          (cx+150,cy-82),(cx+206,cy-52),(cx+222,cy-20),(cx+206,cy-2),(cx-196,cy-2)]
    body_panel(body, BODY_L, BODY_D)
    # cabin glass
    glass=[(cx-70,cy-86),(cx-16,cy-108),(cx+66,cy-108),(cx+118,cy-84),(cx-60,cy-84)]
    body_panel(glass, (120,150,180), (14,20,34))
    # sharp highlight along the shoulder line
    for k in range(140):
        t=k/140.0
        x=cx-200+t*420
        y=cy-56-math.sin(t*3.1)*18
        D(x,y, 2.4*(0.4+0.8*math.sin(t*3.14)), (255,210,200), 0.55)
    # wheels
    for wx in (cx-128, cx+126):
        for r in range(46,0,-1):
            D(wx, cy-16, r, mix((8,8,10),(40,40,46), r/46.0), 1.0)
        for r in range(26,0,-1):
            D(wx, cy-16, r, mix((150,150,160),(60,60,70), r/26.0), 1.0)
        for s in range(10):
            ang=s*(6.2832/10)
            L(wx,cy-16, wx+math.cos(ang)*24, cy-16+math.sin(ang)*24, 2.2, (26,26,32))
    # headlight beam
    for k in range(120):
        u=k/120.0
        x=cx+230+u*620; y=cy-56+u*54
        D(x,y, 14+u*70, (255,236,190), 0.030*(1-u))
    D(cx+224,cy-58, 9,(255,248,222),1.0)
    D(cx+224,cy-58, 20,(255,236,190),0.35)
    # tail lights
    for s in (0,1):
        D(cx-206, cy-46+s*12, 6, (255,60,50), 0.95)
        D(cx-206, cy-46+s*12, 16, (255,60,50), 0.20)
    # ---- reflections on the wet road ----
    for k in range(260):
        x=cx+random.uniform(-230,240)
        y=cy+random.uniform(4,150)
        t=(y-cy)/150.0
        c=mix(BODY,(20,18,26), t*0.85)
        L(x,y, x+random.uniform(14,70), y, random.uniform(0.8,2.0), c)
    for k in range(90):
        y=cy+random.uniform(4,140); t=(y-cy)/140.0
        L(cx+200+random.uniform(-40,60), y, cx+200+random.uniform(60,220), y, random.uniform(1,2.6),
          mix((255,228,180),(40,36,30), t))
    for k in range(60):
        y=cy+random.uniform(4,120); t=(y-cy)/120.0
        L(cx-220+random.uniform(-40,30), y, cx-220+random.uniform(30,120), y, random.uniform(1,2.2),
          mix((255,70,60),(40,16,18), t))
    # street sheen
    for i in range(220):
        D(random.uniform(0,W), random.uniform(ROAD,H), random.uniform(10,40), (70,70,96), 0.020)
    # rain streaks
    for i in range(900):
        x=random.uniform(0,W); y=random.uniform(TOPBAR,H)
        ln=random.uniform(8,26)
        c=(130,142,172) if random.random()<0.7 else (190,200,225)
        L(x,y,x-ln*0.28,y+ln, random.uniform(0.5,0.9), c)

build()
asyncio.run(paint(a))
