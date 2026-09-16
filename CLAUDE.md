# MattPaint — rules for any agent working here

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
