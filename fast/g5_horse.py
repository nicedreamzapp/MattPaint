"""GEN 5 — MORNING FIELD. Built to GEN5_RULES.md.

PROMPT: "A horse standing in an open field in early morning light."

The honest reading. This system cannot know real anatomy — that was settled tonight, and it is a
property of the model, not of the paint program. But GEN5_RULES says a form half-lost in shadow
is READ AS CORRECT. So this is backlit: the sun is low and BEHIND the horse, the animal is
mostly a dark mass against a bright field, and what the viewer gets is a rim and a silhouette.
That is not a dodge, it is why chiaroscuro exists, and it is the right call for a subject whose
interior detail cannot be trusted.

Proportions are the SOURCED ones (3.0 head lengths at the withers, 3.67 long) — see
CONSTRUCTION.md. Gen3 used 2.5, which was invented.

The field gets the budget this time. Gen3 gave it 0.3% of the strokes and 45% to outlining the
horse; here there are no outlines at all and the field is the painting.
"""
import asyncio, math, random, sys
import art as A
from art import Art, mix, TOPBAR
import g3lib as G
import g5lib as G5

GRAY = (len(sys.argv) > 1 and sys.argv[1] == "gray")
A.GEN = "5TH GEN" + (" · FLAT GRAY TEST" if GRAY else "")
random.seed(5800)
W, H = 1380, 900
a = Art(W, H, "MORNING FIELD")
R, L, D = a.R, a.L, a.D
P = G5.Paint(a, GRAY); col = P.col

HOR = H * 0.56
GND = H * 0.80
SUNX, SUNY = W * 0.62, HOR - 26        # low, BEHIND the horse
TO_SUN = (0.34, -0.94)

SKY_HI, SKY_LO = (96, 132, 186), (255, 216, 168)
GRASS_LIT, GRASS_DK = (232, 206, 128), (54, 62, 38)
COAT = (44, 34, 30)
WARM = (255, 206, 146)
COOL = (72, 92, 132)

HEAD = 118.0
def hl(n): return n * HEAD
CX = W * 0.46
TOPLINE = GND - hl(3.00)
ELBOW_Y = GND - hl(1.50)
SHOULDER_X = CX - hl(1.83); BUTTOCK_X = CX + hl(1.83)
FORE_X = CX - hl(1.45)

TOP = [(CX-hl(3.10), TOPLINE-hl(0.26)), (CX-hl(2.78), TOPLINE-hl(0.56)),
       (CX-hl(2.30), TOPLINE-hl(0.86)), (CX-hl(1.95), TOPLINE-hl(0.70)),
       (CX-hl(1.60), TOPLINE-hl(0.34)), (CX-hl(1.35), TOPLINE),
       (CX-hl(0.55), TOPLINE+hl(0.10)), (CX+hl(0.60), TOPLINE+hl(0.06)),
       (CX+hl(1.30), TOPLINE+hl(0.04)), (CX+hl(1.68), TOPLINE+hl(0.34)),
       (BUTTOCK_X, TOPLINE+hl(0.78))]
BOT = [(CX-hl(3.10), TOPLINE-hl(0.26)), (CX-hl(2.86), TOPLINE-hl(0.10)),
       (CX-hl(2.36), TOPLINE-hl(0.22)), (CX-hl(2.02), TOPLINE+hl(0.16)),
       (CX-hl(1.90), TOPLINE+hl(0.62)), (SHOULDER_X, TOPLINE+hl(1.02)),
       (FORE_X-hl(0.02), ELBOW_Y), (CX-hl(0.90), ELBOW_Y+hl(0.05)),
       (CX-hl(0.10), ELBOW_Y-hl(0.04)), (CX+hl(0.70), ELBOW_Y-hl(0.20)),
       (CX+hl(1.02), GND-hl(1.34)), (CX+hl(1.44), TOPLINE+hl(2.10)),
       (BUTTOCK_X, TOPLINE+hl(0.78))]

