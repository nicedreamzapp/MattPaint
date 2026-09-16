"""Dawn ridges: layered mountains fading into haze. Atmospheric depth is what makes it read real."""
import asyncio, sys, time, math, random
from engine import Browser
random.seed(4)
CW=int(sys.argv[1]) if len(sys.argv)>1 else 1300
CH=int(sys.argv[2]) if len(sys.argv)>2 else 820
VISIBLE = "--hidden" not in sys.argv
ops=[]
def R(x,y,w,h,c): ops.append([0,int(x),int(y),int(max(1,w)),int(max(1,h)),int(c[0]),int(c[1]),int(c[2])])
def L(x1,y1,x2,y2,w,c): ops.append([1,round(x1,1),round(y1,1),round(x2,1),round(y2,1),float(w),int(c[0]),int(c[1]),int(c[2])])
def D(x,y,r,c,a=1.0): ops.append([2,round(x,1),round(y,1),int(c[0]),int(c[1]),int(c[2]),round(max(0.4,r),1),round(a,3)])
def mix(a,b,t):
    t=max(0.0,min(1.0,t)); return tuple(int(round(a[i]+(b[i]-a[i])*t)) for i in range(3))

SUNX,SUNY=0.63,0.455
def build():
    HOR=0.70
    HY=CH*HOR
    keys=[(0.0,(58,86,140)),(0.30,(122,140,176)),(0.55,(206,178,168)),(0.78,(246,196,150)),(1.0,(255,226,178))]
    def sky(t):
        for (a,ca),(b,cb) in zip(keys,keys[1:]):
            if a<=t<=b: return mix(ca,cb,(t-a)/(b-a))
        return keys[-1][1]
    for y in range(0,int(HY),2):
        R(0,y,CW,3, sky(y/HY))
    # sun + halo
    sx,sy=SUNX*CW, SUNY*HY
    # tight glow only: each ring takes the sky colour at its own height, so no colour arc
    base=sky(sy/HY)
    for k in range(90):
        u=k/90.0
        r=150*(1-u)+6
        strength=u**2.0                  # u=0 -> biggest circle -> faintest
        a=0.060*(strength**1.3)          # brightest at the small radii, ~0 at the rim
        if a<0.0012: continue
        D(sx,sy,r, mix(base,(255,247,230), 0.25+0.68*strength), a)
    for k in range(16):
        D(sx,sy, 22-k*1.2, (255,253,244), 0.28)
    D(sx,sy,8.5,(255,255,252),1.0)
    # soft cloud banks
    for j in range(11):
        cy=HY*random.uniform(0.10,0.60); cx=random.uniform(-100,CW+100)
        wdt=random.uniform(220,700); ht=random.uniform(14,40)
        base=mix((232,196,186),(255,226,194), cy/HY)
        for k in range(260):
            u=random.random()
            env=math.sin(max(0.0,min(1.0,u))*math.pi)**1.5
            x=cx-wdt/2+wdt*u+random.uniform(-14,14)
            yy=cy+math.sin(u*4.0+j)*ht*0.45+random.gauss(0,ht*0.42)
            rr=ht*env*random.uniform(0.25,0.95)
            if rr<=0.5: continue
            lit=max(0.0,1-abs(yy-(cy-ht*0.4))/(ht*1.6))
            D(x,yy, rr, mix(base,(255,246,228),lit*0.7), 0.030)
    # ---- ridges, far -> near, each hazier the further away ----
    def ridge(f, base_y, col, haze, y_lo):
        x=0.0
        while x<CW:
            y=f(x)
            n=int((base_y-y)/3)+1
            for k in range(n):
                v=k/max(1,n-1)
                c=mix(mix(col,(255,224,190),haze), mix(col,(40,46,66),0.35), v*0.55)
                R(x, y+(base_y-y)*v, 3, 4, c)
            x+=2
    def mk(peaks,noise,seed):
        rnd=random.Random(seed); ph=[rnd.uniform(0,6.3) for _ in range(3)]
        def f(x):
            y=1e9
            for (px,py,sl,sr) in peaks:
                y=min(y, py+((px-x)*sl if x<px else (x-px)*sr))
            return y+(math.sin(x*0.05+ph[0])*0.6+math.sin(x*0.14+ph[1])*0.3)*noise
        return f
    layers=[
        (mk([(CW*0.20,HY*0.52,0.22,0.20),(CW*0.55,HY*0.44,0.20,0.18),(CW*0.86,HY*0.50,0.18,0.22)],7,1), HY*1.02,(150,160,190),0.72),
        (mk([(CW*0.10,HY*0.66,0.26,0.22),(CW*0.44,HY*0.58,0.22,0.22),(CW*0.78,HY*0.62,0.20,0.26)],8,2), HY*1.06,(116,126,158),0.55),
        (mk([(CW*0.05,HY*0.80,0.30,0.26),(CW*0.36,HY*0.72,0.26,0.26),(CW*0.70,HY*0.76,0.24,0.30),(CW*0.97,HY*0.70,0.26,0.28)],8,3), HY*1.12,(84,92,120),0.38),
        (mk([(CW*0.16,HY*0.94,0.34,0.30),(CW*0.52,HY*0.86,0.30,0.30),(CW*0.88,HY*0.90,0.28,0.34)],7,4), CH,(52,58,80),0.20),
        (mk([(CW*0.30,HY*1.06,0.40,0.36),(CW*0.72,HY*1.00,0.34,0.40)],6,5), CH,(28,32,48),0.08),
    ]
    for f,by,col,haze in layers:
        ridge(f,by,col,haze,HY)
        # haze pooling in the valleys at the foot of each ridge
        x=0.0
        mistc=mix(mix((250,230,212),(206,202,214),0.4), col, 0.30)
        while x<CW:
            y=f(x)
            for k in range(7):
                D(x+random.uniform(-5,5), y+8+k*6+random.uniform(-3,3), 17, mistc, 0.011)
            x+=3
    # light rays from the sun
    for i in range(14):
        a=random.uniform(0.55,1.45)
        wdt=random.uniform(14,40)
        for k in range(80):
            u=k/80
            x=sx+math.cos(a)*900*u; y=sy+math.sin(a)*900*u
            if y>CH+40: break
            D(x,y, wdt*(0.3+u*1.0), (255,244,222), 0.011*(1-u*0.92))
    # foreground silhouette trees
    # conifers: tapered silhouettes, varied, slightly hazed so they sit in the air
    clusters=[random.uniform(-40,CW+40) for _ in range(9)]
    for i in range(70):
        cx0=random.choice(clusters)
        x=cx0+random.gauss(0,90)
        if x<-40 or x>CW+40: continue
        h=random.uniform(55,190)*random.uniform(0.8,1.2)
        base=CH+12+random.uniform(-8,10)
        depth=random.random()
        col=mix((14,16,26),(96,104,126), depth*0.45)      # further trees lift toward the haze
        wtr=random.uniform(1.6,3.4)
        L(x,base,x,base-h*0.94,wtr,col)
        tiers=int(10+random.random()*8)
        for k in range(tiers):
            t=k/tiers
            w=h*random.uniform(0.20,0.30)*(1-t*0.86)
            yy=base-h*(0.18+0.82*t)
            drop=h*0.05
            for o in (-1,1):
                L(x, yy, x+o*w, yy+drop, max(0.8,2.2*(1-t*0.5)), col)
                L(x, yy+drop*0.4, x+o*w*0.62, yy+drop*1.2, max(0.7,1.6*(1-t*0.5)), col)
        D(x, base-h*0.5, h*0.10, col, 0.10)               # soften the mass
    # a breath of mist through the treeline
    for i in range(220):
        D(random.uniform(0,CW), CH-random.uniform(0,150), random.uniform(20,60), (226,220,226), 0.014)

async def main():
    t0=time.time(); build(); print(f"{len(ops)} ops in {time.time()-t0:.1f}s",flush=True)
    from engine import launch_brave
    import urllib.request
    try: urllib.request.urlopen("http://localhost:9231/json/version",timeout=1); up=True
    except Exception: up=False
    if not up: launch_brave(9231,size=(1560,1010)); await asyncio.sleep(2.0)
    br=Browser(9231); await br.connect(); tab=await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r="+str(int(time.time())))
    await tab.measure_canvas(); await tab.resize_canvas(CW,CH)
    t1=time.time()
    for i in range(0,len(ops),7000):
        tab.fast(ops[i:i+7000]); await tab.sync(); await asyncio.sleep(0.03)
    await tab.sync()
    print(f"painted {len(ops)} ops in {time.time()-t1:.2f}s",flush=True)
    await tab.png("scene.png")
    await br.close()
asyncio.run(main())
