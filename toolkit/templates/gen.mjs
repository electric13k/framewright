// Builds the episode from ../script.json: index.html (captions and the choice card as timed clips),
// captions.json, events.json, episode.json, and assets/js/episode.js (DUR and the named marks the camera uses).
// Timing comes from the lines, never from typed seconds. If ../voice/timing.json exists, each caption lasts
// exactly as long as its recorded take, so picture, sound cues and score all follow the voice.
// Run from hf/: node gen.mjs
import { readFileSync, writeFileSync, existsSync } from 'node:fs';

const S = JSON.parse(readFileSync('../script.json', 'utf8'));
const die = (msg) => { console.error(`gen.mjs: ${msg}`); process.exit(1); };
if (!Array.isArray(S.lines) || !S.lines.length) die('script.json has no lines');

let VOICE = null;
if (existsSync('../voice/timing.json')) {
  VOICE = JSON.parse(readFileSync('../voice/timing.json', 'utf8'));
  if (VOICE.lines.length !== S.lines.length) die(`voice/timing.json has ${VOICE.lines.length} takes but script.json has ${S.lines.length} lines. Run voice.py again.`);
}
const GAP = VOICE?.gap ?? 0.08;

// Caption length without voice: a brisk read, 0.26 s a word for narration, 0.3 for spoken or texted lines.
const readTime = (l) => Math.max(0.55, 0.1 + l.text.trim().split(/\s+/).length * (l.style ? 0.3 : 0.26));

let clock = S.start ?? 0.15;
const MARK = {}, CAPS = [], EV = [];
S.lines.forEach((l, i) => {
  if (!l.text) die(`line ${i} has no text`);
  const d = VOICE ? VOICE.lines[i].dur + GAP : readTime(l);
  const t0 = +clock.toFixed(2), t1 = +(clock + d).toFixed(2);
  if (l.mark) { if (l.mark in MARK) die(`mark "${l.mark}" is used twice`); MARK[l.mark] = t0; }
  CAPS.push({ t0, t1, text: l.text, style: l.style || '', who: l.who || 'narrator' });
  for (const f of l.fx || []) {
    if (!['move', 'land', 'appear', 'cut'].includes(f.tag)) die(`line ${i}: fx tag must be move, land, appear or cut, got "${f.tag}"`);
    EV.push({ ...f, t: +(t0 + (f.at ?? 0)).toFixed(2), line: i });
  }
  clock = t1 + Math.min(1.0, l.hold || 0); // hold: only for a visual beat that needs the time, never more than 1 s
});
const DUR = +(clock + (S.tail ?? 0.25)).toFixed(2);
MARK.end = DUR;
EV.sort((a, b) => a.t - b.t);

const C = S.choice || null; // no choice = a non-interactive series: no A/B card
if (C && (!C.A || !C.B)) die('script.json choice needs choice.A and choice.B (label and why)');
if (C) for (const k of ['optA', 'optB']) if (!(k in MARK)) die(`mark "${k}" missing: put it on the line that reads option ${k.slice(-1)} aloud`);
const T = !C ? { card: DUR } : { card: +(MARK.optA - 0.25).toFixed(2), aIn: +(MARK.optA - 0.17).toFixed(2), aHi: +(MARK.optA + 0.3).toFixed(2), aOff: +(MARK.optB - 0.2).toFixed(2),
  bIn: +(MARK.optB - 0.15).toFixed(2), bHi: +(MARK.optB + 0.15).toFixed(2), bOff: +(DUR - 1.4).toFixed(2) };
if (C) MARK.choice = T.card;

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const caps = CAPS.map((c, i) =>
  `      <div id="cap${i}" class="clip cap${c.style === 'q' ? ' quote' : ''}${c.style === 'm' ? ' msg' : ''}" data-start="${c.t0}" data-duration="${(c.t1 - c.t0).toFixed(2)}" data-track-index="2"><span>${esc(c.text)}</span></div>`).join('\n');
const title = `EPISODE ${S.episode} · ${String(S.title).toUpperCase()}`;

