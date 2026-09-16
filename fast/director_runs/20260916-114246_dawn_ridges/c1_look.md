A stranger would see a hazy, layered mountain range at dawn, but the sun's glow is buried behind the peaks and the foreground is so washed out that the ridges lose their sense of depth and the light feels flat rather than dramatic.

To make this read strongly as "sun low *behind* them," we need to:
1.  **Raise the sun:** Move `light.y` up to 0.45 so the glow sits *above* the far ridges, creating a strong backlight silhouette effect where the sky is brightest and the mountains are darkest.
2.  **Deepen the foreground:** The current `fog` layer (amount 0.35) is washing out the near ridges, making them look like they are made of the same hazy material as the far ones. We need to reduce the fog amount to 0.15 and lower its `top` to 0.7 so the near ridges stay dark and solid, establishing the "distance is haze" rule properly.
3.  **Increase ridge contrast:** Bump `haze` down slightly to 0.55 and increase `count` to 9. This gives us more distinct steps of atmospheric perspective, ensuring the transition from the bright sky to the dark foreground is a clear ramp of values, not a muddy middle.

```json
{
 "title": "DAWN RIDGES",
 "seed": 12,
 "horizon": 0.7,
 "time": "dawn",
 "light": {
  "kind": "sun",
  "x": 0.58,
  "y": 0.45,
  "color": [
   255,
   190,
   126
  ],
  "strength": 1.2
 },
 "sky": {
  "top": [
   24,
   38,
   80
  ],
  "horizon": [
   255,
   168,
   104
  ],
  "glow": [
   255,
   218,
   154
  ]
 },
 "fog_color": [
  222,
  204,
  182
 ],
 "layers": [
  {
   "type": "clouds",
   "amount": 0.16,
   "y": 0.24,
   "spread": 0.14,
   "color": [
    255,
    208,
    164
   ]
  },
  {
   "type": "ridges",
   "count": 9,
   "top": 0.44,
   "bottom": 1.0,
   "height": 0.34,
   "haze": 0.55,
   "rock": [
    104,
    120,
    154
   ]
  },
  {
   "type": "fog",
   "amount": 0.15,
   "top": 0.7,
   "bottom": 1.0,
   "color": [
    224,
    204,
    182
   ]
  }
 ]
}
```