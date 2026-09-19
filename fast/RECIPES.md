# Scene recipes — how the art director talks to the scene engine

A recipe is a short JSON object. The engine (`scene_engine.py`) owns every drawing technique that
gens 1-5 learned; the recipe only says what to paint, where, and under what light. Nothing is
traced from an image.

All positions and sizes are **fractions of the canvas**: x 0 = left edge, 1 = right edge;
y 0 = top, 1 = bottom. Colours are `[r, g, b]` 0-255 or `"#rrggbb"` (shorter, preferred) and are HUES — the engine sets the value
(brightness) from the light, so a colour says "what kind of warm", not "how bright".

```json
{
  "title": "DAWN RIDGES",
  "seed": 7,
  "horizon": 0.70,
  "time": "dawn",
  "light": {"kind": "sun", "x": 0.62, "y": 0.36, "color": [255, 196, 132], "strength": 1.0},
  "sky": {"top": [26, 42, 88], "horizon": [255, 178, 108], "glow": [255, 218, 156]},
  "fog_color": [214, 214, 198],
  "layers": [ {"type": "ridges", "count": 5}, ... ]
}
```

## Top level
- **horizon** — where the sky meets the land (0.5-0.9).
- **time** — `dawn`, `day`, `dusk` or `night`. Night darkens everything.
- **light.kind** — `sun`, `moon`, or `none` (no source in frame: aurora, overcast).
  **light.x** — across the frame. **light.y** — 0 = top of the sky, 1 = on the horizon.
  A light low and behind the land (y 0.3-0.9) BACKLIGHTS it: near masses go dark, edges glow.
  **light.strength** 0.3-1.5.
- **sky.top / sky.horizon / sky.glow** — hue at the zenith, at the horizon, and around the light.
- **seed** — change it to get a different arrangement of the same idea.

## Layers — painted in the order listed, FAR TO NEAR
Every layer is `{"type": ..., <params>}`. Leave a param out to use its default.

| type | what it paints | params (default) |
|---|---|---|
| `stars` | pinpoint stars (night) | count (1600) |
| `aurora` | aurora curtains in the sky; list it anywhere | strength (1.0), colors (3 hues) |
| `clouds` | soft lit clouds | amount 0-1 (0.4), y (0.25), spread (0.18), color |
| `ridges` | layered mountain ranges receding into haze, faceted by drainage | count 1-7 (5), top (0.45) = far crest, bottom (1.0) = near crest, height (0.30), haze 0-1 (0.7), rock hue, seed |
| `hills` | one low dark far shoreline or hill line | y (0.62), height (0.10), color, seed |
| `water` | still water that MIRRORS everything painted above it — list it after the sky/land it reflects | top (0.60) = waterline, stillness 0-1 (0.85), tint |
| `meadow` | open grass ground to the bottom edge, grass detail growing toward you | top (0.72), lit hue, dark hue |
| `canyon` | two rock walls with light falling down a slot | opening x (0.5), width (0.16), rock, glow |
| `forest` | tree trunks from far (fog-coloured) to near (lit cylinders) standing on a floor | kind `redwood`/`pine` (redwood), count (26), ground (0.86), near (1.0), far (0.0), bark, bark_lit |
| `pines` | conifer silhouettes with drooping branch tiers | count (14), ground (0.80), height (0.30), color |
| `oak` | one big spreading tree: separate lit leaf lobes, limbs, ground shadow | x (0.46), ground (0.78), height (0.30), width (0.30), acorns (true), leaf, leaf_dark |
| `rocks` | foreground boulders with contact shadows | count (7), top (0.84), size (0.08), color |
| `fog` | a veil of fog or haze over what is already painted | amount 0-1 (0.5), top (0.2), bottom (1.0), color |
| `shafts` | sunbeams through fog, falling away from the light, with dust motes | count 1-8 (6), strength (0.8), spread (0.30), color |

## Directing well (the gen 1-5 doctrine, in recipe terms)
- **The subject first, then the light.** Everything the prompt names must be in the picture,
  visible and recognisable. Then decide where the light is and what it reaches.
- **Far to near.** Sky, then distant land, then water (it reflects what is above it), then near
  ground, then objects, then fog and shafts over the top.
- **Distance is haze.** Far layers lift toward the sky colour; use `haze` and `fog` rather than
  darker far things.
- **Backlight hides detail and that is correct.** A dark mass with a bright edge reads as real.
- **Warm light, cool shadow.** Pick a warm `light.color` at dawn/dusk and a cool `sky.top`.
- **Change a few things per round,** and say why. A recipe is small; keep it that way.
