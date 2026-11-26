# Workflow

## Part 1: series setup (once)

1. **Bible** (`R/bible.md`, start from `series/_template/bible.md`): premise in two sentences, the world's rules
   (what the threat can and cannot do), the hero's want and fear, the cast (max 6 recurring), the season arc in
   6 to 12 beats, what is never shown, the tone in five words.
2. **Series name**: one word, unique, ownable. It is the title card; check it is not an existing show.
3. **`R/series.json`** (start from `series/_template/series.json`): name, season, interactive (A/B choice at the
   end), length range, voices per character (Kokoro voice id and speed), fake level, pauses, caption band.
4. **Style** (`references/styles.md`): pick one art style and one palette; write them into the bible. One style
   for the whole season.
5. **Cast** (`references/characters.md`): fill `cast.js`; render the cast sheet; get the owner's OK.
6. **Sets**: list the places the season needs (max 5 to 6); build each once as a module (`world.js` switches
   them by `state.place`). New places are rare and reused.
7. **Sound kit** (`references/sound.md`): music bed, ambience, SFX kit with credits.

## Part 2: season plan and scripts

1. Episode list: one line per episode (what happens, the cliffhanger, the choice if interactive).
2. Scripts as `script.json` (`references/script.md`), lint each: `python build.py R/epNN --only lint`.
3. `hook.json` per episode: the hook line, hit words, and 2 to 3 shots that prove it.

## Part 3: the sample episode

Pick the episode that exercises the most rules (a device on screen, a recurring character, a reveal, the choice).
Build it end to end, review it (`references/review.md`), fix, send. Stop until the owner approves.

## Part 4: roll-out

Per episode, in order, one at a time:
```
voice  ->  build --from gen  ->  keyframes  ->  fix LONG HOLDS / weak frames  ->  re-render only if changed  ->  send
```
Pre-voice the next episode while the current one renders (voicing is light). Never run two renders at once.

## Part 5: after the season

Write what was learned into the series note and, if it is general, into these principles.
