"""Procedural backlit elephant at golden hour, trunk lunging toward the viewer.
Iterated with a look-fix-render loop. Drawn via MattPaint fast accelerator.
"""
import asyncio, sys, time, math, random
from engine import Browser
random.seed(7)
CW = int(sys.argv[2]) if len(sys.argv) > 2 else 1400
CH = int(sys.argv[3]) if len(sys.argv) > 3 else 800
VISIBLE = "--hidden" not in sys.argv   # on-screen by DEFAULT; hiding must be explicit
ops=[]
def clamp(v,a=0,b=255): return max(a,min(b,int(v)))
def mix(c1,c2,t): return tuple(clamp(c1[i]+(c2[i]-c1[i])*t) for i in range(3))
def rect(x,y,w,h,c): ops.append([0,int(x),int(y),int(max(1,w)),int(max(1,h)),c[0],c[1],c[2]])
def stroke(x1,y1,x2,y2,w,c): ops.append([1,round(x1,1),round(y1,1),round(x2,1),round(y2,1),float(w),c[0],c[1],c[2]])
def dab(x,y,r,c,a=1.0):
    if r<=0: return
    ops.append([2,round(x,1),round(y,1),c[0],c[1],c[2],round(r,1),round(a,3)])

SUNx,SUNy = 0.62, 0.30
def sun_dir(cx,cy):
    v=(SUNx*CW-cx, SUNy*CH-cy); n=math.hypot(*v) or 1; return v[0]/n, v[1]/n

def sphere_shade(cx,cy,rx,ry, albedo, ambient=0.34, step=3, frontal=0.5, warm=(255,214,158), cool=(26,22,36)):
    """smooth volumetric ellipse: per-cell diffuse shading from the sun, warm light -> cool shadow"""
    ux,uy=sun_dir(cx,cy)
    lightcol=mix(albedo, warm, 0.32); darkcol=mix(albedo, cool, 0.62)
    yy=-ry
    while yy<=ry:
        nyr=yy/ry; xspan=rx*math.sqrt(max(0.0,1-nyr*nyr)); xx=-xspan
        while xx<=xspan:
            nx=xx/rx; ny=nyr; nz=math.sqrt(max(0.0,1-nx*nx-ny*ny))
            diff=nx*ux+ny*uy+nz*frontal
            shade=max(0.0,min(1.0, ambient+(1-ambient)*max(0.0,diff)))
            rect(cx+xx, cy+yy, step+1, step+1, mix(darkcol,lightcol,shade))
            xx+=step
        yy+=step

def soft_mass(cx,cy,rx,ry, base, light, dark):
    sphere_shade(cx,cy,rx,ry, base)

def halo(cx,cy,rx,ry, c=(255,214,150), grow=12):
    return  # disabled: daytime front-lit, no backlight rim
    """clean continuous backlight rim: bright filled ellipse behind; the mass covers the middle"""
    for g,al in ((grow+8,0.35),(grow,0.9)):
        yy=-(ry+g)
        while yy<=ry+g:
            w=(rx+g)*math.sqrt(max(0.0,1-(yy/(ry+g))**2))
            rect(cx-w, cy+yy, 2*w, 3, mix((255,236,190),c,al) if al<1 else c)
            yy+=2

def rim(cx,cy,rx,ry, c, spread=1.15, dens=90, w=2.4, a=0.55):
    ux,uy=sun_dir(cx,cy); a0=math.atan2(uy,ux)
    prev=None
    for i in range(dens):
        ang=a0-spread + 2*spread*i/dens
        x=cx+rx*math.cos(ang); y=cy+ry*math.sin(ang)
        dab(x,y, w, c, a)
        if prev: stroke(prev[0],prev[1],x,y, w*0.8, c)
        prev=(x,y)

