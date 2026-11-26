# framewright

**A toolkit and agent skill for making episodic 2.5D/3D short-video series (Reels, Shorts, TikTok) from code,
with faceless characters, locked outfits, synced sound and cold-open hooks, in any art style.**

Scenes are three.js, rendered frame by frame by [HyperFrames](https://github.com/heygen-com/hyperframes). Voices are
local [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) TTS. Music and effects come from CC0 libraries and are
placed on the picture's real cuts. Review runs on scene-cut contact sheets instead of watching every frame, so an
AI agent can build and check a whole season cheaply.

It was built while producing a 12-episode interactive horror season, and every rule in it fixes something that
went wrong there.

## What you get

- **`SKILL.md`**: an agent skill (Claude Code and compatible agents) that runs the whole process: series bible,
  season plan, scripts, one approved sample episode, then a serial roll-out.
- **`references/`**: the principles, workflow, characters, scripts and hooks, sound, review, tools and a catalogue
  of art styles.
- **`toolkit/`**: the scripts.

| Script | Does |
| --- | --- |
| `build.py` | builds one episode in stages: lint, gen, check, stills, render, score, cues, mix, mux, qa, hook, phone |
| `voice_kokoro.py` | voices an episode with one locked voice per character and real pauses at punctuation |
| `keyframes.py` | detects cuts with ffmpeg, writes one contact sheet, flags shots held too long |
| `hook.py` + `title_card.py` | cold-open hook (voice, shots, kinetic words, SFX), then the series title card |
| `sfx_trim.py` | cuts downloaded CC0 effects to their loudest window and normalises them |
| `new_episode.py` | makes the next episode folder from the previous one |
| `templates/` | three.js engine starter, the cached faceless `figure.js` + `cast.js`, the cast sheet, the score builder |

- **`series/`**: a blank series template, plus a curated profile (OVERWRITTEN) as a worked example.

## Rules it enforces

- No faces: blank heads, helmets with visors, or featureless masks.
- One locked outfit and one recognition item per character. Characters are built once and reused.
- A new visual every 3 to 4 seconds and no filler. Each frame must show what its line says.
- Sound effects are placed on the cuts detected in the rendered picture, and the music is one continuous track.
- Captions sit in the bottom band only. The camera stays calm and the framing stays wide enough to read.
- Local tools come first: ffmpeg, HyperFrames, Kokoro. The agent looks only at major frame changes, and on each
  iteration only at what changed.
- One sample episode gets approved before the rest are made, and renders run one at a time.

## Requirements

- Node 18+ (for `npx hyperframes`), Python 3.11+, ffmpeg and ffprobe
- Kokoro (kokoro-onnx) with its model files, in a virtual env
- [opus-sound-layer](references/tools.md) for SFX browsing, mixing and loudness QA (run with `uv`)
- Pillow in the system Python (for the title card)
- Optional: the [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) style library, and the
  [claude-video-vision](https://github.com/jordanrendric/claude-video-vision) plugin with a local Whisper backend

## Quick start

```bash
git clone https://github.com/electric13k/framewright
cp framewright/toolkit/kit.config.example.json framewright/toolkit/kit.config.json   # set your tool paths

# as a Claude Code skill
cp -r framewright ~/.claude/skills/framewright

# a new series
mkdir -p ~/series/myshow && cp framewright/series/_template/* ~/series/myshow/
# edit bible.md, series.json; fill cast.js; render the cast sheet (references/characters.md)
```

Building one episode:

```bash
<kokoro_python> framewright/toolkit/voice_kokoro.py ~/series/myshow/ep01
python framewright/toolkit/build.py ~/series/myshow/ep01 --from gen
python framewright/toolkit/keyframes.py ~/series/myshow/ep01/out/body.mp4
```

## Sound credits

The toolkit ships no audio. `references/sound.md` explains how to fetch CC0 sounds and log their credits.

## License

MIT. Art styles referenced from Lemo-Opuscar are © LemoLab under MIT; read each style's own note on learning the
grammar without copying the source.
