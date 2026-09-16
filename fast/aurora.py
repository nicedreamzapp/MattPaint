"""Aurora over a still lake. Layered translucent light, mirrored in the water."""
import asyncio, sys, time, math, random
from engine import Browser
random.seed(21)
CW=int(sys.argv[1]) if len(sys.argv)>1 else 1400
CH=int(sys.argv[2]) if len(sys.argv)>2 else 880
VISIBLE = "--hidden" not in sys.argv
HOR=0.615

ops=[]
refl=[]
MODE=['ops']
def _out():
    return refl if MODE[0]=='refl' else ops
def R(x,y,w,h,c): _out().append([0,int(x),int(y),int(max(1,w)),int(max(1,h)),int(c[0]),int(c[1]),int(c[2])])
def L(x1,y1,x2,y2,w,c): _out().append([1,round(x1,1),round(y1,1),round(x2,1),round(y2,1),float(w),int(c[0]),int(c[1]),int(c[2])])
def D(x,y,r,c,a=1.0): _out().append([2,round(x,1),round(y,1),int(c[0]),int(c[1]),int(c[2]),round(max(0.4,r),1),round(a,3)])
def mix(a,b,t):
    t=max(0.0,min(1.0,t)); return tuple(int(round(a[i]+(b[i]-a[i])*t)) for i in range(3))

HY=CH*HOR
def mirror_y(y):  return HY + (HY - y)*0.46      # slight compression in the reflection

def sky_at(t):
    keys=[(0.0,(6,8,24)),(0.30,(12,18,46)),(0.55,(18,34,66)),(0.82,(26,52,78)),(1.0,(44,76,92))]
    for (a,ca),(b,cb) in zip(keys,keys[1:]):
        if a<=t<=b: return mix(ca,cb,(t-a)/(b-a))
    return keys[-1][1]

