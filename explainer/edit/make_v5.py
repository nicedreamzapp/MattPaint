"""MattPaint explainer v5 (2026-11-02): the crew story, bright footage, no code walls.
Matt: "too much code running... boring... doesn't talk about our tools in a way normal people understand",
"colors dull, dark and gloomy". Each narration paragraph gets a segment; a colored crew bar shows who is working."""
import os, subprocess, json, math, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

E = os.path.expanduser("~/Desktop/PROJECTS/MattPaint/explainer"); G = os.path.expanduser("~/Desktop/PROJECTS/MattPaint/gallery/films")
OUT = f"{E}/edit5"; SEG = f"{OUT}/seg"; os.makedirs(SEG, exist_ok=True)
W, H, FPS, GAP = 1920, 1080, 30, 0.7
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"; REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
def dur(p): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).strip())
def ff(*a): subprocess.run(["ffmpeg","-y","-v","error",*a], check=True)
nar = [f"{E}/narration5/p{i}.wav" for i in range(1, 11)]
D = [dur(p) + GAP for p in nar]

CREW = [("THE WRITER", "you, one sentence", (255, 196, 61)),
        ("SET BUILDER", "Claude Opus", (255, 112, 67)),
        ("LIGHTING", "Blender", (255, 214, 0)),
        ("PAINTER", "MattPaint", (77, 208, 225)),
        ("COMPOSER", "Song Forge", (171, 71, 188)),
        ("VOICE", "my cloned voice", (102, 187, 106)),
        ("EDITOR", "Story Forge", (66, 165, 245))]

def font(p, s): return ImageFont.truetype(p, s)

def crew_bar(active, title=None, sub=None):
    """transparent overlay: the crew strip along the bottom (active one lit) + a big role chip top-left"""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    n = len(CREW); pw, ph, gap = 248, 74, 14; x0 = (W - (n * pw + (n - 1) * gap)) / 2; y0 = H - ph - 34
    for i, (role, who, col) in enumerate(CREW):
        x = x0 + i * (pw + gap); on = (i == active)
        fill = col + (240,) if on else (20, 20, 24, 170)
        d.rounded_rectangle((x, y0, x + pw, y0 + ph), 18, fill=fill, outline=col + (255,), width=3)
        tc = (20, 20, 20, 255) if on else col + (255,)
        f1 = font(BOLD, 22); f2 = font(REG, 19)
        for txt, f, yy in ((role, f1, y0 + 12), (who, f2, y0 + 42)):
            b = d.textbbox((0, 0), txt, font=f); d.text((x + (pw - (b[2] - b[0])) / 2, yy - b[1]), txt, font=f, fill=tc if txt == role else ((40, 40, 40, 255) if on else (220, 220, 220, 255)))
        if i < n - 1:
            ax = x + pw + 2; ay = y0 + ph / 2
            d.polygon([(ax, ay - 6), (ax + gap - 4, ay), (ax, ay + 6)], fill=(255, 255, 255, 160))
    if title:
        col = CREW[active][2] if active is not None and active >= 0 else (255, 255, 255)
        f1 = font(BOLD, 64); f2 = font(BOLD, 34)
        b1 = d.textbbox((0, 0), title, font=f1); b2 = d.textbbox((0, 0), sub or "", font=f2)
        wbox = max(b1[2], b2[2]) + 70
        d.rounded_rectangle((50, 46, 50 + wbox, 46 + 150 if sub else 46 + 100), 22, fill=(10, 10, 14, 185))
        d.rectangle((50, 46, 62, 46 + (150 if sub else 100)), fill=col + (255,))
        d.text((90, 62 - b1[1]), title, font=f1, fill=col + (255,))
        if sub: d.text((92, 138 - b2[1]), sub, font=f2, fill=(240, 240, 240, 255))
    return im

def save_png(im, name): p = f"{OUT}/{name}.png"; im.save(p); return p

def frames_to_mp4(frames_dir, out):
    ff("-framerate", str(FPS), "-i", f"{frames_dir}/%05d.jpg", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out)

