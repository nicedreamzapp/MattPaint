# Painting tricks learned (append every time something works or fails)

**This is the RENDERING file: light, colour, edges, texture, atmosphere.**
Skeleton, proportion, joints, attachment and perspective go in CONSTRUCTION.md and are
diagnosed on flat gray shapes before any lighting pass. Never cross-write the two — a
proportion error critiqued from a lit image gets a lighting fix, which is why the horse
never moved. Loop design and known failure modes: LOOP.md.

## Light
- Glow falloff MUST be: small radius = high alpha, large radius = ~0. Inverting it paints a
  visible hard-edged dome/bubble. (dawn ridges, 3 failed iterations)
- A wide translucent glow stacked over a colour GRADIENT creates a rainbow oil-slick arc.
  Keep halos tight, or blend each ring toward the local background colour.
- Backlit rim light must hug the real silhouette. Guessed arcs float off the shape as stray loops.

## Atmosphere
- Atmospheric perspective is the single strongest realism cue: each further layer lifts toward
  the sky colour and loses contrast. Layered ridges fading into haze read as photographic.
- Haze/mist = MANY low-alpha (0.01) overlapping dabs. Never opaque bars (looks like tape),
  never sparse big circles (looks like bokeh).

## Foliage
- Do NOT space dabs evenly along a twig: it reads as a beaded curtain.
- Foliage reads best as an irregular MASS: many overlapping dabs, varied radius, varied colour,
  clustered with gaps, then a few darker accents for depth.
- Radial line bursts look like snowflakes, not leaves.

## Form
- Smooth volumetric shading = per-cell diffuse from a light direction. Scattered random
  light/dark dabs read as mould/blotches.
- Cylinders (trunks, trunk-like limbs) need a lit band offset from centre, not a centred gradient.
- Uniform spacing/width anywhere reads as clip art. Vary everything.

## Subjects
- Creatures drawn from scratch stay cartoonish. Backlit silhouettes are the honest way to make
  them read well without needing real anatomy detail.
- Photoreal is reachable by sampling a real reference photo's pixels — and the eagle triptych
  reproduction proves the substrate is NOT the limit: rect/line/dab over a canvas holds
  photographic realism at 1000x548 with no banding and no visible primitive vocabulary. So when a
  from-scratch painting doesn't read as real, that is never the brushes failing. It is the
  decision about where the strokes go. (`repro_best.py` on `ref_eagle.png`, compare_best.png)

## Stochastic fine texture (the sampler's own failure class)
- **Condition:** a region whose detail is high-frequency and *random* rather than structured —
  feather fringe, reptile scale, rock micro-texture, bark grain, foliage interior.
- **Mechanism:** both paths resolve flat regions and hard edges well, because both are cheap to
  describe: a flat region is one rect, an edge is one directional stroke. Stochastic texture has
  no such compression — every element is its own op — so under any op pressure it is the first
  thing to get averaged away, and averaging random detail produces mush, not softness.
- **Evidence:** in the eagle reproduction the flat sky, the hard wing edges and the beak survive
  intact; what degrades is exactly this class — the head's feather fringe reads slightly
  sawtoothed, the talon scale pattern drops a level, the panel-one rock micro-texture flattens.
  Same reason foliage tends toward mush in the from-scratch work.
- **Consequence:** texture is the cheapest thing to sacrifice and the first thing to go. Do not
  read its loss as a rendering bug; read it as a budget symptom, and check what the budget went to.

## Rim light (solved)
- For a multi-part silhouette, each part drawing its own arc creates floating lassos across the body.
  Fix: for every candidate rim point, test it against ALL other parts and skip it if it falls inside
  one. Only true outer-boundary points get lit. (`silhouette_rim` in art.py)

## Foliage (solved)
- `canopy()` = irregular mass of overlapping dabs, varied radius/tone, ~16% random gaps so the
  backlight shows through, plus occasional crisp leaf edges. Reads as real backlit canopy.

## Python gotcha
- A negative base with a fractional exponent returns a COMPLEX number in Python, which then blows up
  any later comparison. Loops that start at `int(HORIZON)` can sit a fraction above the horizon and
  produce t = -0.0008. Always clamp: `max(0.0, t) ** 0.9`.

## Structure / process
- When replacing a block of code, check whether the CALL SITES lived inside the replaced range.
  Twice a routine was rewritten perfectly and silently never invoked (temple columns).
- Small repeated objects (acorns, leaves) must be built from dabs, not horizontal rects. Rect rows
  read as brickwork.
