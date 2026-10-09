# Eye template

Files:
- `eye-template-guides.png`: guide layer (240x144, transparent). Put it *under* your drawing layer, then hide it or delete it before exporting.
- `eye-template-starter.png`: a plain eye that's already centred correctly. Duplicate it and reshape it.
- `eye-template-reference.png`: the same guides at 4x with a legend.

## Rules
- **Canvas:** 240x144, transparent background. Draw both eyes: the right eye is the mirror of the left across x=120.
- **Centre:** keep each eye's white centred on **(61,84)** for the left eye and **(178,84)** for the right. All irises, pupils and shines are drawn around those points and get cropped to your white.
- **Colours:** paint the white of the eye pure **white** (Eye Color tints it) and outlines/lids pure **black**. Anything transparent shows the face.
- **Size the white to fit the irises:** it should cover at least the small iris box (orange). Bigger irises are fine to crop.
- **Blink:** the eye squashes toward y~95 (magenta line), so a lower lid near that line looks natural.
- **Avian/goose:** their eye planes only show the green box (x 6-125 and its mirror, y 4-143). Keep avian eyes inside it. The harpy shows the whole canvas.
- **Vanilla look:** build the eye from a few straight-edged shapes (rectangles, angled bars), like cubes in VSMC. Avoid lines thinner than ~4px, because they blur at a distance. The faint 7px grid is one vanilla "pixel".

## Adding it to the game
1. Save as `textures/face/eyes/eye-back-block-<N>.png` (harpy) or `eye-back-avian-block-<N>.png` (avian/goose), using the next free number.
2. Add `{ "code": "block-<N>" }` to the `eyes-overlay` variants in that model's `config/customplayermodels/*-player.json`.
3. Add `"game:skinpart-eyes-overlay-block-<N>": "Geometric <N>",` to `lang/en.json`. It's only needed once per number; harpy and avian share the key.
4. Never rename or remove an existing code later: saved characters that use it would lose their eyes.
