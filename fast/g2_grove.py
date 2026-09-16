"""2ND GEN — FIRST LIGHT IN THE GROVE.
Varied trunks + aggressive occlusion + volumetric broken rays + layered forest floor."""
import asyncio, math, random
import art as A
from art import Art, mix, paint, TOPBAR
A.GEN="2ND GEN"
random.seed(202)
W,H=1360,900
a=Art(W,H,"FIRST LIGHT IN THE GROVE")
R,L,D=a.R,a.L,a.D

def build():
    # fog: brightest where the light enters upper-left, deepening to the floor
    for y in range(TOPBAR,H,2):
        t=(y-TOPBAR)/(H-TOPBAR)
        R(0,y,W,3, mix((204,200,176),(30,36,30), t**1.20))
    for k in range(90):
        u=k/90.0
        D(W*0.26, TOPBAR+40, 620*(1-u)+30, (240,226,172), 0.030*(u**1.5))

    # ---------- trunks, back to front: each layer darker, sharper, and OCCLUDING ----------
    def trunk(x, wdt, depth, lean, cut_top):
        """depth 0 far/hazy .. 1 near/dark"""
        base = mix((150,150,138),(30,26,22), depth)
        lit  = mix((214,210,190),(110,92,70), depth)
        top  = TOPBAR - 30 + cut_top
        for y in range(int(top), H, 3):
            t=(y-top)/(H-top)
            w = wdt*(0.70+0.55*t)
            xc = x + lean*t*110 + math.sin(t*2.2+x)*wdt*0.10      # RULE 5: slight lean + sway
            n=int(w/2.4)+1
            for k in range(n):
                v=k/max(1,n-1)
                shade = 1.0-abs(v-0.28)*2.0                        # tighter falloff = rounder
                c=mix(base, lit, max(0.0,shade)*0.95)
                if v<0.10: c=mix(c,(250,242,214), (0.10-v)*3.2)     # lit rim
                if v>0.86: c=mix(c,(14,12,10), (v-0.86)*2.6)        # core shadow
                c=mix(c,(206,204,186),(1-depth)*0.62*(1-t*0.30))   # fog wash by distance
                R(xc-w/2+w*v, y, 3, 4, c)
            if depth>0.5 and y%11==0:                              # bark only where it's readable
                for b in range(3):
                    bx=xc-w/2+w*random.uniform(0.10,0.90)
                    L(bx,y,bx+random.uniform(-2,2),y+random.uniform(9,22), 1.0, mix(base,(10,8,6),0.6))
        # ---- limbs with dense needle sprays: short, drooping, clearly attached ----
        nlimb=int(7+9*(1-depth))
        for i in range(nlimb):
            ft=random.random()**1.7                                  # biased toward the top
            ly = top + (H-top)*ft*0.50
            lt = (ly-top)/(H-top)
            lxc = x + lean*lt*110 + math.sin(lt*2.2+x)*wdt*0.10
            side = random.choice((-1,1))
            ln = min(140.0, (wdt*1.0 + random.uniform(24,80))*(1.15-lt))
            droop = random.uniform(0.30,0.62)
            fog = (1-depth)*0.60
            limb_c = mix(mix(base,(18,14,10),0.55),(206,204,186), fog)
            needle = mix(mix((34,56,34),(96,126,70), random.random()*0.8), (208,208,188), fog)
            # the limb itself, tapering and sagging
            px,py=lxc,ly
            segs=14
            for k in range(segs):
                p=(k+1)/segs
                nx=lxc+side*ln*p
                ny=ly+droop*ln*(p*p)
                L(px,py,nx,ny, max(0.8, 3.4*(1-p)*(0.45+depth)), limb_c)
                # dense needle spray hanging off this segment
                for q in range(int(16*(1-lt)+7)):
                    sx2=nx+random.uniform(-5,5); sy2=ny+random.uniform(-3,5)
                    na=random.uniform(0.55,1.35)*(1 if random.random()<0.5 else -1)
                    nl=random.uniform(6,17)*(1-lt*0.5)
                    L(sx2,sy2, sx2+math.sin(na)*nl*0.7, sy2+abs(math.cos(na))*nl, 0.9, needle)
                px,py=nx,ny
    far=[(W*0.04,15,0.10),(W*0.14,12,0.08),(W*0.23,17,0.13),(W*0.34,11,0.07),(W*0.44,16,0.12),
         (W*0.55,13,0.09),(W*0.64,18,0.14),(W*0.75,12,0.08),(W*0.86,15,0.11),(W*0.96,13,0.09)]
    for x,w,d in far: trunk(x,w,d, random.uniform(-0.06,0.06), random.uniform(0,150))
    for i in range(800):
        D(random.uniform(0,W), random.uniform(TOPBAR,H), random.uniform(50,130), (208,206,188), 0.013)
    mid=[(W*0.09,38,0.44),(W*0.30,44,0.48),(W*0.52,40,0.45),(W*0.71,46,0.50),(W*0.92,36,0.42)]
    for x,w,d in mid: trunk(x,w,d, random.uniform(-0.08,0.08), random.uniform(0,90))
    for i in range(600):
        D(random.uniform(0,W), random.uniform(TOPBAR,H), random.uniform(36,100), (200,200,184), 0.011)
    near=[(W*0.015,104,0.90),(W*0.40,124,0.94),(W*0.99,112,0.92)]
    for x,w,d in near: trunk(x,w,d, random.uniform(-0.04,0.04), 0)

    # ---------- needle canopy overhead ----------
    for (col,cnt,rad,fog) in [((150,156,120),16,(90,190),0.55),((96,116,72),14,(80,170),0.28),((40,58,36),12,(70,150),0.0)]:
        for i in range(cnt):
            cx=random.uniform(-80,W+80); cy=TOPBAR+random.uniform(-40, (H-TOPBAR)*0.22)
            c=mix(col,(214,212,192),fog)
            for q in range(int(random.uniform(120,240))):
                ang=random.uniform(0,6.2832); rr=random.random()**0.55
                px=cx+math.cos(ang)*random.uniform(*rad)*rr
                py=cy+math.sin(ang)*random.uniform(*rad)*0.55*rr
                if random.random()<0.18: continue
                na=random.uniform(0.3,2.8)
                nl=random.uniform(5,15)
                L(px,py, px+math.cos(na)*nl, py+abs(math.sin(na))*nl, 0.9, c)

    # ---------- volumetric rays: soft -> broken -> variable -> fading ----------
    for i in range(34):
        x0=random.uniform(-W*0.15, W*0.70); ang=1.00+random.uniform(-0.09,0.09)
        wd=random.uniform(14,58)
        for k in range(130):
            u=k/130.0
            x=x0+math.cos(ang-0.38)*1700*u*0.52
            y=TOPBAR+math.sin(ang)*1700*u*0.58
            if y>H: break
            broken = 0.25+0.75*max(0.0, math.sin(u*5.5+i*1.3))     # the beam breaks up
            D(x,y, wd*(0.30+u*1.30), (255,244,198), 0.030*broken*(1-u*0.80))
    for i in range(1300):                                          # the dust that MAKES it visible
        u=random.random()
        x=random.uniform(0,W*0.95); y=TOPBAR+u*(H-TOPBAR)
        if random.random()>0.45+0.55*max(0.0,math.sin(x*0.004+u*3.0)): continue
        D(x,y, random.uniform(0.6,2.0), (255,248,214), random.uniform(0.10,0.55)*(1-u*0.45))

    # ---------- forest floor in layers ----------
    FL=H*0.80
    for y in range(int(FL),H,2):
        t=max(0.0,(y-FL)/(H-FL))
        R(0,y,W,3, mix((70,68,52),(16,18,14), t**0.8))
    for i in range(900):                                           # distant leaf litter
        x=random.uniform(0,W); y=FL+random.uniform(0,(H-FL)*0.45)
        D(x,y, random.uniform(2,5), mix((96,86,54),(58,56,38), random.random()), 0.7)
    for i in range(260):                                           # moss patches
        cx=random.uniform(0,W); cy=FL+random.uniform(0,(H-FL)*0.8)
        for q in range(26):
            D(cx+random.gauss(0,16), cy+random.gauss(0,7), random.uniform(2,5), (58,84,44), 0.45)
    for i in range(150):                                           # fallen branches
        x=random.uniform(0,W); y=FL+random.uniform(6,H-FL)
        ln=random.uniform(20,90); ang=random.uniform(-0.4,0.4)
        L(x,y, x+math.cos(ang)*ln, y+math.sin(ang)*ln, random.uniform(1.4,3.2), (44,36,26))
    clumps=[(random.uniform(-40,W+40), random.uniform(0.25,1.0)) for _ in range(16)]
    for (cx,size) in clumps:
        for i in range(int(26*size)+6):
            x=cx+random.gauss(0,58*size)
            depth=random.random()
            y=H-random.uniform(0,(H-FL)*0.95)*(0.4+0.6*depth)
            fl=random.uniform(30,120)*size*(0.6+0.8*depth)
            ang=random.uniform(-2.05,-1.10)
            col=mix(mix((26,44,26),(104,138,60), random.random()), (150,170,120), (1-depth)*0.45)
            ex,ey=x+math.cos(ang)*fl, y+math.sin(ang)*fl
            L(x,y,ex,ey, 1.0+2.0*depth, col)
            for k in range(9):
                p=k/9.0; px=x+(ex-x)*p; py=y+(ey-y)*p; lw=fl*0.22*(1-p)
                w=0.8+1.4*depth
                L(px,py,px-lw,py-lw*0.45,w,col); L(px,py,px+lw,py-lw*0.45,w,col)
    # green bounce light up onto the near trunks (RULE 2)
    for i in range(300):
        D(random.uniform(0,W), FL-random.uniform(0,90), random.uniform(14,40), (96,120,64), 0.020)

build()
asyncio.run(paint(a))
