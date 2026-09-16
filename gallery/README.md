# The paintings

Each generation repaints the SAME prompts from `../fast/PROMPTS.md`, from the sentence only —
never from the previous picture and never from the previous script.

    gallery/            gen 1   the original set
    gallery/gen2/       gen 2
    gallery/gen3/       gen 3   + _ablation/ showing one change at a time
    gallery/gen4/       gen 4   outlines deleted entirely, terrain lit instead of filled
    gallery/gen5/       gen 5   faceted terrain, full lighting model

Every picture has a `.run.json` beside it: stroke count, seconds, strokes per second, seed,
canvas, script and its hash. Files named FLAT_GRAY_TEST are the construction check — the
silhouette has to read as a mountain range with no colour at all before any colour is added.

The written critiques from Grok, Gemini and ChatGPT are in `../fast/critiques/`.
What was learned is in `../fast/TRICKS.md` (rendering), `../fast/CONSTRUCTION.md` (structure)
and `../fast/LOOP.md` (the loop itself, and what went wrong).
