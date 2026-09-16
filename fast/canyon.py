"""2nd gen. Built on the five rules: believable light first, everything touching something,
three levels of detail, material-specific response, subtle imperfection."""
import asyncio, math, random
import art as A
from art import Art, mix, paint, TOPBAR
A.GEN="2ND GEN"
random.seed(101)
W,H=1360,900
a=Art(W,H,"THE NARROWS")
R,L,D=a.R,a.L,a.D

def build():
    # ---------- RULE 3: three depth planes, each with its own contrast + haze ----------
    # background: the lit slot far above/behind, bleached and low contrast
    for y in range(TOPBAR,H,2):
        t=(y-TOPBAR)/(H-TOPBAR)
        R(0,y,W,3, mix((236,206,158),(28,16,14), t**0.62))
    # the sky slit at the top, blown out
    for k in range(90):
        u=k/90.0
        D(W*0.52, TOPBAR-20, 320*(1-u)+20, mix((255,246,226),(255,214,150),u), 0.030*(u**1.4))

    # ---------- sandstone walls as RECEDING LAYERS with sinuous carved edges ----------
    # each layer is closer to the camera, darker, higher contrast (RULE 3)
    LAYERS=9
    for li in range(LAYERS):
        p = li/(LAYERS-1)                      # 0 = deepest/farthest, 1 = nearest
        # the slot is widest near the camera and pinches with depth
        half_base = W*0.055 + W*0.30*p
        # warm bounced light reaches deep but weakens fast (RULE 1)
        lit_hi = mix((248,196,132),(255,224,176), 1-p)
        lit_lo = mix((70,30,18),(150,74,34), 1-p)
        dark   = mix((16,8,6),(46,20,12), 1-p)
        for side in (-1,1):
            ph = 1.7*li + (0 if side<0 else 2.4)
            for y in range(TOPBAR, H, 2):
                t=(y-TOPBAR)/(H-TOPBAR)
                # sinuous carved edge: the rock waves in and out as it descends
                wave = math.sin(t*4.1+ph)*W*0.045 + math.sin(t*9.3+ph*1.7)*W*0.018
                edge = W*0.5 + side*(half_base + wave + t*W*0.05*p)
                # light dies with depth into the slot (t) and with distance from the lit edge
                lit = max(0.0, 1.0 - t*(1.05+0.5*p))**1.35
                steps=54
                for k in range(steps):
                    v=k/steps
                    x = edge + side*v*(W*0.26)
                    if x<-40 or x>W+40: break
                    fall = max(0.0, 1.0-v*2.0)**1.1
                    c = mix(dark, mix(lit_lo, lit_hi, min(1.0,lit)), min(1.0, lit*(0.22+0.9*fall)))
                    # RULE 5: sedimentary banding that FOLLOWS the carved form, plus grain
                    band  = 0.88+0.12*math.sin((y*0.05 + wave*0.05 + v*2.6 + ph))
                    grain = 0.965+0.035*math.sin(y*0.63 + v*27.0 + ph)
                    c = mix(c,(14,6,5), 1.0-band*grain)
                    R(x, y, W*0.26/steps+2, 2.6, c)
                # occasional flow line carved along the rock
                if int(y)%11==0 and random.random()<0.5:
                    fx=edge+side*random.uniform(4, W*0.16)
                    L(fx,y, fx+side*random.uniform(14,64), y+random.uniform(5,18), 1.0,
                      mix(dark,(10,5,4),0.4))
            # the lit lip where this layer catches the shaft
            for y in range(TOPBAR, int(TOPBAR+(H-TOPBAR)*0.45), 3):
                t=(y-TOPBAR)/(H-TOPBAR)
                wave = math.sin(t*4.1+ph)*W*0.045 + math.sin(t*9.3+ph*1.7)*W*0.018
                edge = W*0.5 + side*(half_base + wave + t*W*0.05*p)
                glow = max(0.0, 1.0-t*2.2)**1.4
                if glow<=0.02: continue
                D(edge, y, 3.0, mix((255,226,178),(255,246,224), glow), 0.30*glow)
    # ---------- RULE 1: the shaft of light, volumetric and broken ----------
    for i in range(34):
        x0=W*0.52+random.uniform(-70,70)
        ang=1.30+random.uniform(-0.09,0.09)
        wd=random.uniform(14,52)
        for k in range(150):
            u=k/150.0
            x=x0+math.cos(ang-0.32)*1700*u*0.42
            y=TOPBAR+math.sin(ang)*1700*u*0.60
            if y>H: break
            broken=0.35+0.65*max(0.0,math.sin(u*6.0+i))
            D(x,y, wd*(0.3+u*1.35), (255,232,190), 0.011*broken*(1-u*0.86))
    # dust hanging in the beam (this is WHY the beam is visible)
    for i in range(1500):
        u=random.random()
        x=W*0.52+math.cos(1.0)*1700*u*0.42+random.gauss(0,70*(0.4+u))
        y=TOPBAR+math.sin(1.30)*1700*u*0.60+random.gauss(0,26)
        if y<TOPBAR or y>H or x<0 or x>W: continue
        D(x,y, random.uniform(0.6,2.2), (255,240,206), random.uniform(0.10,0.55)*(1-u*0.6))

    # ---------- the floor: RULE 2, everything touches something ----------
    FL=H*0.86
    for y in range(int(FL),H,2):
        t=max(0.0,(y-FL)/(H-FL))
        R(0,y,W,3, mix((150,86,44),(40,18,12), t**0.7))
    # sand ripples catching the shaft, with contact shadow under each wall
    for i in range(900):
        x=random.uniform(0,W); y=random.uniform(FL,H)
        d=abs(x-W*0.52)/(W*0.5)
        lit=max(0.0,1.0-d*1.5)
        L(x,y, x+random.uniform(8,34), y+random.uniform(-1,1), random.uniform(0.6,1.4),
          mix((60,28,16),(238,186,124), lit*0.8*random.uniform(0.5,1.0)))
    for side,x0 in ((-1,W*0.14),(1,W*0.86)):
        for i in range(300):
            D(x0+side*random.uniform(-30,120), FL+random.uniform(0,H-FL), random.uniform(10,26), (26,12,8), 0.030)
    # a few fallen rocks, each with a contact shadow (RULE 2)
    for i in range(9):
        rx=random.uniform(W*0.22,W*0.80); ry=FL+random.uniform(10,H-FL-14); rs=random.uniform(9,26)
        for q in range(40):
            D(rx+random.uniform(-8,8), ry+random.uniform(-4,4)+rs*0.3, rs*0.5, (30,14,10), 0.05)
        d=abs(rx-W*0.52)/(W*0.5); lit=max(0.0,1.0-d*1.4)
        for k in range(int(rs)):
            v=k/rs
            R(rx-rs*(1-v*0.5), ry-rs*0.55+k*1.1, rs*2*(1-v*0.5), 1.4,
              mix(mix((44,20,12),(226,166,104), lit*0.9), (18,8,6), v*0.8))

build()
asyncio.run(paint(a))
