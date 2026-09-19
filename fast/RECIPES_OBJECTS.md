## Objects and free shapes — paint what the prompt NAMES (added 2026-09-18)

**Read this before the painting rules below.** Those rules ("light, not object", "backlight hides
detail") are about HOW to paint a thing — never a reason to leave it out or leave it a black shape
against a sunset. A dark silhouette in front of a sunset is a FAILURE unless the prompt asks for
one. The things the prompt names must be lit, coloured and recognisable, and they should fill the
picture: big, near, overlapping, not a thin strip along the horizon. Top-level `"vivid": 1.4`
(up to 1.6) makes every landscape colour more saturated — use it for neon, black light, cartoon.

The layers above are backgrounds. When a prompt names THINGS (a town, a castle, ghosts, spiders,
goblins, a person, a street), paint those things with the objects below. **Never use trees, rocks
or ridges to stand in for buildings, creatures or people** — that is why every picture used to
come back as a forest. First list every thing the prompt names, give each one an object (or build
it from shapes), then set the light.

Sizes are fractions of the canvas HEIGHT; x/y are fractions of the canvas as above. Any colour
called `glow` EMITS light — use it for lit windows, lanterns, jack-o'-lantern faces, glowing eyes
and black-light / neon paint.

| type | what it paints | params (default) |
|---|---|---|
| `ground` | plain ground to the bottom edge, so buildings never float over sky | top (0.8), color, texture (0.15) |
| `path` | a street or path running back to a vanishing point, wet and shining | x (0.5), top (0.62), width (0.5), color, shine, wet (true) |
| `town` | a row of houses with roofs, chimneys and lit windows | count (9), ground (0.8), height (0.22), x0 (0), x1 (1), color, window, lit 0-1 (0.6), roofs `gable`/`spire`/`flat`/`mixed` |
| `house` | one house front, near and big | x, ground (0.82), width (0.18), height (0.22), color, window, roof, porch (true) |
| `castle` | towers with spires and lit windows, optionally on a hill | x (0.55), ground (0.52), size (0.22), color, window, hill (true), hill_color |
| `bare_tree` | a leafless branching tree silhouette | x, ground (0.85), height (0.45), color, lean, seed |
| `ghost` | a translucent glowing sheet ghost | x, y (0.4), size (0.12), color, glow, alpha (0.75) |
| `figure` | a standing figure; kind `goblin`/`witch`/`skeleton`/`zombie`/`person` | kind, x, ground (0.9), height (0.25), color (skin), clothes, eyes (glowing), facing 1 or -1 |
| `pumpkin` | a jack-o'-lantern, face glowing | x, y (0.9), size (0.08), color, glow, face (true) |
| `web` | a spider web, in a corner or free | corner `top-left`/`top-right`/`bottom-left`/`bottom-right`/`none`, x, y, size (0.35), color, rings, spokes |
| `spider` | a hanging spider with glowing eyes | x, y, size (0.06), color, eyes, thread (true) |
| `bats` | a flock of bats | count (8), x0, x1, y0, y1 (the area), size (0.03), color |
| `lamp` | a street lamp or lantern post, glowing | x, ground (0.85), height (0.3), color, glow |
| `moon` | a moon disc with a halo | x, y, size (0.08), color, glow |

**`svg` — paint ANYTHING.** For any subject the list does not have (a car, a specific animal, a
person, a city skyline, a product, a whole scene), draw it as an SVG and place it in a box. The
engine paints your drawing with brush dabs and crisp edges. Draw it well: real proportions, the
parts that make the subject recognisable, a light side and a shadow side, a few layers of detail.
Use single quotes inside the SVG so the JSON stays valid.
```json
{"type": "svg", "x": 0.1, "y": 0.55, "w": 0.45, "h": 0.3,
 "svg": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 90'><path d='M10 60 L25 38 Q60 20 95 22 L140 24 Q165 28 180 45 L192 50 Q196 60 190 66 L12 66 Z' fill='#c8102e'/><circle cx='50' cy='68' r='15' fill='#111'/><circle cx='155' cy='68' r='15' fill='#111'/></svg>"}
```
x, y = the box's top-left corner; w = fraction of the canvas width, h = of the height. The drawing
keeps its own proportions inside the box. Several `svg` layers can share one picture; a full-canvas
one (x 0, y 0, w 1, h 1) can be a whole scene.

**`shapes`** — quick primitives without writing SVG:
```json
{"type": "shapes", "items": [
  {"shape": "polygon", "points": [[0.4, 0.8], [0.5, 0.5], [0.6, 0.8]], "color": "#2a1250"},
  {"shape": "circle", "x": 0.5, "y": 0.3, "r": 0.05, "color": "#ffcc00"},
  {"shape": "ellipse", "x": 0.5, "y": 0.6, "rx": 0.1, "ry": 0.04, "color": "#00ffaa"},
  {"shape": "line", "points": [[0.1, 0.9], [0.3, 0.7]], "width": 0.006, "color": "#ff00ff"},
  {"shape": "glow", "x": 0.5, "y": 0.3, "r": 0.1, "color": "#ff8800", "strength": 1},
  {"shape": "text", "text": "BEWARE", "x": 0.8, "y": 0.5, "size": 0.04, "color": "#66ff66"}]}
```
Up to 80 items. Order still matters: far things first, near things last.

**Black light / neon:** a dark violet world (`sky.top` near #1a0640, `ground` and buildings deep
purple) lit by things that glow in saturated neon — green, magenta, cyan, orange. The glow colours
carry the look, not the sky.

**Sky strength:** `sky.brightness` (1.0; 0.4-0.6 for a dark neon or stormy sky) and
`sky.saturation` (0.66; up to 1.0 for vivid colour).

**`finish` — the finishing pass** (after everything is painted; idea credit: Robbie Tilton's
[Compositor](https://robbietilton.com/compositor)). Every `glow` ADDS light (Screen blending) instead
of covering what is under it; then:
```json
"finish": {"bloom": 0.45, "grade": 0.3, "shadows": "#14043a", "highlights": "#ffb050",
           "contrast": 0.45, "grain": 0.025}
```
- **bloom** 0-1 (0.35): the brightest parts, blurred, added back — light spills around every glow.
- **grade** 0-1 (off): pulls the whole picture toward one look — shadows to `shadows`, lights to
  `highlights` — without changing brightness. Deep violet shadows + hot orange lights = black light.
- **contrast** 0-1 (0.3): deeper darks, hotter lights. **grain** (0.02): fine film noise.
