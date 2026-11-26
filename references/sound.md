# Sound

## Voice
- Local Kokoro TTS (`voice_kokoro.py`), free and offline. One locked voice and speed per character in
  `series.json`; never override per line. Copies of a character (`fake_<who>`) use the same voice with one fixed
  treatment level.
- Lines are spoken in pieces split at punctuation and joined with silence (`series.json` `pauses`).
- Any text change: re-voice, then `build.py --from gen` (timings move).

## Music
- One continuous bed for the whole episode (`audio/score.json` `music`), at least as long as the episode or
  joined with a 4 s equal-power crossfade at a quiet point. Never switch beds between places.
- A low drone layer follows a level curve by marks; planned silences (`hush`) dip it.
- Heartbeat ranges: `heart: [[from, to, "slow"|"fast", level]]`.

## SFX in sync (build.py `cues` stage)
1. Cut times come from scene detection on the rendered `out/picture.mp4` (threshold 0.06, flashes under 0.15 s
   dropped).
2. Script `fx` snap to the nearest real cut within 0.35 s.
3. Every other cut gets a soft swish or cloth sound, so motion is never silent.
4. Fixed beats from marks: sub drop + stinger on a death hit, tape rewind from the rewind start, a clunk back to
   play, a ping for each read-out message, a riser that ends on the choice card, a scrape under the cliffhanger.
5. `audio/sync.json` keeps the cut list for checking.

## SFX kit
- Base kit: `opus-sound-layer` (`sfx.py browse`, `mix.py`, `qa.py`).
- Extras (`kit.config.json` `sfx_extra`): folders `rewind buzz ping lock tvon subdrop scrape stinger cloth swell`.
  Fetch CC0 sounds (freesound previews, Creative Commons 0 filter, most downloaded first), convert to 48 kHz
  stereo, cut each to its loudest window with `sfx_trim.py`, and log every source in `CREDITS.txt`.
- Ask the owner before downloading anything.

## Mix and loudness
- `mix.py` ducks music under voice (10 dB), aligns each cue's peak to its time, masters to -14 LUFS, -1 dBTP.
- `qa.py` checks offset, loudness, true peak, voice, music and silence; the build stops on a hard fail.
