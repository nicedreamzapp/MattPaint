# Construction rules (append every time something works or fails)

> ## ⚠ CONFABULATED CONSTANTS — read before trusting any number in this file
>
> The first version of this file asserted "a horse stands ~2.5 head lengths at the withers" as
> a fact. It is wrong; the standard artist system is ~3 at the withers and ~3 2/3 long. That
> number was never looked up. It was produced to fill a slot in code, and then written here in
> the voice of a reference, where it became the input to the next pass.
>
> The failure mode is specific and it is not ignorance: asked the question directly, the right
> answer comes back immediately. Writing code never poses the question — it demands a number,
> and a number arrives either way, with nothing in the moment marking which came from knowledge
> and which came from plausibility. A search works because a search is a question.
>
> **Rule: any constant in this project that claims to describe the real world must name where
> it came from, or be marked unverified. That includes proportions, angles, falloff ratios,
> subdivision depths and frequencies.** Constants that are pure invention (composition, seed,
> canvas size) are fine and need no source — the danger is only the ones pretending to be facts.
>
> **Also: there is no single correct horse.** Stubbs, Xu Beihong, Persian miniature, Greek,
> Lascaux — each is a different construction system, all of them read as horses. The academic
> realist system below was never chosen, it was assumed. Choose it deliberately or choose
> another, but do not mistake it for the only one.
>
> ### A citation is not correctness
> Sourcing a number makes a wrong number HARDER to catch, not easier, because it now looks
> settled. Withers height in head lengths varies by breed by more than the error it was
> introduced to fix - a draft horse and an Arabian are not close. **Record the RANGE and the
> BREED the number came from, never a bare figure.** Otherwise an invented constant has been
> replaced by a real constant applied to the wrong animal, which is the same failure in
> better clothes.
>
> ### Two zones, and every constant belongs to exactly one
> The test is NOT aesthetic vs factual. It is: **does this number describe the world, or does
> it only have to look good?**
>
> **ZONE 1 — CHECKED AGAINST THE WORLD.** Must cite a source, a range, and what it describes.
> Wrong values here are wrong, not merely unpleasant.
>   - animal proportions and joint positions
>   - value-plan luminance relationships (sky vs ground vs shadow is measurable, and getting
>     it wrong is why a scene reads flat) - CURRENTLY UNSOURCED, needs sourcing
>   - caustic band spacing and frequency (real optics, real reference footage)
>     - CURRENTLY UNSOURCED, needs sourcing
>   - atmospheric extinction with distance
>
> **ZONE 2 — TUNED BY EYE.** No correct value exists to look up. Must be LABELLED as tuned so
> nobody later goes hunting for a citation that cannot exist.
>   - fractal falloff 0.52 (anything 0.5-0.6 gives plausible texture)
>   - subdivision depth 3-4 levels
>   - gap fraction, jitter, alpha, stroke widths
>   - composition, seed, canvas size


**This file is diagnosed on FLAT GRAY SHAPES ONLY, before any lighting pass.**
A construction lesson must never be written into TRICKS.md, and a rendering lesson must never be
written in here. If both are critiqued from the same lit image, every proportion error gets
misdiagnosed as a lighting problem and gets a lighting fix. That is most of why the horse never
moved.

## The order (no step starts until the one above it reads correct)

1. **Structure.** Skeleton before any paint. Joints, proportions, attachment points, on flat gray
   shapes. Approve the silhouette first. No lighting pass until the construction reads correct.
2. **Values.** Assign each plane a value before colour exists. Sky lightest, ground mid, mass
   darkest. Paint the whole scene gray first. Correct values survive any palette.
3. **Edges.** Real scenes mix hard, soft and lost edges. Uniform edge treatment is the strongest
   tell of fake. Hard at focus, dissolving at depth and in shadow.
4. **Occlusion.** Every lighting pass needs a visibility test. Light what the source actually
   reaches. Without it, parts glow independently and the figure reads as assembled pieces.
5. **Reference.** Reference supplies construction, NOT pixels. Extract the proportion skeleton and
   the silhouette, then paint from the technique library. Sampling colour directly is copying,
   not drawing.
6. **Scale.** Detail frequency falls with distance. Near objects get texture, far objects get
   value only. The same stroke size everywhere flattens depth instantly and unmistakably.
7. **Perspective.** Establish horizon and vanishing points first, then place everything against
   them. Eye level decides every ellipse, every ground contact, every relative height in frame.
8. **Noise.** Stochastic texture needs STRUCTURED randomness, not uniform scatter. Clump it, vary
   density, follow the underlying form. Even scatter reads as static, never as feathers or bark.
9. **Budget.** Spend strokes where the error is largest, not evenly. Read the canvas back, diff
   against target, place the next batch there. Below threshold is wasted.
10. **Vocabulary.** Closed at rect, line, dab, replay-identical. The constraint is what forces
    lessons about placement rather than parameters. Add a primitive only if determinism holds and
    placement lessons still transfer.

## Where realism actually sits today (out of 100, 100 = reads as a photograph)

- **Landscape, weather, water, architecture: 70-80.** No anatomy; structure is either geometric
  (buildings, perspective) or statistical (mist, ridgelines, caustics). All of it nameable.
  Dawn Ridges is near 60 and the ten items above are exactly what it is missing.
- **Anything with an animal or a person: 25-40.** Gated entirely by construction. Rendering can be
  at 80 and one wrong joint drops the whole image — a viewer forgives soft focus and does not
  forgive a leg attached in the wrong place. This is the horse, and it stays here until this file
  gets its own diagnosis pass on untextured shapes.
