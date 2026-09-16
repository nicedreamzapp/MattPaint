"""3D triptych done properly: the photo is taller than the panels. Panels show the top part;
the REAL bottom of the photo (trunk + tusks) is painted on the white board below the frames,
masked to the subject, so it genuinely breaks out of the picture.
"""
import asyncio, sys, time
import numpy as np
from PIL import Image
from engine import Browser

REF=sys.argv[1] if len(sys.argv)>1 else "user_elephant.jpg"
CW=int(sys.argv[2]) if len(sys.argv)>2 else 1500
CH=int(sys.argv[3]) if len(sys.argv)>3 else 1020
VISIBLE = "--hidden" not in sys.argv   # on-screen by DEFAULT; hiding must be explicit
MARG_X,MARG_TOP,GAP=46,38,20
BREAK_H=170                      # how far the subject spills past the frames

async def main():
    span_w=CW-2*MARG_X
    pw=(span_w-2*GAP)//3
    panel_h=CH-MARG_TOP-BREAK_H-26
    total_h=panel_h+BREAK_H
    im=Image.open(REF).convert("RGB")
    ar_c,ar_i=span_w/total_h, im.width/im.height
    if ar_i>ar_c:
        w=int(im.height*ar_c); im=im.crop(((im.width-w)//2,0,(im.width+w)//2,im.height))
    else:
        h=int(im.width/ar_c); im=im.crop((0,(im.height-h)//2,im.width,(im.height+h)//2))
    src=im.resize((span_w,total_h),Image.LANCZOS)
    a=np.asarray(src).astype(np.int16)
    ops=[]
    def R(x,y,w,h,c): ops.append([0,int(x),int(y),int(max(1,w)),int(max(1,h)),int(c[0]),int(c[1]),int(c[2])])
    R(0,0,CW,CH,(252,252,252))
    CELL=2
    # ---- panels (top part of the photo) ----
    for i in range(3):
        px0=MARG_X+i*(pw+GAP); sx0=i*(pw+GAP)
        for y in range(0,panel_h,CELL):
            for x in range(0,pw,CELL):
                c=a[y:y+CELL, sx0+x:sx0+x+CELL].reshape(-1,3).mean(0)
                R(px0+x,MARG_TOP+y,CELL,CELL,c)
        for k in range(5): R(px0+4+k,MARG_TOP+panel_h+k,pw-8,1,(216,216,216))
    # ---- breakout: the real lower part of the photo, subject only, on the white board ----
    def is_subj(px):
        r,g,b=int(px[0]),int(px[1]),int(px[2]); v=(r+g+b)/3
        gray=(max(r,g,b)-min(r,g,b))<50
        return gray and (v<152 or v>172)     # hide OR tusk; excludes the warm blurry grass
    fg=[]
    BX0,BX1=int(span_w*0.16),int(span_w*0.82)      # keep the spill to the trunk/tusk zone
    for y in range(panel_h,total_h,CELL):
        mask=[x for x in range(BX0,BX1,CELL) if is_subj(a[y,x])]
        if not mask: continue
        # close small holes: keep contiguous runs, bridging gaps under 46px
        runs=[]; st=mask[0]; prev=mask[0]
        for x in mask[1:]:
            if x-prev>46: runs.append((st,prev)); st=x
            prev=x
        runs.append((st,prev))
        for r0,r1 in runs:
            if r1-r0 < 24: continue                 # drop specks
            for x in range(r0,r1+1,CELL):
                px=a[y,x]
                fg.append([0,MARG_X+x,MARG_TOP+y,CELL,CELL,int(px[0]),int(px[1]),int(px[2])])
    # contact shadow under the spill
    xs=[o[1] for o in fg]
    if xs:
        lo,hi=min(xs),max(xs)
        for k in range(12):
            fg.append([0,lo-24,MARG_TOP+total_h+2+int(k*0.8),(hi-lo)+48,2,236,236,236])
    ops+=fg
    print(f"{len(ops)} ops ({len(fg)} breakout)",flush=True)
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
    await tab.measure_canvas(); t0=time.time(); await tab.resize_canvas(CW,CH)
    for i in range(0,len(ops),6000):
        tab.fast(ops[i:i+6000])
        if i%30000==0: await tab.sync()
    tab.fast_commit(); await tab.sync()
    print(f"DONE {len(ops)} ops in {time.time()-t0:.2f}s",flush=True)
    await tab.png("trip3d.png")
    if not VISIBLE: await tab.close()
    await br.close()
asyncio.run(main())
