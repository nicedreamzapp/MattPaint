"""paint_frames — paints rendered film frames into MattPaint ON SCREEN as they land, then makes the mp4.

Matt 2026-11-02: the light math for a film can come from Blender Cycles (10-50x faster than pt.py on the
Apple GPU), but every frame is still PAINTED INTO MATTPAINT in view, and the frame kept for the film is
the canvas Matt saw, saved from MattPaint.

    paint_frames.py RENDER_DIR NAME --count 120 [--fps 12]

Watches RENDER_DIR for frame_*.png (as Blender writes them), paints each one in order, saves the canvas
to gallery/films/NAME/frames/, and joins them into gallery/films/NAME/NAME.mp4 when all COUNT are done.
"""
import argparse, asyncio, glob, json, os, subprocess, sys, time, urllib.request
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pt

FILMS = os.path.join(os.path.dirname(HERE), "gallery", "films")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("render_dir"); ap.add_argument("name")
    ap.add_argument("--count", type=int, required=True); ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--title", default=None)
    a = ap.parse_args()
    out = os.path.join(FILMS, a.name); fdir = os.path.join(out, "frames"); os.makedirs(fdir, exist_ok=True)
    title = a.title or a.name

    from engine import Browser, launch_brave, paint_url
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up: launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto(paint_url()); await tab.measure_canvas()

    T0 = time.time(); done = 0; strokes = 0; sized = False; last_new = time.time()
    while done < a.count:
        files = sorted(glob.glob(os.path.join(a.render_dir, "frame_*.png")))
        if len(files) <= done:
            if time.time() - last_new > 1800:
                sys.exit(f"no new frame for 30 min after {done}/{a.count}, stopping")
            await asyncio.sleep(2); continue
        f = files[done]; time.sleep(0.5)                      # let Blender finish writing it
        img = np.asarray(Image.open(f).convert("RGB"))
        if not sized:
            await tab.resize_canvas(img.shape[1], img.shape[0]); sized = True
        ops = pt.to_ops(img)
        await tab.eval(pt.BANNER_JS + "window.__opusBanner(" + json.dumps(
            f"<b>{title}</b><br>painting frame {done + 1} of {a.count} · {len(ops):,} strokes") + ")", ret=False)
        for k in range(0, len(ops), 6000):
            tab.fast(ops[k:k + 6000]); await tab.sync(); await asyncio.sleep(0.005)
        await tab.eval("document.getElementById('opus-banner')?.remove()", ret=False)
        await tab.png(os.path.join(fdir, f"{done:04d}.png"))     # the canvas Matt is looking at
        strokes += len(ops); done += 1; last_new = time.time()
        print(f"   painted {done}/{a.count} · {len(ops):,} strokes", flush=True)

    mp4 = os.path.join(out, a.name + ".mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", os.path.join(fdir, "%04d.png"),
                    "-vf", "fps=24,format=yuv420p", "-c:v", "libx264", "-crf", "16", mp4], check=True)
    json.dump({"title": title, "frames": a.count, "fps_drawn": a.fps, "strokes": strokes, "renderer": "Blender Cycles",
               "minutes": round((time.time() - T0) / 60, 1)}, open(os.path.join(out, "film.json"), "w"), indent=1)
    print(f"   film: {mp4} · {strokes:,} strokes · {(time.time() - T0) / 60:.0f} min", flush=True)
    await br.close()


if __name__ == "__main__":
    asyncio.run(main())
