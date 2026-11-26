# Principles

These hold for every series, every style and every step. They came from building a 12-episode season and fixing
what viewers and the owner noticed.

## Story and pacing
- **No fillers.** Every second carries story. No padded holds, no shaky camera standing in for a new shot, no
  repeated lines to fill time. If an episode is short, it is short.
- **A new visual every 3 to 4 seconds**: a real cut to a different angle or subject that shows what the line says.
  Camera drift is not a new visual. `keyframes.py` prints `LONG HOLDS`; the list must be empty before the A/B card.
- **Every frame shows its line.** A centred, unclipped frame of the wrong thing still fails. Check meaning, not layout.
- **A voice from a device shows the device.** A call, a speaker or a message on screen is in frame, readable.
- **Hook first.** Each episode opens on a 3 to 5 s cold-open hook (one spoken line, shots that prove it), then a
  2 s series title card, then the episode. The hook is original; never copy another series' lines.
- **Interactive series:** the wrong answer ends in death or capture, not inconvenience; the right answer puts
  survival first ("you can't save everyone"). Optional per series (`series.json` `interactive`).

## Characters
- **No faces, ever.** Heads are plain circles with an outline, or a helmet with a dark visor, or a featureless mask,
  whichever suits the story. No eyes, mouths or expressions; emotion comes from pose, light, framing and sound.
- **Outfits never change.** One locked look per character in `cast.js`, used in every episode and every way the
  character is drawn (3D, phone avatar, cut-out). One recognition item per character in a colour no one else wears.
- **Build once, reuse.** Characters, props and sets are modules and cached models; the cast sheet is rendered once
  per cast change. Never rebuild a character inside an episode.

## Sound
- **Audio and video in sync.** SFX times come from cut detection on the rendered picture, not from guesses.
  A sound more than ~40 ms off its cut is a bug.
- **Sound on almost every motion**: whooshes on cuts, cloth on body moves, a ping for every message, a buzz for every
  call, a clunk for locks, a hum for screens, sub drops and stingers on reveals, a riser into the choice, a tape
  rewind for rewinds. Ominous beats are low and sparse; the voice always stays clear.
- **One continuous music bed per episode**, never switched or cut, no audible loop seam.
- **Voices are locked per character** for the whole series (`series.json`), with real pauses at punctuation.
- **Heartbeat** under anxious stretches (slow, faint) and chases or countdowns (fast, faint).

## Picture
- **Wide enough to read.** Establish the place; close-ups are for screens and props. Phone text must be legible.
- **Calm camera.** Whip pans become straight cuts; handheld shake stays faint.
- **Captions in the bottom band only** (default top 1480 px of 1920), never over key text or a phone's buttons.

## Working method (token economy)
- **Local, non-agentic tools first**: ffmpeg scene detection, contact sheets, `hyperframes snapshot`, loudness and
  sync checks, renders. A model only judges what a tool cannot (meaning, taste).
- **Review by major frame changes**: read the cut sheet (`out/keys/sheet.jpg`), open single frames only where the
  sheet looks wrong. Never read every frame.
- **On iteration, look only at what changed**: snapshot just the edited times (twice: the first after an edit can be
  stale), and compare the new cut list with the old one.
- **Context lives in one note** (Obsidian or `R/NOTES.md`): commands, locked rules, status per episode. Read it
  instead of re-reading code.
- **Few agents.** Each with a hard time cap, a short brief of paths (not pasted content) and a short return.
  The maker never checks its own work.
- **One sample before the batch.** Prove every rule on one episode, get approval, then roll out.
- **Render serially.** One episode at a time.
- **Ask before downloads and installs**; log credits for every CC0 asset.
- **Never publish** or post anywhere without the owner's explicit go.