def spline(pts, t):
    n = len(pts)-1; u = max(0.0, min(0.9999, t))*n
    i = int(u); f = u-i
    p0=pts[max(0,i-1)]; p1=pts[i]; p2=pts[min(n,i+1)]; p3=pts[min(n,i+2)]
    c=lambda A,B,C,Dd: 0.5*((2*B)+(-A+C)*f+(2*A-5*B+4*C-Dd)*f*f+(-A+3*B-3*C+Dd)*f*f*f)
    return (c(p0[0],p1[0],p2[0],p3[0]), c(p0[1],p1[1],p2[1],p3[1]))

TC=[spline(TOP,i/320.) for i in range(321)]
BC=[spline(BOT,i/320.) for i in range(321)]
XS=[p[0] for p in TC+BC]; XLO,XHI=min(XS),max(XS)

def span(x):
    t=[p[1] for p in TC if abs(p[0]-x)<9]; b=[p[1] for p in BC if abs(p[0]-x)<9]
    return (min(t), max(b)) if t and b else None

LEGS = [((FORE_X, ELBOW_Y), (FORE_X, GND-hl(0.70)), hl(0.16), hl(0.072)),
        ((FORE_X, GND-hl(0.70)), (FORE_X, GND), hl(0.070), hl(0.056)),
        ((FORE_X+hl(0.08), ELBOW_Y), (FORE_X+hl(0.10), GND-hl(0.70)), hl(0.13), hl(0.062)),
        ((FORE_X+hl(0.10), GND-hl(0.70)), (FORE_X+hl(0.11), GND), hl(0.060), hl(0.050)),
        ((CX+hl(1.02), GND-hl(1.34)), (CX+hl(1.56), GND-hl(0.84)), hl(0.19), hl(0.086)),
        ((CX+hl(1.56), GND-hl(0.84)), (CX+hl(1.58), GND), hl(0.082), hl(0.056)),
        ((CX+hl(0.96), GND-hl(1.34)), (CX+hl(1.48), GND-hl(0.84)), hl(0.16), hl(0.076)),
        ((CX+hl(1.48), GND-hl(0.84)), (CX+hl(1.50), GND), hl(0.072), hl(0.050))]

def sky_v(y): return 0.42 + 0.46*G.frac(y, TOPBAR, HOR)**0.8
def sky_h(x,y):
    d=math.hypot((x-SUNX)/(W*0.42),(y-SUNY)/(H*0.30))
    return mix(mix(SKY_HI, SKY_LO, G.frac(y,TOPBAR,HOR)**1.1), (255,240,206),
               min(0.8, math.exp(-d*d*0.9)))

