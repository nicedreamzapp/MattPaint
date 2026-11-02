"""pt_film — a short film made of path-traced frames, every frame PAINTED INTO MATTPAINT ON SCREEN.

Matt 2026-11-02 ("how can we make a movie in this style where everything gets painted"). A film
scene file is a normal pt scene, except it defines shot(t) -> Scene for t from 0 (first frame) to 1
(last frame) instead of one fixed `sc`. Each frame is rendered, painted into the MattPaint window
Matt watches, saved from that canvas, and the frames are joined into an mp4.

Animated "on twos" like hand-drawn anime: 12 drawings a second, each held for two frames of 24 fps.

    pt_film.py scene_file.py NAME [--seconds 10] [--fps 12] [--spp 48] [--w 1280 --h 720]

Fixed noise seed on every frame so the grain does not crawl from frame to frame. Waits between
frames while a Song Forge customer job is running (customer songs outrank renders).
"""
import argparse, asyncio, importlib.util, json, os, subprocess, sys, time, urllib.request
os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
import numpy as np
from multiprocessing import get_context

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pt

FILMS = os.path.join(os.path.dirname(HERE), "gallery", "films")


def load(path):
    spec = importlib.util.spec_from_file_location("film_scene", path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


# ---- workers: spawned (Metal does not survive fork), each loads the scene file once ----
_MOD = None; _T = None
def _init(path):
    global _MOD
    _MOD = load(path)
def _job(args):
    global _T
    t, y0, y1, spp, seed = args
    if t != _T:
        import gpu_isect
        gpu_isect._packed.clear()          # GPU geometry is cached by id(objs); a new frame is a new scene
        pt.SC = _MOD.shot(t); _T = t
    return pt.trace_rows((y0, y1, spp, seed))


def forge_busy():
    try:
        d = json.load(urllib.request.urlopen("http://127.0.0.1:8767/api/status", timeout=3))
        return d.get("jobs_running", 0) > 0
    except Exception:
        return False


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene"); ap.add_argument("name")
    ap.add_argument("--seconds", type=float, default=10); ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--spp", type=int, default=48); ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=720); ap.add_argument("--first", type=int, default=0)
    a = ap.parse_args()
    path = os.path.abspath(a.scene); mod = load(path)
    n = max(2, int(round(a.seconds * a.fps)))
    out = os.path.join(FILMS, a.name); fdir = os.path.join(out, "frames"); os.makedirs(fdir, exist_ok=True)

    from concurrent.futures import ProcessPoolExecutor
    ex = ProcessPoolExecutor(14, mp_context=get_context("spawn"), initializer=_init, initargs=(path,))

    from engine import Browser, launch_brave, paint_url
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up: launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto(paint_url()); await tab.measure_canvas()
    await tab.resize_canvas(a.w, a.h)
    title = getattr(mod, "TITLE", a.name)

    T0 = time.time(); strokes = 0
    for i in range(a.first, n):
        while forge_busy():
            print(f"   frame {i + 1}: a Song Forge customer song is running, waiting...", flush=True)
            await asyncio.sleep(20)
        t = i / (n - 1); f0 = time.time()
        sc = mod.shot(t)
        sc.cam["W"], sc.cam["H"] = a.w, a.h
        rows = [(t, y, min(y + 20, a.h), a.spp, 7) for y in range(0, a.h, 20)]
        img = np.zeros((a.h, a.w, 3), np.float32)
        for y0, blk in ex.map(_job, rows):
            img[y0:y0 + len(blk)] = blk
        frame = pt.develop(pt.denoise(img, 1.2), sc)
        ops = pt.to_ops(frame)
        await tab.eval(pt.BANNER_JS + "window.__opusBanner(" + json.dumps(
            f"<b>{title}</b><br>painting frame {i + 1} of {n} · {len(ops):,} strokes") + ")", ret=False)
        for k in range(0, len(ops), 6000):
            tab.fast(ops[k:k + 6000]); await tab.sync(); await asyncio.sleep(0.005)
        strokes += len(ops)
        await tab.eval("document.getElementById('opus-banner')?.remove()", ret=False)
        await tab.png(os.path.join(fdir, f"{i:04d}.png"))   # the canvas Matt is looking at
        el = time.time() - T0; per = el / (i + 1 - a.first)
        print(f"   frame {i + 1}/{n} {time.time() - f0:.0f}s · done ~{(n - i - 1) * per / 60:.0f} min", flush=True)

    mp4 = os.path.join(out, a.name + ".mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", os.path.join(fdir, "%04d.png"),
                    "-vf", "fps=24,format=yuv420p", "-c:v", "libx264", "-crf", "16", mp4], check=True)
    json.dump({"title": title, "frames": n, "fps_drawn": a.fps, "spp": a.spp, "strokes": strokes,
               "minutes": round((time.time() - T0) / 60, 1)}, open(os.path.join(out, "film.json"), "w"), indent=1)
    print(f"   film: {mp4} · {strokes:,} strokes · {(time.time() - T0) / 60:.0f} min", flush=True)
    await br.close()                                     # paint window stays up on the last frame
    ex.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
