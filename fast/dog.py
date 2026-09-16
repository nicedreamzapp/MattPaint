import asyncio, math, random
from art import Art, mix, paint, TOPBAR, silhouette_rim, canopy
random.seed(5)
W,H=1320,860
a=Art(W,H,"THE LONG WAIT")
R,L,D=a.R,a.L,a.D
HOR=H*0.74
def build():
    keys=[(0.0,(38,52,92)),(0.30,(112,96,128)),(0.55,(214,124,96)),(0.78,(250,176,96)),(1.0,(255,216,140))]
    def sky(t):
        for (p,ca),(q,cb) in zip(keys,keys[1:]):
            if p<=t<=q: return mix(ca,cb,(t-p)/(q-p))
        return keys[-1][1]
    for y in range(TOPBAR,int(HOR),2):
        R(0,y,W,3, sky((y-TOPBAR)/(HOR-TOPBAR)))
    sx,sy=W*0.68, HOR-58
    for k in range(90):
        u=k/90.0
        D(sx,sy, 170*(1-u)+8, mix(sky((sy-TOPBAR)/(HOR-TOPBAR)),(255,246,220),0.30+0.66*(u**2)), 0.060*((u**2)**1.3))
    D(sx,sy,13,(255,252,236),1.0)
    # clouds
    for j in range(9):
        cy=TOPBAR+random.uniform(10,(HOR-TOPBAR)*0.6); cx=random.uniform(-100,W+100)
        wd=random.uniform(220,640); ht=random.uniform(10,30)
        base=mix((232,170,150),(255,214,170), (cy-TOPBAR)/(HOR-TOPBAR))
        for k in range(220):
            u=random.random(); env=math.sin(max(0,min(1,u))*math.pi)**1.4
            D(cx-wd/2+wd*u+random.uniform(-10,10), cy+math.sin(u*4+j)*ht*0.4+random.gauss(0,ht*0.4),
              ht*env*random.uniform(0.25,0.9), mix(base,(255,242,222),0.35), 0.030)
    # hill
    def hill(x):
        return HOR - 42 - 58*math.sin(x/W*2.2+0.4) - 16*math.sin(x/W*7.0)
    for x in range(0,W,2):
        y=hill(x); n=int((H-y)/3)+1
        for k in range(n):
            v=k/max(1,n-1)
            R(x,y+(H-y)*v,2,4, mix((44,40,34),(10,10,10), v**0.6))
    # dry grass catching the light
    for i in range(2600):
        x=random.uniform(0,W); y=hill(x)+random.uniform(0,H-hill(x))
        t=(y-hill(x))/max(1,(H-hill(x)))
        c=mix((196,148,80),(24,22,18), t*1.15)
        L(x,y,x+random.uniform(-3,3),y-random.uniform(5,18), random.uniform(0.6,1.2), c)
    # ---- the dog: sitting, seen from behind-left, backlit ----
    dx,dy=W*0.40, hill(W*0.40)+6
    DARK=(14,13,12); RIM=(255,206,140)
    def blob(cx,cy,rx,ry,col=DARK):
        yy=-ry
        while yy<=ry:
            w=rx*math.sqrt(max(0.0,1-(yy/ry)**2))
            R(cx-w, cy+yy, 2*w, 2.4, col); yy+=2
    parts=[]
    def part(cx,cy,rx,ry):
        blob(cx,cy,rx,ry); parts.append((cx,cy,rx,ry))
    S=1.55                                   # bigger so it reads
    # sitting dog in profile, facing right: haunches low, back rising to chest, head on top
    part(dx-10,      dy-44*S,  34*S, 34*S)   # rear haunch
    part(dx+22*S,    dy-70*S,  30*S, 40*S)   # body / ribcage rising forward
    part(dx+38*S,    dy-100*S, 29*S, 32*S)   # chest & shoulders
    part(dx+50*S,    dy-128*S, 16*S, 15*S)   # short neck
    part(dx+62*S,    dy-150*S, 19*S, 17*S)   # skull
    part(dx+84*S,    dy-146*S, 14*S, 9*S)    # muzzle forward
    # upright ears
    for (ex,ey,rx2,ry2) in [(dx+52*S, dy-168*S, 6.0*S, 12*S), (dx+66*S, dy-170*S, 5.5*S, 11*S)]:
        part(ex,ey,rx2,ry2)
    # front legs straight down from the chest
    for lx,off in ((dx+36*S,0.0),(dx+52*S,1.0)):
        for k in range(34):
            t=k/34.0
            D(lx+t*4*S+off*2, dy-92*S+t*92*S, 5.2*S*(1-t*0.30), DARK)
    # rear foot tucked forward
    part(dx+6*S, dy-10*S, 16*S, 8*S)
    # tail curling along the ground behind
    for k in range(70):
        t=k/70.0
        D(dx-26*S-math.sin(t*2.0)*30*S*t, dy-40*S+t*36*S, 7.5*S*(1-t*0.45), DARK)

    silhouette_rim(a, parts, sx, sy, RIM, w=2.2, dens=200, spread=1.28, alpha=0.85, fuzz=True)
    # motes
    for i in range(320):
        D(random.uniform(0,W), random.uniform(TOPBAR,H*0.95), random.uniform(0.6,1.8), (255,232,186), random.uniform(0.15,0.65))

build()
asyncio.run(paint(a))