def build():
    for y in range(TOPBAR, int(HOR)+4, 2):
        NC=90
        for k in range(NC):
            x0=W*k/NC; xm=x0+W/(2.0*NC)
            R(x0,y,W/NC+2,3, col(sky_v(y)+0.22*math.exp(-(((xm-SUNX)/(W*0.20))**2+((y-SUNY)/(H*0.16))**2)),
                                 sky_h(xm,y), 0.6))
    for k in range(120):
        u=k/120.
        D(SUNX,SUNY,420*(1-u)**1.8+8, col(0.72+0.26*u*u, (255,244,214), 0.6), 0.010*(u**2.2))

    # ---- THE FIELD. This is the painting. Backlit grass glows; every blade is rimmed.
    for y in range(int(HOR), H, 2):
        d=G.frac(y,HOR,H)
        NC=70
        for k in range(NC):
            x0=W*k/NC; xm=x0+W/(2.0*NC)
            glow=math.exp(-((xm-SUNX)/(W*0.40))**2)*(1-d)**1.4
            v=0.30+0.26*(1-d)+0.30*glow
            R(x0,y,W/NC+2,3, col(v, mix(mix(GRASS_LIT,SKY_LO,0.4*(1-d)), GRASS_DK, d*0.8), 0.62))
    # backlit blades, near field only, each catching the sun along its edge
    for _ in range(58000):
        y = HOR + (H-HOR) * random.random()**0.55
        x = random.uniform(-20, W+20)
        d = G.frac(y, HOR, H)
        hgt = (7 + 34*d) * random.uniform(0.6, 1.5)
        glow = math.exp(-((x-SUNX)/(W*0.45))**2) * (1-d*0.7)
        lit = random.random()**1.6
        v = 0.12 + 0.22*d*0.4 + 0.62*glow*lit
        L(x, y, x+random.gauss(0,3.2), y-hgt, random.uniform(0.5,1.4),
          col(min(0.97,v), G5.temp(glow*lit, (255,232,168), GRASS_DK), 0.72))

    # ---- THE HORSE, backlit: a dark mass with a rim of morning sun along its top and back.
    x = XLO
    while x < XHI:
        sp = span(x)
        if sp:
            lo, hi = sp
            y = lo
            while y <= hi:
                n = max(-1.,min(1.,(y-(lo+hi)*0.5)/max(1.,(hi-lo)*0.5)))
                nz = math.sqrt(max(0.,1-n*n))
                # backlit: the viewer sees mostly the shadow side. Sky fill is what little there is.
                sky = (max(0.0,-n)*0.5+0.5)*0.22
                v = 0.030 + sky*0.55
                hue = G5.temp(sky*1.6, WARM, COOL)
                R(x, y, 3, 4, col(v, hue, 0.45))
                y += 3
        x += 2.0
    for (p0,p1,w0,w1) in LEGS:
        n=max(10,int(math.hypot(p1[0]-p0[0],p1[1]-p0[1])/2))
        for i in range(n+1):
            t=i/n; cx=p0[0]+(p1[0]-p0[0])*t; cy=p0[1]+(p1[1]-p0[1])*t
            w=w0+(w1-w0)*t; k=-w
            while k<=w:
                u=k/max(1.,w); body=math.sqrt(max(0.,1-u*u))
                v=0.026+0.10*body
                D(cx+k,cy,1.6,col(v,COOL,0.4),1.0); k+=1.5
    # THE RIM: the sun is behind, so the true outer boundary glows. Occlusion-tested by using
    # only the top profile and only where the sun can actually reach.
    for i in range(1400):
        t=i/1399.
        px,py=spline(TOP,t)
        d=math.hypot((px-SUNX)/(W*0.7),(py-SUNY)/(H*0.7))
        s=math.exp(-d*d*0.8)
        for _ in range(3):
            D(px+random.gauss(0,1.1), py+random.uniform(0.2,2.6)+random.gauss(0,0.8),
              random.uniform(0.6,2.0), col(min(0.97,0.55+0.42*s), WARM, 0.85),
              min(0.85,0.10+0.80*s))
    # mane and tail as strands catching the same rim
    for _ in range(420):
        t=random.uniform(0.15,0.50); mx,my=spline(TOP,t)
        sway=random.gauss(0,hl(0.05)); ln=hl(0.30)*random.uniform(0.4,1.0)
        for k in range(18):
            u=k/17.
            D(mx+sway*u+hl(0.02)*u, my+ln*u, max(0.5,1.3*(1-u*0.5)),
              col(0.05+0.30*(1-u)*random.random(), WARM, 0.5), 0.75)
    for _ in range(360):
        tx,ty=BUTTOCK_X-hl(0.04), TOPLINE+hl(0.80)
        sway=random.gauss(0,hl(0.07)); ln=hl(1.30)*random.uniform(0.6,1.1)
        for k in range(30):
            u=k/29.
            D(tx+hl(0.10)*u+sway*(u**1.5), ty+ln*u, max(0.5,1.4*(1-u*0.4)),
              col(0.04+0.26*(1-u)*random.random(), WARM, 0.5), 0.7)
    # contact shadow: the sun is behind, so it falls TOWARD the viewer
    for _ in range(7000):
        t=random.random()**0.7
        sx=CX+random.gauss(0,hl(1.5)); sy=GND+8+t*hl(1.1)+random.gauss(0,6)
        D(sx,sy,random.uniform(5,24)*(0.5+t), col(0.14, COOL, 0.5), 0.055*(1-t)**1.5+0.004)

build()
OUT = "g5_horse_gray.png" if GRAY else "g5_horse.png"
asyncio.run(G5.paint(a, OUT, {"subject": "morning_field",
    "prompt": "A horse standing in an open field in early morning light."},
    gray=GRAY, focal_y=H*0.7))
