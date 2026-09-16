"""Region-aware reproduction, paced coarse->fine, ON SCREEN, recorded to mp4.
Builds a blocky preview then resolves into focus, then sharpens edges.
"""
import asyncio, sys, time, math, os, base64, glob, subprocess
import numpy as np
from PIL import Image
from engine import Browser, launch_brave

REF = sys.argv[1] if len(sys.argv) > 1 else "ref_eagle.png"
CW = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
CH = int(sys.argv[3]) if len(sys.argv) > 3 else 600
tab = None

def load_ref():
    im = Image.open(REF).convert("RGB")
    arc, ari = CW/CH, im.width/im.height
    if ari > arc:
        w = int(im.height*arc); im = im.crop(((im.width-w)//2,0,(im.width+w)//2,im.height))
    else:
        h = int(im.width/arc); im = im.crop((0,(im.height-h)//2,im.width,(im.height+h)//2))
    return im.resize((CW, CH), Image.LANCZOS)

def mosaic(arr, cell):
    ops=[]
    for y in range(0, CH, cell):
        for x in range(0, CW, cell):
            c = arr[y:y+cell, x:x+cell].reshape(-1,3).mean(0)
            ops.append([0, int(x), int(y), int(cell), int(cell), int(c[0]), int(c[1]), int(c[2])])
    return ops

def edges(arr):
    g = arr.astype(np.float32).mean(2)
    gx = np.zeros_like(g); gy = np.zeros_like(g)
    gx[:,1:-1]=g[:,2:]-g[:,:-2]; gy[1:-1,:]=g[2:,:]-g[:-2,:]
    mag=np.hypot(gx,gy); ops=[]
    for cy in range(2,CH-2,3):
        for cx in range(2,CW-2,3):
            if mag[cy,cx]<26: continue
            dx,dy=gx[cy,cx],gy[cy,cx]; n=math.hypot(dx,dy)
            if n<1e-3: continue
            ux,uy=-dy/n,dx/n; L=2.6; c=arr[cy,cx]
            ops.append([1, round(float(cx-ux*L),1), round(float(cy-uy*L),1), round(float(cx+ux*L),1), round(float(cy+uy*L),1), 1.6, int(c[0]),int(c[1]),int(c[2])])
    return ops

async def main():
    global tab
    im=load_ref(); im.save("ref_fit.png")
    arr=np.asarray(im,dtype=np.int16)
    passes=[mosaic(arr,24), mosaic(arr,10), mosaic(arr,4), edges(arr)]
    total=sum(len(p) for p in passes)
    print(f"passes: {[len(p) for p in passes]} = {total} ops", flush=True)
    proc=launch_brave(9231,size=(1500,900)); await asyncio.sleep(2.0)
    br=Browser(9231); await br.connect()
    tab=await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r="+str(int(time.time())))
    await tab.measure_canvas()
    # recorder
    FR="rec2"; os.makedirs(FR,exist_ok=True)
    for f in glob.glob(f"{FR}/*.jpg"): os.remove(f)
    stop=asyncio.Event()
    async def grab():
        i=0
        while not stop.is_set():
            try:
                c=tab.canvas
                r=await tab.call("Page.captureScreenshot",{"format":"jpeg","quality":72,
                    "clip":{"x":c["x"],"y":c["y"],"width":c["w"],"height":c["h"],"scale":1},"captureBeyondViewport":True})
                open(f"{FR}/f{i:04d}.jpg","wb").write(base64.b64decode(r["data"])); i+=1
            except Exception: pass
            await asyncio.sleep(0.05)
        return i
    await tab.resize_canvas(CW,CH)
    g=asyncio.create_task(grab())
    t0=time.time()
    # pace: total build ~14s across passes
    for pi,ops in enumerate(passes):
        # subdivide each pass into ~30 chunks with a small delay so it visibly builds
        nch=30
        step=max(1,len(ops)//nch)
        for i in range(0,len(ops),step):
            tab.fast(ops[i:i+step]); await tab.sync()
            await asyncio.sleep(0.06)
    tab.fast_commit(); await tab.sync()
    dt=time.time()-t0
    await asyncio.sleep(0.6)
    stop.set(); nfr=await g
    print(f"built in {dt:.1f}s, {nfr} frames", flush=True)
    await tab.png("repro2_rec.png")
    await br.close()   # leave window open
asyncio.run(main())
