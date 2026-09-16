"""GEN 5 — THE LONG WAIT.  *** HOLDOUT — PAINTED ONCE, NEVER DIAGNOSED, NEVER ITERATED. ***

PROMPT: "A dog lying on the ground, waiting."

Held out of every tuning pass all night so there is one ANIMAL the rules were never fitted to.
Whatever this run produces is the answer. It does not get fixed.

Read as light: "waiting" is the subject, and waiting is low and still and long. Side light,
late in the day, raking across the floor so the ground reads as a surface and the dog reads as
a weight resting on it. A dog lying down is mostly a mass in contact with a plane — so the
contact is the picture, and a dog that does not deform where it meets the floor reads as pasted.
"""
import asyncio, math, random, sys
import art as A
from art import Art, mix, TOPBAR
import g3lib as G
import g5lib as G5

GRAY = (len(sys.argv) > 1 and sys.argv[1] == "gray")
A.GEN = "5TH GEN · HOLDOUT" + (" · FLAT GRAY" if GRAY else "")
random.seed(6000)
W, H = 1380, 900
a = Art(W, H, "THE LONG WAIT")
R, L, D = a.R, a.L, a.D
P = G5.Paint(a, GRAY); col = P.col

FLOOR = H * 0.66
TO_SUN = (0.88, -0.48)                 # low and from BEHIND-RIGHT: the dog is
                                       # backlit, a dark mass on a lit floor
WALL_C  = (128, 120, 110)
FLOOR_C = (146, 122, 96)
WARM    = (255, 214, 156)
COOL    = (62, 74, 104)
COAT    = (128, 92, 58)
COAT_D  = (34, 26, 22)

# ONE CONTINUOUS SILHOUETTE, not separate ellipses. The first holdout run built the dog from
# five ellipses and it came out as a pile of furry boulders floating above the floor — which is
# lesson 2 in CONSTRUCTION.md, written after the horse, and not applied here. Separate parts
# detach. A profile filled between a top and a bottom curve cannot.
#
# Proportions TUNED BY EYE: the prompt names no breed and there is no correct answer to look up.
BLEN = 620.0
DX, DY = W * 0.47, H * 0.80          # DY is the GROUND LINE the dog lies ON,
                                     # well forward on the floor, not up at the wall junction

TOPP = [(DX-BLEN*0.70, DY-BLEN*0.190),   # nose, resting low and forward
        (DX-BLEN*0.645, DY-BLEN*0.232),  # bridge, short
        (DX-BLEN*0.585, DY-BLEN*0.252),  # the STOP: a distinct step up to the skull
        (DX-BLEN*0.525, DY-BLEN*0.318),  # skull, deep
        (DX-BLEN*0.440, DY-BLEN*0.300),  # back of the head
        (DX-BLEN*0.34, DY-BLEN*0.235),   # neck
        (DX-BLEN*0.20, DY-BLEN*0.235),   # withers
        (DX+BLEN*0.02, DY-BLEN*0.215),   # back, level
        (DX+BLEN*0.22, DY-BLEN*0.230),   # loin rising to the hip
        (DX+BLEN*0.36, DY-BLEN*0.215),   # hip
        (DX+BLEN*0.48, DY-BLEN*0.130)]   # rump falling to the ground
BOTP = [(DX-BLEN*0.70, DY-BLEN*0.190),   # nose (shared)
        (DX-BLEN*0.655, DY-BLEN*0.150),  # under the muzzle
        (DX-BLEN*0.560, DY-BLEN*0.165),  # jaw, deep
        (DX-BLEN*0.44, DY-BLEN*0.105),   # throat, tucked down
        (DX-BLEN*0.30, DY),              # chest MEETING the floor
        (DX-BLEN*0.10, DY),              # belly, flat on the ground
        (DX+BLEN*0.16, DY),              # flank, flat
        (DX+BLEN*0.34, DY-BLEN*0.010),   # thigh, spread where it bears weight
        (DX+BLEN*0.48, DY-BLEN*0.130)]   # rump (shared)

def spline(pts, t):
    n=len(pts)-1; u=max(0.0,min(0.9999,t))*n
    i=int(u); f=u-i
    p0=pts[max(0,i-1)]; p1=pts[i]; p2=pts[min(n,i+1)]; p3=pts[min(n,i+2)]
    c=lambda A,B,C,Dd: 0.5*((2*B)+(-A+C)*f+(2*A-5*B+4*C-Dd)*f*f+(-A+3*B-3*C+Dd)*f*f*f)
    return (c(p0[0],p1[0],p2[0],p3[0]), c(p0[1],p1[1],p2[1],p3[1]))

TCD=[spline(TOPP,i/340.) for i in range(341)]
BCD=[spline(BOTP,i/340.) for i in range(341)]
_xs=[p[0] for p in TCD+BCD]; DXLO,DXHI=min(_xs),max(_xs)