def build():
    # ---------- sky ----------
    for y in range(0,int(HY),2):
        R(0,y,CW,3, sky_at(y/HY))
    # ---------- stars (sky + reflection) ----------
    for i in range(700):
        x=random.uniform(0,CW); y=random.uniform(0,HY*0.97)
        b=random.random()
        depth=1-(y/HY)*0.5
        r=0.5+b*1.7; a=(0.14+b*0.72)*depth
        c=random.choice([(255,255,255),(210,226,255),(255,240,220),(200,255,246)])
        D(x,y,r,c,a)
        if b>0.988:
            D(x,y,r*2.6,c,0.18)
            L(x-7,y,x+7,y,0.8,c); L(x,y-7,x,y+7,0.8,c)
        if y>HY*0.15 and random.random()<0.18:      # star reflection
            MODE[0]='refl'
            D(x+random.uniform(-2.5,2.5), mirror_y(y), r*0.9, c, a*0.34)
            MODE[0]='ops'
    # ---------- aurora curtains ----------
    def curtain(base_y, amp, freq, phase, height, top_c, mid_c, alpha, density=1.0, sway=1.0):
        step=1.4/density
        x=-40.0
        while x<CW+40:
            u=x/CW
            top = base_y + math.sin(u*freq+phase)*amp + math.sin(u*freq*2.3+phase*1.7)*amp*0.38
            h = height*(0.55+0.45*math.sin(u*freq*0.8+phase*0.6))
            h *= 0.75+0.5*random.random()
            # vertical striation: a ribbon is made of many fine hanging filaments
            n=int(h/3)
            for k in range(n):
                v=k/max(1,n-1)
                yy=top+h*v
                if yy<0: continue
                c=mix(top_c, mid_c, v**0.8)
                a=alpha*(1-v)**1.5*(0.55+0.45*math.sin(x*0.11+phase))
                if a<=0.004: continue
                xx=x+math.sin(v*3.0+u*7.0)*4.0*sway
                D(xx, yy, 2.6, c, a)
                if v<0.5:   # brighter crown
                    D(xx, yy, 1.3, mix(c,(235,255,240),0.5), a*0.55)
                # reflection
                if yy<HY:
                    MODE[0]='refl'
                    D(xx+random.uniform(-3,3), mirror_y(yy), 3.4, c, a*0.40)
                    MODE[0]='ops'
            x+=step
    curtain(HY*0.16, 42, 5.4, 0.4,  240, (120,255,196), (34,120,150), 0.055, 1.0, 1.0)
    curtain(HY*0.30, 30, 7.2, 2.1,  190, (176,255,214), (60,150,170), 0.045, 0.9, 1.2)
    curtain(HY*0.10, 54, 3.6, 4.3,  300, (198,170,255), (54,86,160), 0.030, 0.7, 0.8)
    curtain(HY*0.42, 22, 9.1, 1.2,  120, (150,255,224), (40,110,140), 0.038, 1.1, 1.4)
    # soft bloom where the curtains are brightest
    for i in range(90):
        x=random.uniform(0,CW); y=random.uniform(HY*0.12,HY*0.5)
        D(x,y, random.uniform(40,110), (40,120,110), 0.012)

    # ---------- mountains ----------
    def ridge(peaks, noise, seed):
        rnd=random.Random(seed)
        ph=[rnd.uniform(0,6.28) for _ in range(3)]
        def f(x):
            y=HY
            for (px,py,sl,sr) in peaks:
                yy=py+((px-x)*sl if x<px else (x-px)*sr)
                y=min(y,yy)
            n=(math.sin(x*0.06+ph[0])*0.6+math.sin(x*0.17+ph[1])*0.28+math.sin(x*0.41+ph[2])*0.12)*noise
            return min(HY,y+n)
        return f
    far=ridge([(CW*0.14,HY*0.60,0.30,0.26),(CW*0.42,HY*0.50,0.26,0.24),(CW*0.74,HY*0.56,0.24,0.30)],9,4)
    near=ridge([(CW*0.05,HY*0.80,0.36,0.30),(CW*0.33,HY*0.70,0.30,0.30),(CW*0.62,HY*0.76,0.28,0.34),(CW*0.92,HY*0.68,0.30,0.34)],7,8)
    for f,ctop,cbot,_rs in ((far,(30,44,64),(16,24,42),0.22),(near,(14,20,34),(6,9,18),0.16)):
        x=0.0
        while x<CW:
            y=f(x)
            n=int((HY-y)/3)+1
            for k in range(n):
                v=k/max(1,n-1)
                R(x, y+(HY-y)*v, 3, 4, mix(ctop,cbot,v))
            # reflection in the lake
            MODE[0]='refl'
            m=int((HY-y)*0.46/4)+1
            for k in range(m):
                v=k/max(1,m-1)
                R(x+random.uniform(-1,1), HY+(HY-y)*0.46*v, 3, 4, mix(mix(ctop,cbot,0.45),(9,15,28),0.30+0.45*v))
            MODE[0]='ops'
            x+=3
    # snow catching the aurora light
    for f,amt,lim in ((far,0.5,0.56),(near,0.32,0.74)):
        x=0.0
        while x<CW:
            y=f(x)
            if y<HY*lim:
                d=(HY*lim-y)*0.42*amt
                for k in range(max(1,int(d/2))):
                    v=k/max(1,int(d/2))
                    D(x+random.uniform(-1.0,1.0), y+k*2, 1.1, mix((170,208,214),(60,96,112),v), 0.30*(1-v))
            x+=3.0

    # ---------- lake ----------
    for y in range(int(HY),CH,2):
        t=(y-HY)/(CH-HY)
        R(0,y,CW,3, mix((12,22,40),(4,7,16), t))
    # lay the reflections into the water now that the water exists
    ops.extend(refl); refl.clear()
    # gentle ripples that break the reflection without erasing it
    for i in range(34):
        y=HY+random.uniform(6,(CH-HY)*0.92)
        t=(y-HY)/(CH-HY)
        w=random.uniform(40,210)*(0.35+t)
        x=random.uniform(-40,CW)
        c=mix((52,86,96),(18,34,48), t)
        for k in range(3):
            D(x+w*k/3.0, y, 1.2+t*1.4, c, 0.35)
        L(x,y,x+w,y, 0.8+t*0.9, c)
    for i in range(9):
        y=HY+random.uniform(6,(CH-HY)*0.30)
        L(random.uniform(0,CW), y, random.uniform(0,CW)+random.uniform(20,80), y, 0.8, (120,176,170))
    # glassy horizon line
    L(0,HY,CW,HY,1.4,(120,190,180))
    # ---------- foreground shore ----------
    for y in range(int(CH*0.93),CH,2):
        R(0,y,CW,3,(4,6,12))
    for i in range(50):
        x=random.uniform(0,CW); y=CH*random.uniform(0.935,0.995)
        D(x,y,random.uniform(3,11),(3,5,10),0.95)

async def main():
    t0=time.time(); build()
    print(f"{len(ops)} ops built in {time.time()-t0:.1f}s",flush=True)
    if VISIBLE:
        from engine import launch_brave
        import urllib.request
        try: urllib.request.urlopen("http://localhost:9231/json/version",timeout=1); up=True
        except Exception: up=False
        if not up: launch_brave(9231,size=(1560,1010)); await asyncio.sleep(2.0)
        br=Browser(9231); await br.connect(); tab=await br.existing_page("replay") or await br.new_tab("replay")
    else:
        br=Browser(9222); await br.connect(); tab=await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r="+str(int(time.time())))
    await tab.measure_canvas(); await tab.resize_canvas(CW,CH)
    t1=time.time()
    for i in range(0,len(ops),8000):
        tab.fast(ops[i:i+8000])
        if i%40000==0: await tab.sync()
    await tab.sync()
    dt=time.time()-t1
    print(f"DONE {len(ops)} ops in {dt:.2f}s = {len(ops)/dt:,.0f} ops/s",flush=True)
    await tab.png("aurora.png")
    await br.close()
asyncio.run(main())
