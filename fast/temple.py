import asyncio, math, random
from art import Art, mix, paint, TOPBAR
random.seed(77)
W,H=1400,920
a=Art(W,H,"THE GLASS CHOIR")
R,L,D=a.R,a.L,a.D
VX,VY=W*0.5, TOPBAR+(H-TOPBAR)*0.56          # vanishing point
FLOOR=H*0.80
GLASS=[]   # (u, v, colour) sampled from the rose window, for the floor light map
JEWELS=[(206,52,60),(230,138,40),(240,206,72),(70,150,96),(48,110,196),(120,64,168),(228,110,150),(70,190,190)]

def build():
    # ---- dim stone interior ----
    for y in range(TOPBAR,H,2):
        t=(y-TOPBAR)/(H-TOPBAR)
        R(0,y,W,3, mix((26,26,34),(12,12,16), t**0.7))
    # ---- far wall with the rose window ----
    wall_w, wall_h = W*0.34, (H-TOPBAR)*0.62
    wx0,wy0 = VX-wall_w/2, VY-wall_h*0.60
    for y in range(int(wy0), int(wy0+wall_h), 2):
        t=(y-wy0)/wall_h
        R(wx0, y, wall_w, 3, mix((54,52,58),(30,29,34), t))
    # rose window
    RCX,RCY,RR = VX, VY-wall_h*0.20, wall_w*0.30
    for k in range(70):                              # outer glow into the room
        u=k/70.0
        D(RCX,RCY, RR*3.0*(1-u)+8, (200,170,220), 0.010*(u**1.5))
    rings=[(1.00,0.74,16),(0.72,0.46,12),(0.44,0.20,8)]
    for (ro,ri,seg) in rings:
        for s in range(seg):
            a0=s*(6.2832/seg); a1=(s+1)*(6.2832/seg)
            col=JEWELS[(s+int(ro*7))%len(JEWELS)]
            steps=int(RR*(ro-ri)/1.4)+1
            for k in range(steps):
                rr=RR*(ri+(ro-ri)*k/steps)
                arc=int(rr*(a1-a0)/1.4)+1
                for j in range(arc):
                    ang=a0+(a1-a0)*j/arc
                    glow=0.55+0.45*math.sin(ang*3+ro*5)
                    cc=mix(col,(255,250,235), glow*0.45)
                    D(RCX+math.cos(ang)*rr, RCY+math.sin(ang)*rr, 1.5, cc, 1.0)
                    if j%3==0 and k%3==0:
                        GLASS.append((math.cos(ang)*rr/RR, math.sin(ang)*rr/RR, cc, glow))
        # lead came between rings
        for s in range(seg):
            ang=s*(6.2832/seg)
            L(RCX+math.cos(ang)*RR*ri, RCY+math.sin(ang)*RR*ri,
              RCX+math.cos(ang)*RR*ro, RCY+math.sin(ang)*RR*ro, 2.0, (16,14,18))
        for j in range(int(RR*ro*2)):
            ang=j*(6.2832/max(1,int(RR*ro*2)))
            D(RCX+math.cos(ang)*RR*ro, RCY+math.sin(ang)*RR*ro, 1.6, (16,14,18))
    for r in range(int(RR*0.20),0,-1):               # blazing centre
        D(RCX,RCY,r, mix((255,252,240),(255,214,150), r/max(1,RR*0.20)), 0.5)
    # lancet windows flanking
    for side in (-1,1):
        lx=VX+side*wall_w*0.36
        ly0,ly1 = VY-wall_h*0.02, VY+wall_h*0.34
        lw=wall_w*0.10
        for y in range(int(ly0),int(ly1),2):
            t=(y-ly0)/(ly1-ly0)
            col=JEWELS[int(t*7)%len(JEWELS)]
            R(lx-lw/2, y, lw, 3, mix(col,(255,246,226), 0.35+0.3*math.sin(t*9)))
        for k in range(int(lw)):                      # arched top
            v=k/lw
            hw=lw/2*math.sin(math.pi*v)
            R(lx-hw, ly0-lw*0.5+k*0.5, hw*2, 1.6, mix(JEWELS[k%8],(255,244,220),0.4))
    # ---- receding columns + arches (one-point perspective) ----
    def col_pair(depth):
        """depth 0 = nearest, 1 = far"""
        s_=1.0-depth
        x_off = W*0.40*s_ + W*0.085
        wdt   = 108*s_ + 16
        top   = VY - (VY-TOPBAR)*(0.92*s_+0.16)
        bot   = FLOOR + (H-FLOOR)*(s_*0.92)
        for side in (-1,1):
            cx = VX + side*x_off
            base=mix((40,38,45),(84,81,92), s_)
            # shaft with fluting
            for y in range(int(top), int(bot), 2):
                n=int(wdt/2.4)+1
                for k in range(n):
                    v=k/max(1,n-1)
                    lit=0.30 if side<0 else 0.70
                    shade=1.0-abs(v-lit)*1.5
                    flute=0.86+0.14*math.sin(v*math.pi*7 + side*0.4)
                    grain=0.94+0.06*math.sin(y*0.21+v*11.0+cx*0.03)      # marble variation
                    c=mix(mix(base,(10,10,14),0.6), mix(base,(196,190,204),0.66), max(0.0,shade)*flute*grain)
                    if (y+int(cx)) % max(40,int(96*s_)) < 2: c=mix(c,(12,12,16),0.45)   # block seam
                    R(cx-wdt/2+wdt*v, y, 2.6, 2.6, c)
            # base block and capital
            for (by,bh,bw) in [(bot-8*s_-10, 14*s_+10, wdt*1.34), (top-16*s_-10, 18*s_+10, wdt*1.42)]:
                for k in range(int(bh)):
                    v=k/max(1,bh)
                    R(cx-bw/2, by+k, bw, 1.6, mix(mix(base,(190,184,198),0.55), mix(base,(16,16,20),0.5), v))
            # semicircular arch springing from this capital toward the centre
            span=abs(VX-cx); rise=span*0.62
            th=10*s_+4
            for k in range(110):
                t=k/110.0
                ang=math.pi*(0.5 - 0.5*t) if side<0 else math.pi*(0.5 + 0.5*t)
                ax=VX - side*span*math.cos(math.pi*0.5*t)
                ay=(top-16*s_-10) - rise*math.sin(math.pi*0.5*t)
                for j in range(int(th)):
                    w=j/max(1,th)
                    D(ax, ay+j*1.5, th*0.55, mix(mix(base,(180,174,190),0.5), mix(base,(12,12,16),0.5), w))
        return
    for d in [0.90,0.80,0.68,0.54,0.38,0.20,0.02]:
        col_pair(d)

    # ---- floor ----
    for y in range(int(FLOOR),H,2):
        t=(y-FLOOR)/(H-FLOOR)
        R(0,y,W,3, mix((40,38,44),(16,15,19), t))
    # stone flags receding toward the vanishing point
    rows=[]
    for k in range(16):
        t=k/16.0
        rows.append(VY+(H-VY)*(t**2.0))
    rows.append(H)
    for i in range(len(rows)-1):
        y0,y1=rows[i],rows[i+1]
        depth=i/len(rows)
        ncol=max(3,int(16-depth*6))
        for c in range(ncol):
            u0=(c/ncol)*2-1; u1=((c+1)/ncol)*2-1
            spread0=(y0-VY)/(H-VY)*W*1.5+W*0.05
            spread1=(y1-VY)/(H-VY)*W*1.5+W*0.05
            xa=VX+u0*spread0; xb=VX+u1*spread0
            xc=VX+u0*spread1; xd=VX+u1*spread1
            tone=mix((54,52,60),(24,23,28), depth) if (c+i)%2==0 else mix((44,42,50),(18,17,22), depth)
            steps=int(y1-y0)+1
            for k in range(steps):
                v=k/max(1,steps-1)
                lx=xa+(xc-xa)*v; rx2=xb+(xd-xb)*v
                R(lx, y0+ (y1-y0)*v, max(1,rx2-lx), 2.0, tone)
            L(xa,y0,xc,y1,1.0,(16,15,19))
        L(0,y1,W,y1,1.0,(16,15,19))
    # ---- LIGHT MAP: the rose window projected onto the floor in perspective ----
    col_centres=[VX + sd*(W*0.40*(1.0-d) + W*0.085) for d in [0.90,0.80,0.68,0.54,0.38,0.20,0.02] for sd in (-1,1)]
    col_widths =[108*(1.0-d)+16 for d in [0.90,0.80,0.68,0.54,0.38,0.20,0.02] for _ in (0,1)]
    def occluded(x):
        for cx0,cw0 in zip(col_centres,col_widths):
            if abs(x-cx0) < cw0*0.62: return True
        return False
    # soft coloured pools where each pane's light lands
    for (u,v,cc,glow) in GLASS:
        t = max(0.02,min(1.0, 0.10 + 0.90*(0.5 - v*0.5)))
        fy = VY + (H-VY)*(t**1.55)
        spread = (fy-VY)/(H-VY)*W*0.78 + W*0.03
        fx = VX + u*spread
        if fx<-80 or fx>W+80: continue
        occ = 0.15 if occluded(fx) else 1.0
        base_a = 0.010*glow*occ*(0.30+0.70*t)
        # many small overlapping dabs = a soft pool, stretched toward the viewer
        for q in range(22):
            rr=random.random()**0.6
            ang=random.uniform(0,6.2832)
            px=fx+math.cos(ang)*(10+40*t)*rr*1.7
            py=fy+math.sin(ang)*(10+40*t)*rr*0.55
            if occluded(px): continue
            D(px,py, random.uniform(3,9)+6*t, cc, base_a)
        D(fx,fy, 4+7*t, mix(cc,(255,252,244),0.30), base_a*1.6)
    # the beams, visible only because dust hangs in them: soft, broken, fading
    for (u,v,cc,glow) in GLASS[::3]:
        t = max(0.02,min(1.0, 0.10 + 0.90*(0.5 - v*0.5)))
        fy = VY + (H-VY)*(t**1.55)
        spread = (fy-VY)/(H-VY)*W*0.78 + W*0.03
        fx = VX + u*spread
        for k in range(90):
            p=k/90.0
            bx = RCX + (fx-RCX)*p + random.uniform(-3,3)
            by = RCY + (fy-RCY)*p + random.uniform(-3,3)
            if occluded(bx): continue
            broken = 0.30+0.70*max(0.0, math.sin(p*7.0+u*9.0))
            D(bx, by, 1.6+7.0*p, cc, 0.0045*glow*broken*(1-p*0.5))
    # dust motes in the beams
    for i in range(700):
        x=VX+random.gauss(0,W*0.16); y=random.uniform(VY-120,H)
        if x<0 or x>W: continue
        if occluded(x): continue
        D(x,y, random.uniform(0.6,1.8), (240,230,214), random.uniform(0.04,0.28))

build()
asyncio.run(paint(a))
