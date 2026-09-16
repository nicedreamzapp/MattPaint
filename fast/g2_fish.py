"""2ND GEN — DEEP LIGHT. Caustics move across the fish, light falls from above,
fins overlap and go translucent at the edge, scales are directional texture not outlines."""
import asyncio, math, random
import art as A
from art import Art, mix, paint, TOPBAR
A.GEN="2ND GEN"
random.seed(404)
W,H=1360,900
a=Art(W,H,"DEEP LIGHT")
R,L,D=a.R,a.L,a.D

def build():
    # ---------- water column: value first, bright at the surface ----------
    for y in range(TOPBAR,H,2):
        t=(y-TOPBAR)/(H-TOPBAR)
        R(0,y,W,3, mix((118,204,206),(2,14,38), t**0.80))
    # surface, seen from below: rippling mirror
    for i in range(420):
        x=random.uniform(0,W); y=TOPBAR+random.uniform(0,30)
        L(x,y, x+random.uniform(12,64), y+random.uniform(-2,2), random.uniform(0.8,2.2),
          mix((186,242,244),(238,252,252), random.random()))
    # ---------- volumetric shafts ----------
    for i in range(30):
        x0=random.uniform(-140,W+60); ang=1.34+random.uniform(-0.15,0.15)
        wd=random.uniform(16,64)
        for k in range(130):
            u=k/130.0
            x=x0+math.cos(ang-0.34)*1700*u*0.48
            y=TOPBAR+math.sin(ang)*1700*u*0.62
            if y>H: break
            broken=0.30+0.70*max(0.0,math.sin(u*5.0+i))
            D(x,y, wd*(0.30+u*1.30), (196,246,238), 0.014*broken*(1-u*0.88))
    # caustic bands rippling near the surface
    for band in range(34):
        y0=TOPBAR+random.uniform(0,H*0.42); amp=random.uniform(4,16)
        freq=random.uniform(0.009,0.030); ph=random.uniform(0,6.28)
        t=(y0-TOPBAR)/(H*0.42)
        for x in range(0,W,3):
            D(x, y0+math.sin(x*freq+ph)*amp, random.uniform(4,12), (206,250,242), 0.030*(1-t*0.7))
    # RULE 3: distance = lower contrast, bluer, blurrier
    for i in range(900):
        x=random.uniform(0,W); y=random.uniform(TOPBAR,H)
        t=(y-TOPBAR)/(H-TOPBAR)
        D(x,y, random.uniform(0.6,2.4), (200,236,236), (0.08+0.45*random.random())*(1-t*0.55))
    for i in range(14):                                   # vague distant shapes for depth
        cx=random.uniform(0,W); cy=random.uniform(H*0.30,H*0.85)
        for q in range(70):
            D(cx+random.gauss(0,70), cy+random.gauss(0,22), random.uniform(6,18), (10,44,72), 0.030)

    # ---------- the koi ----------
    fx,fy=W*0.45, H*0.53
    LEN,DEP = 226, 76
    def prof(u):                                           # body half-height, asymmetric
        if u<-1 or u>1: return 0.0
        return (1-u*u)**0.58 * (1.0 + 0.06*math.sin(u*3.0))
    ORANGE=(236,132,54); ORANGE_D=(112,44,18); PALE=(250,238,220); WHITE=(252,250,246)
    for ix in range(-LEN, LEN):
        u=ix/LEN
        hh=prof(u)*DEP
        if hh<=0: continue
        spine = math.sin(u*1.9)*10                         # the body curves, it isn't a football
        n=int(2*hh/2.0)+1
        for k in range(n):
            v=k/max(1,n-1)
            yy=fy+spine-hh+2*hh*v
            # RULE 1: light from above. top lit warm, belly cool and pale
            if v<0.20:  c=mix(ORANGE_D, ORANGE, v/0.20)
            elif v<0.58: c=mix(ORANGE, PALE, (v-0.20)/0.38*0.7)
            else:        c=mix(PALE, WHITE, (v-0.58)/0.42)
            # koi blotches, soft-edged
            b1=math.sin(u*6.2)*math.cos(v*4.4)
            if b1>0.52: c=mix(c,(252,250,246), min(1.0,(b1-0.52)*4.0))
            b2=math.sin(u*3.6+1.9)*math.cos(v*2.8)
            if b2>0.70: c=mix(c,(38,30,28), min(1.0,(b2-0.70)*3.0))
            # caustics play across the body (RULE 4: this is what water does)
            caus=math.sin(ix*0.055 + yy*0.045 + math.sin(ix*0.02)*2.0)
            if caus>0.55: c=mix(c,(236,255,246), (caus-0.55)*1.1)
            # cool water bounce on the underside
            if v>0.82: c=mix(c,(120,180,200),(v-0.82)*1.6)
            R(fx+ix, yy, 2, 2.2, c)
    # scales suggested by directional texture, never outlined
    for i in range(2600):
        u=random.uniform(-0.97,0.97); v=random.uniform(0.05,0.95)
        hh=prof(u)*DEP; spine=math.sin(u*1.9)*10
        x=fx+u*LEN; y=fy+spine-hh+2*hh*v
        ang=-0.35+0.5*v
        L(x,y, x+math.cos(ang)*random.uniform(3,8), y+math.sin(ang)*random.uniform(1,3),
          0.8, (255,244,224) if random.random()<0.6 else (170,96,44))
    # gill plate
    for k in range(70):
        t=k/70.0
        u=-0.72+0.02*math.sin(t*3.14)
        hh=prof(u)*DEP; spine=math.sin(u*1.9)*10
        yy=fy+spine-hh*0.86+2*hh*0.86*t
        xx=fx+u*LEN + math.sin(t*3.14)*13
        D(xx,yy, 1.6, (168,86,44), 0.85)
        D(xx-3,yy, 1.2, (252,214,180), 0.40)
    # fins: overlapping, translucent at the edge
    def fin(ax,ay, ang0, length, depth, col, sweep=0.55, rays=7):
        """a swept membrane: leading edge, trailing edge, soft translucent tip"""
        for r in range(120):
            p=r/120.0                              # along the leading edge
            lx=ax+math.cos(ang0)*length*p
            ly=ay+math.sin(ang0)*length*p
            span=depth*math.sin(math.pi*min(1.0,p*1.05))**0.8      # membrane depth here
            tang=ang0+1.5708
            for k in range(26):
                q=k/26.0
                # trailing edge sweeps back as it goes out
                bend=sweep*p
                x=lx+math.cos(tang+bend)*span*q
                y=ly+math.sin(tang+bend)*span*q
                edge=max(q, p)**1.5
                D(x,y, 1.7, mix(col,(206,236,240), edge*0.80), 1.0-edge*0.78)
        for i in range(rays):                       # a few soft ray lines, never dense spokes
            p=(i+1)/(rays+1)
            lx=ax+math.cos(ang0)*length*p*0.95
            ly=ay+math.sin(ang0)*length*p*0.95
            tang=ang0+1.5708+sweep*p
            span=depth*math.sin(math.pi*min(1.0,p*1.05))**0.8
            L(lx,ly, lx+math.cos(tang)*span*0.92, ly+math.sin(tang)*span*0.92, 0.9,
              mix(col,(150,90,50),0.45))

    fin(fx+LEN-20, fy+math.sin(1.9)*10, 0.10, 128, 76, (240,164,104), sweep=0.95, rays=9)   # tail
    fin(fx-10,  fy-DEP*0.78, -1.30, 84, 34, (246,182,122), sweep=0.75, rays=6)              # dorsal
    fin(fx-LEN*0.42, fy+DEP*0.26, 0.95, 76, 28, (250,198,148), sweep=0.85, rays=5)          # pectoral
    fin(fx+LEN*0.16, fy+DEP*0.62, 1.25, 56, 22, (248,188,138), sweep=0.70, rays=4)          # pelvic
    # eye with a real cornea
    ex,ey=fx-LEN*0.80, fy+math.sin(-0.80*1.9)*10-14
    D(ex,ey,13,(250,242,226)); D(ex,ey,8.5,(40,28,20)); D(ex,ey,4.5,(10,8,8))
    D(ex-2.6,ey-3.2,2.6,(255,255,255),0.95); D(ex+3,ey+3,1.6,(150,190,200),0.6)
    L(fx-LEN*0.96, fy+6, fx-LEN*0.80, fy+11, 2.2, (120,54,30))                # mouth
    # ---------- bubbles: varied, wandering, refracting ----------
    for i in range(34):
        t=i/34.0
        bx=fx-LEN*0.98 - t*90 + math.sin(t*5.0)*26 + random.uniform(-10,10)
        by=fy-10 - t*300 + random.uniform(-14,14)
        r=random.uniform(2,9)*(0.5+t)
        blur=random.random()<0.4
        D(bx,by,r,(214,246,248), 0.20 if blur else 0.40)
        if not blur:
            D(bx-r*0.32,by-r*0.32, r*0.34,(255,255,255),0.75)
            D(bx+r*0.2,by+r*0.3, r*0.5,(150,210,220),0.20)
    # deep haze
    for i in range(300):
        D(random.uniform(0,W), H-random.uniform(0,190), random.uniform(30,95), (6,26,52), 0.045)

build()
asyncio.run(paint(a))