- **Still life, single object, controlled light: 55-70.** Simple structure; realism rests mostly on
  values, edges and occlusion, which are all reachable now.

Both figures assume the starvation runs happen. Budget discipline is where placement gets learned
and it is untested as of 2026-09-14.

A construction skeleton derived from reference, then painted entirely from the technique library,
is worth roughly +15 on the animal case and is NOT a copy. That is how human painters work.

## Texture: fractal, not Fibonacci

- **Works — statistical self-similarity.** Natural texture is self-similar across scales, not
  uniform random. Generate foliage, rock, bark, cloud and mist by recursive subdivision: place
  large masses, subdivide with smaller versions at reduced amplitude, three or four levels deep.
  This fixes the mush problem directly, because it clumps detail the way nature does instead of
  scattering it evenly. Same for branching: recursive splits, fixed angle range, a diameter ratio
  at each junction. Correct-looking trees without anatomy knowledge, and cheap in ops.
- **Works — phyllotaxis, narrowly.** Golden-angle spiral is literally how seed heads, pinecones,
  sunflower centres and some succulents are built. Logarithmic spirals are real in nautilus
  shells, horns, fern crosiers. That is the entire list.
- **Does not work — composition.** Fibonacci and rule-of-thirds overlays are post-hoc descriptions
  imposed on finished paintings, not what makes an image read as real. A perfect golden-ratio
  composition with flat values still looks fake; a badly composed image with correct light still
  looks photographic. Attention spent on spiral overlays is spent on the one axis that does not
  move the number.
- **Test rather than believe.** Paint the same subject twice — recursive self-similar texture vs
  uniform scatter — diff both against reference and look. Then golden-section composition vs an
  arbitrary one. Prediction: the first comparison shows a large difference, the second shows none.

---

## Diagnosed on flat gray — MORNING FIELD, gen3 (2026-09-14, seed 3002)

Five construction passes, no light in any of them. Every error below was nameable as a number
or an attachment, which is the whole claim this file was built to test.

1. **Height at the withers was 1.62 head lengths.** The animal read as a donkey,
   and "donkey head, short legs, long barrel" were all the same single error. One number fixed
   all three. **A proportion error looks like several rendering errors until you measure it.**
   **CORRECTED 2026-09-14 — I then wrote 2.5 here and it was ALSO wrong. The standard artist
   system is ~3 head lengths at the withers and ~3 2/3 head lengths long, body excluding tail.
   See the CONFABULATED CONSTANTS warning at the top of this file.**
2. **Three ellipses for body, shoulder and hindquarter = a pasted-on circle and a hole at the
   throat.** Fix: one continuous silhouette, a top profile and a bottom profile through named
   anatomical points, filled between. Head, neck, barrel and hindquarter become the same mass and
   nothing can read as stuck on. **If a part can be drawn separately it can detach; build the
   body as one outline and there is nothing to detach.**
3. **Far-side legs offset by 0.2 head lengths read as flaps hanging outside the silhouette.**
   0.07 reads as a second leg. The offset that says "there is another leg behind this one" is
   much smaller than it feels.
4. **The point of buttock sat level with the croup, so there was no thigh behind the stifle** and
   the hindquarter ended in a vertical chop. The rearmost point of a standing horse is about
   1.55 head lengths above the ground, not level with the back.
5. **The upper limb segments are INSIDE the barrel.** Drawing shoulder-to-elbow and hip-to-stifle
   as limbs on top of the body produced cardboard tubes lying over the animal. Only elbow-down
   and stifle-down are separate limbs. **A joint being in the skeleton does not make the segment
   a separate shape.**

**Result against the prediction.** Matt predicted the horse would move very little because
construction is the newest and least tested part. Structure moved: the gen3 horse has correct
proportion, a continuous silhouette and attached limbs, and it reads as a horse rather than as a
toy animal. **Rendering did not follow.** The painted version is smooth and plastic — the coat
texture does not register at this scale, there is no self-shadow under the barrel, and the legs
are cones. So the gate moved from construction to rendering-on-a-figure, which is a different
and so far unsolved problem. Structure being fixable does NOT mean the picture is fixed.


## Horse proportions — SOURCED 2026-09-14
Source: standard artist head-length (HL) system, as set out in horseart.net's study guide,
Envato Tuts+ horse anatomy, and Monika Zagrobelna's horse drawing notes.

- **HL** = muzzle tip to the front of the ear.
- **Height at the withers ≈ 3 HL.**  (gen3 built 2.5 — too short by a sixth)
- **Body length excluding tail ≈ 3 2/3 HL.**  (gen3 built roughly square — too short by a third)
- **Leg length ≈ the depth of the body, back to belly.** Useful as a check: if the legs are
  shorter than the barrel is deep, the proportion is wrong.
- **Head ≈ as long as the shoulder; the neck is not much longer than the head.**
- The head divides into four equal parts: ear base to eye corner, eye corner to zygomatic,
  zygomatic to just above the mouth corner, mouth corner to the nose tip.
- **The joints are not where instinct puts them.** The backwards-bending joint on the hind leg
  is the HOCK, which is an ankle, not a knee. The true knee (stifle) is high up and tucked
  against the body. On the foreleg, the "knee" is a wrist.
- **The two legs are not the same shape.** A foreleg in side view is a near-vertical column
  from the elbow down. A hind leg is a **Z**: femur down-and-forward to the stifle, tibia
  down-and-back to the hock, then vertical cannon to the ground. gen3 drew both as gentle
  diagonals, which is neither one.
- **Most common beginner error, and gen3 made it:** body too short relative to leg length.
