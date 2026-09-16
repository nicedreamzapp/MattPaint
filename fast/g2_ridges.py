"""2ND GEN — DAWN RIDGES. Atmospheric perspective in explicit steps, texture that follows
the terrain, a forest that isn't repetitive, real scattering around the sun."""
import asyncio, math, random
import art as A
from art import Art, mix, paint, TOPBAR
A.GEN="2ND GEN"
random.seed(808)
W,H=1380,900
a=Art(W,H,"DAWN RIDGES")
R,L,D=a.R,a.L,a.D
HOR=H*0.74
SX,SY=W*0.62, HOR*0.30

def build():
    keys=[(0.0,(62,92,150)),(0.30,(128,148,186)),(0.56,(210,186,180)),(0.80,(248,202,158)),(1.0,(255,230,190))]
    def sky(t):
        for (p,ca),(q,cb) in zip(keys,keys[1:]):
            if p<=t<=q: return mix(ca,cb,(t-p)/(q-p))
        return keys[-1][1]
    for y in range(TOPBAR,int(HOR),2):
        R(0,y,W,3, sky((y-TOPBAR)/(HOR-TOPBAR)))
    # real scattering: tight core, wide faint halo, both fading to nothing
    for k in range(110):
        u=k/110.0
        D(SX,SY, 130*(1-u)+6, mix(sky(max(0.0,min(1.0,SY/HOR))),(255,250,238),0.25+0.70*(u**2)), 0.052*((u**2)**1.25))
    for k in range(60):
        u=k/60.0
        D(SX,SY, 400*(1-u)+40, mix(sky(max(0.0,min(1.0,SY/HOR))),(255,238,212),0.22), 0.0045*((u**2)**1.1))
    D(SX,SY,11,(255,254,250),1.0)
    for j in range(9):
        cy=TOPBAR+random.uniform(6,(HOR-TOPBAR)*0.55); cx=random.uniform(-120,W+120)
        wd=random.uniform(230,620); ht=random.uniform(9,26)
        for k in range(230):
            u=random.random(); env=math.sin(max(0,min(1,u))*math.pi)**1.4
            px=cx-wd/2+wd*u+random.uniform(-12,12)
            py=cy+math.sin(u*4+j)*ht*0.4+random.gauss(0,ht*0.4)
            under=max(0.0,(py-cy)/(ht*1.1))
            D(px,py, ht*env*random.uniform(0.25,0.95), mix((216,196,198),(255,224,190),1-under), 0.026)

    # ---------- ridges: explicit atmospheric steps, texture follows the terrain ----------
    def mk(peaks,noise,seed):
        rnd=random.Random(seed); ph=[rnd.uniform(0,6.3) for _ in range(3)]
        def f(x):
            y=1e9
            for (px,py,sl,sr) in peaks:
                y=min(y, py+((px-x)*sl if x<px else (x-px)*sr))
            return y+(math.sin(x*0.05+ph[0])*0.6+math.sin(x*0.13+ph[1])*0.3+math.sin(x*0.37+ph[2])*0.1)*noise
        return f
    # farther = lighter + bluer + lower contrast (explicit steps, per the note)
    layers=[
      (mk([(W*0.18,HOR*0.50,0.20,0.18),(W*0.54,HOR*0.42,0.18,0.17),(W*0.86,HOR*0.48,0.17,0.20)],7,1),
       (202,206,224),(178,186,212), 0.10),
      (mk([(W*0.08,HOR*0.64,0.24,0.20),(W*0.42,HOR*0.56,0.20,0.20),(W*0.76,HOR*0.60,0.19,0.24)],8,2),
       (170,178,206),(140,150,186), 0.18),
      (mk([(W*0.04,HOR*0.78,0.28,0.24),(W*0.34,HOR*0.70,0.24,0.24),(W*0.68,HOR*0.74,0.22,0.28),(W*0.96,HOR*0.68,0.24,0.26)],8,3),
       (126,134,168),(92,100,138), 0.30),
      (mk([(W*0.14,HOR*0.92,0.32,0.28),(W*0.50,HOR*0.84,0.28,0.28),(W*0.86,HOR*0.88,0.26,0.32)],7,4),
       (78,84,116),(46,52,78), 0.48),
      (mk([(W*0.30,HOR*1.04,0.38,0.34),(W*0.72,HOR*0.98,0.32,0.38)],6,5),
       (42,46,66),(18,20,32), 0.70),
    ]
    for li,(f,ctop,cbot,contrast) in enumerate(layers):
        base_y = H + 20            # every layer runs to the bottom edge; nearer ones cover farther
        x=0.0
        while x<W:
            y=f(x)
            n=int((base_y-y)/3)+1
            for k in range(n):
                v=k/max(1,n-1)
                c=mix(ctop,cbot, v*contrast*1.4)
                R(x, y+(base_y-y)*v, 3, 4, c)
            # texture follows the terrain: gullies run DOWN the slope
            if li>=2 and random.random()<0.30:
                gx=x; gy=f(gx)
                slope = (f(min(W-1,gx+8))-f(max(0,gx-8)))/16.0
                for k in range(int(random.uniform(6,22))):
                    p=k/22.0
                    D(gx+slope*p*40+random.uniform(-2,2), gy+p*random.uniform(20,80),
                      random.uniform(1.0,2.4), mix(cbot,(12,14,22),0.4), 0.18)
            x+=3
        # snow only on the true tops, following the ridge
        if li>=2:
            x=0.0
            while x<W:
                y=f(x)
                thresh=HOR*(0.58+0.05*li)
                if y < thresh:
                    d=min(26.0, (thresh-y)*0.30)          # shallow cap only
                    for k in range(max(1,int(d/2))):
                        v=k/max(1,int(d/2))
                        D(x+random.uniform(-1,1), y+k*2, 1.1,
                          mix((236,238,246),mix(ctop,cbot,0.5), v), 0.35*(1-v))
                x+=3
        # haze BETWEEN layers: this is what sells the distance
        for i in range(420):
            hx=random.uniform(0,W)
            D(hx, f(hx)+random.uniform(4,54), random.uniform(12,30),
              mix((242,226,220),(206,212,230), li/5.0), 0.016)

    # ---------- forest: varied heights, gaps, clusters, dead trees ----------
    base=layers[-1][0]
    clumps=[(random.uniform(-40,W+40), random.uniform(0.4,1.0)) for _ in range(14)]
    for (cxc,size) in clumps:
        for i in range(int(30*size)+8):
            x=cxc+random.gauss(0,70*size)
            if x<-30 or x>W+30: continue
            gy=base(x)
            h=random.uniform(26,96)*size*random.uniform(0.6,1.4)
            dead = random.random()<0.08
            col=(14,16,24) if not dead else (52,46,40)
            L(x,gy+10,x,gy+10-h*0.92, random.uniform(1.4,3.0), col)
            if not dead:
                tiers=int(8+random.random()*7)
                for k in range(tiers):
                    t=k/tiers
                    wdt=h*random.uniform(0.17,0.27)*(1-t*0.85)
                    yy=gy+10-h*(0.16+0.84*t)
                    L(x,yy, x-wdt, yy+h*0.05, max(0.7,1.8*(1-t*0.5)), col)
                    L(x,yy, x+wdt, yy+h*0.05, max(0.7,1.8*(1-t*0.5)), col)
            else:
                for k in range(5):
                    ang=random.uniform(-2.4,-0.7)
                    L(x,gy+10-h*random.uniform(0.4,0.9), x+math.cos(ang)*h*0.3, gy+10-h*random.uniform(0.5,0.95), 1.2, col)
    for i in range(500):                                   # mist sitting in the treeline
        D(random.uniform(0,W), H-random.uniform(0,150), random.uniform(24,70), (218,214,220), 0.022)
    for i in range(300):
        D(random.uniform(0,W), random.uniform(TOPBAR,H*0.9), random.uniform(0.6,1.8), (255,246,220), random.uniform(0.10,0.45))

build()
asyncio.run(paint(a))