- Anything drawn before a large fill gets covered. Reflections must be painted AFTER the water,
  columns before the floor but the floor must not span the full height.
- Animal proportion cheat-sheet that worked: horse legs ≈ half total height, neck carried forward
  ~45° not vertical, barrel long not round. Dog: short neck, head forward, legs thin and separated.

# ART DIRECTION (external critique, 2026-09-14) — the five rules
1. **Not more detail — more believable light.** A simple tree with correct lighting beats a detailed
   tree with wrong lighting.
2. **Everything occupies physical space.** For every object ask: what is it touching? what is it
   casting a shadow on? what reflects light onto it? what does it block? what is behind it?
3. **Three levels of detail.** Foreground sharp/high-contrast, middle moderate, background simplified
   and hazy. Never texture everything equally.
4. **Materials respond to light differently.** stone ≠ glass ≠ water ≠ metal ≠ bark ≠ fur ≠ wet asphalt.
   Change the surface response, not the geometry.
5. **Add subtle imperfections.** Vary shape, colour, texture, spacing, scale, orientation. Real things
   are never uniform. Keep the variation quiet.

**Goal is "illustrated realism":** keep the simplified shapes, make the PHYSICS real.
simple horse + real lighting  >  photorealistic horse.

## Specific techniques worth stealing
- **Light map:** render the stained glass, then project it onto the floor with a perspective transform
  so coloured patches correspond to the bright glass pieces. Darken where columns occlude.
- **Wet asphalt reflection:** flip, blur, stretch vertically, horizontally displace, break apart with
  road texture, lower opacity. Never a clean mirror. Red lights become long irregular streaks.
- **Volumetric light:** rays are visible because they hit mist/dust. Soft → broken → variable → fading,
  not clean geometric polygons.
- **Foliage LOD:** silhouette → foliage clusters → small leaf groups → occasional individual leaves.
  Only 3-4 levels needed.
- **Scales/fur:** suggest with directional texture, never outline each one.
- **Contact:** grass overlaps hooves, a heavy animal bends the branch it sits on, soft contact shadows
  directly beneath. Objects must not float on top of the scene.
- **Silhouettes:** not 100% black. shadow #111 / body #191919 / warm rim. Form without losing the shape.
- **Distance:** farther = lighter, bluer, lower contrast, blurrier.

## Never state an edge twice
- **Condition:** a boundary that is already defined by something else — a rim light along a
  backlit crest, a cast shadow, a hard value break.
- **Mechanism:** an edge pass that draws over it adds a second, slightly different line in a
  slightly different colour. Two statements of the same boundary read as an outline, and an
  outline is the most reliable tell of illustration rather than photograph.
- **Fix:** before drawing an edge, test whether light already owns that point; skip it if so, and
  take the edge colour from the mass side so it can only soften, never outline.
  (gen3 dawn ridges, first edges pass: pale chalk line along the near crest)

## RULE THAT KEEPS GETTING BROKEN
- **ANY per-part lighting pass on a multi-part figure must run the occlusion test.** Rim light, cool
  sky fill, warm bounce, fur fuzz — all of it. Without it, every internal ellipse boundary lights up
  and the figure looks stitched together. Broken 3 separate times (monkey rim, horse cool fill, dog
  warm bounce). If you write a loop `for part in parts:` that draws light, add the test in the same edit.

## Bugs that produced obvious visual failures (all real, all fixed)
- Bare canvas showing through: layers that stop short of the frame edge leave WHITE. Always run
  background layers to H, or paint a base first. (Dawn Ridges bottom third went solid white.)
- Snow/overlay rules keyed to a height threshold flood down near slopes. Cap the depth (`min(26, ...)`).
- Junction swelling on branches: keep it under 1.35x and confine it to the first ~8%, then taper
  `(1-p)**1.75`, or limbs read as clubs/fingers.
- Fins/wings drawn as radial rays from a point become paper fans with visible spokes. Build them as
  a membrane swept between a leading and trailing edge, translucent toward the tip.
- Rain/streaks drawn with opaque lines dominate everything. Use low-alpha dab trails for the bulk,
  opaque lines only for a handful of foreground drops.

## Hair is dense strands — not a band, not a spray
- **Condition:** mane, tail, forelock, feathering, any long hair mass.
- **Mechanism:** hair has to be solid in the middle and broken at the edge at the same time.
  A filled band of constant width gives a clean boundary, which reads as a painted stripe (the
  gen3 tail came out a literal black rectangle). Loose separate dabs give no interior, which
  reads as flung dirt. Drawing MANY overlapping strands, each a continuous line with a jittered
  root, produces both behaviours from one construction: they merge where they are dense and
  separate where they thin out. That is also what hair physically is.
