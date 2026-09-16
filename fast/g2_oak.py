"""2ND GEN — THE ACORN YEAR. Branch junctions swell into the trunk, foliage in 4 levels,
acorns varied with contact shadows, grass at multiple distances."""
import asyncio, math, random
import art as A
from art import Art, mix, paint, TOPBAR, canopy
A.GEN="2ND GEN"
random.seed(707)
W,H=1380,920
a=Art(W,H,"THE ACORN YEAR")
R,L,D=a.R,a.L,a.D
GND=H*0.84
SX,SY=W*0.16, TOPBAR+90

def build():
    keys=[(0.0,(104,148,192)),(0.42,(176,196,210)),(0.74,(236,218,182)),(1.0,(252,236,200))]
    def sky(t):
        for (p,ca),(q,cb) in zip(keys,keys[1:]):
            if p<=t<=q: return mix(ca,cb,(t-p)/(q-p))
        return keys[-1][1]
    for y in range(TOPBAR,int(GND),2):
        R(0,y,W,3, sky((y-TOPBAR)/(GND-TOPBAR)))
    for k in range(70):
        u=k/70.0
        D(SX,SY, 260*(1-u)+12, (255,246,216), 0.020*(u**1.4))
    for j in range(9):
        cy=TOPBAR+random.uniform(6,(GND-TOPBAR)*0.45); cx=random.uniform(-120,W+120)
        wd=random.uniform(240,640); ht=random.uniform(10,28)
        for k in range(230):
            u=random.random(); env=math.sin(max(0,min(1,u))*math.pi)**1.4
            D(cx-wd/2+wd*u+random.uniform(-12,12), cy+math.sin(u*4+j)*ht*0.4+random.gauss(0,ht*0.42),
              ht*env*random.uniform(0.25,0.95), (255,252,246), 0.026)
    # RULE 3: far hedgerow, hazy
    for i in range(120):
        x=random.uniform(-40,W+40); h=random.uniform(20,70)
        for k in range(int(h*1.3)):
            ang=random.uniform(0,6.2832); rr=random.random()**0.6
            D(x+math.cos(ang)*h*0.45*rr, GND-8-h*0.55+math.sin(ang)*h*0.32*rr,
              random.uniform(2,5), (176,186,168), 0.40)
    for i in range(180):
        D(random.uniform(0,W), GND-random.uniform(0,60), random.uniform(50,130), (226,226,208), 0.024)
    # meadow
    for y in range(int(GND),H,2):
        t=max(0.0,(y-GND)/(H-GND))
        R(0,y,W,3, mix((160,156,96),(52,54,32), t**0.8))

    # ---------- the oak ----------
    tx,ty=W*0.47, GND+8
    BARK=(78,60,44); BARK_D=(24,18,13); BARK_L=(168,142,106)
    TRUNK_H=330
    def trunk_w(t):  return 108*(1-t*0.50)               # t 0 at base -> 1 at first fork
    # flared base + roots that MEET the ground (RULE 2)
    for i in range(44):
        ang=random.uniform(3.30,6.12); ln=random.uniform(46,150)
        x0=tx+random.uniform(-52,52)
        for k in range(24):
            p=k/24.0
            D(x0+math.cos(ang)*ln*p, ty-10+abs(math.sin(ang))*ln*p*0.26,
              11*(1-p*0.72), mix(BARK,BARK_D, 0.35+0.4*p))
    for y in range(int(ty), int(ty-TRUNK_H), -2):
        t=(ty-y)/TRUNK_H
        w=trunk_w(t)
        n=int(w/2.2)+1
        for k in range(n):
            v=k/max(1,n-1)
            shade=1.0-abs(v-0.28)*1.6
            c=mix(BARK_D, mix(BARK,BARK_L,0.55), max(0.0,shade)*0.95)
            # bark ridges that FLOW with the trunk, plus knots
            ridge=0.95+0.05*math.sin(v*7.0 + y*0.04 + math.sin(y*0.010)*2.0)
            c=mix(c,(14,10,8), 1.0-ridge)
            R(tx-w/2+w*v, y, 2.4, 2.6, c)
        if y%17==0:
            for b in range(2):
                bx=tx-w/2+w*random.uniform(0.06,0.94)
                L(bx,y,bx+random.uniform(-2,2),y-random.uniform(10,24), 0.9, mix(BARK_D,(12,9,7),0.4))
    for i in range(7):                                    # knots
        ky=ty-random.uniform(40,TRUNK_H*0.9); kw=trunk_w((ty-ky)/TRUNK_H)
        kx=tx+random.uniform(-kw*0.35,kw*0.35)
        for r in range(int(random.uniform(7,16)),0,-1):
            D(kx,ky,r, mix(BARK_D,BARK_L, r/16.0*0.6), 0.85)

    # limbs: swell where they meet the trunk, taper outward
    tips=[]
    def limb(x0,y0,ang,ln,w,depth=0):
        x1=x0+math.cos(ang)*ln; y1=y0+math.sin(ang)*ln
        steps=int(ln/3)+1
        for k in range(steps):
            p=k/steps
            x=x0+(x1-x0)*p; y=y0+(y1-y0)*p
            # swelling only right at the junction, then a strong taper to a thin tip
            sw = 1.0 + 0.32*max(0.0, 1.0-p/0.08)
            rr = w*sw*((1-p)**1.75)
            D(x,y, max(0.7,rr), mix(BARK,BARK_D, 0.22+0.40*p))
            if rr>3: D(x-rr*0.32, y-rr*0.32, rr*0.26, BARK_L, 0.22)
        if depth>=3 or ln<42:
            tips.append((x1,y1,ln)); return
        for k in range(random.randint(2,3)):
            limb(x1,y1, ang+random.uniform(-0.70,0.70), ln*random.uniform(0.56,0.76), w*0.58, depth+1)
    top=ty-TRUNK_H
    for ang,ln,w in [(-2.42,166,14),(-1.98,158,13),(-1.58,184,15),(-1.16,160,13),(-0.74,158,13),(-2.86,120,10),(-0.30,120,10)]:
        limb(tx, top+random.uniform(-10,16), ang, ln, w)
    # foliage in 4 levels of detail (RULE 3)
    for (x1,y1,ln) in tips:
        for (col,shade,sc,n) in [((66,92,42),(26,40,18),1.7,int(ln*5)),
                                 ((96,120,52),(42,58,24),1.3,int(ln*4)),
                                 ((132,146,64),(66,76,32),0.95,int(ln*3)),
                                 ((178,178,92),(96,96,44),0.62,int(ln*2))]:
            canopy(a, x1+random.uniform(-16,16), y1+random.uniform(-14,14),
                   ln*1.95*sc, ln*1.45*sc, col, n=int(n*1.25), shade=shade)
    for (x1,y1,ln) in tips[::2]:                          # a few individual leaves at the silhouette
        for i in range(14):
            ang=random.uniform(0,6.2832); rr=random.uniform(0.8,1.25)
            lx=x1+math.cos(ang)*ln*1.4*rr; ly=y1+math.sin(ang)*ln*1.05*rr
            la=random.uniform(0,6.2832); ll=random.uniform(5,11)
            c=random.choice([(150,164,76),(104,128,56),(196,190,102)])
            for q in range(4):
                p=q/4.0
                D(lx+math.cos(la)*ll*p, ly+math.sin(la)*ll*p, 2.6*(1-p*0.5), c, 0.95)

    # ---------- acorns: varied, some hanging, some falling, with contact shadows ----------
    def acorn(x,y,s=1.0,tilt=0.0,al=1.0):
        cn=random.choice([(206,150,78),(188,128,62),(220,168,96)])
        for k in range(10):
            v=k/9.0
            rr=4.6*s*(1.0-0.72*v*v)
            D(x+math.sin(tilt)*v*3*s, y+1.4*s+v*7.0*s, rr, mix(cn,(112,70,30), v*0.9), al)
        D(x-1.4*s, y+3.0*s, 1.8*s, (240,200,140), al*0.8)
        for k in range(5):
            v=k/4.0
            D(x, y-1.2*s+v*1.7*s, 5.6*s*(1.0-0.16*v), mix((104,66,30),(64,40,18), v), al)
        for i in range(4):
            D(x+random.uniform(-4,4)*s, y+random.uniform(-1.5,1.5)*s, 0.7*s, (50,32,14), al*0.8)
        D(x, y-4.2*s, 1.0*s, (86,56,26), al)
    for (x1,y1,ln) in tips:
        for i in range(random.randint(1,3)):
            ax=x1+random.uniform(-ln*1.5,ln*1.5); ay=y1+random.uniform(-ln*1.0,ln*1.2)
            for q in range(10):                              # contact shadow on the leaves behind
                D(ax+random.uniform(-5,5), ay+random.uniform(4,12), random.uniform(3,7), (22,34,14), 0.10)
            acorn(ax, ay, random.uniform(0.8,1.35), random.uniform(-0.4,0.4))
    for i in range(6):                                       # a few falling
        acorn(random.uniform(tx-250,tx+250), random.uniform(GND-200,GND-40), random.uniform(0.7,1.0), random.uniform(-0.9,0.9))
    for i in range(60):                                      # on the ground, with shadows
        gx=random.uniform(tx-330,tx+330); gy=GND+random.uniform(12,H-GND-14)
        for q in range(14):
            D(gx+random.uniform(-7,7), gy+random.uniform(5,11), random.uniform(3,8), (38,40,22), 0.08)
        acorn(gx, gy, random.uniform(0.6,1.0), random.uniform(-0.5,0.5))
    # grass at multiple distances (RULE 3)
    for i in range(4200):
        x=random.uniform(0,W); y=random.uniform(GND,H)
        t=max(0.0,(y-GND)/(H-GND))
        L(x,y, x+random.uniform(-3,3)*(1+t), y-random.uniform(4,10)*(0.5+2.0*t), 0.5+1.2*t,
          mix((196,188,112),(48,52,30), t*1.05))
    for i in range(320):                                     # fallen leaves
        D(random.uniform(0,W), GND+random.uniform(4,H-GND), random.uniform(2,6),
          random.choice([(176,132,54),(146,102,40),(198,162,74)]), 0.92)
    # tree's own shadow, soft and directional
    for i in range(1400):
        D(tx+random.uniform(-70,330), GND+random.uniform(2,96), random.uniform(8,22), (46,48,28), 0.022)

build()
asyncio.run(paint(a))
