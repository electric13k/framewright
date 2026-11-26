# Background bed for one episode, built from score.json (same folder) and ../hf/episode.json (marks and length).
# Recorded CC0 audio only (kit.config.json ambience_dir, credits in CREDITS.md there): one continuous music bed
# (rain outside, room tone inside), crossfaded at scene changes, plus a low drone whose level follows a curve.
# Hush ranges are planned silences: beds dip, the drone stops. Deterministic: same inputs, same file.
# Times in score.json are seconds, a mark name, "mark+0.3", "mark-0.1", "end" or "end-0.3".
# Run from the episode's audio dir: python score.py   (writes score.wav and silence.json)
import json, os, re, sys, wave
from pathlib import Path
import numpy as np

SR = 48000
ep = json.load(open('../hf/episode.json', encoding='utf-8'))
P = json.load(open('score.json', encoding='utf-8'))
AMB = Path(os.environ.get('FRAMEWRIGHT_AMBIENCE', 'ambience')).resolve()  # from the machine config only, never score.json
MARKS = dict(ep['marks']); MARKS['end'] = ep['dur']; DUR = float(ep['dur'])
N = int(SR * DUR); t = np.arange(N) / SR


def T(v):  # resolve a time: number, "mark", "mark+0.3", "mark-0.1"
    if isinstance(v, (int, float)): return float(v)
    m = re.fullmatch(r'\s*([A-Za-z_]\w*)\s*(?:([+-])\s*([\d.]+))?\s*', str(v))
    if not m or m.group(1) not in MARKS:
        sys.exit(f'score.py: unknown time "{v}". Marks: {", ".join(MARKS)}')
    t0 = MARKS[m.group(1)]
    if m.group(2): t0 += float(m.group(3)) * (1 if m.group(2) == '+' else -1)
    return t0


def env(points):  # piecewise-linear curve from [(time, value), ...]
    p = sorted((T(a), float(b)) for a, b in points)
    return np.interp(t, [a for a, _ in p], [b for _, b in p])


def ranges(rs, ramp):  # 0..1 gate, 1 inside each [from, to, ramp?]
    g = np.zeros(N)
    for r in rs:
        a, b = T(r[0]), T(r[1]); k = float(r[2]) if len(r) > 2 else ramp
        g = np.maximum(g, env([(0, 0), (a, 0), (a + k, 1), (b - k, 1), (b, 0), (DUR + 1, 0)]))
    return g


def load(name, offset_s=0.0):  # stereo 48 kHz float at unit RMS, looped with a 1 s crossfade to cover the episode
    if not re.fullmatch(r'[A-Za-z0-9_-]+', str(name)):
        sys.exit(f'score.py: bad sound name {name!r}: letters, digits, _ and - only')
    f = (AMB / f'{name}.wav').resolve()
    if AMB not in f.parents:
        sys.exit(f'score.py: {name!r} is outside {AMB}')
    if not f.exists():
        sys.exit(f'score.py: no ambience "{name}" in {AMB}. Have: {", ".join(p.stem for p in AMB.glob("*.wav"))}')
    with wave.open(str(f)) as w:
        if w.getframerate() != SR or w.getnchannels() != 2 or w.getsampwidth() != 2:
            sys.exit(f'score.py: {f} must be 48 kHz stereo 16-bit (ffmpeg -i x.mp3 -ar 48000 -ac 2 x.wav)')
        y = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, 2) / 32768.0
    y = y[int(offset_s * SR) % max(1, len(y) - SR):]
    x = min(4 * SR, len(y) // 3); out = y.copy()  # 4 s equal-power crossfade: no audible loop seam
    while len(out) < N + SR:
        u = np.linspace(0, np.pi / 2, x)[:, None]
        out = np.concatenate([out[:-x], out[-x:] * np.cos(u) + y[:x] * np.sin(u), y[x:]])
    y = out[:N]
    return y / (np.sqrt(np.mean(y ** 2)) + 1e-9)


hush = ranges(P.get('hush', []), 0.15)
L = P.get('levels', {})

# beds: [[start, name, offset_s?], ...]; each plays until the next one starts, with a short crossfade
beds = sorted(((T(b[0]), b[1], float(b[2]) if len(b) > 2 else 0.0) for b in P.get('beds', [])), key=lambda b: b[0])
bed = np.zeros((N, 2)); xf = P.get('crossfade_s', 0.6)
for j, (s0, name, off) in enumerate(beds):
    s1 = beds[j + 1][0] if j + 1 < len(beds) else DUR + 1
    a = -1 if j == 0 else s0
    w = np.interp(t, [-2, a - xf / 2, a + xf / 2, s1 - xf / 2, s1 + xf / 2, DUR + 2], [0, 0, 1, 1, 0, 0])
    bed += load(name, off) * (w * L.get(name, 1.0))[:, None]
bed *= (1 - P.get('hush_cut', 0.8) * hush)[:, None]

# drone: one recording under everything, level by curve, silent in the hush
D = P.get('drone') or {}
drone = load(D.get('name', 'drone-dark'), D.get('offset_s', 0.0)) * (env(D['level']) * (1 - hush))[:, None] if D else 0

# heart: [[from, to, "slow"|"fast", level?], ...] faint recorded heartbeat (CC0) under anxious ("slow", 80 bpm) or
# adrenaline ("fast", 120 bpm) scenes, 0.5 s fades; it keeps beating through a hush, where it is the loudest thing left
heart = np.zeros((N, 2))
for k, r in enumerate(P.get('heart', [])):
    a, b = T(r[0]), T(r[1])
    g = np.interp(t, [a - 0.01, a + 0.5, b - 0.5, b + 0.01], [0, 1, 1, 0]) * (float(r[3]) if len(r) > 3 else 0.3)
    heart += load('heart-120' if r[2] == 'fast' else 'heart-80', 3.0 * k) * g[:, None]

# music: one continuous dark bed for the whole episode (series theme), never switched or cut; dips in the hush
M = P.get('music') or {}
music = load(M['name'], M.get('offset_s', 0.0)) * (M.get('level', 0.6) * (1 - 0.6 * hush))[:, None] if M else 0

out = bed + drone + heart + music
fi, fo = int(0.02 * SR), int(0.3 * SR); out[:fi] *= np.linspace(0, 1, fi)[:, None]; out[-fo:] *= np.linspace(1, 0, fo)[:, None]
out /= max(1e-9, np.max(np.abs(out))) / 0.8
with wave.open('score.wav', 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((out * 32767).astype('<i2').tobytes())
sil = []
for r in P.get('hush', []):
    k = float(r[2]) if len(r) > 2 else 0.15
    sil.append([round(T(r[0]) + k * 0.67, 2), round(T(r[1]) - k * 0.33, 2)])
json.dump(sil, open('silence.json', 'w'))
print(f"score.wav {DUR} s, {len(beds)} beds, drone {'on' if D else 'off'}, {len(P.get('heart', []))} heartbeat ranges, {len(sil)} planned silences")
