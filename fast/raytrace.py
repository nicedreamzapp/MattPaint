"""A real raytracer: physically computed reflection, shadows and specular.
Rendered with numpy, then painted into MattPaint as run-length rects.
"""
import asyncio, sys, time, math
import numpy as np
from engine import Browser

W=int(sys.argv[1]) if len(sys.argv)>1 else 1200
H=int(sys.argv[2]) if len(sys.argv)>2 else 750
VISIBLE = "--hidden" not in sys.argv
AA=2                     # supersampling factor

def norm(v):
    return v/np.linalg.norm(v,axis=-1,keepdims=True).clip(1e-9)

# ---- scene ----
SPHERES=[
    # centre, radius, colour, reflectivity, gloss
    (np.array([ 0.00, 1.00, 0.0]), 1.00, np.array([0.92,0.93,0.96]), 0.85, 256),  # chrome
    (np.array([-2.15, 0.70,-1.1]), 0.70, np.array([0.85,0.18,0.15]), 0.30, 128),  # red
    (np.array([ 1.95, 0.62,-0.9]), 0.62, np.array([0.13,0.35,0.80]), 0.35, 160),  # blue
    (np.array([ 1.05, 0.34, 1.5]), 0.34, np.array([0.95,0.76,0.16]), 0.45, 200),  # gold
    (np.array([-1.15, 0.30, 1.7]), 0.30, np.array([0.10,0.62,0.42]), 0.25, 120),  # green
]
LIGHT=norm(np.array([[-0.45,0.80,0.42]]))[0]
SUN_C=np.array([1.0,0.96,0.88])

def sky(d):
    t=(d[...,1].clip(-1,1)+1)*0.5
    top=np.array([0.22,0.42,0.78]); bot=np.array([0.78,0.86,0.96])
    c=bot[None,:]*(1-t)[...,None]+top[None,:]*t[...,None]
    sun=np.clip((d*LIGHT[None,:]).sum(-1),0,1)**900
    halo=np.clip((d*LIGHT[None,:]).sum(-1),0,1)**26
    return c + SUN_C[None,:]*(sun*24.0+halo*0.28)[...,None]

def trace_spheres(o,d):
    """nearest sphere hit; returns t, index"""
    best=np.full(d.shape[0],np.inf); idx=np.full(d.shape[0],-1,dtype=np.int32)
    for i,(c,r,_,_,_) in enumerate(SPHERES):
        oc=o-c[None,:]
        b=(oc*d).sum(-1); cc=(oc*oc).sum(-1)-r*r
        disc=b*b-cc
        m=disc>0
        if not m.any(): continue
        sq=np.sqrt(np.maximum(disc,0))
        t=-b-sq
        t2=-b+sq
        t=np.where(t>1e-3,t,t2)
        hit=m&(t>1e-3)&(t<best)
        best=np.where(hit,t,best); idx=np.where(hit,i,idx)
    return best,idx

def plane_t(o,d):
    with np.errstate(divide='ignore',invalid='ignore'):
        t=-o[...,1]/d[...,1]
    t=np.where((d[...,1]<-2e-3)&(t>1e-3)&(t<160.0),t,np.inf)   # far clip keeps p finite
    return t

def shadowed(p,ldir):
    o=p+ldir[None,:]*1e-3
    d=np.broadcast_to(ldir[None,:],o.shape)
    t,_=trace_spheres(o,d)
    return t<np.inf

def checker(p):
    c=((np.floor(p[...,0]*0.5)+np.floor(p[...,2]*0.5))%2)
    a=np.array([0.86,0.86,0.88]); b=np.array([0.13,0.14,0.16])
    return b[None,:]*(1-c)[...,None]+a[None,:]*c[...,None]