def dog_span(x):
    t=[p[1] for p in TCD if abs(p[0]-x)<10]; b=[p[1] for p in BCD if abs(p[0]-x)<10]
    return (min(t), max(b)) if t and b else None

def inside(x, y):
    sp = dog_span(x)
    return sp is not None and sp[0] <= y <= sp[1]

def normal_at(x, y):
    sp = dog_span(x)
    if sp is None: return 0.0, -1.0
    lo, hi = sp
    n = max(-1.0, min(1.0, (y - (lo+hi)*0.5) / max(1.0, (hi-lo)*0.5)))
    nz = math.sqrt(max(0.0, 1 - n*n))
    # along the body the surface also turns: the chest and rump face outward
    along = G.frac(x, DXLO, DXHI)
    nx = (0.5 - along) * 1.1
    ny = n
    m = math.hypot(nx, ny) or 1.0
    return nx/m, ny/m

def build():
    for y in range(TOPBAR, H, 4):
        R(0, y, W, 5, col(0.06, COOL, 0.5))
    # the wall behind: raked light, so it carries a gradient left to right
    for y in range(TOPBAR, int(FLOOR)+4, 2):
        NC=60
        for k in range(NC):
            x0=W*k/NC; xm=x0+W/(2.0*NC)
            lit = math.exp(-((xm - W*0.82)/(W*0.50))**2)
            v = 0.10 + 0.34*lit*(1 - G.frac(y,TOPBAR,FLOOR)*0.45)
            R(x0,y,W/NC+2,3, col(v, G5.temp(lit, WARM, COOL), 0.55))
    # the floor: raking light makes it a SURFACE, with the grain running away from the window
    for y in range(int(FLOOR), H, 2):
        d=G.frac(y,FLOOR,H)
        NC=60
        for k in range(NC):
            x0=W*k/NC; xm=x0+W/(2.0*NC)
            lit = math.exp(-((xm - W*0.78)/(W*0.58))**2) * (0.40+0.60*d)
            v = 0.12 + 0.40*lit
            R(x0,y,W/NC+2,3, col(v, G5.temp(lit, WARM, FLOOR_C), 0.62))
    for _ in range(22000):
        x=random.uniform(0,W); y=random.uniform(FLOOR,H)
        d=G.frac(y,FLOOR,H)
        lit = math.exp(-((x - W*0.78)/(W*0.58))**2)*(0.40+0.60*d)
        L(x,y,x+random.uniform(10,60),y+random.gauss(0,0.7), random.uniform(0.5,1.4),
          col(0.10+0.38*lit+random.uniform(-0.05,0.05), G5.temp(lit, WARM, FLOOR_C), 0.6))

    # ---- the cast shadow FIRST, so the dog sits in it. Light from the left: shadow to the right.
    for _ in range(9000):
        t=random.random()**0.7
        sx = DX - BLEN*0.62 + BLEN*1.30*random.random() - BLEN*0.50*t + random.gauss(0, BLEN*0.07*(0.3+t))
        sy = DY - BLEN*0.006 + random.gauss(0, 5 + 16*t)
        D(sx, sy, random.uniform(4,22)*(0.5+t), col(0.085, COOL, 0.55),
          0.075*(1-t)**1.5 + 0.005)

    # ---- THE DOG: one continuous mass, resting ON the floor
    x = DXLO
    while x < DXHI:
        sp = dog_span(x)
        if sp:
            lo, hi = sp
            y = lo
            while y <= hi:
                nx, ny = normal_at(x, y)
                near_floor = G.frac(y, hi - BLEN*0.055, hi)
                occ = 0.60 * near_floor                    # the underside is buried in its own shadow
                lit = G5.shade(nx, ny, TO_SUN, occ=occ, ambient=0.18)
                v = 0.030 + 0.13 * lit          # backlit: the viewer sees the shadow side
                R(x, y, 3, 4, col(v, G5.temp(lit*0.5, WARM, COOL), 0.42))
                y += 3
        x += 2.0
    # coat: short hair lying along the body, mid-tones only
    for _ in range(30000):
        x = random.uniform(DXLO, DXHI)
        sp = dog_span(x)
        if not sp: continue
        lo, hi = sp
        y = random.uniform(lo, hi)
        nx, ny = normal_at(x, y)
        lit = G5.shade(nx, ny, TO_SUN, ambient=0.26)
        band = math.exp(-((lit-0.95)**2)/0.06)
        if band < 0.20: continue
        ang = 0.12 + random.gauss(0, 0.22)
        ln = random.uniform(5, 15)
        L(x, y, x+math.cos(ang)*ln, y+math.sin(ang)*ln, random.uniform(0.5,1.2),
          col(0.10 + 0.52*lit + random.uniform(-0.05,0.05), G5.temp(lit, WARM, COAT), 0.72))
    # the front legs, stretched out ahead — a lying dog rests its chin near them
    for s_i, (lx0, ly0, lx1, ly1, wid) in enumerate([
            (DX-BLEN*0.28, DY-BLEN*0.085, DX-BLEN*0.60, DY-BLEN*0.014, BLEN*0.055),
            (DX-BLEN*0.24, DY-BLEN*0.062, DX-BLEN*0.53, DY-BLEN*0.010, BLEN*0.045)]):
        n=90
        for i in range(n+1):
            t=i/n
            cx=lx0+(lx1-lx0)*t; cy=ly0+(ly1-ly0)*t
            w=wid*(1-t*0.35)
            k=-w
            while k<=w:
                u=k/max(1.,w)
                nz=math.sqrt(max(0.,1-u*u))
                lit=G5.shade(u*0.7,-nz*0.7,TO_SUN,occ=0.30+0.32*t,ambient=0.16)*(1-s_i*0.22)
                D(cx+k,cy,1.7,col(0.028+0.13*lit, G5.temp(lit*0.5, WARM, COOL), 0.42),1.0)
                k+=1.6
    # the tail, laid flat along the ground behind
    for _ in range(2400):
        t=random.random()
        tx = DX+BLEN*0.46 + t*BLEN*0.30 + random.gauss(0,5)
        ty = DY-BLEN*0.055 + t*BLEN*0.045 + random.gauss(0,4)
        lit = G5.shade(0.3,-0.7,TO_SUN,occ=0.3+0.3*t,ambient=0.18)
        D(tx,ty,random.uniform(1.4,3.6)*(1-t*0.4),
          col(0.030+0.42*lit*(1-t*0.5), G5.temp(lit, WARM, COOL), 0.55), 0.6)

    # the rim the backlight puts on the top and rear of the animal — strands, never an outline
    for i in range(1800):
        t = i/1799.
        px, py = spline(TOPP, t)
        along = t
        s_here = math.exp(-((1.0-along)**2)/0.55) * 0.55 + 0.45*math.exp(-((along-0.5)**2)/0.30)
        for _ in range(3):
            D(px + random.gauss(0,1.0), py + random.uniform(0.2,2.4) + random.gauss(0,0.7),
              random.uniform(0.6,1.9), col(min(0.97, 0.48+0.46*s_here), WARM, 0.88),
              min(0.85, 0.08+0.78*s_here))
    # fur catching the rim: individual hairs separating against the bright floor
    for _ in range(9000):
        t = random.random()
        px, py = spline(TOPP, t)
        ln = random.uniform(3, 12)
        ang = -1.35 + random.gauss(0, 0.5)
        L(px+random.gauss(0,2), py+random.gauss(0,1.5),
          px+math.cos(ang)*ln, py+math.sin(ang)*ln, random.uniform(0.4,0.9),
          col(0.40+0.45*random.random(), WARM, 0.8))

    # ears, muzzle shadow, and the one thing that says "waiting": the eye, open, looking off
    ex, ey = DX - BLEN*0.575, DY - BLEN*0.252
    D(ex, ey, 6.0, col(0.05, COAT_D, 0.5), 0.9)
    D(ex, ey, 4.0, col(0.16, COAT_D, 0.6), 1.0)
    D(ex-1.2, ey-1.4, 1.5, col(0.90, WARM, 0.4), 0.95)
    for _ in range(5200):     # the ear, hanging
        t=random.random()
        w = BLEN*0.048 * (0.55 + 0.75*math.sin(min(1.0,t*1.05)*math.pi)**0.6)
        x = DX - BLEN*0.492 + random.gauss(0, w)
        y = DY - BLEN*0.300 + t*BLEN*0.150 + random.gauss(0, 3)
        nx, ny = -0.4, -0.5
        lit = G5.shade(nx, ny, TO_SUN, ambient=0.14) * (1-t*0.4)
        D(x, y, random.uniform(1.2,3.0), col(0.028+0.12*lit, G5.temp(lit*0.5, WARM, COOL), 0.42), 0.6)
    for _ in range(1800):     # the nose and the front paws laid out ahead
        if random.random() < 0.4:
            x = DX - BLEN*0.700 + random.gauss(0, 6); y = DY - BLEN*0.186 + random.gauss(0, 5)
            D(x, y, random.uniform(1.2,3.0), col(0.045, COAT_D, 0.5), 0.8)
        else:
            t = random.random()
            x = DX - BLEN*0.60 - t*BLEN*0.06 + random.gauss(0, 7)
            y = DY - BLEN*0.012 + random.gauss(0, 4)
            lit = G5.shade(-0.2, -0.8, TO_SUN, occ=0.45, ambient=0.16)
            D(x, y, random.uniform(1.4,3.4), col(0.028+0.11*lit, G5.temp(lit*0.5, WARM, COOL), 0.42), 0.6)

build()
OUT = "g5_dog_gray.png" if GRAY else "g5_dog_fixed.png"
asyncio.run(G5.paint(a, OUT, {"subject": "the_long_wait", "holdout": True,
    "prompt": "A dog lying on the ground, waiting."}, gray=GRAY, focal_y=H*0.66))
