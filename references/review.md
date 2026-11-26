# Review (cheap and by meaning)

## Tools, cheapest first
1. **Cut sheet**: `python toolkit/keyframes.py R/epNN/out/body.mp4` writes `out/keys/sheet.jpg` (one settled frame
   per real cut, flashes skipped), `keys.json` (cut times) and prints `LONG HOLDS`. Read the sheet, one image.
   Dark scenes can hide real cuts from the detector: before fixing a `LONG HOLD`, check it with a 1 fps strip
   (`ffmpeg -ss <t> -t <hold> -i body.mp4 -vf "fps=1,scale=150:-1,tile=9x1" -frames:v 1 hold.jpg`).
2. **Snapshot only what you changed**: in `R/epNN/hf`,
   `npx hyperframes snapshot . --at 12.4,18.0 --no-end -o ../snap` (run twice; the first run after an edit can be
   stale). Shrink with ffmpeg (`-vf scale=360:-1`) before reading.
3. **Hook strip**: `ffmpeg -t 5 -i epNN.mp4 -vf "fps=2,scale=200:-1,tile=10x1" -frames:v 1 hook.jpg`.
4. **Audio facts**: loudness from `qa.py`; cue times vs cut times from `audio/cues.json` and `audio/sync.json`.
5. **Video perception plugin** (claude-video-vision) for a whole-video pass with a local Whisper backend, when the
   frames come back as images. Prefer `frame_mode: descriptions` with a small describer model to save tokens.

## What to check, per frame
- Does the picture show what the caption says at that moment? (Meaning, not layout.)
- Readable: not near-black, not one colour, nothing cut by the edge, caption not over key text.
- Characters match the cast sheet: outfit, recognition item, no face.
- A new visual every 3 to 4 s; the death beat reads (if interactive); the rewind shows earlier shots backwards.

## Reviewer brief (one fresh agent, sample episode only)
Hard time cap. Read-only. Inputs: the video path, the cut sheet, `episode.json` captions, `hook.json`, the cast
sheet. Return: first line PASS or FAIL, then at most 10 lines `where | time s | problem`.
