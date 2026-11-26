# Tools and companion skills

| Need | Tool | Notes |
| --- | --- | --- |
| Render HTML/three.js to video, frame-exact | [HyperFrames](https://github.com/heygen-com/hyperframes) CLI (`npx hyperframes`) and its skill | `render`, `snapshot`, `check`; pin the version in `kit.config.json` |
| 3D scenes | three.js (vendored `three.module.js`) | deterministic: every value is a function of timeline time |
| Voice | [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) (kokoro-onnx) in its own venv | free, offline; voices locked in `series.json` |
| Cut detection, sheets, mux, phone copy | ffmpeg / ffprobe | local, no model needed |
| SFX browse, mix, loudness QA | opus-sound-layer (`sfx.py`, `mix.py`, `qa.py`) | run with `uv run` |
| Title card frames | Pillow (system Python) | `title_card.py` |
| Art styles | [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) style library (MIT) | style grammar and demos; see `styles.md` |
| Whole-video perception | [claude-video-vision](https://github.com/jordanrendric/claude-video-vision) plugin | pick the local Whisper backend so audio stays on the machine |
| Instagram reference reels | a local reel watcher that writes a digest and contact sheet | study grammar only, never copy |
| Project memory | Obsidian (or `R/NOTES.md`) | one note per series: rules, commands, status |

## Machine config
Copy `toolkit/kit.config.example.json` to `toolkit/kit.config.json` and set: `ffmpeg`, `ffprobe` (or leave empty
for PATH), `kokoro_dir`, `kokoro_python`, `sound_layer`, `sfx_extra`, `ambience_dir`, `system_python`.