- **Cost:** ~32,000 strokes on one horse's mane and tail. Hair is expensive and there is no
  cheap version — both cheap versions are the two failure modes above.

## A leg is a cylinder, and a cylinder's darkest value is NOT at its edge
- **Condition:** any limb, trunk, pipe, neck — anything round lit from the side.
- **Mechanism:** across a lit cylinder the values run highlight, terminator, CORE SHADOW, then
  reflected light lifting the far edge back up. Putting the darkest value at the silhouette edge
  makes a cone. The bounce at the far edge is what makes it read as round, and near the ground
  that bounce takes the colour of the ground, not the colour of the sun — off a sunlit field it
  comes back green.
- **Trap:** if key and core shadow already describe the turn, do NOT also multiply by
  sqrt(1-n²) for roundness. Doing both drove every leg on the gen3 horse to black.

## Occlusion is a separate statement from light
- **Condition:** any figure with masses that meet — shoulder into neck, flank into stifle,
  barrel over belly and inner legs.
- **Mechanism:** light says which side is bright. Occlusion says which parts are buried, and it
  is independent of where the sun is. A figure lit correctly but with no occlusion reads as an
  inflated toy, because nothing is tucked under anything. The specific darks that make a horse
  read as a horse — the groove behind the shoulder blade, the flank crease in front of the
  stifle, the shadow the barrel throws onto the belly — are all occlusion, not lighting.
- **Fix:** a crease list (point, radius, strength) plus a depth term, applied as a multiplier
  AFTER the diffuse term. Both, or neither.

## A cast shadow is the second statement of the light
- **Condition:** anything standing on a surface.
- **Mechanism:** a symmetric blob under the subject says nothing about where the sun is and
  reads as a sticker. A low sun throws a LONG shadow, away from the light, that is hard and
  dark only at the contact points and dissolves as it runs. Direction and length are the
  content; the darkness is not.

## Low-alpha coverage has TWO safe regimes, and the middle is a trap
- **Condition:** any wash laid over a large area with low alpha — vignette, haze, mist, glaze,
  atmospheric veil, dust.
- **Mechanism:** the dabs must average out. MANY TINY dabs average because each contributes
  almost nothing and they overlap densely. FEW HUGE dabs average because each one covers so
  much area that its own boundary is off-frame. **Moderate radius at moderate count does
  neither** — the dabs are big enough to see individually and sparse enough not to merge, so
  they clump into visible lumps.
- **This is one rule with four names already:** the bokeh discs in the gen3 ridge haze, the
  mottled crust in vignette v2, "never sparse big circles" in the old haze note, and the
  beaded rim. Same failure every time.
- **Huge-and-faint is the cheap regime.** Radius 55-150 at alpha ~0.01 covered a full frame in
  ~2,000 ops. Tiny-and-many costs an order of magnitude more.

## Any full-frame effect placed on a grid is a screen door
- **Condition:** vignette, noise, grain, scan-lines, any pass that walks the whole canvas.
- **Mechanism:** stepping x and y by a fixed amount puts every dab on a lattice, and the eye
  finds a lattice instantly even at 1% alpha. Vignette v1 stepped 9px and produced a visible
  screen-door mesh over the entire painting.
- **Fix:** random position, varied radius, always. There is no case where a grid is correct.

## PHOTOGRAPHIC DEFECTS — the highest return per stroke found so far
- **Condition:** a finished painting that looks clean.
- **Mechanism:** the gap between these paintings and photographs is not detail, it is DEFECT.
  A photograph carries lens fall-off (cos^4 off axis), chromatic fringing at high-contrast
  edges that grows toward the corners, sensor noise that rises as signal falls so it is loudest
  in shadow, one plane of focus with everything else soft, dust, and veiling glare. A render has
  none of these and CLEAN IS WHAT READS AS RENDERED.
- **Result (dawn ridges A/B, 2026-09-14): 29,241 defect strokes on a 345,198 stroke painting —
  8.5% — and it changed the read more than any construction work in the whole of gen3.**
- **Rule: a defect that can be seen as itself has failed.** Every magnitude here is set so the
  effect is only perceptible as "this was photographed," never as "something was applied."
- Implemented in `defects.py`, deliberately separable from the loop so it can be A/B'd alone.
