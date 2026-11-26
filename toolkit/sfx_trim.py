"""Cut each downloaded SFX to its loudest window (per-kind length), fade the edges, normalise peak to -3 dBFS."""
import sys, numpy as np, soundfile as sf
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kitcfg import P  # noqa: E402
K = Path(P['sfx_extra'])
LEN = {'rewind': 2.6, 'buzz': 1.2, 'ping': 1.0, 'lock': 0.9, 'tvon': 1.8, 'subdrop': 2.4, 'scrape': 2.8,
       'stinger': 3.0, 'cloth': 0.55, 'swell': 2.2}
CLIPS = {'cloth': 6, 'scrape': 2, 'lock': 2}
for kind, L in LEN.items():
    for f in sorted((K / kind).glob('fs-*.wav')):
        y, sr = sf.read(f, always_2d=True)
        n = int(L * sr)
        e = np.convolve((y ** 2).mean(1), np.ones(n) / n, 'valid') if len(y) > n else np.array([1.0])
        taken = []
        for c in range(CLIPS.get(kind, 1)):
            i = int(np.argmax(e)) if len(e) > 1 else 0
            if len(e) > 1 and e[i] <= 1e-9: break
            seg = y[i:i + n].copy()
            fi, fo = min(int(0.005 * sr), len(seg) // 4), min(int(min(0.25, L / 3) * sr), len(seg) // 3)
            seg[:fi] *= np.linspace(0, 1, fi)[:, None]; seg[-fo:] *= np.linspace(1, 0, fo)[:, None]
            seg *= 0.707 / (np.abs(seg).max() + 1e-9)
            sf.write(K / kind / f'cut-{f.stem[3:]}-{c}.wav', seg.astype(np.float32), sr, subtype='PCM_16')
            if len(e) > 1: e[max(0, i - n):i + n] = 0
        f.unlink()
print('ok')
