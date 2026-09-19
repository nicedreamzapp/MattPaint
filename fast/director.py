"""DIRECTOR — generation 6. Qwen 3.8 (local) art-directs; the scene engine paints from scratch.

The old loop had the model type out every brush stroke as a program, which is why a round took
eleven minutes. Here the drawing knowledge lives in scene_engine.py, and the model only writes
and revises a short recipe (RECIPES.md): a few hundred tokens instead of a few thousand.

    director.py "DAWN RIDGES"                 a PROMPTS.md subject
    director.py "a lighthouse in a storm"     any prompt
    director.py "DAWN RIDGES" --rounds 6
    director.py --all                         every PROMPTS.md subject (holdouts painted once)
    --no-think                                skip the reasoning step when writing the first recipe

Each round: the model LOOKS at the painting and returns a revised recipe -> preflight (no
browser) -> paint -> the model JUDGES new vs best in both orders; the new one only replaces the
best if it wins both. Flat-gray construction check first. Run it through run_director.sh.
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import local_loop as LL                                   # Qwen (with the verified prefix cache)

PAINT_PY = LL.PAINT_PY
GALLERY = HERE.parent / "gallery" / "gen6"
TAG = os.environ.get("MATTPAINT_TAG", "")          # e.g. "_gemma" so a head-to-head keeps both
HOLDOUTS = LL.HOLDOUTS
WHO = os.environ.get("MATTPAINT_NAME") or ("Qwen 3.8" if "qwen" in LL.MODEL.lower() else
       "SuperGemma" if "supergemma" in LL.MODEL.lower() else "Gemma 4")   # shown in the terminal and on the painting
os.environ["MATTPAINT_NAME"] = WHO           # the painter subprocess reads it for the header line
# 2026-09-18: the engine can paint things, not only landscape (scene_objects.py). Only tell the
# director about objects when the engine in this folder actually has them.
import scene_engine as _SE
HAS_OBJECTS = hasattr(_SE, "SO")
OBJECTS_DOC = ("\n\n" + (HERE / "RECIPES_OBJECTS.md").read_text()) if HAS_OBJECTS else ""
FIRST_ASK = ("First list every thing the prompt names and give each one an object (or build it from "
             "shapes); then decide the light. Reply with the full recipe in one ```json block."
             if HAS_OBJECTS else
             "Read the prompt as LIGHT first, then write the recipe. Reply with the full recipe in one ```json block.")    # who the terminal says is working


def slug_of(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40]


def extract_json(text):
    m = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    cand = m[-1] if m else None
    if cand is None:
        i, j = text.find("{"), text.rfind("}")
        cand = text[i:j + 1] if i >= 0 and j > i else ""
    try:
        return json.loads(cand), None
    except Exception as e:
        return None, f"The recipe is not valid JSON ({e}). Reply with one ```json block."


HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")


def unhex(v):
    """The model may write colours as "#rrggbb" (a third of the tokens of [r, g, b])."""
    if isinstance(v, str) and HEX.match(v):
        h = HEX.match(v).group(1)
        return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    if isinstance(v, list):
        return [unhex(x) for x in v]
    if isinstance(v, dict):
        return {k: unhex(x) for k, x in v.items()}
    return v


def tohex(v):
    if isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v):
        return "#%02x%02x%02x" % tuple(int(max(0, min(255, x))) for x in v)
    if isinstance(v, list):
        return [tohex(x) for x in v]
    if isinstance(v, dict):
        return {k: tohex(x) for k, x in v.items()}
    return v


def compact(r):
    """The recipe as the model sees it: hex colours, one layer per numbered line. Short to read,
    and nothing in it invites the model to copy a long pretty-printed block back."""
    h = tohex(r)
    head = {k: v for k, v in h.items() if k != "layers"}
    lines = [json.dumps(head, separators=(",", ":"))]
    for i, l in enumerate(h.get("layers", [])):
        lines.append(f"layer {i}: " + json.dumps(l, separators=(",", ":")))
    return "\n".join(lines)


def apply_patch(recipe, patch):
    """{"set": {"light.y": 0.7, "layers.3.amount": 0.6}, "add": [{"at": 2, "layer": {...}}],
        "remove": [5]}  -> new recipe, or (None, problem)."""
    import copy
    r = copy.deepcopy(recipe)
    try:
        for path, val in (patch.get("set") or {}).items():
            keys = path.split(".")
            cur = r
            for k in keys[:-1]:
                cur = cur[int(k)] if isinstance(cur, list) else cur.setdefault(k, {})
            last = keys[-1]
            if isinstance(cur, list):
                cur[int(last)] = unhex(val)
            else:
                cur[last] = unhex(val)
        for i in sorted((int(x) for x in patch.get("remove") or []), reverse=True):
            del r["layers"][i]
        for a in patch.get("add") or []:
            r["layers"].insert(int(a.get("at", len(r["layers"]))), unhex(a["layer"]))
    except Exception as e:
        return None, f"The change list could not be applied ({type(e).__name__}: {e}). Paths look like light.y or layers.3.amount."
    return r, None


def validate(r):
    """Drop what the engine can't paint and clamp numbers, so a slip becomes a note, not a crash."""
    import scene_engine as SE
    r = unhex(r)
    notes = []
    if not isinstance(r, dict):
        return None, "The recipe must be a JSON object."
    layers = []
    for l in r.get("layers", []):
        if not isinstance(l, dict) or l.get("type") not in SE.LAYERS:
            notes.append(f"unknown layer {l!r} was dropped (types: {', '.join(SE.LAYERS)})")
            continue
        layers.append(l)
    if not layers:
        return None, "The recipe has no paintable layers."
    for l in layers:                     # keep counts inside what RECIPES.md documents (and the budget)
        for k, hi in (("count", {"ridges": 7, "shafts": 8}.get(l["type"], 60)), ("amount", 1.0),
                      ("haze", 1.0), ("stillness", 1.0), ("strength", 1.5)):
            if isinstance(l.get(k), (int, float)) and l[k] > hi:
                notes.append(f"{l['type']}.{k} {l[k]} capped at {hi}")
                l[k] = hi
    r["layers"] = layers
    r["horizon"] = min(0.95, max(0.3, float(r.get("horizon", 0.7))))
    return r, "; ".join(notes) or None


