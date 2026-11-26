# Scripts

## script.json
```json
{ "episode": 3, "title": "The Third Stair",
  "lines": [
    { "who": "narrator", "text": "Mum lifts the third stair.", "mark": "tin",
      "fx": [{ "at": 0.3, "tag": "move", "what": "board lifts", "sound": "thump", "weight": "hero" }] },
    { "who": "text", "text": "It's Tam. New phone.", "style": "m" }
  ],
  "choice": { "A": { "label": "Hide", "why": "It cannot see in the dark" }, "B": { "label": "...", "why": "..." }, "right": "A" } }
```
- `who`: a key of `series.json` `voices` (`narrator`, `text` for read-out messages, characters; `fake_<who>` for a
  copy of a character). `style`: `""` narration, `"q"` spoken line (quote caption), `"m"` message bubble.
- One caption per line, at most 38 characters. Split long sentences. No em or en dashes.
- `mark` names a moment the camera and sound can find (`m('tin')` in shots.js; the riser ends on `choice`).
- `fx.what` words pick the synced sound: lock/door/bolt, message/text/counter/post (ping), phone/call (buzz),
  tv/screen/speaker (hum).

## Shape of an episode (45 to 75 s)
1. Hook (separate, `hook.json`) and the title card.
2. Interactive only: the wrong answer to last episode's choice, 3 to 4 lines, ending in death or capture, then the
   rewind, then the right answer.
3. The episode: one new fact, at most one new person, a turn, a cliffhanger.
4. Interactive only: the A/B card. Both options sound reasonable; the right one puts survival first.

## Hook lines
- One spoken sentence, 3 to 5 s, first person or a cold statement of the worst fact in the episode.
- Concrete and specific (a number, a time, a name), impossible on its face, true by the end.
- Original. Learn the grammar of good hooks, never their words.
- `hook.json`: `{ "series", "season", "episode", "title", "line", "who", "hit_words": [...],
  "shots": [{ "line": 13, "dt": 0.7 }, { "t": 22.4 }] }`: each shot shows what the line names.
