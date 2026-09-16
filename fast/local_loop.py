"""LOCAL LOOP — generation 6, painted entirely by Qwen 3.8 Heretic VL (bf16) on this Mac.

The same method the mini used for gens 3-5, with a local model in every seat:

    PLAN        read the prompt as LIGHT; write a value plan, a construction plan and a budget,
                with every real-world constant labelled ZONE 1 (sourced) or ZONE 2 (tuned by eye)
    WRITE       turn the plan into a gen-style script (art.py / g3lib / g5lib vocabulary)
    PREFLIGHT   build the op list with no browser (PAINT_PREFLIGHT=1): crashes, empty or runaway
                paintings and slow scripts are caught and sent back before anything opens on screen
    GRAY        construction first. Paint in flat gray and look ONLY at structure, against
                CONSTRUCTION.md. No colour work starts until the gray reads as the subject.
    COLOUR      paint it properly (defects pass included), then look ONLY at rendering, against
                GEN5_RULES.md + TRICKS.md. Construction and rendering are never critiqued together.
    REWRITE     every rewrite starts from a written change plan and comes back as SEARCH/REPLACE
                edits, not a whole new script; edits that don't apply are sent back, and after two
                misses it falls back to a full rewrite. An unchanged script is refused.
    SPEED       every text step opens with the same brief (rules, API, example, subject). It is
                read once per subject and reused; a load-time self-test must show cached and
                uncached output identical, token for token, or the reuse stays off.
    JUDGE       the new painting is compared with the best so far, in BOTH orders. It only
                replaces the best if it wins both times. A round can never make the result worse.
    LESSONS     at the end the model writes at most three lessons, each as condition + mechanism
                + fix, into LOCAL_TRICKS.md / LOCAL_CONSTRUCTION.md — kept apart from the mini's
                files so a smaller model's notes never rot the originals.

Holdouts (LOOP.md: "hold two subjects out entirely") are painted once and never iterated.

    local_loop.py "DAWN RIDGES"                     one subject, default rounds
    local_loop.py "DAWN RIDGES" --rounds 4 --gray-rounds 2
    local_loop.py --all                             every PROMPTS.md subject, holdouts included
    local_loop.py --resume local_runs/<dir>         carry on after an interruption
    --no-think                                      skip the reasoning channel (faster, weaker)
    --no-cache                                      read the full brief on every step

Run it through run_local_loop.sh, which waits for Song Forge to be idle, pauses it, holds a
forge_guard seat, and puts Song Forge back when this exits.
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GALLERY = HERE.parent / "gallery" / "gen6_local"
MODEL = "donedynamics/Qwen3.8-27B-heretic-VL-MLX-bf16"
PAINT_PY = os.path.expanduser("~/.local/mlx-server/bin/python3")   # has websockets/numpy/PIL
GEN_LABEL = "6TH GEN · LOCAL QWEN 3.8"
HOLDOUTS = ("AURORA LAKE", "THE LONG WAIT")    # same two the mini held out in gen5
FIX_TRIES = 3
PREFLIGHT_TIMEOUT = 180
PAINT_TIMEOUT = 300
OPS_MIN, OPS_MAX = 20_000, 900_000
LESSON_LINES = 80                               # how much of each LOCAL_*.md goes into a brief
ANIMATE = ("MORNING FIELD", "THE LONG WAIT", "THE WATCHER", "DEEP LIGHT")   # get CONSTRUCTION.md in full


# ------------------------------------------------------------------------------------ inputs
def prompts():
    out = {}
    for m in re.finditer(r"\*\*([A-Z' ]+)\*\* — (.+)", (HERE / "PROMPTS.md").read_text()):
        out[m.group(1).strip()] = m.group(2).strip()
    return out

def slug_of(key):
    return key.lower().replace(" ", "_").replace("'", "")

def read(name, tail=None):
    p = HERE / name
    if not p.exists():
        return ""
    t = p.read_text()
    if tail:
        t = "\n".join(t.splitlines()[-tail:])
    return t

def example_for(key):
    """A complete working gen5 script of a DIFFERENT subject (PROMPTS.md: never port the previous
    script of the same subject)."""
    return "g5_narrows.py" if key == "AURORA LAKE" else "g5_aurora.py"

API = """
PAINTING VOCABULARY (the only way to put paint on the canvas; canvas is W x H pixels, y grows down)
  a = Art(W, H, "TITLE")          R, L, D = a.R, a.L, a.D
  R(x, y, w, h, (r,g,b))                  opaque rectangle — NO alpha, never use for washes/haze
  L(x1, y1, x2, y2, width, (r,g,b))       opaque line
  D(x, y, radius, (r,g,b), alpha=1.0)     round dab — the ONLY op with alpha
  The canvas starts WHITE: lay a base coat over all of it. The top 58 px get a title bar afterwards.