const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      :root { --ink: #0b0f14; --bone: #f1eee9; --ember: #fd8358; --red: #e5484d; --dim: #8b939c; }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: var(--ink); }
      #root { position: relative; width: 100%; height: 100%; font-family: Inter, sans-serif; }
      #street { position: absolute; inset: 0; width: 1080px; height: 1920px; }
      /* captions at the foot of the Reels safe band (168..1330 px) */
      .cap { position: absolute; left: 0; right: 0; top: 1480px; text-align: center; z-index: 5; }
      .cap span { display: inline-block; max-width: 1000px; white-space: nowrap; padding: 12px 26px; font: 800 50px/1.15 Inter, sans-serif; color: var(--bone);
        background: rgba(11,15,20,0.8); border-radius: 14px; letter-spacing: -0.01em; }
      .cap.quote span { font: italic 500 56px/1.15 'EB Garamond', serif; color: var(--ember); background: rgba(11,15,20,0.85); }
      #choice { position: absolute; left: 54px; right: 54px; top: 484px; padding: 36px; border-radius: 34px; background: rgba(11,15,20,0.9); box-shadow: 0 0 0 3000px rgba(11,15,20,0.72); z-index: 6; }
      .opt { display: flex; align-items: center; gap: 28px; margin-bottom: 26px; padding: 26px 36px; border-radius: 26px; background: rgb(11,15,20);
        border: 3px solid rgba(241,238,233,0.25); color: var(--bone); }
      .opt b { flex: none; display: grid; place-items: center; width: 96px; height: 96px; border-radius: 50%; background: var(--ember); color: var(--ink); font: 900 58px/1 Inter, sans-serif; }
      .opt .lab { display: block; font: 800 60px/1 Inter, sans-serif; }
      .opt .why { display: block; margin-top: 10px; font: 600 30px/1.2 Inter, sans-serif; color: var(--dim); }
      #ask { color: var(--bone); font: 900 74px/1.05 Inter, sans-serif; margin-bottom: 36px; text-shadow: 0 4px 30px #000; }
      #timer { height: 14px; border-radius: 7px; background: var(--red); transform-origin: left center; }
      #cta { margin-top: 22px; text-align: center; color: var(--bone); font: 800 34px Inter, sans-serif; letter-spacing: 0.18em; }
      #epText { display: none; }
      #ep { position: absolute; top: 210px; left: 0; right: 0; text-align: center; z-index: 6; color: var(--bone); font: 800 30px Inter, sans-serif; letter-spacing: 0.3em; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="${DUR}" data-width="1080" data-height="1920">
      <canvas id="street" data-layout-allow-overflow width="1080" height="1920"></canvas>
      <div id="ep" class="clip" data-start="0" data-duration="2.2" data-track-index="3"><span id="epText">${esc(title)}</span></div>
${caps}
${C ? `      <div id="choice" class="clip" data-start="${T.card}" data-duration="${(DUR - T.card).toFixed(2)}" data-track-index="4">
        <div id="ask">${esc(C.ask || 'What should they do?')}</div>
        <div id="optA" class="opt"><b>A</b><span><span class="lab">${esc(C.A.label)}</span><span class="why">${esc(C.A.why)}</span></span></div>
        <div id="optB" class="opt"><b>B</b><span><span class="lab">${esc(C.B.label)}</span><span class="why">${esc(C.B.why)}</span></span></div>
        <div id="timer"></div>
        <div id="cta">COMMENT A OR B</div>
      </div>` : ''}
    </div>
    <script type="module" src="assets/js/main.js"></script>
    <script>
      const tl = gsap.timeline({ paused: true });
      tl.fromTo('#epText', { opacity: 0, scale: 1.25 }, { opacity: 1, scale: 1, duration: 0.5, ease: 'expo.out' }, 0.05);
      tl.to('#epText', { opacity: 0, duration: 0.3 }, 1.8);
      document.querySelectorAll('.cap').forEach((c) => {
        tl.fromTo(c.firstElementChild, { y: 26, opacity: 0, scale: 0.94 }, { y: 0, opacity: 1, scale: 1, duration: 0.18, ease: 'back.out(2)' }, +c.dataset.start);
      });
      if (document.getElementById('ask')) {
      tl.fromTo('#ask', { y: -60, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, ease: 'expo.out' }, ${T.card});
      tl.fromTo('#optA', { x: -1100 }, { x: 0, duration: 0.35, ease: 'expo.out' }, ${T.aIn});
      tl.fromTo('#optB', { x: 1100 }, { x: 0, duration: 0.35, ease: 'expo.out' }, ${T.bIn});
      tl.to('#optA', { borderColor: '#fd8358', scale: 1.05, duration: 0.15 }, ${T.aHi}).to('#optA', { borderColor: 'rgba(241,238,233,0.25)', scale: 1, duration: 0.2 }, ${T.aOff});
      tl.to('#optB', { borderColor: '#fd8358', scale: 1.05, duration: 0.15 }, ${T.bHi}).to('#optB', { borderColor: 'rgba(241,238,233,0.25)', scale: 1, duration: 0.2 }, ${T.bOff});
      tl.fromTo('#timer', { scaleX: 1 }, { scaleX: 0, duration: ${(DUR - 0.1 - T.card).toFixed(2)}, ease: 'none' }, ${T.card});
      tl.fromTo('#cta', { opacity: 0 }, { opacity: 1, duration: 0.25 }, ${T.bIn});
      }
      window.__timelines = window.__timelines || {};
      window.__timelines['main'] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
`;
writeFileSync('index.html', html);
writeFileSync('captions.json', JSON.stringify(CAPS, null, 1));
writeFileSync('events.json', JSON.stringify(EV, null, 1));
writeFileSync('episode.json', JSON.stringify({ episode: S.episode, title: S.title, dur: DUR, marks: MARK, choice: T, lines: CAPS }, null, 1));
writeFileSync('assets/js/episode.js', `// Written by gen.mjs from script.json. Do not edit: change script.json and run node gen.mjs.\nexport const DUR = ${DUR};\nexport const MARK = ${JSON.stringify(MARK)};\nexport const LINES = ${JSON.stringify(CAPS.map((c) => [c.t0, c.t1, c.who]))};\n`);
console.log(`gen.mjs: ${CAPS.length} captions, ${EV.length} events, ${Object.keys(MARK).length} marks, ${DUR} s${VOICE ? ' (timed to the voice)' : ' (read-time estimate, no voice yet)'}`);
if (DUR < 40 || DUR > 62) console.warn(`gen.mjs: warning: ${DUR} s is outside 40..62 s. Add or cut events, never pad.`);
