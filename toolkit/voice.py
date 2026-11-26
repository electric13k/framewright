"""Voice an episode with ElevenLabs through Composio, one take per line, then write voice/timing.json for gen.mjs.

Composio is reached through the agent's MCP tools, not from this script, so voicing has three steps:

  1. python voice.py <series>/ep02 plan
       Writes voice/el/jobs.json: only the lines whose text or voice changed since the last take, each with
       voice_id, text, voice_settings and the mp3 name to save. Prints the character count (the credit cost).
       Stops if a speaker has no approved voice_id.
  2. The agent runs each job once with COMPOSIO_MULTI_EXECUTE_TOOL, tool ELEVENLABS_TEXT_TO_SPEECH, arguments
       exactly as in jobs.json, and saves each response's data.file.s3url to voice/el/<file> (the URL expires in
       an hour). One take per line. No retakes for taste. A retake only when the owner asks for that line.
  3. python voice.py <series>/ep02 ingest
       Trims each mp3, adds the fake treatment where a line has one, writes 48 kHz WAVs and voice/timing.json.
       Then: python build.py <episode> --from gen   (captions, camera marks and cues retime to the voice)

  python voice.py <episode> plan --lines 3,4     # ask for exactly these lines again (owner-requested retake)

No API key is read, stored or printed here.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))
from kitcfg import P  # noqa: E402
SR = 44100


def die(msg, code=1):
    print(f'voice: {msg}', file=sys.stderr)
    sys.exit(code)


def resolve(voices, who):
    if who not in voices:
        die(f'no voice for who="{who}" in the config. Voices: {", ".join(voices)}')
    v = dict(voices[who])
    seen = {who}
    while 'same_as' in v:
        base = v.pop('same_as')
        if base in seen:
            die(f'same_as loop at "{who}"')
        seen.add(base)
        v = {**voices[base], **v}
    return v


def fake_chain(f, sr):
    """ffmpeg filter for a cloned voice: slightly off pitch, phone band, a short comb and grit. f=0 is clean."""
    if f <= 0:
        return None
    return ','.join([
        f'asetrate={int(sr * (1 + 0.02 * f))}', f'aresample={sr}',
        f'highpass=f={int(200 + 150 * f)}', f'lowpass=f={int(6000 - 2600 * f)}',
        f'aecho=0.8:0.5:{int(8 + 10 * f)}:{0.2 + 0.3 * f:.2f}',
        f'acrusher=bits={16 - 6 * f:.1f}:mix={0.35 * f:.2f}:mode=log',
        f'tremolo=f=11:d={0.25 * f:.2f}',
    ])


def finish(raw, out, fake):
    """Trim silence at both ends (no padded holds), apply the fake treatment, write 48 kHz mono 16-bit."""
    trim = 'silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse'
    chain = ','.join(x for x in (f'aresample={SR}', trim, fake_chain(fake, SR), 'aresample=48000') if x)
    r = subprocess.run([P['ffmpeg'], '-y', '-loglevel', 'error', '-i', str(raw), '-af', chain, '-ac', '1', '-c:a', 'pcm_s16le', str(out)],
                       capture_output=True, text=True)
    if r.returncode:
        die(f'ffmpeg failed on {raw.name}: {r.stderr.strip()[-400:]}')
    p = subprocess.run([P['ffprobe'], '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(out)], capture_output=True, text=True)
    return float(p.stdout.strip())


def take_key(text, v, C):
    return hashlib.sha1(json.dumps([text, v.get('voice_id'), v.get('settings'), C['model_id']], sort_keys=True).encode()).hexdigest()[:12]


def load(ep, cfg):
    S = json.loads((ep / 'script.json').read_text(encoding='utf-8'))
    C = json.loads(Path(cfg).read_text(encoding='utf-8'))
    el = ep / 'voice' / 'el'
    el.mkdir(parents=True, exist_ok=True)
    tf = ep / 'voice' / 'timing.json'
    old = json.loads(tf.read_text(encoding='utf-8')) if tf.exists() else None
    return S, C, el, tf, old


def rows(S, C):
    for i, l in enumerate(S['lines']):
        who = l.get('who', 'narrator')
        v = resolve(C['voices'], who)
        fake = float(l.get('fake', v.get('fake', 0)))
        yield i, l, who, v, fake, take_key(l['text'], v, C)


def plan(ep, a):
    S, C, el, tf, old = load(ep, a.config)
    pick = {int(x) for x in a.lines.split(',')} if a.lines else None
    missing = sorted({who for _, _, who, v, _, _ in rows(S, C) if not v.get('voice_id')})
    if missing:
        die(f'no approved voice for: {", ".join(missing)}. Pick one curated voice each, generate ONE sample, get the owner\'s approval, '
            'then set voice_id in voice.config.json. Nothing planned.')
    jobs = []
    for i, l, who, v, fake, key in rows(S, C):
        name = f'{i:02d}-{who}.mp3'
        prev = old['lines'][i] if old and i < len(old['lines']) else None
        have = prev and prev.get('key') == key and (el / name).exists()
        redo = (i in pick) if pick is not None else not have
        if redo:
            jobs.append({'i': i, 'who': who, 'file': name, 'key': key,
                         'arguments': {'voice_id': v['voice_id'], 'text': l['text'], 'model_id': C['model_id'],
                                       'output_format': C['output_format'], 'voice_settings': v.get('settings', {})}})
    chars = sum(len(j['arguments']['text']) for j in jobs)
    (el / 'jobs.json').write_text(json.dumps({'tool_slug': C['tool_slug'], 'chars': chars, 'jobs': jobs}, indent=1), encoding='utf-8')
    print(f'voice: {len(jobs)} takes to record, {chars} characters. Jobs: {el / "jobs.json"}')
    print('voice: run each job once through Composio, save data.file.s3url to voice/el/<file>, then: voice.py <episode> ingest')


def ingest(ep, a):
    S, C, el, tf, old = load(ep, a.config)
    jf = el / 'jobs.json'
    keys = {j['i']: j['key'] for j in json.loads(jf.read_text(encoding='utf-8'))['jobs']} if jf.exists() else {}
    todo = list(rows(S, C))
    for i, l, who, v, fake, key in todo:
        mp3 = el / f'{i:02d}-{who}.mp3'
        if not mp3.exists():
            die(f'line {i} take missing: {mp3}. Nothing converted, timing.json not changed.')
        prev = old['lines'][i] if old and i < len(old['lines']) else None
        if i not in keys and not (prev and prev.get('key') == key):
            die(f'line {i} ({mp3.name}) is older than the script text. Run plan, record that job, then ingest.')
    out = []
    for i, l, who, v, fake, key in todo:
        mp3 = el / f'{i:02d}-{who}.mp3'
        wav = f'{i:02d}-{who}.wav'
        dur = finish(mp3, ep / 'voice' / wav, fake)
        out.append({'i': i, 'who': who, 'file': wav, 'dur': round(dur, 3), 'fake': fake, 'key': key})
    tf.write_text(json.dumps({'engine': 'elevenlabs', 'model': C['model_id'], 'gap': C.get('gap', 0.08), 'lines': out}, indent=1), encoding='utf-8')
    print(f'voice: {len(out)} takes timed in {tf}. Next: python {KIT / "build.py"} {ep} --from gen')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('episode')
    ap.add_argument('step', choices=['plan', 'ingest'])
    ap.add_argument('--config', default=str(KIT / 'voice.config.json'))
    ap.add_argument('--lines', help='plan only: comma-separated line numbers (0-based) the owner asked to retake')
    a = ap.parse_args()
    ep = Path(a.episode).resolve()
    (plan if a.step == 'plan' else ingest)(ep, a)


if __name__ == '__main__':
    main()
