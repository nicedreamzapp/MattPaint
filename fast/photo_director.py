"""PHOTO DIRECTOR — any prompt, painted to look like a photograph.

Matt 2026-11-02 ("MattPaint should be able to paint anything, any scene, any time, and make it look
real"): MattPaint Studio was wired to the gen-6 scene engine, which draws subjects from flat shapes and
comes out cartoon. The photoreal path tracer (pt.py, the 2026-09-23 set: chess scored 8/10 as a photo)
only ran hand-written ph*.py scenes. This connects them: Claude writes a pt scene for the prompt, the
tracer lights it, and pt.run() paints it into MattPaint on screen (rough pass, then final).

    photo_director.py "a red apple on a kitchen table"

If the scene crashes, the error goes back to Claude to fix (up to 2 tries). Scenes and logs are kept
in photo_runs/<time>_<slug>/; the picture lands in gallery/opus-photoreal/studio_<slug>.png.
"""
import os, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLAUDE_BIN = os.path.expanduser("~/.claude/bin/claude-stable")
MODEL = "claude-opus-5-5"
PY = "/usr/bin/python3"                 # the interpreter run_photos.sh paints the ph*.py set with

API = (HERE / "pt.py").read_text().split('"""')[1]   # the module docstring: what pt can do
SIGS = "\n".join(l for l in (HERE / "pt.py").read_text().splitlines()
                 if re.match(r"\s*(def |class )", l) and not re.match(r"\s*def _", l))
EXAMPLES = "\n\n".join(f"### {n}\n```python\n{(HERE / n).read_text()}```" for n in ("ph05_whiskey.py", "ph02_chess.py"))
LESSONS = (HERE.parent / "gallery" / "opus-photoreal" / "SCORECARD.md").read_text()

BRIEF = """You write scene files for pt, a small photoreal path tracer in numpy. The tracer renders your scene
and MattPaint paints it on screen. The goal is a picture a stranger would take for a PHOTOGRAPH.

THE PROMPT: {prompt}

WHAT pt CAN DO:
{api}
ITS FUNCTIONS AND CLASSES:
{sigs}

TWO REAL SCENES THAT RENDERED WELL (study the shape: materials, procedural textures, lights, camera, the
__main__ block):
{examples}

LESSONS FROM EVERY PICTURE SO FAR (each one cost a render; do not repeat them):
{lessons}

IT MUST NOT LOOK LIKE:
- CGI or a game engine: plastic materials, perfect clean surfaces, flat uniform colour, no wear.
- A floating object: everything rests ON something, contact points checked in numbers.
- A black blob: metal and glass need something bright to reflect or sit in front of.
- An empty void: give the scene a real setting, a surface with texture and a background with depth.
- Cold, dim or muddy light: a warm key light clearly brighter than the fill, real shadows.

RULES:
- What the prompt names IS the picture. Build each thing it names from the primitives (spheres and
  ellipsoids, boxes, lathes, cylinders, planes), with procedural textures for wood, stone, cloth, skin.
- Living things (animals, people) are the hard case: build the form from many overlapping ellipsoids so
  the silhouette reads, give it a fine fbm texture and bump for fur or skin, and frame the camera so the
  subject fills the frame and is recognisable at a glance.
- Units: 1 unit = 10 cm. Camera W=1400, H=900 (the defaults).
- Keep it fast: at most ~40 objects, bounces 4-6. The run budget is about a minute of rendering.
- The file must end exactly like the examples, with the name given below:
    if __name__ == "__main__":
        if "--time" in sys.argv: print("s/spp", timing(sc)); sys.exit()
        run(sc, "{name}", spp=int(sys.argv[1]) if len(sys.argv) > 1 else None)
- Put TITLES["{name}"] = "<a short human title for the picture>" right after `from pt import *`.

Reply with ONLY the complete scene file in one ```python block."""

FIX = """The scene file you wrote failed when it ran. Fix it and reply with ONLY the complete corrected file in
one ```python block. Keep everything else the same.

THE FILE:
```python
{code}```

THE ERROR (last lines):
{err}"""


def ask(text):
    t0 = time.time()
    p = subprocess.run([CLAUDE_BIN, "-p", "--model", MODEL, "--output-format", "json",
                        "--strict-mcp-config", "--no-session-persistence", "--tools", ""],
                       input=text, capture_output=True, text=True, timeout=900, cwd=str(HERE))
    import json
    try:
        out = json.loads(p.stdout).get("result", "")
    except Exception:
        out = p.stdout or p.stderr
    m = re.search(r"```python\n(.*?)```", out, re.S)
    return (m.group(1) if m else ""), round(time.time() - t0)


def slug_of(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40] or "picture"


def main():
    prompt = " ".join(a for a in sys.argv[1:]).strip()
    if not prompt:
        sys.exit('give a prompt, e.g. photo_director.py "a red apple on a kitchen table"')
    slug = slug_of(prompt); name = "studio_" + slug
    rundir = HERE / "photo_runs" / f"{time.strftime('%Y%m%d-%H%M%S')}_{slug}"
    rundir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {prompt}\n   Claude Opus 5.5 is building the scene in 3D...", flush=True)
    code, s = ask(BRIEF.format(prompt=prompt, api=API, sigs=SIGS, examples=EXAMPLES, lessons=LESSONS, name=name))
    print(f"   scene written in {s}s", flush=True)
    env = dict(os.environ, PYTHONPATH=str(HERE), OBJC_DISABLE_INITIALIZE_FORK_SAFETY="YES", PYTHONUNBUFFERED="1")
    for attempt in range(3):
        if not code:
            print("   no scene came back", flush=True); break
        f = rundir / f"scene{attempt}.py"; f.write_text(code)
        print("   lighting it and painting in MattPaint (rough pass, then final)...", flush=True)
        p = subprocess.run([PY, "-u", str(f)], cwd=str(HERE), env=env, capture_output=True, text=True, timeout=1800)
        (rundir / f"scene{attempt}.log").write_text(p.stdout + p.stderr)
        for line in p.stdout.splitlines():
            if line.startswith("["):
                print("   " + line, flush=True)
        if p.returncode == 0:
            print(f"   done: gallery/opus-photoreal/{name}.png", flush=True)
            return
        err = "\n".join((p.stderr or p.stdout).strip().splitlines()[-15:])
        print(f"   the scene crashed ({err.splitlines()[-1][:120] if err else 'no output'}), Claude is fixing it...", flush=True)
        code, s = ask(FIX.format(code=code, err=err))
    print("   could not paint this one", flush=True)
    sys.exit(1)


if __name__ == "__main__":
    main()
