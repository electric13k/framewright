"""Build one episode end to end, stopping at the first failure with a plain message.

Usage:
  python build.py <series>/ep02                  # everything
  python build.py <series>/ep02 --until stills   # lint, gen, check, stills only (fast look)
  python build.py <series>/ep02 --from score     # redo sound after a picture you already rendered
  python build.py <series>/ep02 --only qa

Stages, in order:
  lint    script.json rules (no TODO, caption length, marks, choice reasons, no em dashes)
  gen     node gen.mjs (index.html, captions, events, marks)
  check   npx hyperframes check
  stills  npx hyperframes snapshot at every mark and hero event -> stills/ (+ contact-sheet.jpg)
  render  npx hyperframes render -> out/picture.mp4
  score   python score.py -> audio/score.wav (music bed)
  cues    events.json + voice timing -> audio/cues.json
  mix     opus-sound-layer mix.py -> audio/audio/mix.wav
  mux     ffmpeg: picture + mix -> epNN.mp4 (h264 bt709, aac)
  qa      opus-sound-layer qa.py on epNN.mp4, then the publish gate
  hook    hook.py: cold-open hook + series title card in front (body kept in out/body.mp4)
  phone   epNN-phone.mp4 under the size limit
Writes build-report.json every run, and BUILD-FAILED.md when a stage fails (deleted on a clean run).
Exit code 0 only if every stage that ran passed.
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))
from kitcfg import P, series_cfg  # noqa: E402
STAGES = ['lint', 'gen', 'check', 'stills', 'render', 'score', 'cues', 'mix', 'mux', 'qa', 'hook', 'phone']
HARD_QA = {'offset', 'loudness', 'true peak', 'voice', 'music', 'silence'}  # these must pass before publishing
DEFAULT_SOUND = {'move': 'whoosh', 'land': 'thump', 'appear': 'pop', 'cut': 'hit+boom'}
MAX_CAPTION_CHARS, MAX_LABEL_CHARS, MAX_WHY_CHARS = 38, 14, 32



KIT2 = Path(P['sfx_extra'])  # CC0 extras (credits in KIT2/CREDITS.txt): rewind buzz ping lock tvon subdrop scrape stinger cloth swell


def k2(kind, i=0):
    fs = sorted((KIT2 / kind).glob('*.wav'))
    return fs[i % len(fs)].as_posix() if fs else None


def scene_cuts(video, thr=0.06, flash=0.15):
    """Times where the picture really changes (ffmpeg scene score); flash frames shorter than `flash` dropped."""
    if not Path(video).exists():
        return []
    r = subprocess.run([P['ffmpeg'], '-hide_banner', '-i', str(video), '-vf', f"select='gt(scene,{thr})',showinfo",
                        '-an', '-f', 'null', '-'], capture_output=True, text=True)
    ts = [float(x) for x in re.findall(r'pts_time:([\d.]+)', r.stderr)]
    return [round(t, 3) for i, t in enumerate(ts) if i + 1 >= len(ts) or ts[i + 1] - t >= flash]

class StageError(Exception):
    def __init__(self, msg, hint=''):
        super().__init__(msg); self.hint = hint


def run(cmd, cwd, log, env=None, timeout=3600):
    """Run a command, keep its full output in log, raise StageError with the tail on failure."""
    log.parent.mkdir(parents=True, exist_ok=True)
    e = dict(os.environ, **(env or {}))
    try:
        r = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    except FileNotFoundError:
        raise StageError(f'program not found: {cmd[0]}', 'check toolkit/kit.config.json and that the tool is installed')
    except subprocess.TimeoutExpired:
        raise StageError(f'timed out after {timeout} s: {" ".join(map(str, cmd))}')
    out = (r.stdout or '') + (r.stderr or '')
    log.write_text(out, encoding='utf-8')
    if r.returncode != 0:
        tail = '\n'.join(out.strip().splitlines()[-15:])
        raise StageError(f'exit {r.returncode} from {Path(str(cmd[0])).name}. Last lines:\n{tail}\nFull log: {log}')
    return out


def which(name):
    p = shutil.which(name)
    if not p:
        raise StageError(f'{name} is not on PATH')
    return p


def probe_duration(f):
    r = subprocess.run([P['ffprobe'], '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        raise StageError(f'cannot read the duration of {f}', 'the file is missing or damaged')


class Episode:
    def __init__(self, d):
        self.d = Path(d).resolve()
        self.name = self.d.name
        self.hf, self.audio, self.voice, self.out, self.stills_dir = (self.d / x for x in ('hf', 'audio', 'voice', 'out', 'stills'))
        self.logs = self.out / 'logs'
        self.final = self.d / f'{self.name}.mp4'
        self.phone_file = self.d / f'{self.name}-phone.mp4'
        self.picture = self.out / 'picture.mp4'
        self.mixwav = self.audio / 'audio' / 'mix.wav'

    def ep(self):
        f = self.hf / 'episode.json'
        if not f.exists():
            raise StageError('hf/episode.json missing', 'run the gen stage first')
        return json.loads(f.read_text(encoding='utf-8'))

    # ---------- stages ----------
    def lint(self):
        f = self.d / 'script.json'
        if not f.exists():
            raise StageError('script.json missing', 'run new_episode.py or copy a branch file to script.json')
        raw = f.read_text(encoding='utf-8')
        S = json.loads(raw)
        errs = []
        if 'TODO' in raw:
            errs.append('script.json still contains TODO placeholders')
        if '\u2014' in raw or '\u2013' in raw:
            errs.append('script.json contains an em or en dash; use a comma, colon or full stop')
        marks = [l.get('mark') for l in S.get('lines', []) if l.get('mark')]
        for m in (('optA', 'optB') if series_cfg(self.d)['interactive'] else ()):
            if m not in marks:
                errs.append(f'no line has mark "{m}"')
        for i, l in enumerate(S.get('lines', [])):
            if len(l.get('text', '')) > MAX_CAPTION_CHARS:
                errs.append(f'line {i} is {len(l["text"])} characters (max {MAX_CAPTION_CHARS}): split it: "{l["text"]}"')
            if l.get('style') not in (None, '', 'q', 'm'):
                errs.append(f'line {i}: style must be "", "q" (spoken) or "m" (text message)')
        # Preplanned choices: from episode 2 the film opens on the wrong answer (3 to 4 lines, ends in a rewind),
        # then the right answer. See plotkit/branch-format.md.
        if series_cfg(self.d)['interactive'] and int(S.get('episode') or 0) >= 2:
            idx = {l.get('mark'): i for i, l in enumerate(S.get('lines', [])) if l.get('mark')}
            if idx.get('wrong') != 0:
                errs.append('line 0 must be the wrong turn: "If you chose <wrong label>:" with mark "wrong"')
            if 'wrongEnd' not in idx or 'open' not in idx or not (idx.get('wrong', -1) < idx['wrongEnd'] < idx['open']):
                errs.append('marks must run "wrong", then "wrongEnd" (the rewind), then "open" (the right answer)')
            elif not 3 <= idx['wrongEnd'] - idx.get('wrong', 0) + 1 <= 4:
                errs.append('the wrong turn must be 3 to 4 lines')
            else:
                end_fx = S['lines'][idx['wrongEnd']].get('fx', [])
                if not any('reverse' in str(x.get('sound', '')) and x.get('weight') == 'hero' for x in end_fx):
                    errs.append('the "wrongEnd" line needs a hero fx with a "reverse" sound: the rewind back to the choice')
            P = S.get('previous_choice') or {}
            if P.get('right') not in ('A', 'B') or P.get('wrong') not in ('A', 'B') or P.get('right') == P.get('wrong'):
                errs.append('previous_choice needs "right" and "wrong", one "A" and one "B"')
        C = S.get('choice') or {}
        if series_cfg(self.d)['interactive'] and C.get('right') not in ('A', 'B'):
            errs.append('choice.right must be "A" or "B": the story is preplanned')
        for k in (('A', 'B') if series_cfg(self.d)['interactive'] else ()):
            o = C.get(k) or {}
            if not o.get('label') or len(o['label']) > MAX_LABEL_CHARS:
                errs.append(f'choice.{k}.label must be 1..{MAX_LABEL_CHARS} characters')
            if not o.get('why') or len(o['why']) > MAX_WHY_CHARS:
                errs.append(f'choice.{k}.why must give the reason in 1..{MAX_WHY_CHARS} characters (where he would go and why)')
        heroes = sum(1 for l in S.get('lines', []) for x in l.get('fx', []) if x.get('weight') == 'hero')
        if heroes < 3:
            errs.append(f'only {heroes} hero fx: an episode needs at least 3 major events marked weight "hero"')
        if errs:
            raise StageError('script.json breaks the rules:\n  - ' + '\n  - '.join(errs), 'fix script.json; see references/script.md')
        return f'{len(S["lines"])} lines, {heroes} hero events'

    def gen(self):
        out = run(['node', 'gen.mjs'], self.hf, self.logs / 'gen.log')
        return ' | '.join(l for l in out.strip().splitlines() if l.startswith('gen.mjs'))

    def check(self):
        run([which('npx'), '--yes', P['hyperframes'], 'check'], self.hf, self.logs / 'check.log', timeout=600)
        return 'hyperframes check passed'

    def still_times(self):
        e = self.ep(); dur = e['dur']
        ts = [1.0, dur - 0.6] + ([e['choice']['card'] + 0.8, e['choice']['bHi'] + 0.5] if 'bHi' in e.get('choice', {}) else [])
        ts += [v + 0.4 for k, v in e['marks'].items() if k not in ('end', 'choice')]
        ev = json.loads((self.hf / 'events.json').read_text(encoding='utf-8'))
        ts += [x['t'] + 0.2 for x in ev if x.get('weight') == 'hero']
        keep = []
        for t in sorted(min(max(0.1, t), dur - 0.1) for t in ts):
            if not keep or t - keep[-1] >= 0.6:
                keep.append(round(t, 2))
        return keep[:14]

    def stills(self):
        ts = self.still_times()
        run([which('npx'), '--yes', P['hyperframes'], 'snapshot', '--at', ','.join(map(str, ts)), '--no-end', '--output', str(self.stills_dir)],
            self.hf, self.logs / 'stills.log', timeout=1200)
        pngs = sorted(self.stills_dir.glob('*.png'))
        if len(pngs) < len(ts):
            raise StageError(f'expected {len(ts)} stills, found {len(pngs)} in {self.stills_dir}')
        return f'{len(pngs)} stills in {self.stills_dir} (look at every one before rendering)'

    def render(self):
        e = self.ep()
        self.out.mkdir(exist_ok=True)
        run([which('npx'), '--yes', P['hyperframes'], 'render', '--fps', str(P['fps']), '--workers', str(P['render_workers']), '-o', '../out/picture.mp4'],
            self.hf, self.logs / 'render.log', timeout=5400)
        d = probe_duration(self.picture)
        if abs(d - e['dur']) > 0.15:
            raise StageError(f'picture is {d:.2f} s but the episode is {e["dur"]} s')
        return f'{self.picture} ({d:.2f} s)'

    def score(self):
        out = run([sys.executable, 'score.py'], self.audio, self.logs / 'score.log', env={'SERIALKILN_AMBIENCE': P['ambience_dir']}, timeout=900)
        return out.strip().splitlines()[-1]

    def cues(self):
        """SFX cues in sync with the picture. Cut times come from scene detection on the rendered picture, so a
        sound lands on the frame where the image changes; script events snap to the nearest real cut. Fixed beats
        come from the marks: death hit, tape rewind, clunk back to play, notification pings, the choice riser."""
        e = self.ep()
        ev = json.loads((self.hf / 'events.json').read_text(encoding='utf-8'))
        sil = json.loads((self.audio / 'silence.json').read_text()) if (self.audio / 'silence.json').exists() else []
        M, lines = e.get('marks', {}), e['lines']
        cuts = scene_cuts(self.out / 'picture.mp4')
        end_ok = M.get('choice', e['dur'])
        hit = M['wrongEnd'] + 0.55 if 'wrongEnd' in M else None
        rw0 = M['wrongEnd'] + 1.35 if 'wrongEnd' in M else None
        rw1 = M.get('open')

        def in_rew(t):
            return hit is not None and rw1 is not None and hit - 0.05 <= t <= rw1 + 0.1
        cues, used = [], set()

        def add(t, sound, weight='support', align='peak', pan=0.0, visual='cut', **kw):
            if sound:
                cues.append({'id': '', 't': round(t, 3), 'sound': sound, 'weight': weight, 'align': align,
                             'pan': pan, 'visual': visual, **kw})
        for x in ev:  # meaning-based events from the script, snapped to the real picture change
            t = x['t']
            near = min(cuts, key=lambda c: abs(c - t), default=None)
            if near is not None and abs(near - t) <= 0.35 and x['tag'] in ('cut', 'move', 'land'):
                t = near
                used.add(near)
            if in_rew(t):
                continue
            what = (x.get('what') or '').lower()
            snd = x.get('sound') or DEFAULT_SOUND[x['tag']]
            if any(w in what for w in ('lock', 'door', 'bolt')):
                snd = k2('lock')
            elif any(w in what for w in ('message', 'text', 'notification', 'sms', 'counter', 'share', 'post')):
                snd = k2('ping')
            elif any(w in what for w in ('phone', 'call', 'ring')):
                snd = k2('buzz')
            elif any(w in what for w in ('tv', 'screen', 'speaker')):
                snd = k2('tvon')
            add(t, snd, x.get('weight', 'support'), x.get('align', 'peak'), x.get('pan', 0), x['tag'])
        for i, c in enumerate(cuts):  # every other picture change gets a soft sound, so motion is never silent
            if c in used or c < 0.1 or c >= end_ok or in_rew(c) or any(abs(c - q['t']) < 0.25 for q in cues):
                continue
            add(c, 'swish' if i % 3 else k2('cloth', i), 'support', 'peak', 0.15 * ((-1) ** i))
        for k, l in enumerate(lines):  # read-out texts are messages arriving on a phone
            if l.get('who') == 'text' and not in_rew(l['t0']):
                add(max(0, l['t0'] - 0.12), k2('ping', k), 'support', 'start', visual='appear')
        if hit is not None:  # the wrong turn: sub drop + stinger on the hit, tape rewind, clunk back into play
            add(hit, k2('subdrop'), 'hero', 'start', visual='land')
            add(hit + 0.05, k2('stinger'), 'hero', 'start', visual='land')
            if rw1 and rw1 > rw0:
                add(rw0, k2('rewind'), 'hero', 'start', visual='move')
                add(rw1, 'thump', 'hero', 'peak', visual='cut')
        if 'choice' in M:  # tension riser ending on the choice card, a scrape under the cliffhanger
            add(M['choice'], 'riser', 'hero', 'end', visual='build')
            if 'cliff' in M:
                add(M['cliff'], k2('scrape'), 'support', 'start', visual='appear')
        cues.sort(key=lambda c: c['t'])
        for i, c in enumerate(cues):
            c['id'] = f'c{i}'
        sheet = {'fps': P['fps'], 'duration_s': e['dur'], 'energy': 'punchy', 'kit': f'{P["sound_layer"]}/audio/kit',
                 'room': {'decay_s': 0.9, 'wet_db': -14},
                 'music': {'file': (self.audio / 'score.wav').as_posix(), 'start_s': 0, 'loop': False, 'fade_out_s': 0.3},
                 'silence_ok': sil, 'cues': cues}
        tf = self.voice / 'timing.json'
        if tf.exists():
            vt = json.loads(tf.read_text(encoding='utf-8'))
            voice = []
            for i, (vl, cap) in enumerate(zip(vt['lines'], e['lines'])):
                wav = Path(vl['file']) if Path(vl['file']).is_absolute() else self.voice / vl['file']
                if not wav.exists():
                    raise StageError(f'voice take missing: {wav}', 'run voice.py again')
                voice.append({'file': wav.as_posix(), 'start_s': cap['t0']})
            sheet['voice'] = voice
            sheet['duck_db'] = 10
        if not cues:
            raise StageError('no cues', 'render first (cut detection) or add fx to script.json')
        (self.audio / 'cues.json').write_text(json.dumps(sheet, indent=1), encoding='utf-8')
        (self.audio / 'sync.json').write_text(json.dumps({'cuts': cuts}, indent=1), encoding='utf-8')
        return f'{len(cues)} cues on {len(cuts)} picture cuts' + (f', voice {len(sheet["voice"])} takes' if 'voice' in sheet else '')

    def mix(self):
        if not (self.audio / 'score.wav').exists():
            raise StageError('audio/score.wav missing', 'run the score stage')
        out = run([which('uv'), 'run', f'{P["sound_layer"]}/scripts/mix.py', 'cues.json'], self.audio, self.logs / 'mix.log',
                  env={'UV_NATIVE_TLS': '1'}, timeout=1800)
        if not self.mixwav.exists():
            raise StageError(f'{self.mixwav} was not written')
        return next((l for l in out.splitlines() if l.startswith('mix.wav')), 'mix.wav written')

    def mux(self):
        for f in (self.picture, self.mixwav):
            if not f.exists():
                raise StageError(f'{f} missing', 'run render and mix first')
        dp, de = probe_duration(self.picture), self.ep()['dur']
        if abs(dp - de) > 0.15:
            raise StageError(f'out/picture.mp4 is {dp:.2f} s but the episode is now {de} s: the picture is older than the script or voice',
                             f'python build.py {self.d} --from render')
        run([P['ffmpeg'], '-y', '-loglevel', 'error', '-i', str(self.picture), '-i', str(self.mixwav), '-map', '0:v', '-map', '1:a',
             '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709',
             '-color_trc', 'bt709', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', str(self.final)],
            self.d, self.logs / 'mux.log', timeout=1800)
        out = ''
        if not self.final.exists():
            raise StageError(f'{self.final} was not written')
        if 'missed the target' in out:
            raise StageError('mux.sh says the film missed -14 LUFS / -1 dBTP', 'the mix is too hot: lower hero cue weights or the score level')
        return f'{self.final}'

    def qa(self):
        e = self.ep()
        rep = self.audio / 'audio' / 'qa-report.json'
        try:
            run([which('uv'), 'run', f'{P["sound_layer"]}/scripts/qa.py', f'../{self.final.name}'], self.audio, self.logs / 'qa.log',
                env={'UV_NATIVE_TLS': '1'}, timeout=1800)
        except StageError:
            if not rep.exists():
                raise  # qa.py crashed rather than reporting failures
        R = json.loads(rep.read_text(encoding='utf-8'))['results']
        hard = [r for r in R if r['check'] in HARD_QA and r['status'] == 'FAIL']
        soft = [r for r in R if r['check'] not in HARD_QA and r['status'] == 'FAIL']
        ncues = sum(1 for r in R if r['check'].startswith('picture '))
        d = probe_duration(self.final)
        problems = [f'{r["check"]}: {r["detail"]}' for r in hard]
        if abs(d - e['dur']) > 0.15:
            problems.append(f'final film is {d:.2f} s, episode is {e["dur"]} s')
        if ncues and len(soft) > ncues * 2 / 3:
            problems.append(f'{len(soft)} soft QA fails for {ncues} cues (limit two thirds): the sound is off the picture')
        (self.out / 'qa-summary.txt').write_text('\n'.join(f'{r["status"]:5} {r["check"]}: {r["detail"]}' for r in R if r['status'] != 'pass'), encoding='utf-8')
        if problems:
            raise StageError('publish gate failed:\n  - ' + '\n  - '.join(problems), f'details in {rep}')
        return f'gate passed ({len(soft)} soft fails, listed in out/qa-summary.txt)'

    def hook(self):
        # Cold-open hook + series title card in front of the QA-passed body (hook.py keeps the body in out/body.mp4).
        if not (self.d / 'hook.json').exists():
            raise StageError('hook.json missing', 'write it: see references/script.md, Hook lines')
        out = run([P['kokoro_python'], str(KIT / 'hook.py'), str(self.d)], self.d, self.logs / 'hook.log', timeout=1800)
        return out.strip().splitlines()[-1] if out.strip() else 'hooked'

    def phone(self):
        if not self.final.exists():
            raise StageError(f'{self.final} missing')
        run([P['ffmpeg'], '-y', '-loglevel', 'error', '-i', str(self.final), '-c:v', 'libx264', '-preset', 'slow', '-b:v', f"{P['phone_kbps']}k", '-maxrate', f"{int(P['phone_kbps'] * 1.17)}k",
             '-bufsize', '7M', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(self.phone_file)], self.d, self.logs / 'phone.log', timeout=1800)
        mb = self.phone_file.stat().st_size / 1e6
        if mb >= P['phone_max_mb']:
            raise StageError(f'phone copy is {mb:.1f} MB (limit {P["phone_max_mb"]})', 'lower -b:v in build.py phone stage')
        return f'{self.phone_file} ({mb:.1f} MB)'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('episode', help='episode folder, e.g. <series>/ep02')
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--only', help='comma-separated stages')
    g.add_argument('--from', dest='start', choices=STAGES, help='start at this stage')
    ap.add_argument('--until', choices=STAGES, help='stop after this stage')
    a = ap.parse_args()
    E = Episode(a.episode)
    if not (E.hf / 'gen.mjs').exists():
        sys.exit(f'build: {E.d} is not an episode folder (no hf/gen.mjs)')
    if a.only:
        todo = [s.strip() for s in a.only.split(',')]
        bad = [s for s in todo if s not in STAGES]
        if bad:
            sys.exit(f'build: unknown stage {bad}; stages: {", ".join(STAGES)}')
    else:
        i0 = STAGES.index(a.start) if a.start else 0
        i1 = STAGES.index(a.until) + 1 if a.until else len(STAGES)
        todo = STAGES[i0:i1]
    report = {'episode': str(E.d), 'started': time.strftime('%Y-%m-%d %H:%M:%S'), 'stages': [], 'ok': False}
    failed = E.d / 'BUILD-FAILED.md'
    for s in todo:
        t0 = time.time()
        print(f'[{s}] ...', flush=True)
        try:
            msg = getattr(E, s)()
        except StageError as ex:
            report['stages'].append({'stage': s, 'ok': False, 'error': str(ex), 'hint': ex.hint})
            (E.d / 'build-report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
            failed.write_text(f'# Build failed at stage "{s}"\n\n{time.strftime("%Y-%m-%d %H:%M")}\n\n```\n{ex}\n```\n\nFix: {ex.hint or "read the log named above"}\n\nNothing was published.\n', encoding='utf-8')
            print(f'BUILD FAILED at {s}: {ex}' + (f'\nFix: {ex.hint}' if ex.hint else ''), file=sys.stderr)
            sys.exit(1)
        report['stages'].append({'stage': s, 'ok': True, 'result': msg, 'seconds': round(time.time() - t0, 1)})
        print(f'[{s}] ok: {msg}', flush=True)
    report['ok'] = True
    report['files'] = {k: str(v) for k, v in (('final', E.final), ('phone', E.phone_file), ('stills', E.stills_dir)) if v.exists()}
    (E.d / 'build-report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
    if failed.exists() and todo[-1] == 'phone':
        failed.unlink()
    print(f'build: done ({", ".join(todo)})')


if __name__ == '__main__':
    main()
