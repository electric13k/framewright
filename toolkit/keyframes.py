"""Pull only the frames where the picture changes (ffmpeg scene detection), plus one contact sheet.
Use this for review instead of sampling every N seconds or reading every frame.

Usage:
  python -I keyframes.py <video.mp4> [threshold=0.06] [max=36]
Writes <video folder>/keys/NN-<time>s.jpg, keys/sheet.jpg and keys/keys.json {threshold, times}.
Read sheet.jpg first; open single keys only where the sheet looks wrong.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kitcfg import P  # noqa: E402
FFMPEG = P['ffmpeg']
COLS = 6
FLASH = 0.15  # seconds
SETTLE = 0.4  # seconds after a cut before the frame is grabbed
LONG = 4.0  # seconds; longer with no picture change is flagged


def ff(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([FFMPEG, '-hide_banner', *args], capture_output=True, text=True)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('usage: keyframes.py <video.mp4> [threshold] [max]')
    src = Path(sys.argv[1]).resolve()
    thr = float(sys.argv[2]) if len(sys.argv) > 2 else 0.06
    cap = int(sys.argv[3]) if len(sys.argv) > 3 else 36
    out = src.parent / 'keys'
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    # Timestamps of frames whose scene-change score beats the threshold; frame 0 always kept.
    r = ff('-i', str(src), '-vf', f"select='eq(n,0)+gt(scene,{thr})',showinfo", '-an', '-f', 'null', '-')
    times = [float(t) for t in re.findall(r'pts_time:([\d.]+)', r.stderr)]
    if not times:
        sys.exit('no frames found: ' + r.stderr[-300:])
    # Long holds are judged on every detected change, before the sheet is thinned.
    all_holds = [(t, round((times[i + 1] if i + 1 < len(times) else 9e9) - t, 2)) for i, t in enumerate(times)]
    long = [(t, h) for t, h in all_holds if LONG < h < 9e8]
    if len(times) > cap:  # too many cuts: keep an even spread
        times = [times[int(i * len(times) / cap)] for i in range(cap)]
    # hold = seconds until the next change. Under FLASH it is a whip or cut frame the eye barely sees: skipped.
    # Other shots are grabbed after they settle (cut + half the hold, at most SETTLE), not on the blurred first frame.
    holds = [round((times[i + 1] if i + 1 < len(times) else 9e9) - t, 2) for i, t in enumerate(times)]
    flashes = [t for t, h in zip(times, holds) if h < FLASH]
    shots = [round(t + min(SETTLE, h / 2), 2) for t, h in zip(times, holds) if h >= FLASH]
    for i, t in enumerate(shots):
        ff('-loglevel', 'error', '-ss', f'{t:.3f}', '-i', str(src), '-frames:v', '1', '-vf', 'scale=360:-1',
           str(out / f'{i:02d}-{t:.2f}s.jpg'))
        shutil.copyfile(out / f'{i:02d}-{t:.2f}s.jpg', out / f'seq{i:02d}.jpg')
    rows = -(-len(shots) // COLS)
    ff('-loglevel', 'error', '-i', str(out / 'seq%02d.jpg'), '-vf', f'tile={COLS}x{rows}', '-frames:v', '1',
       str(out / 'sheet.jpg'))
    for p in out.glob('seq*.jpg'):
        p.unlink()
    (out / 'keys.json').write_text(json.dumps({'threshold': thr, 'cuts': times, 'holds': holds, 'sheet_times': shots,
                                               'flash_times': flashes}, indent=1), encoding='utf-8')
    print(f'{len(shots)} settled shots ({len(flashes)} flash frames skipped), sheet: {out / "sheet.jpg"}')
    # A new visual every 3-4 s: flag any stretch with no picture change longer than LONG (shaky cam is not a change).
    end = float(re.findall(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr)[0][2]) if re.search(r'Duration: ', r.stderr) else None
    if end is not None and times and LONG < end - times[-1] < 9e8:
        long.append((times[-1], round(end - times[-1], 2)))
    if long:
        print('LONG HOLDS (need a new visual every 3-4 s):', ', '.join(f'{t:.1f}s for {h:.1f}s' for t, h in long))


if __name__ == '__main__':
    main()
