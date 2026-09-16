import asyncio, math, random
from art import Art, mix, paint, TOPBAR, silhouette_rim
random.seed(12)
W,H=1360,860
a=Art(W,H,"MORNING FIELD")
R,L,D=a.R,a.L,a.D
HOR=H*0.72
def build():
    keys=[(0.0,(96,124,158)),(0.35,(168,178,186)),(0.62,(226,206,180)),(0.85,(248,224,182)),(1.0,(252,238,206))]
    def sky(t):
        for (p,ca),(q,cb) in zip(keys,keys[1:]):
            if p<=t<=q: return mix(ca,cb,(t-p)/(q-p))
        return keys[-1][1]
    for y in range(TOPBAR,int(HOR),2):
        R(0,y,W,3, sky((y-TOPBAR)/(HOR-TOPBAR)))
    sx,sy=W*0.24, HOR-150
    for k in range(90):
        u=k/90.0
        D(sx,sy, 230*(1-u)+10, mix(sky((sy-TOPBAR)/(HOR-TOPBAR)),(255,250,236),0.25+0.7*(u**2)), 0.050*((u**2)**1.2))
    D(sx,sy,16,(255,254,246),1.0)
    # mist layers over a far treeline
    for i in range(34):
        x=random.uniform(-60,W); y=HOR-random.uniform(10,90); wd=random.uniform(90,260)
        for k in range(18):
            D(x+random.uniform(-wd/2,wd/2), y+random.gauss(0,9), random.uniform(20,60), (226,224,214), 0.028)
    for i in range(120):
        x=random.uniform(-30,W+30); h=random.uniform(26,96)
        col=(146,154,144) if random.random()<0.6 else (128,138,128)
        L(x,HOR,x,HOR-h*0.42,random.uniform(1.4,2.6),(112,120,112))
        for k in range(int(h*1.4)):
            ang=random.uniform(0,6.2832); rr=random.random()**0.6
            px=x+math.cos(ang)*h*0.42*rr
            py=HOR-h*0.62+math.sin(ang)*h*0.34*rr
            D(px,py, random.uniform(2.0,5.5), col, 0.55)
    # field
    for y in range(int(HOR),H,2):
        t=max(0.0,(y-HOR)/(H-HOR))
        R(0,y,W,3, mix((150,152,110),(48,54,36), t**0.9))
    for i in range(3000):
        x=random.uniform(0,W); y=random.uniform(HOR,H)
        t=max(0.0,(y-HOR)/(H-HOR))
        c=mix((206,196,136),(40,48,30), t*1.1)
        L(x,y,x+random.uniform(-2,2),y-random.uniform(4,16), random.uniform(0.5,1.1), c)
    # ---- horse, standing in profile, facing left toward the light ----
    hx,hy=W*0.58, HOR+30
    DARK=(24,22,20); RIM=(255,238,198)
    parts=[]
    def blob(cx,cy,rx,ry,col=DARK,rot=0.0):
        yy=-ry
        while yy<=ry:
            w=rx*math.sqrt(max(0.0,1-(yy/ry)**2))
            if rot:
                for k in range(int(2*w/2)+1):
                    xx=-w+k*2
                    X=cx+xx*math.cos(rot)-yy*math.sin(rot)
                    Y=cy+xx*math.sin(rot)+yy*math.cos(rot)
                    R(X,Y,2.4,2.6,col)
            else:
                R(cx-w, cy+yy, 2*w, 2.4, col)
            yy+=2
    def part(cx,cy,rx,ry,rot=0.0):
        blob(cx,cy,rx,ry,DARK,rot); parts.append((cx,cy,max(rx,ry)*0.92,max(rx,ry)*0.92) if rot else (cx,cy,rx,ry))
    GND=hy
    WTH=286                                    # height at the withers
    BX, BY = hx, GND-WTH*0.66                  # barrel centre
    part(BX, BY, 104, 50)                      # barrel: long, not round
    part(BX-86, BY-8, 44, 46)                  # deep chest
    part(BX+92, BY-6, 46, 48)                  # hindquarters
    # neck: thin, arched, up and forward
    for k in range(30):
        t=k/30.0
        nx=BX-92-t*104                          # carried forward, not straight up
        ny=BY-24-t*58 - math.sin(t*3.14)*10     # slight arch along the crest
        part(nx, ny, 26-13*t, 24-11*t)
    # head: long wedge with a muzzle
    part(BX-206, BY-92, 32, 18)
    part(BX-242, BY-84, 20, 12)
    part(BX-196, BY-114, 5, 11); part(BX-184, BY-112, 5, 10)   # ears
    # legs: long, about half the total height
    LEGTOP=BY+34
    def leg(x0, knee_dx, cannon_dx, w0):
        seg=[(x0,LEGTOP),(x0+knee_dx, LEGTOP+(GND-LEGTOP)*0.46),(x0+cannon_dx, GND-6)]
        for i in range(len(seg)-1):
            ax,ay=seg[i]; bx,by=seg[i+1]
            for k in range(30):
                t=k/30.0
                D(ax+(bx-ax)*t, ay+(by-ay)*t, w0*(1-0.42*(i*0.45+t*0.45)), DARK)
        D(seg[-1][0], GND-3, w0*0.62, DARK)
    leg(BX-70, -10, -2, 13)
    leg(BX-44,   8, 16, 12)
    leg(BX+74,  12,  0, 14)
    leg(BX+100, -6, 10, 13)
    # mane
    for k in range(90):
        t=k/90.0
        x=hx-92-t*104; y=(hy-286*0.66)-24-t*58
        L(x,y, x-random.uniform(5,16), y+random.uniform(4,22), 1.5, DARK)
    # tail
    for k in range(80):
        t=k/80.0
        x=hx+136+math.sin(t*2.2)*16
        y=(hy-286*0.66)-8+t*150
        D(x,y, 10*(1-t*0.6), DARK)
    silhouette_rim(a, parts, sx, sy, RIM, w=2.0, dens=150, spread=1.2, alpha=0.8, fuzz=True)
    # ground shadow
    for k in range(40):
        D(hx+random.uniform(-150,150), hy+random.uniform(-6,10), random.uniform(20,60), (40,44,30), 0.06)
    # motes
    for i in range(300):
        D(random.uniform(0,W), random.uniform(TOPBAR,H*0.92), random.uniform(0.6,1.8), (255,248,222), random.uniform(0.15,0.6))

build()
asyncio.run(paint(a))