HELPERS
  mix(c1, c2, t) -> colour                 t clamped 0..1
  P = G5.Paint(a, GRAY); col = P.col       col(value 0..1, hue(r,g,b), sat=0.62) -> colour
        ALL colour must go through col() so the flat-gray pass works: value first, hue as a tint.
  G5.frac(v, v0, v1)   clamped 0..1 ramp   — ALWAYS use this, never hand-divide (complex-number trap)
  G5.env(t, power)     0 at both ends, 1 in the middle, clamped
  G5.vnoise(x, y) / G5.fbm(x, y, oct) / G5.ridged(x, y, oct, sharp)   hashed noise, 0..1, never periodic
  G5.shade(nx, ny, to_sun, occ=0, ambient=0.30, bounce=0) -> light amount (full lighting model)
  G5.temp(lit, warm, cool, bounce_col=None, bounce=0) -> colour temperature by light
  G5.wash_tiny(a, n, (x0,x1), (y0,y1), colf, alpha=0.03)   many tiny dabs (over BRIGHT fields)
  G5.wash_huge(a, n, (x0,x1), (y0,y1), colf, alpha=0.010)  few huge dabs (over DARK fields)
        wash colf is a function (x, y) -> colour
  G5.fill_columns(a, x0, x1, top_of, bottom, colf, step_y=3, step_x=2.0)
        fills from top_of(x) down to bottom with colf(x, y, yt), yt = top_of(x);
        step_x must suit the SHARPEST feature in the field, not the average
  G5.envelope(seed, W, base_y, amp, n_mass) -> h(x)   a skyline built like geology (returns y)
  G5.drainage(seed, n, W, top_of) / G5.terrain_normal(x, y, ridges)   terrain organised by water
  G.atmos(col, depth, sky, strength)       atmospheric perspective (depth 1 near, 0 far)

REQUIRED SCRIPT SHAPE (the harness depends on it)
  import asyncio, math, random, sys
  import art as A
  from art import Art, mix, TOPBAR
  import g3lib as G
  import g5lib as G5
  OUT = sys.argv[1]
  GRAY = "gray" in sys.argv[2:]
  A.GEN = "<label>"
  random.seed(<int>)
  W, H = 1380, 900
  a = Art(W, H, "<TITLE IN CAPS>")
  R, L, D = a.R, a.L, a.D
  P = G5.Paint(a, GRAY); col = P.col
  def build(): ...
  build()
  asyncio.run(G5.paint(a, OUT, {"subject": "<key>", "prompt": "<prompt>", "painter": "local-qwen3.8"},
      gray=GRAY, focal_y=H*0.6))