def shade(o,d,depth=0):
    ts,si=trace_spheres(o,d)
    tp=plane_t(o,d)
    col=sky(d)
    # ---- plane ----
    mp=(tp<ts)&(tp<np.inf)
    if mp.any():
        p=o[mp]+d[mp]*tp[mp][:,None]
        n=np.zeros_like(p); n[:,1]=1.0
        base=checker(p)
        sh=shadowed(p,LIGHT)
        diff=np.clip(n@LIGHT,0,1)*(~sh)
        amb=0.34+0.22*np.clip(n@np.array([0,1,0]),0,1)
        c=base*(amb[...,None]+diff[:,None]*0.85)
        if depth<2:
            rd=norm(d[mp]-2*(d[mp]*n).sum(-1)[:,None]*n)
            c=c*0.72+shade(p+n*1e-3,rd,depth+1)*0.28
        fog=np.clip(tp[mp]/34.0,0,1)[:,None]
        c=c*(1-fog)+sky(d[mp])*fog
        col[mp]=c
    # ---- spheres ----
    ms=(ts<=tp)&(si>=0)
    if ms.any():
        p=o[ms]+d[ms]*ts[ms][:,None]
        idx=si[ms]
        n=np.zeros_like(p); base=np.zeros_like(p)
        refl=np.zeros(p.shape[0]); gloss=np.zeros(p.shape[0])
        for i,(c0,r,col0,rf,gl) in enumerate(SPHERES):
            m=idx==i
            if not m.any(): continue
            n[m]=norm(p[m]-c0[None,:]); base[m]=col0[None,:]
            refl[m]=rf; gloss[m]=gl
        sh=shadowed(p+n*1e-3,LIGHT)
        diff=np.clip((n*LIGHT[None,:]).sum(-1),0,1)*(~sh)
        h=norm(LIGHT[None,:]-d[ms])
        spec=np.clip((n*h).sum(-1),0,1)**gloss*(~sh)
        fres=0.04+0.96*(1-np.clip((-d[ms]*n).sum(-1),0,1))**5
        c=base*(0.22+0.80*diff[:,None])+SUN_C[None,:]*spec[:,None]*1.15
        if depth<3:
            rd=norm(d[ms]-2*(d[ms]*n).sum(-1)[:,None]*n)
            rc=shade(p+n*1e-3,rd,depth+1)
            k=np.clip(refl+fres*0.55,0,1)[:,None]
            c=c*(1-k)+rc*k
        col[ms]=c
    return col

def render():
    aspect=W/H
    cam=np.array([0.0,1.55,5.6]); look=np.array([0.0,0.85,0.0])
    fwd=norm((look-cam)[None,:])[0]
    right=norm(np.cross(fwd,np.array([0,1,0]))[None,:])[0]
    up=np.cross(right,fwd)
    fov=math.radians(42); sh_=math.tan(fov/2)
    Wx,Hy=W*AA,H*AA
    ys,xs=np.mgrid[0:Hy,0:Wx]
    px=((xs+0.5)/Wx*2-1)*sh_*aspect
    py=(1-(ys+0.5)/Hy*2)*sh_
    d=norm(fwd[None,None,:]+right[None,None,:]*px[...,None]+up[None,None,:]*py[...,None]).reshape(-1,3)
    o=np.broadcast_to(cam[None,:],d.shape).copy()
    out=np.zeros((d.shape[0],3))
    CH_=200000
    for i in range(0,d.shape[0],CH_):
        c=shade(o[i:i+CH_],d[i:i+CH_])
        out[i:i+CH_]=np.nan_to_num(c, nan=0.0, posinf=6.0, neginf=0.0)
    bad=int((~np.isfinite(out)).sum()); 
    out=np.nan_to_num(out, nan=0.0, posinf=6.0, neginf=0.0)
    out=np.clip(out,0.0,60.0)
    if bad: print('sanitised',bad,'bad samples',flush=True)
    hdr=out.reshape(Hy,Wx,3)
    hdr=hdr.reshape(H,AA,W,AA,3).mean(axis=(1,3))           # downsample = anti-aliasing
    hdr=np.nan_to_num(hdr, nan=0.0, posinf=8.0, neginf=0.0)
    hdr=np.maximum(hdr,0.0)*1.15                            # exposure
    ldr=hdr/(hdr+1.0)                                       # Reinhard tonemap
    ldr=np.power(np.clip(ldr*1.45,0.0,1.0), 1.0/2.2)        # lift + gamma
    return np.clip(ldr*255.0,0,255).astype(np.uint8)

def to_ops(img):
    ops=[]
    q=img//3*3                                              # quantise so runs stay long
    for y in range(H):
        row=q[y]
        st=0
        cur=row[0]
        for x in range(1,W):
            if not (row[x]==cur).all():
                ops.append([0,st,y,x-st,1,int(cur[0]),int(cur[1]),int(cur[2])])
                st=x; cur=row[x]
        ops.append([0,st,y,W-st,1,int(cur[0]),int(cur[1]),int(cur[2])])
    return ops

async def main():
    t0=time.time(); img=render(); print(f"raytraced {W}x{H} (AA{AA}) in {time.time()-t0:.1f}s",flush=True)
    ops=to_ops(img); print(f"{len(ops)} ops",flush=True)
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
    await tab.measure_canvas(); await tab.resize_canvas(W,H)
    t1=time.time()
    for i in range(0,len(ops),8000):
        tab.fast(ops[i:i+8000])
        if i%40000==0: await tab.sync()
    await tab.sync()
    print(f"painted in {time.time()-t1:.2f}s",flush=True)
    await tab.png("raytrace.png")
    await br.close()
asyncio.run(main())