def tube(pts, r0, r1, base, light, dark, wr=True):
    N=len(pts); samp=[]
    for i in range(N-1):
        for t in [j/16 for j in range(16)]:
            x=pts[i][0]+(pts[i+1][0]-pts[i][0])*t; y=pts[i][1]+(pts[i+1][1]-pts[i][1])*t
            f=(i+t)/(N-1); samp.append((x,y,r0+(r1-r0)*f,f))
    lightcol=mix(base,(255,214,158),0.32); darkcol=mix(base,(26,22,36),0.6)
    for x,y,r,f in samp:
        ux,uy=sun_dir(x,y)
        # cross-section shading: a few offset dabs from shadow edge to lit edge
        for o in range(-3,4):
            fo=o/3.0
            px=x+ux*r*fo*0.9; py=y+uy*r*fo*0.9
            sh=max(0.0,min(1.0,0.5+0.5*fo))
            dab(px,py, r*0.5, mix(darkcol,lightcol,sh), 1.0)
    if wr:
        for k in range(1,N-1):
            x,y=pts[k]; r=r0+(r1-r0)*(k/(N-1))
            stroke(x-r*0.8,y, x+r*0.8,y, 1.6, mix(darkcol,(0,0,0),0.25))

def filled_curve_taper(x0,y0,x1,y1,x2,y2, r0,r1, c_light):
    """solid tapered curved shape (tusk) via quadratic bezier, filled with dabs"""
    for t in [i/40 for i in range(41)]:
        x=(1-t)**2*x0+2*(1-t)*t*x1+t*t*x2
        y=(1-t)**2*y0+2*(1-t)*t*y1+t*t*y2
        r=r0+(r1-r0)*t
        dab(x,y,r, mix(c_light,(180,150,96),t), 1.0)
        dab(x-2,y, r*0.6, mix(c_light,(255,240,200),0.5),0.5)

def foot(cx,cy,r, base, rimC):
    """big foreshortened round foot reaching at camera, with toenails"""
    halo(cx,cy,r,r*0.9, rimC, 12)
    sphere_shade(cx,cy,r,r*0.92, base, frontal=0.85)     # rounder, faces camera
    # sole pads
    for a in (-0.5,0.0,0.5):
        dab(cx+math.sin(a)*r*0.5, cy+r*0.42, r*0.16, mix(base,(20,16,14),0.5), 0.6)
    # toenails across the front
    for k in (-1,-0.34,0.34,1):
        nx=cx+k*r*0.62; ny=cy+r*0.6
        dab(nx,ny, r*0.14, (232,220,198), 0.95)
        dab(nx,ny+2, r*0.10, (200,186,158), 0.7)

def acacia(x,y,scl):
    stroke(x,y,x,y-40*scl,3*scl,(40,34,28))
    for dx in (-1,0,1):
        stroke(x,y-38*scl, x+dx*46*scl, y-52*scl, 2.4*scl,(40,34,28))
    dab(x,y-56*scl, 42*scl,(46,52,36),0.85); dab(x-34*scl,y-50*scl,28*scl,(46,52,36),0.8); dab(x+34*scl,y-50*scl,28*scl,(46,52,36),0.8)

def in_ell(dx,dy,rx,ry): return (dx/rx)**2+(dy/ry)**2 <= 1.0