BUDGET: 60,000-400,000 ops. Never loop over every pixel; step 2-6 px. The script must finish
building in well under a minute.
"""


# ------------------------------------------------------------------------------------ model
class Qwen:
    """The model, loaded once.

    Text-only calls can name a PREFIX (the rulebook, API and example — identical for every call on a
    subject). Its KV/state is computed once and a copy is reused for each call, so only the part
    that changes is read. Same weights, same precision. A self-test at load compares cached against
    uncached output token for token; any mismatch turns the cache off for the whole session.
    Calls with images always take the ordinary uncached path."""

    def __init__(self, think=True, cache=True):
        from mlx_vlm import load
        t = time.time()
        self.model, self.proc = load(MODEL)
        self.load_s = round(time.time() - t, 1)
        self.think = think
        self.tok = getattr(self.proc, "tokenizer", self.proc)
        self.snapshots = {}
        self.cache_on = cache and self._selftest()

    # -- plain path (images, or cache off)
    def _generate(self, prompt, images, max_tokens, temperature, think):
        from mlx_vlm import generate
        from mlx_vlm.prompt_utils import apply_chat_template
        p = apply_chat_template(self.proc, self.model.config, prompt,
                                num_images=len(images), enable_thinking=think)
        lm = self.model.language_model
        lm._position_ids = None; lm._rope_deltas = None
        r = generate(self.model, self.proc, p, image=list(images) or None,
                     max_tokens=max_tokens, temperature=temperature, verbose=False)
        return r.text, r.generation_tokens, r.generation_tps

    # -- cached path
    def _ids(self, text):
        return list(self.tok.encode(text, add_special_tokens=False))

    def _prefill(self, ids, cache):
        import mlx.core as mx
        lm = self.model.language_model
        for i in range(0, len(ids), 2048):
            lm(mx.array([ids[i:i + 2048]]), cache=cache)
            mx.eval([c.state for c in cache])
        mx.clear_cache()

    def _copy(self, cache):
        import mlx.core as mx
        new = self.model.language_model.make_cache()
        for n, o in zip(new, cache):
            st = o.state
            n.state = [mx.array(x) if x is not None else None for x in st] if isinstance(st, (list, tuple)) else st
            try:
                n.meta_state = o.meta_state
            except Exception:
                pass
            if hasattr(o, "offset") and hasattr(n, "offset"):
                n.offset = o.offset
        return new

    def _cached(self, prefix, prompt, max_tokens, temperature, think, use_snapshot=True):
        """use_snapshot=False runs the identical code path without reusing anything — that is
        what the self-test compares against."""
        import mlx.core as mx
        from mlx_vlm.prompt_utils import apply_chat_template
        full = apply_chat_template(self.proc, self.model.config, prefix + prompt,
                                   num_images=0, enable_thinking=think)
        ids = self._ids(full)
        cut = full.find(prefix[:200])
        if cut < 0:
            return None
        pids = self._ids(full[:cut] + prefix)
        keep = len(pids) - 8                       # stay clear of a token that merges across the seam
        if keep < 64 or ids[:keep] != pids[:keep]:
            return None
        lm = self.model.language_model
        if use_snapshot:
            key = hash(tuple(pids[:keep]))
            if key not in self.snapshots:
                lm._position_ids = None; lm._rope_deltas = None
                snap = lm.make_cache()
                self._prefill(pids[:keep], snap)
                self.snapshots = {key: (snap, lm._rope_deltas)}      # one subject at a time
            snap, deltas = self.snapshots[key]
            cache = self._copy(snap)
            lm._position_ids = None; lm._rope_deltas = deltas
        else:
            lm._position_ids = None; lm._rope_deltas = None
            cache = lm.make_cache()
            self._prefill(ids[:keep], cache)
        suffix = ids[keep:]
        eos = {self.tok.eos_token_id} | {self.tok.convert_tokens_to_ids(t) for t in ("<|im_end|>", "<|endoftext|>")}
        out = []
        t = time.time()
        logits = lm(mx.array([suffix]), cache=cache).logits[:, -1, :]
        for _ in range(max_tokens):
            if temperature == 0:
                nxt = mx.argmax(logits, axis=-1)
            else:
                lp = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
                nxt = mx.random.categorical(lp * (1 / temperature))
            y = int(nxt.item())
            if y in eos:
                break
            out.append(y)
            logits = lm(mx.array([[y]]), cache=cache).logits[:, -1, :]
        secs = max(time.time() - t, 1e-6)
        return self.tok.decode(out), len(out), round(len(out) / secs, 1)

    def _selftest(self):
        """The cache may only change WHEN work is done, never WHAT comes out: cached and uncached
        runs of the same code must match token for token, twice (the second catches a snapshot
        corrupted by the first reuse)."""
        prefix = API + "\n" + read("GEN5_RULES.md") + "\n"
        q = "In one sentence, what is the only op with alpha? Then name two helpers."
        try:
            base = self._cached(prefix, q, 40, 0.0, False, use_snapshot=False)
            one = self._cached(prefix, q, 40, 0.0, False)
            two = self._cached(prefix, q, 40, 0.0, False)
        except Exception as e:
            print(f"prefix cache self-test error ({type(e).__name__}: {e}) — cache OFF", flush=True)
            self.snapshots = {}
            return False
        ok = base is not None and base[0].strip() != "" and base[0] == (one or ("",))[0] == (two or ("",))[0]
        print(f"prefix cache self-test: {'PASS — cache ON' if ok else 'mismatch — cache OFF'}", flush=True)
        if not ok:
            for label, r in (("uncached", base), ("cached", one), ("again", two)):
                print(f"   {label}: {(r or ('<none>',))[0][:120]!r}", flush=True)
        self.snapshots = {}
        return ok

    def ask(self, prompt, images=(), max_tokens=6000, temperature=0.2, think=False, prefix=""):
        import mlx.core as mx
        think = think and self.think
        max_tokens += 4000 if think else 0
        mx.reset_peak_memory()
        t = time.time()
        r = None
        if prefix and not images and self.cache_on:
            r = self._cached(prefix, prompt, max_tokens, temperature, think)
        cached = r is not None
        if r is None:
            r = self._generate(prefix + prompt, images, max_tokens, temperature, think)
        text, ntok, tps = r
        if "</think>" in text:
            text = text.split("</think>", 1)[1]
        return text.strip(), {"s": round(time.time() - t, 1), "tok": ntok, "tps": tps,
                              "peak_gb": round(mx.get_peak_memory() / 1e9, 1),
                              "think": think, "cached": cached}


def extract_code(text, rnd):
    m = re.findall(r"```(?:python)?\n(.*?)```", text, re.S)
    code = max(m, key=len) if m else text
    # The harness owns the output path, the gray switch and the label, whatever the model wrote.
    # (Round 1 of the first run hardcoded OUT = "g5_dawn_ridges.png".)
    code = re.sub(r"(?m)^OUT\s*=.*$", "OUT = sys.argv[1]", code)
    code = re.sub(r"(?m)^GRAY\s*=.*$", 'GRAY = "gray" in sys.argv[2:]', code)
    code = re.sub(r"(?m)^A\.GEN\s*=.*$", f'A.GEN = "{GEN_LABEL} · {rnd}"', code)
    code = re.sub(r"G5\.paint\(\s*a\s*,\s*[^,]+,", "G5.paint(a, OUT,", code)
    head = []
    if not re.search(r"(?m)^OUT = sys\.argv\[1\]", code):
        head.append("OUT = sys.argv[1]")
    if not re.search(r"(?m)^GRAY = ", code):
        head.append('GRAY = "gray" in sys.argv[2:]')
    if head:
        code = "import sys\n" + "\n".join(head) + "\n" + code
    return code.strip() + "\n"

EDIT_HOWTO = """Reply ONLY with edit blocks — never the whole script. Each block:
<<<<<<< SEARCH
(lines copied EXACTLY from the current script, enough to be unique)
=======
(the replacement lines)
>>>>>>> REPLACE
Use as many blocks as the change needs. Unchanged lines are never repeated."""

def apply_edits(code, text):
    """Apply SEARCH/REPLACE blocks. Returns (new_code, None) or (None, problem)."""
    blocks = re.findall(r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n?>>>>>>> REPLACE", text, re.S)
    if not blocks:
        return None, "No edit blocks were found. Reply with SEARCH/REPLACE blocks."
    for i, (old, new) in enumerate(blocks, 1):
        n = code.count(old)
        if n == 0:   # tolerate trailing-space differences only
            loose = re.compile(r"[ \t]*\n".join(re.escape(l.rstrip()) for l in old.split("\n")))
            hits = list(loose.finditer(code))
            if len(hits) == 1:
                code = code[:hits[0].start()] + new + code[hits[0].end():]
                continue
            return None, f"Edit block {i}: its SEARCH text is not in the script. Copy the lines exactly:\n{old}"
        if n > 1:
            return None, f"Edit block {i}: its SEARCH text appears {n} times. Include more lines so it is unique:\n{old}"
        code = code.replace(old, new, 1)
    return code, None

def same(a, b):
    norm = lambda c: re.sub(r"(?m)^A\.GEN.*$", "", c or "").strip()
    return norm(a) == norm(b)


# ------------------------------------------------------------------------------------ running
def run_script(path, png=None, gray=False, preflight=False):
    env = dict(os.environ)
    if preflight:
        env["PAINT_PREFLIGHT"] = "1"
    limit = PREFLIGHT_TIMEOUT if preflight else PAINT_TIMEOUT
    argv = [PAINT_PY, path.name, str(png or "/dev/null")] + (["gray"] if gray else [])
    t = time.time()
    try:
        p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True, env=env, timeout=limit)
        out, rc = (p.stdout + p.stderr), p.returncode
    except subprocess.TimeoutExpired:
        out, rc = (f"TIMEOUT: the script took longer than {limit}s. It is looping over too many "
                   "pixels — step coarser."), -9
    return rc, out[-3000:], round(time.time() - t, 1)

def preflight_verdict(rc, out):
    if rc != 0:
        return f"The script crashed:\n```\n{out}\n```"
    m = re.search(r"PREFLIGHT ops=(\d+) x=(-?\d+)\.\.(-?\d+) y=(-?\d+)\.\.(-?\d+)", out)
    if not m:
        return f"The script ran but never reached G5.paint(a, OUT, ...):\n```\n{out}\n```"
    ops, x0, x1, y0, y1 = map(int, m.groups())
    if ops < OPS_MIN:
        return f"Only {ops:,} ops — far too few to paint this. Budget is 60,000-400,000."
    if ops > OPS_MAX:
        return f"{ops:,} ops — far over budget (60,000-400,000). Step coarser."
    if x1 < 1200 or y1 < 800 or x0 > 100:
        return (f"The paint only covers x {x0}..{x1}, y {y0}..{y1} of a 1380x900 canvas. "
                "The canvas starts WHITE, so anything uncovered reads as a blown-out hole.")
    return None


# ------------------------------------------------------------------------------------ one subject
class Run:
    def __init__(self, q, key, prompt, rundir, holdout, rounds, gray_rounds):
        self.q, self.key, self.prompt, self.dir = q, key, prompt, rundir
        self.holdout, self.rounds, self.gray_rounds = holdout, rounds, gray_rounds
        self.slug = slug_of(key)
        self.state_path = rundir / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {
            "subject": key, "prompt": prompt, "model": MODEL, "holdout": holdout,
            "stage": "plan", "round": 0, "gray_round": 0, "best": None, "steps": []}
        rules, tricks, cons = read("GEN5_RULES.md"), read("TRICKS.md"), read("CONSTRUCTION.md")
        self.base = (f"You paint by writing a Python program.\n{API}\n"
                     f"THE RULES (apply from the first line — they were earned over five generations):\n{rules}\n")
        self.example = (f"A COMPLETE WORKING SCRIPT for a DIFFERENT subject (never copy its scene):\n"
                        f"```python\n{read(example_for(key))}```\n")
        self.cons = cons if key in ANIMATE else cons.split("## Where realism actually sits")[0]
        self.cons += "\n" + read("LOCAL_CONSTRUCTION.md", LESSON_LINES)
        self.tricks = tricks + "\n" + read("LOCAL_TRICKS.md", LESSON_LINES)
        self.subject = f"\nSUBJECT: {key}\nPROMPT (the ONLY description you get): {prompt}\n"
        # Every text-only step starts with exactly this, so the model reads it once per subject.
        self.prefix = (self.base + "\nRENDERING RULES:\n" + self.tricks +
                       "\nCONSTRUCTION RULES:\n" + self.cons + "\n" + self.example + self.subject + "\n")
        self.script = HERE / f"_local_{self.slug}.py"

    # -- bookkeeping
    def log(self, step, **kw):
        kw.update(step=step, t=time.strftime("%H:%M:%S"))
        self.state["steps"].append(kw)
        self.save()
        print(f"   [{kw['t']}] {step} " + " ".join(f"{k}={v}" for k, v in kw.items()
                                                  if k not in ("step", "t")), flush=True)

    def save(self):
        self.state_path.write_text(json.dumps(self.state, indent=1))

    def put(self, name, text):
        (self.dir / name).write_text(text)

    # -- steps
    def plan(self):
        text, st = self.q.ask(
            "Before any code, write the PLAN:\n"
            "1. LIGHT: what is the light doing in this prompt? Where is the source, what does it reach, "
            "what is lost in shadow? Most of the budget goes to the light.\n"
            "2. VALUE PLAN: every region of the frame with a value 0..1 (sky, far, mid, near, darkest dark, "
            "brightest light). The picture must read in flat gray from these numbers alone.\n"
            "3. CONSTRUCTION: what organises the structure (water for terrain, a skeleton for a body, "
            "perspective for a room)? One continuous silhouette per mass.\n"
            "4. BUDGET: ops per part, following the gen5 budget split.\n"
            "5. CONSTANTS: every number that claims to describe the real world, labelled ZONE 1 "
            "(where it comes from, and the range) or ZONE 2 (tuned by eye).\n"
            "No code.", max_tokens=1800, think=True, prefix=self.prefix)
        self.put("plan.md", text)
        self.log("plan", **st)
        return text

    def full_script(self, ask, rnd, temperature=0.2):
        text, st = self.q.ask(ask + "\nReply with the COMPLETE script in one ```python block only.",
                              max_tokens=7000, temperature=temperature, prefix=self.prefix)
        self.log("write-full", rnd=rnd, **st)
        return extract_code(text, rnd)

    def edit_script(self, code, ask, rnd, temperature=0.2):
        """Ask for SEARCH/REPLACE edits against `code`. A block that doesn't apply goes back with the
        reason; after two misses, fall back to a full rewrite so a formatting slip never costs quality.
        Returns the new code, or None if the model keeps returning it unchanged."""
        note = ""
        for attempt in range(3):
            text, st = self.q.ask(f"CURRENT SCRIPT:\n```python\n{code}```\n\n{ask}\n{note}\n{EDIT_HOWTO}",
                                  max_tokens=2500, temperature=temperature if attempt == 0 else 0.5,
                                  prefix=self.prefix)
            new, problem = apply_edits(code, text)
            if new is not None and same(new, code):
                problem = ("Those edits leave the script unchanged, so the painting would be identical. "
                           "Make the changes the plan calls for.")
                new = None
            self.log("write-edits", rnd=rnd, attempt=attempt, ok=new is not None, **st)
            if new is not None:
                return extract_code("```python\n" + new + "```", rnd)
            note = f"\nYOUR LAST EDITS DID NOT APPLY: {problem}\n"
            self.put(f"{rnd}_edits{attempt}_rejected.txt", f"{problem}\n\n--- reply ---\n{text}")
        new = self.full_script(f"CURRENT SCRIPT:\n```python\n{code}```\n\n{ask}", rnd, temperature=0.5)
        if same(new, code):
            self.log("unchanged-script-refused", rnd=rnd)
            return None
        return new

    def preflight(self, code, rnd):
        for attempt in range(FIX_TRIES + 1):
            self.script.write_text(code)
            rc, out, secs = run_script(self.script, preflight=True)
            problem = preflight_verdict(rc, out)
            ops = re.search(r"PREFLIGHT ops=(\d+)", out)
            self.log("preflight", rnd=rnd, attempt=attempt, s=secs,
                     ops=int(ops.group(1)) if ops else None, ok=problem is None)
            if problem is None:
                return code
            self.put(f"{rnd}_preflight{attempt}.txt", f"{problem}\n\n--- script ---\n{code}")
            if attempt == FIX_TRIES:
                return None
            fixed = self.edit_script(code, f"THE SCRIPT FAILED ITS TEST BUILD:\n{problem}\n\nFix that.", rnd)
            if fixed is None:
                return None
            code = fixed
        return None

    def paint(self, code, rnd, gray):
        name = f"{rnd}{'_gray' if gray else ''}"
        self.script.write_text(code)
        self.put(f"{rnd}.py", code)
        png = self.dir / f"{name}.png"
        rc, out, secs = run_script(self.script, png=png, gray=gray)
        ok = rc == 0 and png.exists()
        self.log("paint", rnd=rnd, gray=gray, ok=ok, s=secs)
        if not ok:
            self.put(f"{name}_paint_error.txt", out)
            return None
        if gray:   # the test is "reads with zero colour" — enforce it even if a colour slipped past col()
            from PIL import Image
            Image.open(png).convert("L").save(png)
        return png

    def look_gray(self, png, rnd):
        text, st = self.q.ask(
            f"This is the FLAT GRAY construction pass of a painting of: \"{self.prompt}\"\n\n"
            "Judge STRUCTURE ONLY: silhouettes, proportion, attachment, perspective, the value plan. "
            f"Not light, colour or texture.\nThe construction rules:\n{self.cons}\n\n"
            "The first line must be exactly VERDICT: PASS or VERDICT: FAIL. PASS only if a stranger "
            "would name the subject from this gray image alone. If FAIL, list the 3 most important "
            "structural problems: what you SEE, where, and the concrete change to the program. "
            "Ignore the title bar.", images=[str(png)], max_tokens=900)
        self.put(f"{rnd}_gray_look.md", text)
        passed = bool(re.search(r"VERDICT:\s*PASS", text))
        self.log("look-gray", rnd=rnd, passed=passed, **st)
        return passed, text

    def look_colour(self, png, rnd):
        text, st = self.q.ask(
            f"This is a painting made by a program from the prompt: \"{self.prompt}\"\n\n"
            "Judge RENDERING: light, value, colour temperature, edges, atmosphere, texture, defects. "
            "Structure was approved in gray; only raise it if it is badly broken.\n"
            f"The rules:\n{self.tricks}\n\n"
            "First say in one sentence what a stranger would think it shows. Then the 3 most important "
            "problems that stop it reading as the prompt, most important first. For each: what you SEE, "
            "where, which rule it breaks, and the concrete change to the program. Ignore the title bar "
            "and the stroke count.", images=[str(png)], max_tokens=1000)
        self.put(f"{rnd}_look.md", text)
        self.log("look", rnd=rnd, **st)
        return text

    def change_plan(self, code, critique, rnd, scope):
        text, st = self.q.ask(
            f"CURRENT SCRIPT:\n```python\n{code}```\n\nWhat it painted has these problems:\n{critique}\n\n"
            "Do NOT write the script yet. Write a numbered CHANGE PLAN: for each problem, the exact "
            "function or block you will change, what it does now, and what it will do instead, with the "
            f"new numbers. Change only {scope}. No code.", max_tokens=1200, think=True, prefix=self.prefix)
        self.put(f"{rnd}_change_plan.md", text)
        self.log("change-plan", rnd=rnd, scope=scope, **st)
        return text

    def rewrite_ask(self, critique, plan):
        return (f"PROBLEMS IN WHAT IT PAINTED:\n{critique}\n\n"
                f"YOUR CHANGE PLAN (implement every item, keep everything that already works):\n{plan}\n")

    def judge(self, best_png, new_png, rnd):
        """Asked in both orders; the challenger must win both, so position bias can't promote a
        worse painting."""
        wins = 0
        for first, second, challenger in ((best_png, new_png, 2), (new_png, best_png, 1)):
            text, st = self.q.ask(
                f"Two paintings of: \"{self.prompt}\"\n"
                "Which one reads more convincingly as that scene, with believable light? Ignore the "
                "title bars. The first line must be exactly WINNER: 1 or WINNER: 2, then one sentence why.",
                images=[str(first), str(second)], max_tokens=120)
            m = re.search(r"WINNER:\s*([12])", text)
            won = bool(m and int(m.group(1)) == challenger)
            wins += won
            self.log("judge", rnd=rnd, challenger_shown=challenger, challenger_won=won,
                     why=(text.splitlines() or [""])[-1][:160], **st)
        return wins == 2

    def lessons(self):
        steps = json.dumps([s for s in self.state["steps"]
                            if s["step"] in ("judge", "look-gray", "paint", "new-best", "kept-previous-best")])
        plans = "\n---\n".join(p.read_text()[:1500] for p in sorted(self.dir.glob("*_change_plan.md")))
        text, st = self.q.ask(
            f"You painted \"{self.prompt}\" over several rounds. What happened, step by step:\n{steps}\n\n"
            f"Your change plans, in order:\n{plans}\n\n"
            "Write AT MOST 3 lessons that would help paint a DIFFERENT subject. Each must be scoped:\n"
            "### <short title>\n- **Condition:** when it applies\n- **Mechanism:** why it works or fails\n"
            "- **Fix:** what to do\n- **Scope:** RENDERING or CONSTRUCTION\n"
            "Only write a lesson the rounds actually showed (a change that won or lost the judge, or a "
            "gray pass that flipped). If nothing was shown, reply NONE.", max_tokens=900, think=True,
            prefix=self.prefix)
        self.put("lessons.md", text)
        self.log("lessons", **st)
        if text.strip().upper().startswith("NONE"):
            return
        stamp = f"\n<!-- {time.strftime('%Y-%m-%d')} · {self.key} · local Qwen 3.8 -->\n"
        for block in re.split(r"(?m)^(?=### )", text):
            if not block.startswith("### "):
                continue
            target = ("LOCAL_CONSTRUCTION.md" if re.search(r"Scope:\**\s*CONSTRUCTION", block)
                      else "LOCAL_TRICKS.md")
            p = HERE / target
            if not p.exists():
                p.write_text(f"# {target[:-3]} — lessons from the local gen6 loop\n\n"
                             "Written by the local model. Kept apart from TRICKS.md and CONSTRUCTION.md "
                             "on purpose; only the last lines are fed back into a brief.\n")
            with p.open("a") as f:
                f.write(stamp + block.strip() + "\n")

    def publish(self):
        best = self.state.get("best")
        if not best:
            return
        GALLERY.mkdir(parents=True, exist_ok=True)
        src = self.dir / best
        shutil.copy(src, GALLERY / f"{self.slug}.png")
        side = src.with_suffix(".run.json")
        if side.exists():
            shutil.copy(side, GALLERY / f"{self.slug}.run.json")
        shutil.copy(self.dir / "best.py", GALLERY / f"{self.slug}.py")
        self.log("published", file=f"gallery/gen6_local/{self.slug}.png")

    # -- the whole subject; every stage is resumable from state.json
    def go(self):
        S = self.state
        tag = " (HOLDOUT — painted once, never iterated)" if self.holdout else ""
        print(f"\n=== {self.key}{tag} ===", flush=True)
        try:
            if S["stage"] == "plan":
                plan = self.plan()
                code = self.preflight(self.full_script(
                    f"YOUR PLAN:\n{plan}\n\nWrite the complete script from this plan.", "R0"), "R0")
                if not code:
                    return self.finish("could not write a script that passes preflight")
                self.put("current.py", code)
                S["stage"] = "gray"; self.save()

            code = (self.dir / "current.py").read_text()
            if S["stage"] == "gray":
                while True:
                    rnd = f"G{S['gray_round']}"
                    png = self.paint(code, rnd, gray=True)
                    if not png:
                        return self.finish("the gray pass failed to paint")
                    passed, crit = self.look_gray(png, rnd)
                    if passed or self.holdout or S["gray_round"] >= self.gray_rounds:
                        break
                    S["gray_round"] += 1; self.save()
                    rnd = f"G{S['gray_round']}"
                    plan = self.change_plan(code, crit, rnd, "construction")
                    new = self.edit_script(code, self.rewrite_ask(crit, plan), rnd, temperature=0.5)
                    new = new and self.preflight(new, rnd)
                    if not new:
                        self.log("gray-rewrite-failed", rnd=rnd)
                        break
                    code = new; self.put("current.py", code)
                S["stage"] = "colour"; self.save()

            if S["stage"] == "colour":
                if not S["best"]:
                    png = self.paint(code, "C0", gray=False)
                    if not png:
                        return self.finish("the colour pass failed to paint")
                    S["best"] = png.name; self.put("best.py", code); self.save()
                best_code = (self.dir / "best.py").read_text()
                while not self.holdout and S["round"] < self.rounds:
                    S["round"] += 1; self.save()
                    rnd = f"C{S['round']}"
                    crit = self.look_colour(self.dir / S["best"], rnd)
                    plan = self.change_plan(best_code, crit, rnd, "rendering")
                    new = self.edit_script(best_code, self.rewrite_ask(crit, plan), rnd, temperature=0.5)
                    new = new and self.preflight(new, rnd)
                    if not new:
                        self.log("round-skipped", rnd=rnd)
                        continue
                    png = self.paint(new, rnd, gray=False)
                    if not png:
                        continue
                    if self.judge(self.dir / S["best"], png, rnd):
                        S["best"] = png.name; best_code = new
                        self.put("best.py", new); self.log("new-best", rnd=rnd)
                    else:
                        self.log("kept-previous-best", rnd=rnd, best=S["best"])
                    self.save()
                if self.holdout:
                    self.look_colour(self.dir / S["best"], "C0")   # on file, never acted on
                S["stage"] = "lessons"; self.save()

            if S["stage"] == "lessons":
                if not self.holdout:
                    self.lessons()
                self.publish()
                S["stage"] = "done"; self.save()
            return self.finish("done")
        finally:
            self.script.unlink(missing_ok=True)

    def finish(self, why):
        S = self.state
        S["result"] = why; self.save()
        lines = [f"# {self.key} — gen 6, local Qwen 3.8", "", f"Prompt: {self.prompt}", "",
                 f"Result: {why}. Best: {S.get('best')}. Holdout: {self.holdout}.", "",
                 "| time | step | details |", "|---|---|---|"]
        for s in S["steps"]:
            d = ", ".join(f"{k}={v}" for k, v in s.items() if k not in ("step", "t"))
            lines.append(f"| {s['t']} | {s['step']} | {d[:180]} |")
        self.put("summary.md", "\n".join(lines) + "\n")
        print(f"   {self.key}: {why} — {self.dir}", flush=True)
        return why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subject", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--gray-rounds", type=int, default=2)
    ap.add_argument("--no-think", action="store_true")
    ap.add_argument("--no-cache", action="store_true", help="read the full brief on every step")
    ap.add_argument("--resume")
    a = ap.parse_args()
    P = prompts()
    stamp = time.strftime("%Y%m%d-%H%M%S")

    if a.resume:
        d = Path(a.resume).resolve()
        dirs = [d] if (d / "state.json").exists() else sorted(p.parent for p in d.glob("*/state.json"))
        jobs = [(json.loads((x / "state.json").read_text())["subject"], x) for x in dirs]
    elif a.all:
        jobs = [(k, HERE / "local_runs" / f"{stamp}_gen6" / slug_of(k)) for k in P]
    elif a.subject and a.subject.upper() in P:
        k = a.subject.upper()
        jobs = [(k, HERE / "local_runs" / f"{stamp}_{slug_of(k)}")]
    else:
        sys.exit(f"give a subject from {sorted(P)}, or --all, or --resume <dir>")

    q = Qwen(think=not a.no_think, cache=not a.no_cache)
    print(f"model loaded in {q.load_s}s, prefix cache {'on' if q.cache_on else 'off'}", flush=True)
    for key, d in jobs:
        d.mkdir(parents=True, exist_ok=True)
        try:
            Run(q, key, P[key], d, key in HOLDOUTS, a.rounds, a.gray_rounds).go()
        except Exception as e:           # one bad subject must not stop a batch
            import traceback
            (d / "crash.txt").write_text(traceback.format_exc())
            print(f"   {key}: harness error {type(e).__name__}: {e} — resume with --resume {d}", flush=True)


if __name__ == "__main__":
    main()
