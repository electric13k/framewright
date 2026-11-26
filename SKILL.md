---
name: framewright
description: Plan, script, build and review an episodic 2.5D/3D short-video series (Reels, Shorts, TikTok) with faceless characters, locked outfits, synced sound and a cold-open hook, in any art style. Use when asked to start a new series, write a series bible or episode scripts, make a sample episode, build or rebuild an episode, add sound effects in sync, make a title card, or review an episode cheaply by its cuts.
---

# framewright

A pipeline for faceless episodic shorts rendered from code (three.js scenes rendered by HyperFrames), voiced locally
(Kokoro), scored and mixed from local CC0 libraries, and reviewed by scene cuts instead of by every frame.

K = the folder holding this file. Toolkit: `K/toolkit`. Docs: `K/references`. Series profiles: `K/series`.
A series lives in its own folder (R): `R/series.json`, `R/bible.md`, `R/cast/`, `R/ep01`, `R/ep02`, ...

Read `K/references/principles.md` once per session before any work. It holds the rules every step below obeys.

## Stages (never skip, never reorder)

1. **Series setup** (`references/workflow.md` part 1). The bible, `series.json` (voices, interactivity, length),
   style choice (`references/styles.md`), and the cast in `cast.js`. Render the cast sheet once
   (`references/characters.md`) and get the owner's OK on it. Characters are built once and reused, never redrawn.
2. **Season plan and scripts** (`references/script.md`). Arc, episode list, then every script as `script.json`.
   Each episode gets its hook line (`hook.json`).
3. **Sample episode.** Build ONE episode end to end with every rule in force. Review it by its cuts
   (`references/review.md`) and send it. **Do not build the rest until the owner approves the sample.**
4. **Roll out.** One episode at a time, in order. Render serially, never several at once.
5. **Review and fix.** Only re-check what changed: the cuts you touched, the cues you added.

## Build one episode

```
<kokoro_python> K/toolkit/voice_kokoro.py R/epNN            # voice, locked per character, pauses at punctuation
python K/toolkit/build.py R/epNN --from gen                  # gen check stills render score cues mix mux qa hook phone
python K/toolkit/keyframes.py R/epNN/out/body.mp4            # cut sheet + LONG HOLDS list
```
`--until stills` for a fast look before rendering; `--from score` to redo sound only; `--only hook`.
Machine paths: `K/toolkit/kit.config.json` (copy the example). Series settings: `R/series.json`.
Tools and the other skills this one leans on: `references/tools.md`. Sound: `references/sound.md`.

## Who does what (token economy)

| Job | Who |
| --- | --- |
| Bible, arc, scripts, hook lines, shot choices that need taste | the main model, or one strong agent |
| Code edits with a clear spec (a camera key, a colour) | the main model inline |
| Frame sheets, cut detection, renders, voicing, mixing, loudness | local CLI tools (ffmpeg, HyperFrames, Kokoro), no model |
| One full review of the sample episode | one fresh reviewer that did not make it |

Use as few agents as possible. Never have an agent watch a render. Never read every frame.
