import asyncio, math, random
from art import Art, mix, paint, TOPBAR, canopy, silhouette_rim
random.seed(9)
W,H=1300,880
a=Art(W,H,"THE WATCHER")
R,L,D=a.R,a.L,a.D

def build():
    # jungle mist at golden hour
    for y in range(TOPBAR,H,2):
        t=(y-TOPBAR)/(H-TOPBAR)
        R(0,y,W,3, mix((252,206,128),(46,52,34), t**1.15))
    sx,sy=W*0.62,H*0.30
    for k in range(90):
        u=k/90.0
        D(sx,sy, 300*(1-u)+10, mix((252,222,160),(255,246,214),u), 0.055*(u**1.5))
    # far canopy haze bands
    for i in range(240):
        D(random.uniform(0,W), random.uniform(TOPBAR,H*0.8), random.uniform(50,140), (240,214,160), 0.014)
    # background foliage silhouettes, soft
    for (col,scale,cnt,shade) in [((150,138,90),1.0,26,(96,88,54)),((98,96,60),0.85,24,(52,52,32)),((46,50,32),0.7,20,(18,20,14))]:
        for i in range(cnt):
            cx=random.uniform(-60,W+60); cy=random.uniform(TOPBAR-30, H*0.60)
            canopy(a, cx, cy, random.uniform(50,120)*scale, random.uniform(34,80)*scale, col,
                   n=int(random.uniform(120,260)), shade=shade)
    # the branch
    by=H*0.63
    for x in range(0,W,2):
        t=x/W
        yy=by+math.sin(t*2.2)*16
        th=26-6*math.sin(t*3.0)
        for k in range(int(th)):
            v=k/th
            R(x, yy+k*1.6, 3, 2, mix((58,44,30),(18,14,10), v))
    # ---- the monkey, backlit silhouette with a warm rim ----
    mx,my=W*0.40, by-4
    DARK=(22,18,16); RIM=(255,216,150)
    def blob(cx,cy,rx,ry,rot=0.0,col=DARK):
        steps=int(max(rx,ry)*1.6)
        for i in range(steps):
            v=i/steps
            yy=-ry+2*ry*v
            w=rx*math.sqrt(max(0.0,1-(yy/ry)**2))
            R(cx-w, cy+yy, 2*w, 2.4, col)
    # haunches + body
    blob(mx, my-82, 72, 76)
    blob(mx-8, my-156, 44, 46)          # head
    blob(mx+44, my-92, 34, 52)          # shoulder
    # muzzle
    blob(mx-30, my-142, 23, 18)
    # ears
    blob(mx-44, my-168, 13, 15); blob(mx+26, my-168, 13, 15)
    # arms
    for (ax,ay,bx2,by2,wt) in [(mx-32,my-138,mx-68,my-18,14),(mx+34,my-122,mx+58,my-16,13)]:
        for k in range(40):
            t=k/40.0
            x=ax+(bx2-ax)*t; y=ay+(by2-ay)*t+math.sin(t*3.1)*7
            D(x,y, wt*(1-t*0.35), DARK)
    # legs gripping the branch
    for (ax,ay,bx2,by2,wt) in [(mx-24,my-28,mx-52,my+8,15),(mx+26,my-26,mx+50,my+8,15)]:
        for k in range(30):
            t=k/30.0
            x=ax+(bx2-ax)*t; y=ay+(by2-ay)*t
            D(x,y, wt*(1-t*0.3), DARK)
    # tail curling down
    for k in range(90):
        t=k/90.0
        x=mx+68+math.sin(t*3.4)*58*t
        y=my-70+t*230
        D(x,y, 10*(1-t*0.75), DARK)
    # warm rim light, clipped to the true outer silhouette
    parts=[(mx, my-82, 72, 76), (mx-8, my-156, 44, 46), (mx+44, my-92, 34, 52),
           (mx-30, my-142, 23, 18), (mx-44, my-168, 13, 15), (mx+26, my-168, 13, 15)]
    silhouette_rim(a, parts, sx, sy, RIM, w=2.4, dens=170, spread=1.30, alpha=0.85)
    # eye catchlights
    for s in (-1,1):
        D(mx-12+s*14, my-160, 4.0, (250,236,206), 0.95)
    # foreground leaves framing
    for i in range(9):
        cx=random.choice([random.uniform(-60,W*0.10), random.uniform(W*0.92,W+60)])
        cy=random.uniform(TOPBAR,H)
        canopy(a, cx, cy, random.uniform(120,200), random.uniform(90,170), (13,17,11),
               n=420, shade=(0,0,0))
    # motes
    for i in range(260):
        D(random.uniform(0,W), random.uniform(TOPBAR,H*0.9), random.uniform(0.7,2.0), (255,238,196), random.uniform(0.15,0.7))

build()
asyncio.run(paint(a))
