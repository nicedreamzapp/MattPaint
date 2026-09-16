import asyncio, math, random
from art import Art, mix, paint, TOPBAR
random.seed(23)
W,H=1340,880
a=Art(W,H,"DEEP LIGHT")
R,L,D=a.R,a.L,a.D
def build():
    # water column: bright near the surface, deepening down
    for y in range(TOPBAR,H,2):
        t=(y-TOPBAR)/(H-TOPBAR)
        R(0,y,W,3, mix((92,186,196),(3,18,44), t**0.82))
    # surface shimmer
    for i in range(300):
        x=random.uniform(0,W); y=TOPBAR+random.uniform(0,26)
        L(x,y,x+random.uniform(14,60),y+random.uniform(-2,2), random.uniform(0.8,2.0),(210,246,250))
    # ---- god rays from the surface ----
    for i in range(26):
        x0=random.uniform(-120,W+60); ang=1.32+random.uniform(-0.16,0.16)
        wd=random.uniform(18,66)
        for k in range(120):
            u=k/120.0
            x=x0+math.cos(ang-0.35)*1600*u*0.5
            y=TOPBAR+math.sin(ang)*1600*u*0.60
            if y>H: break
            D(x,y, wd*(0.3+u*1.3), (188,240,236), 0.013*(1-u*0.92))
    # caustic net on the upper water
    for band in range(30):
        y0=TOPBAR+random.uniform(0,H*0.40)
        amp=random.uniform(4,14); freq=random.uniform(0.010,0.030); ph=random.uniform(0,6.28)
        t=(y0-TOPBAR)/(H*0.40)
        for x in range(0,W,3):
            y=y0+math.sin(x*freq+ph)*amp
            D(x,y, random.uniform(4,11), (196,244,240), 0.030*(1-t*0.7))
    # drifting particles
    for i in range(700):
        x=random.uniform(0,W); y=random.uniform(TOPBAR,H)
        t=(y-TOPBAR)/(H-TOPBAR)
        D(x,y, random.uniform(0.6,2.2), (206,238,236), (0.10+0.5*random.random())*(1-t*0.6))
    # ---- the fish: koi in profile, lit from above ----
    fx,fy=W*0.46, H*0.56
    BODY=(232,138,66); BODY_D=(96,40,22); BODY_L=(255,226,180); WHITE=(244,238,226)
    def body_shape(x):
        """half-height of the body at offset x from centre (-1..1 of length)"""
        if x<-1 or x>1: return 0.0
        return (1-x*x)**0.62
    LEN, DEPTH = 210, 74
    for ix in range(-LEN, LEN):
        u=ix/LEN
        hh=body_shape(u)*DEPTH
        if hh<=0: continue
        n=int(2*hh/2.2)+1
        for k in range(n):
            v=k/max(1,n-1)
            yy=fy-hh+2*hh*v
            # top lit, belly pale, flank mid
            if v<0.24: c=mix(BODY_D,BODY,(v/0.24))
            elif v<0.62: c=mix(BODY,BODY_L,(v-0.24)/0.38*0.55)
            else: c=mix(BODY_L,WHITE,(v-0.62)/0.38)
            # koi blotches
            if math.sin(u*7.0)*math.cos(v*5.0)>0.55: c=mix(c,(250,250,246),0.75)
            if math.sin(u*4.0+1.7)*math.cos(v*3.0)>0.72: c=mix(c,(40,32,30),0.55)
            R(fx+ix, yy, 2, 2.4, c)
    # scales
    for i in range(1400):
        u=random.uniform(-0.96,0.96); v=random.uniform(0.06,0.94)
        hh=body_shape(u)*DEPTH
        x=fx+u*LEN; y=fy-hh+2*hh*v
        D(x,y, random.uniform(1.4,3.0), (255,240,214), 0.10)
    # tail fin
    for k in range(120):
        t=k/120.0
        sp=58*t
        x=fx+LEN-6+t*120
        for s in (-1,1):
            L(x, fy+s*sp*0.30, x+6, fy+s*sp*0.92, 1.4, mix((250,190,136),(158,80,46), t))
    # dorsal + pectoral fins
    for k in range(70):
        t=k/70.0
        L(fx-40+t*120, fy-DEPTH*body_shape((-40+t*120)/LEN)+2, fx-20+t*120, fy-DEPTH-34*math.sin(t*3.14), 1.5,
          mix((250,190,140),(160,80,46), t))
    for k in range(70):
        t=k/70.0
        x0=fx-96; y0=fy+22
        L(x0+t*6, y0+t*4, x0+22+t*58, y0+18+t*40, 1.5, mix((250,204,160),(150,84,52), t))
    # eye
    D(fx-LEN+44, fy-16, 11, (250,244,232)); D(fx-LEN+44, fy-16, 7, (24,20,18)); D(fx-LEN+42, fy-19, 2.4,(255,255,255))
    # mouth
    L(fx-LEN+6, fy+4, fx-LEN+26, fy+8, 2.2, (120,58,34))
    # bubbles rising from the mouth
    for i in range(26):
        t=i/26.0
        bx=fx-LEN-10-t*70+random.uniform(-8,8); by=fy-t*260+random.uniform(-10,10)
        r=random.uniform(2.5,7)
        D(bx,by,r,(220,248,248),0.35); D(bx-r*0.3,by-r*0.3,r*0.35,(255,255,255),0.6)
    # sea floor haze
    for i in range(200):
        D(random.uniform(0,W), H-random.uniform(0,140), random.uniform(30,90), (10,30,54), 0.05)

build()
asyncio.run(paint(a))
