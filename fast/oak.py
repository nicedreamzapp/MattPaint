import asyncio, math, random
from art import Art, mix, paint, TOPBAR, canopy
random.seed(44)
W,H=1360,900
a=Art(W,H,"THE ACORN YEAR")
R,L,D=a.R,a.L,a.D
GND=H*0.82
def build():
    # warm autumn sky
    keys=[(0.0,(96,140,186)),(0.40,(168,190,208)),(0.70,(232,214,178)),(1.0,(250,232,194))]
    def sky(t):
        for (p,ca),(q,cb) in zip(keys,keys[1:]):
            if p<=t<=q: return mix(ca,cb,(t-p)/(q-p))
        return keys[-1][1]
    for y in range(TOPBAR,int(GND),2):
        R(0,y,W,3, sky((y-TOPBAR)/(GND-TOPBAR)))
    for j in range(8):
        cy=TOPBAR+random.uniform(10,(GND-TOPBAR)*0.5); cx=random.uniform(-100,W+100)
        wd=random.uniform(240,620); ht=random.uniform(12,32)
        for k in range(200):
            u=random.random(); env=math.sin(max(0,min(1,u))*math.pi)**1.4
            D(cx-wd/2+wd*u+random.uniform(-12,12), cy+math.sin(u*4+j)*ht*0.4+random.gauss(0,ht*0.4),
              ht*env*random.uniform(0.25,0.9), (255,252,246), 0.028)
    # meadow
    for y in range(int(GND),H,2):
        t=max(0.0,(y-GND)/(H-GND))
        R(0,y,W,3, mix((150,146,88),(58,58,34), t**0.85))
    for i in range(2600):
        x=random.uniform(0,W); y=random.uniform(GND,H)
        t=max(0.0,(y-GND)/(H-GND))
        L(x,y,x+random.uniform(-2,2),y-random.uniform(4,15), random.uniform(0.5,1.1),
          mix((206,192,116),(52,54,32), t*1.1))
    # ---- the oak ----
    tx,ty=W*0.46, GND+6
    BARK=(74,58,44); BARK_D=(26,20,15); BARK_L=(146,124,94)
    # trunk: wide base flaring into roots
    for y in range(int(ty), int(ty-300), -2):
        t=(ty-y)/300.0
        wdt=96*(1-t*0.52)
        n=int(wdt/2.2)+1
        for k in range(n):
            v=k/max(1,n-1)
            shade=1.0-abs(v-0.32)*1.7
            c=mix(BARK_D, BARK_L, max(0.0,shade)*0.9)
            c=mix(c, BARK, 0.35)
            R(tx-wdt/2+wdt*v, y, 2.6, 2.6, c)
    # root flare
    for i in range(34):
        ang=random.uniform(3.34,6.08)
        ln=random.uniform(40,120)
        x0,y0=tx+random.uniform(-46,46), ty-8
        for k in range(20):
            t=k/20.0
            D(x0+math.cos(ang)*ln*t, y0+abs(math.sin(ang))*ln*t*0.30, 9*(1-t*0.7), mix(BARK,BARK_D,0.4))
    # bark texture
    for i in range(900):
        yy=random.uniform(ty-296, ty)
        t=(ty-yy)/300.0; wdt=96*(1-t*0.52)
        xx=tx+random.uniform(-wdt/2, wdt/2)
        L(xx,yy,xx+random.uniform(-2,2),yy-random.uniform(8,26), random.uniform(0.7,1.5), mix(BARK_D,(10,8,6),0.4))
    # limbs, forking upward and out
    limbs=[]
    def limb(x0,y0,ang,ln,w,depth=0):
        x1=x0+math.cos(ang)*ln; y1=y0+math.sin(ang)*ln
        steps=int(ln/4)+1
        for k in range(steps):
            t=k/steps
            x=x0+(x1-x0)*t; y=y0+(y1-y0)*t
            D(x,y, w*(1-t*0.32), mix(BARK,BARK_D,0.25+0.3*t))
            D(x-w*0.25,y-w*0.25, w*0.30*(1-t*0.3), BARK_L, 0.35)
        if depth>=3 or ln<40:
            limbs.append((x1,y1,ln))
            return
        for k in range(random.randint(2,3)):
            limb(x1,y1, ang+random.uniform(-0.72,0.72), ln*random.uniform(0.58,0.76), w*0.66, depth+1)
    top=ty-292
    for ang,ln,w in [(-2.35,150,26),(-1.62,168,30),(-0.85,152,26),(-2.85,118,20),(-0.36,120,20)]:
        limb(tx, top, ang, ln, w)
    # canopy masses at the limb tips
    for (x1,y1,ln) in limbs:
        for (col,shade,sc) in [((78,102,48),(30,44,18),1.5),((104,128,56),(48,62,26),1.2),((140,152,70),(74,82,36),0.95),((176,174,88),(100,100,44),0.7)]:
            for rep in range(2):
                canopy(a, x1+random.uniform(-34,34), y1+random.uniform(-30,30),
                       ln*1.5*sc, ln*1.1*sc, col, n=int(ln*6*sc), shade=shade)
    # ---- acorns: on the branches and scattered below ----
    def acorn(x,y,s=1.0,al=1.0):
        # nut: egg shape, widest just under the cap, tapering to a tip
        for k in range(10):
            v=k/9.0
            rr=4.6*s*(1.0-0.72*v*v)
            D(x, y+1.4*s+v*7.0*s, rr, mix((206,150,78),(118,74,32), v*0.9), al)
        D(x-1.4*s, y+3.0*s, 1.8*s, (238,196,132), al*0.8)      # highlight
        # cap
        for k in range(5):
            v=k/4.0
            D(x, y-1.2*s+v*1.7*s, 5.6*s*(1.0-0.16*v), mix((104,66,30),(66,42,18), v), al)
        for i in range(4):
            D(x+random.uniform(-4,4)*s, y+random.uniform(-1.5,1.5)*s, 0.7*s, (50,32,14), al*0.8)
        D(x, y-4.0*s, 1.0*s, (86,56,26), al)                    # stalk

    for (x1,y1,ln) in limbs:
        for i in range(random.randint(3,6)):
            acorn(x1+random.uniform(-ln*0.9,ln*0.9), y1+random.uniform(-ln*0.6,ln*0.8), random.uniform(0.85,1.3))
    for i in range(70):
        acorn(random.uniform(tx-330,tx+330), GND+random.uniform(10,H-GND-16), random.uniform(0.6,1.0))
    # fallen leaves
    for i in range(340):
        x=random.uniform(0,W); y=GND+random.uniform(4,H-GND)
        D(x,y, random.uniform(2,5), random.choice([(178,132,54),(146,102,40),(196,160,72)]), 0.9)
    # tree shadow
    for i in range(900):
        D(tx+random.uniform(-300,300), GND+random.uniform(2,86), random.uniform(9,22), (52,50,30), 0.020)

build()
asyncio.run(paint(a))
