# MattPaint — read this first

## What this project is (Matt's special project, in active development)
MattPaint is an MS Paint clone for the web (index.html, js/app.js). The research project inside
it, `fast/`, paints pictures stroke by stroke in MattPaint, from scratch, with no images going in.

- Gens 1-5 (Sept 2026, on the Mac mini): one hand-written script per painting. What they learned
  is in fast/GEN5_RULES.md, fast/TRICKS.md, fast/CONSTRUCTION.md, fast/LOOP.md.
- **Gen 6 (2026-09-16, on the M5): the scene engine.** `fast/scene_engine.py` holds the drawing
  knowledge; `fast/RECIPES.md` is the short recipe language; `fast/director.py` has the LOCAL
  Qwen 3.8 model write a recipe, look at the painting, revise it, and judge new vs best.
  Run with `fast/run_director.sh "prompt"` or the MattPaint Studio launcher. Fully offline.
- **Growing it = teaching the engine new things.** A new subject (lighthouse, horse, person,
  building...) is a new layer function in scene_engine.py, a row in LAYERS, and a row in
  RECIPES.md. Follow the gen 1-5 rules: value first via Paint.col, full lighting model, no
  outlines, washes in the two safe regimes, construction checked in flat gray.
- Work on branch `gen6-scene-engine`. Commit each step. Back up with
  `rsync -a --exclude __pycache__ ./ mini-vps:Desktop/PROJECTS/MattPaint-gen6-M5-backup/`.
  Never push: origin is Matt's PUBLIC GitHub — ask first.


## EVERY PICTURE IS PAINTED IN VIEW. No exceptions.
Matt watches the painting happen. That is the product.

- Every picture — real runs, tests, checks, "quick looks" — is painted by MattPaint in the Brave
  paint window, on screen, fully in view (engine.py fits the window and zooms the canvas).
- There is NO off-screen renderer in this project. Do not write one (cairo, PIL, numpy, headless
  Chrome, a hidden tab). One was built on 2026-09-16 "to check work quickly" and made 8 pictures
  Matt never saw; it was deleted.
- Preflight (`PAINT_PREFLIGHT=1`) only counts strokes. It never produces a picture, so it is allowed.
- When a run ends, the paint window STAYS OPEN on the last picture. Never close it on exit.
- Before saying "done", Matt must be able to see the result on his screen. Check the window is up.

Why agents keep breaking this: other machines' rules say "don't pop windows on Matt's screen"
and "don't crash-test on his screen", and it is faster to verify privately. For MattPaint those
instincts are WRONG — the screen is where the work is supposed to happen.
