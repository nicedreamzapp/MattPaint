"""Cuts the MattPaint explainer to Matt's narration (2026-11-02). Each paragraph gets its own picture segment."""
import os, subprocess, json
from PIL import Image, ImageDraw, ImageFont
E = os.path.expanduser("~/Desktop/PROJECTS/MattPaint/explainer"); G = os.path.expanduser("~/Desktop/PROJECTS/MattPaint/gallery/films")
OUT = f"{E}/edit"; SEG = f"{OUT}/seg"; os.makedirs(SEG, exist_ok=True)
W, H, FPS, GAP = 1920, 1080, 30, 0.7
def dur(p): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).strip())
def ff(*a): subprocess.run(["ffmpeg","-y","-v","error",*a], check=True)
FIT = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={FPS}"
nar = [f"{E}/narration/p{i}.wav" for i in range(1, 9)]
D = [dur(p) + GAP for p in nar]

def stretch(src, out, d, png=None):
    s = dur(src)
    if png:
        ff("-i", src, "-i", png, "-filter_complex", f"[0:v]setpts={d/s:.5f}*PTS,{FIT}[v];[v][1:v]overlay=0:0", "-t", f"{d:.3f}", "-an", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out)
    else:
        ff("-i", src, "-vf", f"setpts={d/s:.5f}*PTS,{FIT}", "-t", f"{d:.3f}", "-an", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", out)

FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
_ln = [0]
def card(items, bg=None):
    im = Image.new("RGBA", (W, H), bg or (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for text, size, col, xc, y, box in items:
        f = ImageFont.truetype(FONT, size); b = d.textbbox((0, 0), text, font=f); tw, th = b[2] - b[0], b[3] - b[1]
        x = xc - tw / 2
        if box: d.rounded_rectangle((x - 22, y - 16, x + tw + 22, y + th + 22), 12, fill=(0, 0, 0, 150))
        d.text((x, y - b[1]), text, font=f, fill=col)
    _ln[0] += 1; p = f"{OUT}/label{_ln[0]}.png"; im.save(p); return p
def label(text, size=44):
    return card([(text, size, (255, 255, 255, 255), W / 2, H - 140, True)])

# A: the robot film (hook)
stretch(f"{G}/robot_blender/robot_blender.mp4", f"{SEG}/a.mp4", D[0])
# B: the scene code Opus wrote, scrolling
code = open(os.path.expanduser("~/Desktop/PROJECTS/MattPaint/fast/blender/robot_forest_bl.py")).read().splitlines()
mono = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 22); hdr = ImageFont.truetype(FONT, 34)
fd = f"{OUT}/codeframes"; os.makedirs(fd, exist_ok=True)
n = int(D[1] * FPS); start, span = 40, 420; rows = 38
for f in range(n):
    im = Image.new("RGB", (W, H), (22, 24, 30)); d = ImageDraw.Draw(im)
    d.text((80, 40), "robot_forest_bl.py  ·  1,418 lines Opus wrote from one sentence", font=hdr, fill=(240, 220, 160))
    top = start + span * f / max(n - 1, 1); i0 = int(top); off = (top - i0) * 26
    for k in range(rows):
        if i0 + k < len(code):
            d.text((80, 120 + k * 26 - off), f"{i0+k+1:5d}  " + code[i0 + k][:130], font=mono, fill=(170, 200, 230) if not code[i0+k].strip().startswith("#") else (120, 160, 110))
    im.save(f"{fd}/{f:05d}.png")
ff("-framerate", str(FPS), "-i", f"{fd}/%05d.png", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", f"{SEG}/b.mp4")
# C: the light changing, dawn to gold
stretch(f"{G}/robot_blender/robot_blender.mp4", f"{SEG}/c.mp4", D[2], png=label("Blender works out the light"))
# D: MattPaint painting one frame onto a blank page
stretch(f"{E}/footage/slow_paint/recording.mp4", f"{SEG}/d.mp4", D[3])
# E: first try vs now, side by side
lab = card([("First try · homemade engine · 4.5 hours", 34, (255,255,255,255), 40 + 475, 230, True),
            ("Now · Blender · 7 minutes", 34, (255,255,255,255), 970 + 475, 230, True)])
half = "scale=950:-2"
ff("-i", f"{G}/robot_forest/robot_forest.mp4", "-i", f"{G}/robot_blender/robot_blender.mp4", "-i", lab, "-filter_complex",
   f"[0:v]setpts={D[4]/10:.4f}*PTS,{half}[l];[1:v]setpts={D[4]/10:.4f}*PTS,{half}[r];"
   f"[l][r]hstack=inputs=2,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,fps={FPS},setsar=1[v];[v][2:v]overlay=0:0",
   "-t", f"{D[4]:.3f}", "-an", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", f"{SEG}/e.mp4")
# F: the whole rising shot being painted, sped way up
stretch(f"{E}/footage/rise_paint/recording.mp4", f"{SEG}/f.mp4", D[5], png=label("120 frames painted · sped up 70x", 38))
# G: the forest film being painted, sped up, with the GitHub links
stretch(f"{E}/footage/robot_paint/recording.mp4", f"{SEG}/g.mp4", D[6], png=label("github.com/nicedreamzapp/MattPaint  ·  /story-forge", 40))
# H: hold on the robot
stretch(f"{G}/robot_blender/robot_blender.mp4", f"{SEG}/h.mp4", D[7])
# I: the robot wakes (full speed) + end card
ff("-i", f"{G}/robot_rise/robot_rise.mp4", "-vf", FIT, "-an", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", f"{SEG}/i.mp4")
endc = card([("MattPaint  ·  Story Forge", 64, (255,255,255,255), W/2, H/2 - 60, False),
             ("every frame painted, stroke by stroke", 34, (160,160,160,255), W/2, H/2 + 30, False)], bg=(0,0,0,255))
ff("-loop", "1", "-i", endc, "-t", "4", "-r", str(FPS), "-vf", "format=yuv420p,setsar=1", "-c:v", "libx264", "-crf", "17", f"{SEG}/j.mp4")

segs = "abcdefghij"
open(f"{OUT}/concat.txt", "w").write("".join(f"file 'seg/{s}.mp4'\n" for s in segs))
ff("-f", "concat", "-safe", "0", "-i", f"{OUT}/concat.txt", "-c", "copy", f"{OUT}/video.mp4")

# audio: narration at its segment starts, bed under the talk, forest sfx under A and C, rise score + sfx under I
starts = [sum(D[:i]) for i in range(8)]; t_rise = sum(D); total = t_rise + dur(f"{SEG}/i.mp4") + 4
ins = []; flt = []
for i, p in enumerate(nar):
    ins += ["-i", p]; flt.append(f"[{i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay={int((starts[i]+0.25)*1000)}:all=1,volume=1.0[n{i}]")
k = len(nar)
ins += ["-i", f"{E}/music/bed.wav"]; flt.append(f"[{k}:a]aresample=48000,atrim=0:{t_rise+1:.2f},afade=t=in:d=2,afade=t=out:st={t_rise-1:.2f}:d=2,volume=0.22[bed]")
ins += ["-i", f"{E}/sfx/forest.wav"]; flt.append(f"[{k+1}:a]aresample=48000,volume=0.35,asplit=2[fa][fc]"); 
flt.append(f"[fa]adelay=0:all=1[fa2]"); flt.append(f"[fc]adelay={int(starts[2]*1000)}:all=1[fc2]")
ins += ["-i", f"{E}/music/rise.wav"]; flt.append(f"[{k+2}:a]aresample=48000,atrim=0:15,afade=t=out:st=12:d=3,adelay={int(t_rise*1000)}:all=1,volume=0.9[rm]")
ins += ["-i", f"{E}/sfx/rise.wav"]; flt.append(f"[{k+3}:a]aresample=48000,adelay={int(t_rise*1000)}:all=1,volume=0.8[rs]")
mix = "".join(f"[n{i}]" for i in range(8)) + "[bed][fa2][fc2][rm][rs]"
flt.append(f"{mix}amix=inputs=13:normalize=0:duration=longest,atrim=0:{total:.2f},alimiter=limit=0.95[out]")
ff(*ins, "-filter_complex", ";".join(flt), "-map", "[out]", "-c:a", "pcm_s16le", f"{OUT}/audio.wav")
final = f"{E}/MattPaint_explainer_v1.mp4"
ff("-i", f"{OUT}/video.mp4", "-i", f"{OUT}/audio.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", final)
json.dump({"segments": dict(zip(segs, [*D, dur(f"{SEG}/i.mp4"), 4])), "narration_starts": starts, "rise_at": t_rise, "total": total},
          open(f"{OUT}/timeline.json", "w"), indent=1)
print(final, f"{dur(final):.1f}s")
