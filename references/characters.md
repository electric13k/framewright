# Characters

## The rules
- **No faces.** Choose per character: `blank` (bone-white circle, ink outline; the default), `helmet` (shell in
  the outfit colour with a dark visor: riders, soldiers, divers, astronauts), or `mask` (a featureless plate: cults,
  surgeons, masked killers). Never eyes, mouths, brows or expressions. Emotion is pose, light, framing and sound.
- **One locked look.** Every colour and prop lives in `cast.js`. Episodes never restyle a character; only pose and
  light change. If a costume change is a story beat (a uniform), add it as a second cast entry (`hero_uniform`) and
  use it only where the bible says.
- **One recognition item** per character, in a colour nobody else wears (a scarf, a cap, a bag, an apron, a helmet
  colour). Test: in a 1-second dark silhouette, can a viewer name them?
- **Same look in every medium.** The phone avatar, the poster, the cut-out and the 3D figure read from the same
  `cast.js` values.

## Build once, store, reuse
- `toolkit/templates/hf/assets/js/cast.js`: the specs. `figure.js`: builds each figure once, caches it, and returns
  clones (`figure('mother')`), with `pose()` and `walk(t)`. Episodes import these; they never construct bodies.
- The **cast sheet** (`toolkit/templates/castsheet`): every character from four angles in one image.
  ```
  cd toolkit/templates/castsheet   (copy cast.js in first)
  npx hyperframes snapshot . --at 0.5 --no-end -o <R>/cast
  ```
  Keep `R/cast/frame-00-at-0.5s.png` as the reference. Re-render it only when `cast.js` changes. Reviewers compare
  episode frames with it instead of re-describing characters.
- **2D sprites** (styles that need flat cut-outs, e.g. paper or HD-2D): render each figure once to a transparent PNG
  (front, side, back) from the cast sheet page and use the PNGs as sprites; do not redraw them per shot.

## Posing without faces
- Fear: shoulders up, arms in, step back, head down. Resolve: square to camera, still. Grief: head tilted, arms limp.
- Look direction is the body and head turn; light from the screen or lamp on the head sells attention.