def still_seg(name, d, layers, ov, zoom=(1.0, 1.08), xfade=None):
    """Ken-Burns push on a still; layers = [img] or [imgA, imgB] crossfaded at xfade=(start,end) fraction"""
    fd = f"{OUT}/f_{name}"; os.makedirs(fd, exist_ok=True)
    ims = [Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS) for p in layers]
    n = int(d * FPS)
    for k in range(n):
        t = k / max(n - 1, 1); z = zoom[0] + (zoom[1] - zoom[0]) * t
        if len(ims) == 1: base = ims[0]
        else:
            a = 0 if t < xfade[0] else 1 if t > xfade[1] else (t - xfade[0]) / (xfade[1] - xfade[0])
            idx = min(int(a * (len(ims) - 1)), len(ims) - 2); la = a * (len(ims) - 1) - idx
            base = Image.blend(ims[idx], ims[idx + 1], la)
        cw, ch = W / z, H / z; cx, cy = W / 2, H / 2 - 40 * t
        fr = base.crop((cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)).resize((W, H), Image.LANCZOS).convert("RGBA")
        fr.alpha_composite(ov); fr.convert("RGB").save(f"{fd}/{k:05d}.jpg", quality=92)
    frames_to_mp4(fd, f"{SEG}/{name}.mp4")

FIT = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={FPS}"
def video_seg(name, src, d, ov_png=None, speed=None):
    s = dur(src); k = (d / s) if speed is None else 1 / speed
    if ov_png:
        ff("-i", src, "-i", ov_png, "-filter_complex", f"[0:v]setpts={k:.5f}*PTS,{FIT}[v];[v][1:v]overlay=0:0", "-t", f"{d:.3f}", "-an", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", f"{SEG}/{name}.mp4")
    else:
        ff("-i", src, "-vf", f"setpts={k:.5f}*PTS,{FIT}", "-t", f"{d:.3f}", "-an", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", f"{SEG}/{name}.mp4")

def wav_mono(p):
    a = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", "24000", "-f", "f32le", "-"], capture_output=True).stdout, np.float32)
    return a

def wave_seg(name, d, bg_png, sources, ov_list):
    """animated sound bars over a blurred frame; sources = [(wav, offset_s, color)] switch halfway"""
    fd = f"{OUT}/f_{name}"; os.makedirs(fd, exist_ok=True)
    bg = Image.open(bg_png).convert("RGB").resize((W, H)).filter(ImageFilter.GaussianBlur(14))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (10, 8, 20)), 0.35)
    datas = [(wav_mono(w), off, col) for w, off, col in sources]
    def levels(a, i0):
        seg = a[i0:i0 + 2400] if 0 <= i0 and i0 + 2400 < len(a) else np.zeros(2400, np.float32)
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))[:600]
        return np.array([sp[int(600 * (j / bars) ** 1.6):int(600 * ((j + 1) / bars) ** 1.6) + 1].mean() for j in range(bars)])
    bars = 64
    # each source scaled to its own loudness, so a voice moves the bars as much as a full orchestra
    peaks = []
    for a, off, col in datas:
        smp = [levels(a, int(x * 24000)) for x in np.arange(0, len(a) / 24000 - 0.2, 0.25)]
        peaks.append(np.percentile(np.log1p(np.array(smp)), 97) + 1e-6)
    n = int(d * FPS)
    for k in range(n):
        t = k / FPS; part = 0 if t < d / 2 or len(datas) == 1 else 1
        a, off, col = datas[part]; i0 = int((off + (t if part == 0 else t - d / 2)) * 24000)
        lv = np.clip(np.log1p(levels(a, i0)) / peaks[part], 0, 1) ** 1.5
        fr = bg.copy().convert("RGBA"); dr = ImageDraw.Draw(fr)
        bw = 18; gap = 8; x0 = (W - bars * (bw + gap)) / 2; cy = H / 2
        for j in range(bars):
            h = 20 + lv[j] * 360
            dr.rounded_rectangle((x0 + j * (bw + gap), cy - h / 2, x0 + j * (bw + gap) + bw, cy + h / 2), 8, fill=col + (235,))
        fr.alpha_composite(ov_list[part]); fr.convert("RGB").save(f"{fd}/{k:05d}.jpg", quality=92)
    frames_to_mp4(fd, f"{SEG}/{name}.mp4")

