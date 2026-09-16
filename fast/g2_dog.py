"""2ND GEN — THE LONG WAIT. Real contact with the ground, tail with thickness,
body not pure black, sunset haze and colour bounce."""
import asyncio, math, random
import art as A
from art import Art, mix, paint, TOPBAR, silhouette_rim
A.GEN="2ND GEN"
random.seed(606)
W,H=1340,880
a=Art(W,H,"THE LONG WAIT")
R,L,D=a.R,a.L,a.D
HOR=H*0.72

def build():
    keys=[(0.0,(30,44,86)),(0.26,(96,86,124)),(0.50,(200,116,98)),(0.74,(248,168,92)),(1.0,(255,214,138))]
    def sky(t):
        for (p,ca),(q,cb) in zip(keys,keys[1:]):
            if p<=t<=q: return mix(ca,cb,(t-p)/(q-p))
        return keys[-1][1]
    for y in range(TOPBAR,int(HOR),2):
        R(0,y,W,3, sky((y-TOPBAR)/(HOR-TOPBAR)))
    SX,SY=W*0.70, HOR-46
    for k in range(90):
        u=k/90.0
        D(SX,SY, 200*(1-u)+8, mix(sky((SY-TOPBAR)/(HOR-TOPBAR)),(255,246,224),0.25+0.7*(u**2)), 0.055*((u**2)**1.3))
    D(SX,SY,14,(255,252,238),1.0)
    # clouds lit from beneath by the low sun
    for j in range(11):
        cy=TOPBAR+random.uniform(8,(HOR-TOPBAR)*0.66); cx=random.uniform(-120,W+120)
        wd=random.uniform(220,620); ht=random.uniform(9,28)
        for k in range(240):
            u=random.random(); env=math.sin(max(0,min(1,u))*math.pi)**1.35
            px=cx-wd/2+wd*u+random.uniform(-12,12)
            py=cy+math.sin(u*4+j)*ht*0.42+random.gauss(0,ht*0.42)
            under=max(0.0,(py-cy)/(ht*1.1))
            base=mix((188,150,168),(255,198,140), 1-under)
            D(px,py, ht*env*random.uniform(0.25,0.95), base, 0.028)
    # haze stacked on the horizon
    for i in range(260):
        D(random.uniform(0,W), HOR-random.uniform(0,52), random.uniform(50,140), (255,206,150), 0.020)

    def hill(x): return HOR - 40 - 56*math.sin(x/W*2.1+0.5) - 14*math.sin(x/W*6.6)
    for x in range(0,W,2):
        y=hill(x); n=int((H-y)/3)+1
        for k in range(n):
            v=k/max(1,n-1)
            R(x,y+(H-y)*v,2,4, mix((52,44,34),(9,9,10), v**0.55))
    # backlit grass: bright rim on the tips, dark at the base
    for i in range(4200):
        x=random.uniform(0,W); base=hill(x)
        y=base+random.uniform(0,H-base)
        t=(y-base)/max(1,(H-base))
        tip=mix((236,182,104),(92,64,36), t*1.1)
        L(x,y,x+random.uniform(-3,3),y-random.uniform(6,22)*(1-t*0.4), random.uniform(0.6,1.3),
          mix(tip,(18,16,14), t*0.75))

    # ---------- the dog ----------
    dx,dy=W*0.38, hill(W*0.38)+8
    BODY=(22,20,20); RIM=(255,208,138)
    parts=[]
    def blob(cx,cy,rx,ry,col=BODY):
        yy=-ry
        while yy<=ry:
            w=rx*math.sqrt(max(0.0,1-(yy/ry)**2))
            R(cx-w, cy+yy, 2*w, 2.4, col); yy+=2
    def part(cx,cy,rx,ry):
        blob(cx,cy,rx,ry); parts.append((cx,cy,rx,ry))
    S=1.70
    part(dx-12,     dy-42*S,  33*S, 33*S)     # rear haunch
    part(dx+20*S,   dy-68*S,  29*S, 39*S)     # ribcage
    part(dx+38*S,   dy-100*S, 28*S, 31*S)     # chest/shoulders
    part(dx+48*S,   dy-126*S, 16*S, 14*S)     # neck
    part(dx+60*S,   dy-148*S, 19*S, 17*S)     # skull
    part(dx+82*S,   dy-144*S, 14*S,  9*S)     # muzzle
    part(dx+50*S,   dy-166*S, 6*S,  12*S); part(dx+64*S, dy-168*S, 5.5*S, 11*S)   # ears
    for lx,off in ((dx+34*S,0.0),(dx+50*S,1.0)):     # front legs
        for k in range(34):
            t=k/34.0
            D(lx+t*4*S+off*2, dy-92*S+t*92*S, 5.0*S*(1-t*0.30), BODY)
    part(dx+4*S, dy-9*S, 15*S, 7*S)           # rear foot, flat on the ground
    for k in range(90):                        # tail with real thickness, resting on the ground
        t=k/90.0
        x=dx-22*S-math.sin(t*1.9)*32*S*t
        y=dy-38*S+t*38*S
        D(x, min(y, dy-2), 7.6*S*(1-t*0.42), BODY)
    # RULE 5: internal value so it isn't a flat cutout
    for i in range(600):
        cx,cy,rx,ry=random.choice(parts)
        ang=random.uniform(0,6.2832); rr=random.random()**0.6
        D(cx+math.cos(ang)*rx*rr*0.82, cy+math.sin(ang)*ry*rr*0.82, random.uniform(1.6,4.2),
          mix(BODY,(52,46,42),0.6), 0.10)
    silhouette_rim(a, parts, SX, SY, RIM, w=2.2, dens=210, spread=1.28, alpha=0.88, fuzz=True)
    # RULE 2: contact — grass rises over the feet, shadow pools beneath, ground darkens
    for i in range(420):
        gx=dx+random.uniform(-60*S,80*S); gy=dy-random.uniform(0,16)
        L(gx,gy, gx+random.uniform(-3,3), gy-random.uniform(8,26), 1.0, (92,70,40))
    for i in range(500):
        D(dx+random.uniform(-70*S,90*S), dy+random.uniform(-4,22), random.uniform(6,18), (14,12,12), 0.035)
    # warm bounce from the lit grass — outer silhouette ONLY (internal seams must never light)
    def outer(x,y,skip):
        for (ox,oy,orx,ory) in parts:
            if (ox,oy,orx,ory)==skip: continue
            if ((x-ox)/orx)**2+((y-oy)/ory)**2 < 1.06: return False
        return True
    for prt in parts:
        cx,cy,rx,ry=prt
        for i in range(40):
            ang=random.uniform(0.5,2.6)
            x=cx+math.cos(ang)*rx*0.94; y=cy+math.sin(ang)*ry*0.94
            if not outer(x,y,prt): continue
            D(x,y, 2.2, (150,96,50), 0.16)
    for i in range(320):
        D(random.uniform(0,W), random.uniform(TOPBAR,H*0.95), random.uniform(0.6,1.9), (255,226,176), random.uniform(0.12,0.55))

build()
asyncio.run(paint(a))
