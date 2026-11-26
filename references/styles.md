# Art and graphic styles

Pick one style per season. The engine is three.js rendered by HyperFrames, so any style is a set of choices about
**geometry, materials, light, camera, post-processing and type**. Faceless figures (`figure.js`) work in all of them;
change the materials and the head finish, not the rules.

## Built-in looks (tested with this toolkit)

| Style | Geometry and material | Light and post | Camera | Good for |
| --- | --- | --- | --- | --- |
| **Faceless noir** | flat-shaded boxes, bone heads, one warm item per hero | dark night palette, rim light, grain, cyan for the uncanny | wide establishing, slow push, phone inserts | thriller, horror, tech dread |
| **Toy diorama** | rounded low-poly, saturated plastics | soft key + bounce, tilt-shift blur band, bloom | high three-quarter, slow orbit | comedy, kids, explainers |
| **Paper cut-out (2.5D)** | layered planes with paper textures, sprites rendered once from the cast sheet | hard shadows between layers, warm lamp | lateral parallax tracks | fables, history, folk horror |
| **Low-poly world** | faceted terrain and props, flat colour per face | sun + sky gradient, fog | drone-like moves, big wides | adventure, survival |
| **Neon city** | dark geometry, emissive signs and screens | bloom, wet reflections, chromatic edge | low angles, glides | cyberpunk, crime |
| **Clay / soft toon** | rounded shapes, matte pastel materials, slight squash | soft shadows, AO, light grain | close and warm | slice of life, comedy |
| **Silhouette** | black figures and props against lit backdrops | one strong backlight colour per scene | static compositions, slow cuts | tragedy, myth, war stories |
| **Blueprint / white model** | untextured white or line geometry | flat light, line overlays, labels | orthographic, isometric | mysteries told as investigations, explainers |

## From the Lemo-Opuscar library (MIT)

[Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) ships 68 styles, each with a `STYLE.md` (grammar, palette,
type, motion) and a demo. Read the style's `STYLE.md` before using it and follow its "learn the grammar, never copy
the source" note. Styles that suit 2.5D/3D faceless series:

- **Diorama and miniature:** `hd-2d` (pixel sprites in a lit 3D diorama), `tilt-shift`, `isometric-picture-book`,
  `iso-infographic`, `lowpoly-island`, `brick-toy`, `memphis-diorama`, `white-model`.
- **Paper and cut-out:** `paper-popup`, `papercut-red`, `shadow-puppet`, `paper-lantern`, `crayon-book`.
- **Toon and anime:** `scifi-toon`, `midcentury-toon`, `rubber-hose`, `cel-anime-80s`.
- **Painterly:** `impasto`, `watercolor`, `ink-wash`, `ukiyoe`, `stained-glass`, `woodcut`, `engraving`.
- **Print and graphic:** `risograph`, `silkscreen-poster`, `halftone-dossier`, `swiss-motion`, `art-deco`,
  `spy-titles`, `one-line`.
- **Screen and data:** `hologram-hud`, `ascii-crt`, `lidar-survey`, `satellite-briefing`, `desktop-flythrough`,
  `living-screencast`, `visual-investigation`, `transit-map`.
- **Period and found footage:** `silent-film`, `newsreel`, `kino-montage`, `archive-lighttable`, `backrooms`.
- **Pixel and game:** `pixel-rpg`, `microgame`.

## Applying a style
1. Write the style's palette (5 to 7 colours with roles), type pair and grain level into the bible.
2. Put materials and colours in `cast.js` and the set modules; put light, fog and post (grain, vignette, bloom,
   chromatic edge, grade) in `main.js`'s post shader.
3. Re-render the cast sheet in the new style; approve it before any episode.
4. Keep the readability rules whatever the style: wide enough to read, captions in the bottom band, phone text legible.
