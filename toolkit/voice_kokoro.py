"""Voice an episode locally with Kokoro (free, offline). Writes voice/NN-who.wav and voice/timing.json.

Usage (run with the Kokoro venv python, see kit.config.json "kokoro_python"):
  <kokoro_python> voice_kokoro.py <series>/ep02

Voices are locked for the whole series in <series>/series.json "voices" (who -> [kokoro voice, speed]); no per-line
or per-episode overrides, so a character always sounds the same. A fake_<who> line uses <who>'s voice with the
cloned-voice treatment at series "fake_level". Each line is spoken in pieces split at punctuation and joined with
series "pauses" seconds of silence, so commas and full stops breathe.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))
from kitcfg import P, series_cfg  # noqa: E402

sys.path.insert(0, P['kokoro_dir'])
from kokoro_onnx import Kokoro  # noqa: E402

import voice as V  # noqa: E402  (finish, die)

GAP = 0.08
MODEL = (str(Path(P['kokoro_dir']) / 'kokoro-v1.0.onnx'), str(Path(P['kokoro_dir']) / 'voices-v1.0.bin'))


def voice_for(who: str, ser: dict):
    base = who[5:] if who.startswith('fake_') else who
    if base not in ser['voices']:
        V.die(f'no voice for "{base}": add it to "voices" in series.json')
    name, speed = ser['voices'][base]
    return name, float(speed), (float(ser['fake_level']) if who.startswith('fake_') else 0.0)


def trim(a: np.ndarray, rate: int, floor: float = 0.01) -> np.ndarray:
    """Cut leading/trailing near-silence of one piece so the added pause is the only gap."""
    idx = np.nonzero(np.abs(a) > floor)[0]
    if not len(idx):
        return a[:0]
    pad = int(0.02 * rate)
    return a[max(0, idx[0] - pad): idx[-1] + pad]


def synth(K, text: str, who: str, ser: dict):
    """Speak text in the locked voice for who, with silence after each punctuation mark. Returns (audio, rate)."""
    name, speed, _ = voice_for(who, ser)
    parts = [p for p in re.split(r"(?<=[,;:.!?—])\s+|\s+-\s+", text.strip()) if p.strip()]
    out, rate = [], 24000
    for k, p in enumerate(parts):
        a, rate = K.create(p, voice=name, speed=speed, lang='en-us')
        out.append(trim(np.asarray(a, dtype=np.float32), rate))
        if k < len(parts) - 1:
            out.append(np.zeros(int(ser['pauses'].get(p.rstrip()[-1], 0.14) * rate), dtype=np.float32))
    return (np.concatenate(out) if out else np.zeros(1, dtype=np.float32)), rate


def main() -> None:
    if len(sys.argv) != 2:
        V.die('usage: voice_kokoro.py <episode folder>')
    ep = Path(sys.argv[1]).resolve()
    ser = series_cfg(ep)
    S = json.loads((ep / 'script.json').read_text(encoding='utf-8'))
    K = Kokoro(*MODEL)
    out_dir = ep / 'voice'
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, l in enumerate(S['lines']):
            who = l.get('who', 'narrator')
            name, speed, fake = voice_for(who, ser)
            audio, rate = synth(K, l['text'], who, ser)
            raw = Path(tmp) / f'{i:02d}.wav'
            sf.write(raw, audio, rate)
            wav = f'{i:02d}-{who}.wav'
            dur = V.finish(raw, out_dir / wav, fake)
            rows.append({'i': i, 'who': who, 'file': wav, 'dur': round(dur, 3), 'fake': fake, 'key': f'kokoro:{name}:{speed}:p1'})
    timing = {'engine': 'kokoro', 'model': 'kokoro-v1.0', 'gap': GAP, 'lines': rows}
    (out_dir / 'timing.json').write_text(json.dumps(timing, indent=1), encoding='utf-8')
    total = sum(r['dur'] for r in rows) + GAP * len(rows)
    print(f'{len(rows)} lines, speech {total:.1f} s')


if __name__ == '__main__':
    main()