def ticking(label, fn, *a, **kw):
    """Matt, 2026-09-18: the first recipe is four silent minutes and it looked frozen. Show a live
    clock on one terminal line while the model thinks or MattPaint paints, then clear it."""
    import threading
    done = threading.Event()
    t0 = time.time()
    frames = "|/-\\"
    def tick():
        i = 0
        while not done.wait(0.5):
            e = int(time.time() - t0)
            sys.stdout.write(f"\r\033[K   {frames[i % 4]} {label} {e // 60}:{e % 60:02d}")
            sys.stdout.flush(); i += 1
    th = threading.Thread(target=tick, daemon=True); th.start()
    try:
        return fn(*a, **kw)
    finally:
        done.set(); th.join()
        sys.stdout.write("\r\033[K"); sys.stdout.flush()


def run(py, args, timeout, env_extra=None):
    env = dict(os.environ, **(env_extra or {}))
    t = time.time()
    try:
        p = subprocess.run([py] + args, cwd=HERE, capture_output=True, text=True, env=env, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr)[-2500:], round(time.time() - t, 1)
    except subprocess.TimeoutExpired:
        return -9, f"TIMEOUT after {timeout}s", round(time.time() - t, 1)


class Direction:
    def __init__(self, q, key, prompt, rundir, rounds, gray_rounds, holdout, ref=None):
        self.q, self.key, self.prompt, self.dir = q, key, prompt, rundir
        self.ref = ref          # --ref: the director SEES a target picture (2026-09-18 experiment)
        self.rounds, self.gray_rounds, self.holdout = rounds, gray_rounds, holdout
        self.steps = []
        self.lost = []          # (changes, judge's reason) for revisions that lost
        self.prefix = ("You are the art director for a painting engine. You never draw strokes yourself: "
                       "you write a short recipe and the engine paints it from scratch.\n\n"
                       + (HERE / "RECIPES.md").read_text() + OBJECTS_DOC + "\n\nTHE PAINTING RULES THE ENGINE FOLLOWS:\n"
                       + (HERE / "GEN5_RULES.md").read_text()
                       + (f"\n\nTHE PROMPT: {prompt}\nYou are also shown THE TARGET PICTURE (always the "
                          "first image). Match it as closely as the engine's layers allow.\n" if ref else
                          f"\n\nTHE PROMPT (the only description you get): {prompt}\n"))

    def log(self, step, **kw):
        kw.update(step=step, t=time.strftime("%H:%M:%S"))
        self.steps.append(kw)
        (self.dir / "log.json").write_text(json.dumps(self.steps, indent=1))
        print(f"   [{kw['t']}] {step} " + " ".join(f"{k}={v}" for k, v in kw.items() if k not in ("step", "t")),
              flush=True)

    def save_recipe(self, r, name):
        p = self.dir / f"{name}.json"
        p.write_text(json.dumps(r, indent=1))
        return p

    def checked(self, text, name, base=None):
        """JSON -> (patch applied to base) -> validated -> engine preflight. Returns (recipe, problem)."""
        r, problem = extract_json(text)
        if r is None:
            return None, problem
        if base is not None and "layers" not in r:
            r, problem = apply_patch(base, r)
            if r is None:
                return None, problem
        r, note = validate(r)
        if r is None:
            return None, note
        r.setdefault("title", self.key.upper())
        p = self.save_recipe(r, name)
        rc, out, secs = run(PAINT_PY, ["scene_engine.py", str(p), "/dev/null"], 120, {"PAINT_PREFLIGHT": "1"})
        ops = re.search(r"PREFLIGHT ops=(\d+)", out)
        self.log("preflight", recipe=name, s=secs, ops=int(ops.group(1)) if ops else None, ok=rc == 0 and bool(ops))
        if rc != 0 or not ops:
            return None, f"The engine could not paint that recipe:\n{out[-1200:]}"
        if note:
            self.log("recipe-note", recipe=name, note=note[:200])
        return r, None

    def ask_recipe(self, ask, name, images=(), think=False, max_tokens=2500):
        note = ""
        for attempt in range(3):
            text, st = ticking(f"{WHO} is thinking up the recipe (~4 min)" if think else f"{WHO} is writing the recipe",
                               self.q.ask, (self.prefix if images else "") + ask + note, images=images, max_tokens=max_tokens, think=think,
                                  temperature=0.3 if attempt == 0 else 0.6,
                                  prefix="" if images else self.prefix)
            self.log("director", recipe=name, attempt=attempt, **st)
            (self.dir / f"{name}_director{attempt}.md").write_text(text)
            r, problem = self.checked(text, name)
            if r is not None:
                return r, text
            note = f"\n\nYOUR LAST RECIPE FAILED: {problem}\nFix it and reply with the full recipe in one ```json block."
        return None, text

    def paint(self, r, name, gray=False):
        p = self.save_recipe(r, name)
        png = self.dir / f"{name}{'_gray' if gray else ''}.png"
        # Matt's rule: every picture is painted in MattPaint, in view. There is no off-screen path.
        for attempt in range(2):         # one retry: a page that loads slowly is not a bad recipe
            rc, out, secs = ticking("painting in MattPaint" + (" (gray sketch)" if gray else ""), run, PAINT_PY,
                                    ["scene_engine.py", str(p), str(png)] + (["gray"] if gray else []), 300)
            ok = rc == 0 and png.exists()
            if ok:
                break
        self.log("paint", recipe=name, gray=gray, ok=ok, s=secs)
        if not ok:
            (self.dir / f"{name}_paint_error.txt").write_text(out)
            return None
        if gray:
            from PIL import Image
            Image.open(png).convert("L").save(png)
        return png

    def seen(self, png):
        return [str(self.ref), str(png)] if self.ref else [str(png)]

    def look_prompt(self, gray, recipe):
        head = self.prefix + ("\nImage 1 is THE TARGET PICTURE; image 2 is the current painting.\n" if self.ref else "")
        what = ("This is the FLAT GRAY construction test of the painting. Judge ONLY composition and "
                "structure: does the arrangement of light and dark read as the prompt? First line exactly "
                "VERDICT: PASS or VERDICT: FAIL."
                if gray else
                "This is the painting. First say in one sentence what a stranger would think it shows. "
                + ("Then list every thing the prompt names that is MISSING, too small, or only a dark shape, "
                   "and fix the worst 3: add objects, svg drawings or shapes, move them nearer, light them, "
                   "colour them." if HAS_OBJECTS else
                   "Then name the 3 changes that would make it read most strongly as the prompt, with the "
                   "believable light the rules ask for."))
        tried = ""
        if self.lost:
            tried = ("\nALREADY TRIED THIS SUBJECT AND JUDGED WORSE (do not repeat these):\n"
                     + "\n".join(f"- {c} -> {why}" for c, why in self.lost[-4:]) + "\n")
        return (head + f"\nTHE CURRENT RECIPE (colours may be written #rrggbb):\n{compact(recipe)}\n{tried}\n{what}\n"
                "Then reply with ONLY the changes, in one ```json block:\n"
                '{"set": {"light.y": 0.7, "layers.3.amount": 0.6, "fog_color": "#e0c8a8"}, '
                '"add": [{"at": 2, "layer": {"type": "shafts", "count": 5}}], "remove": [4]}\n'
                "Use only the parts you need. Never repeat the whole recipe.")

    def judge(self, best, new, name):
        wins = 0
        self.last_why = ""
        for first, second, challenger in ((best, new, 2), (new, best, 1)):
            text, st = ticking(f"{WHO} is judging new vs best", self.q.ask,
                f"Two paintings of: \"{self.prompt}\"\n" + ("Which one SHOWS more of the things the prompt names, "
                "clearly and recognisably, in the colours it asks for? A dark silhouette against a sunset "
                "loses to a picture where you can see what things are." if HAS_OBJECTS else
                "Which reads more convincingly as that scene, with believable light?") + " Ignore the title bars. First line exactly WINNER: 1 or WINNER: 2, then one "
                "sentence why.", images=[str(first), str(second)], max_tokens=80, temperature=0.0)
            m = re.search(r"WINNER:\s*([12])", text)
            won = bool(m and int(m.group(1)) == challenger)
            wins += won
            if not won:
                self.last_why = (text.splitlines() or [""])[-1][:160]
            self.log("judge", recipe=name, challenger_shown=challenger, won=won,
                     why=(text.splitlines() or [""])[-1][:140], **st)
        return wins == 2

    def go(self):
        print(f"\n=== {self.key}{' (HOLDOUT)' if self.holdout else ''} — {self.prompt}", flush=True)
        r, _ = self.ask_recipe(FIRST_ASK, "r0", think=True, max_tokens=5000 if HAS_OBJECTS else 2500,
                               images=[str(self.ref)] if self.ref else ())
        if r is None:
            return self.finish("no paintable recipe")
        g = 0
        while True:
            png = self.paint(r, f"g{g}", gray=True)
            if png is None:
                return self.finish("gray paint failed")
            text, st = ticking(f"{WHO} is checking the gray sketch", self.q.ask, self.look_prompt(True, r),
                               images=self.seen(png), max_tokens=4000)
            (self.dir / f"g{g}_look.md").write_text(text)
            passed = bool(re.search(r"VERDICT:\s*PASS", text))
            self.log("look-gray", round=g, passed=passed, **st)
            if passed or self.holdout or g >= self.gray_rounds:
                break
            g += 1
            new, problem = self.checked(text, f"g{g}", base=r)
            if new is None or new == r:
                self.log("gray-revision-skipped", reason=(problem or "unchanged")[:120])
                break
            r = new
        best = self.paint(r, "c0")
        if best is None:
            return self.finish("colour paint failed")
        best_recipe = r
        tried = []
        for n in range(1, 0 if self.holdout else self.rounds + 1):
            name = f"c{n}"
            text, st = ticking(f"round {n}: {WHO} is studying the painting", self.q.ask,
                               self.look_prompt(False, best_recipe), images=self.seen(best), max_tokens=4000)
            (self.dir / f"{name}_look.md").write_text(text)
            self.log("look", round=n, **st)
            new, problem = self.checked(text, name, base=best_recipe)
            if new is None or new == best_recipe or new in tried:
                self.log("round-skipped", round=n, reason=(problem or "recipe unchanged or already tried")[:160])
                continue
            tried.append(new)
            png = self.paint(new, name)
            if png and self.judge(best, png, name):
                best, best_recipe = png, new
                self.log("new-best", round=n)
            else:
                change = (extract_json(text)[0] or {})
                self.lost.append((json.dumps(change, separators=(",", ":"))[:300], self.last_why))
                self.log("kept-best", round=n, best=best.name)
        GALLERY.mkdir(parents=True, exist_ok=True)
        slug = slug_of(self.key) + TAG
        shutil.copy(best, GALLERY / f"{slug}.png")
        (GALLERY / f"{slug}.json").write_text(json.dumps(best_recipe, indent=1))
        self.log("published", file=f"gallery/gen6/{slug}.png", best=best.name)
        return self.finish("done")

    def finish(self, why):
        lines = [f"# {self.key} — gen 6 (director + scene engine)", "", f"Prompt: {self.prompt}", "",
                 f"Result: {why}", "", "| time | step | details |", "|---|---|---|"]
        for s in self.steps:
            d = ", ".join(f"{k}={v}" for k, v in s.items() if k not in ("step", "t"))
            lines.append(f"| {s['t']} | {s['step']} | {d[:160]} |")
        (self.dir / "summary.md").write_text("\n".join(lines) + "\n")
        print(f"   {self.key}: {why} — {self.dir}", flush=True)
        return why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--gray-rounds", type=int, default=1)
    ap.add_argument("--no-think", action="store_true")
    ap.add_argument("--ref", help="a target picture the director gets to see")
    a = ap.parse_args()
    P = LL.prompts()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    if a.all:
        jobs = [(k, P[k]) for k in P]
    elif a.prompt and a.prompt.upper() in P:
        jobs = [(a.prompt.upper(), P[a.prompt.upper()])]
    elif a.prompt:
        jobs = [(a.prompt[:40].upper(), a.prompt)]
    else:
        sys.exit("give a prompt or a PROMPTS.md subject, or --all")
    q = LL.Qwen(think=not a.no_think)
    print(f"model loaded in {q.load_s}s, prefix cache {'on' if q.cache_on else 'off'}", flush=True)
    for key, prompt in jobs:
        d = HERE / "director_runs" / f"{stamp}_{slug_of(key)}{TAG}"
        d.mkdir(parents=True, exist_ok=True)
        try:
            Direction(q, key, prompt, d, a.rounds, a.gray_rounds, key in HOLDOUTS,
                      ref=Path(a.ref).resolve() if a.ref else None).go()
        except Exception:
            import traceback
            (d / "crash.txt").write_text(traceback.format_exc())
            print(f"   {key}: harness error — see {d / 'crash.txt'}", flush=True)


if __name__ == "__main__":
    main()