def skin_tex(cx,cy,rx,ry, base, n=520, wrinkle='cell'):
    """cracked elephant hide: dark crevices + light ridges + tonal mottling inside an ellipse"""
    dk=mix(base,(18,14,12),0.55); lt=mix(base,(210,180,140),0.35)
    # mottling patches (dust + shadow)
    for i in range(n//4):
        a=random.uniform(0,6.283); rr=random.random()**0.5
        dx=math.cos(a)*rx*rr; dy=math.sin(a)*ry*rr
        if not in_ell(dx,dy,rx,ry): continue
        col=random.choice([mix(base,(190,166,120),0.3), mix(base,(30,24,20),0.4), base])
        dab(cx+dx,cy+dy, random.uniform(6,16), col, 0.12)
    # crevices + ridges
    for i in range(n):
        a=random.uniform(0,6.283); rr=random.random()**0.5
        dx=math.cos(a)*rx*rr; dy=math.sin(a)*ry*rr
        if not in_ell(dx,dy,rx,ry): continue
        x,y=cx+dx,cy+dy
        if wrinkle=='ring':      # trunk: horizontal rings
            ang=0.0
        elif wrinkle=='radial':  # ears: radial from center
            ang=math.atan2(dy,dx)+1.5708
        else:                    # face/body: mostly vertical with jitter
            ang=1.3+random.uniform(-0.9,0.9)
        L=random.uniform(7,15)
        ex,ey=x+math.cos(ang)*L, y+math.sin(ang)*L
        stroke(x,y,ex,ey, random.uniform(0.8,1.5), dk)
        # light ridge just beside the crevice
        ox,oy=math.cos(ang+1.5708)*2, math.sin(ang+1.5708)*2
        stroke(x+ox,y+oy,ex+ox,ey+oy, 0.8, lt)

def build():
    HOR=0.72
    # savanna sky (bright, warm low sun) + soft clouds
    keys=[(0.0,(96,140,196)),(0.4,(150,178,208)),(0.62,(224,206,178)),(HOR,(255,232,182))]
    def sky(t):
        for (a,ca),(b,cb) in zip(keys,keys[1:]):
            if a<=t<=b: return mix(ca,cb,(t-a)/(b-a))
        return keys[-1][1]
    for i in range(0,int(CH*HOR),2): rect(0,i,CW,3, sky(i/(CH*HOR)))
    for cxp,cyp in [(0.14,0.14),(0.4,0.09),(0.72,0.17),(0.9,0.11)]:
        for k in range(4): dab(cxp*CW+random.uniform(-90,90),cyp*CH+random.uniform(-12,12),random.uniform(30,54),(255,255,255),0.45)
    # ground: dry golden plain
    for i in range(int(CH*HOR),CH,2):
        t=(i-CH*HOR)/(CH*(1-HOR)); rect(0,i,CW,3, mix((196,166,102),(112,88,52),t))
    for xp in (0.06,0.16,0.82,0.94):
        x=xp*CW; stroke(x,CH*HOR+4,x,CH*HOR-30,3,(46,40,32)); dab(x,CH*HOR-40,34,(52,58,40),0.8)
    for i in range(30): dab(CW*0.5+random.uniform(-360,360),CH*0.78+random.uniform(-18,22),random.uniform(50,110),(206,176,116),0.12)

    baseC=(120,112,104); rimC=(255,220,160); darkC=(30,24,20)   # elephant gray (lighter, real)
    cx=CW*0.5
    # ---- HEAD-ON CHARGING ELEPHANT (fills frame, coming at viewer) ----
    # body/chest below, coming forward
    halo(cx,CH*0.82,300,150, rimC,14); sphere_shade(cx,CH*0.82,300,150, mix(baseC,darkC,0.15), frontal=0.7); skin_tex(cx,CH*0.82,300,150, baseC, 300)
    # EARS: large rounded fans attached to the head, flopping outward, textured
    for s2 in (-1,1):
        ex,ey=cx+s2*230, CH*0.44
        sphere_shade(ex,ey,175,210, mix(baseC,(96,88,80),0.15), frontal=0.4)
        skin_tex(ex,ey,160,195, mix(baseC,(108,98,88),0.15), 300, 'radial')
        # inner fold shadow near the head
        sphere_shade(ex-s2*60,ey+16,90,150, mix(baseC,darkC,0.4), frontal=0.3)
    # HEAD (big, central)
    hx,hy=cx, CH*0.42
    halo(hx,hy,205,190, rimC,14)
    sphere_shade(hx,hy,205,190, mix(baseC,(104,96,88),0.15), frontal=0.7)
    skin_tex(hx,hy,196,182, baseC, 460, 'cell')
    # forehead двух-domes
    sphere_shade(hx-64,hy-96,84,86, mix(baseC,(120,112,102),0.3), frontal=0.6); skin_tex(hx-64,hy-96,78,80,baseC,120)
    sphere_shade(hx+64,hy-96,84,86, mix(baseC,(120,112,102),0.3), frontal=0.6); skin_tex(hx+64,hy-96,78,80,baseC,120)
    # TRUNK coming down toward viewer (thicker/closer at bottom)
    trunk=[(hx,hy+96),(hx-18,hy+190),(hx+14,hy+286),(hx-8,hy+380),(hx+10,hy+470),(hx-4,CH*0.98)]
    tube(trunk, 52, 150, mix(baseC,(108,100,92),0.2), rimC, darkC)
    for k in range(1,len(trunk)):
        tx,ty=trunk[k]; r=52+(150-52)*(k/(len(trunk)-1))
        skin_tex(tx,ty,r*0.8,r*0.5, baseC, 40, 'ring')
    tipx,tipy=trunk[-1]
    sphere_shade(tipx,tipy+6,120,74, mix(baseC,(110,102,94),0.2), frontal=0.85)
    dab(tipx-38,tipy+4,20,(20,15,12),0.9); dab(tipx+38,tipy+4,20,(20,15,12),0.9)
    stroke(tipx-84,tipy-16,tipx+84,tipy-16,2.4,darkC)
    # TUSKS curving down and out
    for s2 in (-1,1):
        mx=hx+s2*46; my=hy+156
        filled_curve_taper(mx,my, mx+s2*120,my+150, mx+s2*175,my+300, 21,6, (236,224,190))
    # EYES (small, deep-set, catchlight)
    for s2 in (-1,1):
        ex,ey=hx+s2*96, hy-8
        dab(ex,ey,20,(52,40,30),1.0); dab(ex,ey,12,(16,10,8),1.0); dab(ex-4,ey-5,4,(245,235,210),0.95)
        for a in (-0.6,0.6): stroke(ex-24,ey+a*10,ex+24,ey+a*10-6,1.6, mix(darkC,(70,54,42),0.5))
    # motion dust at bottom
    for i in range(40): dab(cx+random.uniform(-380,380),CH*0.96+random.uniform(-30,20),random.uniform(20,60),(200,172,116),0.14)
    # ---- triptych divider lines, subject breaks through ----
    # (drawn last, only over background: detect gray elephant vs sky/ground by column—approximate by skipping central band)
    for xd in (CW/3, 2*CW/3):
        yy=0
        while yy<CH:
            # skip the line where the elephant silhouette is, so it pops in front
            dxr=abs(xd-cx)
            over_ele = (CH*0.14<yy<CH*0.98) and dxr<430 and not (yy<CH*0.20 and dxr>360)
            if not over_ele:
                rect(xd-2,yy,5,4,(250,250,250))
            yy+=4

async def main():
    global ops
    build(); print(f"{len(ops)} ops",flush=True)
    if VISIBLE:
        from engine import launch_brave
        import urllib.request
        up=False
        try: urllib.request.urlopen("http://localhost:9231/json/version",timeout=1); up=True
        except Exception: up=False
        if not up:
            launch_brave(9231,size=(1500,900)); await asyncio.sleep(2.0)
        br=Browser(9231); await br.connect()
        tab=await br.existing_page("replay") or await br.new_tab("replay")
    else:
        br=Browser(9222); await br.connect(); tab=await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r="+str(int(time.time())))
    await tab.measure_canvas(); t0=time.time(); await tab.resize_canvas(CW,CH)
    for i in range(0,len(ops),4000):
        tab.fast(ops[i:i+4000])
        if VISIBLE: await tab.sync(); await asyncio.sleep(0.05)
    tab.fast_commit(); await tab.sync()
    print(f"DONE {len(ops)} ops in {time.time()-t0:.2f}s",flush=True)
    await tab.png("elephant.png")
    if not VISIBLE: await tab.close()
    await br.close()
def pkillport():
    import subprocess; subprocess.run(["pkill","-9","-f","remote-debugging-port=9231"])
asyncio.run(main())