def type_seg(name, d, text, ov):
    fd = f"{OUT}/f_{name}"; os.makedirs(fd, exist_ok=True)
    n = int(d * FPS); f = font(BOLD, 58)
    words = text.split(); lines = []; cur = ""
    for w_ in words:
        if len(cur + " " + w_) > 34: lines.append(cur); cur = w_
        else: cur = (cur + " " + w_).strip()
    lines.append(cur); full = "\n".join(lines)
    for k in range(n):
        t = k / max(n - 1, 1)
        g = Image.new("RGB", (W, H)); gp = g.load()
        top = np.array([255, 140, 66]); bot = np.array([196, 43, 128])
        arr = np.zeros((H, W, 3), np.uint8)
        yy = np.linspace(0, 1, H)[:, None, None]; xx = np.linspace(0, 1, W)[None, :, None]
        mix = np.clip(0.6 * yy + 0.4 * xx + 0.08 * math.sin(t * 3), 0, 1)
        arr[:] = (top * (1 - mix) + bot * mix).astype(np.uint8)
        g = Image.fromarray(arr).convert("RGBA"); dr = ImageDraw.Draw(g)
        dr.rounded_rectangle((260, 300, W - 260, 700), 30, fill=(255, 255, 255, 235))
        shown = full[:int(len(full) * min(1, t / 0.75))]
        dr.multiline_text((320, 350), shown + ("|" if (k // 15) % 2 == 0 else ""), font=f, fill=(30, 30, 40, 255), spacing=22)
        g.alpha_composite(ov); g.convert("RGB").save(f"{fd}/{k:05d}.jpg", quality=92)
    frames_to_mp4(fd, f"{SEG}/{name}.mp4")

B = f"{E}/buildup"; FB = f"{G}/robot_bright/frames"
# 1 hook: the bright robot film
video_seg("s01", f"{G}/robot_bright/robot_bright.mp4", D[0], save_png(crew_bar(None), "ov01"))
# 2 the writer
type_seg("s02", D[1], "A giant robot has knelt in a forest so long that moss grows over it.", crew_bar(0, "THE WRITER", "one sentence, that's it"))
# 3 set builder: clay
still_seg("s03", D[2], [f"{B}/clay.png"], crew_bar(1, "THE SET BUILDER", "Claude Opus builds the world from shapes"))
# 4 props: clay -> materials
still_seg("s04", D[3], [f"{B}/clay.png", f"{B}/paint.png"], crew_bar(1, "PAINTING THE PROPS", "rust, moss, bark"), zoom=(1.08, 1.14), xfade=(0.1, 0.55))
# 5 lighting: materials -> lit, then the film
still_seg("s05", D[4], [f"{B}/paint.png", f"{B}/full.png"], crew_bar(2, "THE LIGHTING CREW", "Blender works out real sunlight"), zoom=(1.14, 1.0), xfade=(0.05, 0.5))
# 6 painter: one frame painted on a blank page
video_seg("s06", f"{E}/footage/slow_paint_bright/recording.mp4", D[5], save_png(crew_bar(3, "THE PAINTER", "MattPaint, line by line"), "ov06"))
# 7 composer, then the voice
wave_seg("s07", D[6], f"{FB}/0090.png", [(f"{E}/music/rise.wav", 2.0, (171, 71, 188)), (nar[6], D[6] / 2 - 0.25, (102, 187, 106))],
         [crew_bar(4, "THE COMPOSER", "Song Forge wrote the score"), crew_bar(5, "THE VOICE", "a copy of my voice, made locally")])
# 8 editor: the whole rising shot being painted, sped up
video_seg("s08", f"{E}/footage/rise_bright_paint/recording.mp4", D[7], save_png(crew_bar(6, "THE EDITOR", "Story Forge puts it together"), "ov08"))
# 9 first try vs now
lab = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(lab)
for x, t1, t2, col in ((40, "FIRST TRY", "4.5 hours · a pile of blocks", (255, 112, 67)), (970, "NOW", "7 minutes", (77, 208, 225))):
    dl.rounded_rectangle((x, 140, x + 910, 250), 20, fill=(10, 10, 14, 200)); dl.text((x + 30, 150), t1, font=font(BOLD, 48), fill=col + (255,)); dl.text((x + 30, 208), t2, font=font(REG, 30), fill=(240, 240, 240, 255))
lab.alpha_composite(crew_bar(None)); labp = save_png(lab, "ov09")
ff("-i", f"{G}/robot_forest/robot_forest.mp4", "-i", f"{G}/robot_bright/robot_bright.mp4", "-i", labp, "-filter_complex",
   f"[0:v]setpts={D[8]/10:.4f}*PTS,scale=950:-2[l];[1:v]setpts={D[8]/10:.4f}*PTS,scale=950:-2[r];"
   f"[l][r]hstack=inputs=2,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x101018,fps={FPS},setsar=1[v];[v][2:v]overlay=0:0",
   "-t", f"{D[8]:.3f}", "-an", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", f"{SEG}/s09.mp4")
# 10 outro: the forest film being painted, sped up, GitHub
ov10 = crew_bar(None, "FREE ON GITHUB", "nicedreamzapp/MattPaint · nicedreamzapp/story-forge")
video_seg("s10", f"{E}/footage/robot_bright_paint/recording.mp4", D[9], save_png(ov10, "ov10"))
# 11 the robot wakes, 12 end card
ff("-i", f"{G}/rise_bright/rise_bright.mp4", "-vf", FIT, "-an", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", f"{SEG}/s11.mp4")
end = Image.new("RGB", (W, H), (12, 10, 20)); de = ImageDraw.Draw(end)
for i, (role, who, col) in enumerate(CREW):
    de.rectangle((i * W / 7, H - 18, (i + 1) * W / 7, H), fill=col)
for txt, f, y, col in (("MattPaint  ·  Story Forge", font(BOLD, 84), 400, (255, 255, 255)), ("every frame painted, stroke by stroke", font(REG, 40), 520, (200, 200, 210))):
    b = de.textbbox((0, 0), txt, font=f); de.text(((W - b[2]) / 2, y), txt, font=f, fill=col)
endp = f"{OUT}/end.png"; end.save(endp)
ff("-loop", "1", "-i", endp, "-t", "4", "-r", str(FPS), "-vf", "format=yuv420p,setsar=1", "-c:v", "libx264", "-crf", "17", f"{SEG}/s12.mp4")

segs = [f"s{i:02d}" for i in range(1, 13)]
open(f"{OUT}/concat.txt", "w").write("".join(f"file 'seg/{s}.mp4'\n" for s in segs))
ff("-f", "concat", "-safe", "0", "-i", f"{OUT}/concat.txt", "-c", "copy", f"{OUT}/video.mp4")

# audio: voice, bed under the talk (louder in the composer beat), rise score under the finale. No generated sfx (they were static).
starts = [sum(D[:i]) for i in range(10)]; t_rise = sum(D); total = t_rise + dur(f"{SEG}/s11.mp4") + 4
ins = []; flt = []
for i, p in enumerate(nar):
    ins += ["-i", p]; flt.append(f"[{i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay={int((starts[i] + 0.25) * 1000)}:all=1[n{i}]")
k = len(nar)
c0 = starts[6]
ins += ["-i", f"{E}/music/bed.wav"]
flt.append(f"[{k}:a]aresample=48000,atrim=0:{t_rise + 1:.2f},highpass=f=40,"
           f"volume='if(between(t,{c0:.2f},{c0 + D[6] / 2:.2f}),0.55,0.2)':eval=frame,afade=t=in:d=2,afade=t=out:st={t_rise - 1:.2f}:d=2[bed]")
ins += ["-i", f"{E}/music/rise.wav"]
flt.append(f"[{k + 1}:a]aresample=48000,atrim=0:15,highpass=f=32,equalizer=f=43:t=q:w=1.2:g=-10,afade=t=out:st=12:d=3,adelay={int(t_rise * 1000)}:all=1,volume=0.9[rm]")
mix = "".join(f"[n{i}]" for i in range(10)) + "[bed][rm]"
flt.append(f"{mix}amix=inputs=12:normalize=0:duration=longest,atrim=0:{total:.2f},alimiter=limit=0.95[out]")
ff(*ins, "-filter_complex", ";".join(flt), "-map", "[out]", "-c:a", "pcm_s16le", f"{OUT}/audio.wav")
final = f"{E}/MattPaint_explainer_v5.mp4"
ff("-i", f"{OUT}/video.mp4", "-i", f"{OUT}/audio.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", final)
json.dump({"durations": D, "narration_starts": starts, "rise_at": t_rise, "total": total}, open(f"{OUT}/timeline.json", "w"), indent=1)
print(final, f"{dur(final):.1f}s")
