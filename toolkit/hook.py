"""Prepend a cold-open hook and a series title card to a finished episode (heavy VFX + SFX).

Usage (Kokoro venv python):
  <kokoro_python> hook.py <episode folder> [--video PATH] [--out PATH]

Reads <folder>/hook.json {"series","season","episode","title","line","who","hit_words":[...],"src_t","shots":[...]}.
Without --out: copies epNN.mp4 to out/body.mp4 (once), writes the hooked result to epNN.mp4 and epNN-phone.mp4.
"""
import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kitcfg import P, series_cfg  # noqa: E402
from voice_kokoro import MODEL, synth  # noqa: E402  (one locked voice map for the series)

FFMPEG = P["ffmpeg"]
SFX = Path(P["sound_layer"]) / "audio" / "kit"
SR = 48000
W, H_PX, FPS = 1080, 1920, 30
RED, BONE, INK = "e5484d", "f1eee9", "0b0f14"
TITLE_LEN = 2.0
PICK = {"riser": "fs-503800-riser-1-wav-1.wav", "glitch": "fs-195541-glitch-1.wav", "hit": "fs-328448-hard-cinematic-hit-2.wav",
        "boom": "fs-539968-deep-boom-3.wav", "reverse": "fs-446010-backwards-whoosh-1.wav",
        "whoosh": "fs-449994-whoosh-med-mid-wav-1.wav"}


def die(msg):
    sys.exit(f"hook.py: {msg}")


def run(args, cwd=None):
    r = subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *map(str, args)], cwd=cwd,
                       capture_output=True, text=True)
    if r.returncode:
        die("ffmpeg failed: " + r.stderr[-1500:])


def resample(x, sr):
    if sr == SR:
        return x
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def sfx(kind, rnd, max_len=None):
    f = SFX / kind / PICK[kind]
    if not f.exists():
        files = sorted((SFX / kind).glob("*.wav"))
        if not files:
            die(f"no sfx in {kind}")
        f = rnd.choice(files)
    a, sr = sf.read(f, dtype="float32", always_2d=True)
    a = resample(a.mean(axis=1), sr)
    if max_len:
        a = a[: int(max_len * SR)]
    peak = np.abs(a).max() or 1.0
    return (a / peak).astype(np.float32)


def put(buf, clip, t, gain):
    i = int(max(t, 0) * SR)
    n = min(len(clip), len(buf) - i)
    if n > 0:
        buf[i:i + n] += clip[:n] * gain


def fade(a, fi=0.0, fo=0.0):
    a = a.copy()
    ni, no = int(fi * SR), int(fo * SR)
    if ni:
        a[:ni] *= np.linspace(0, 1, ni)
    if no:
        a[-no:] *= np.linspace(1, 0, no)
    return a


def kokoro_line(text, who, path, ser):
    from voice_kokoro import Kokoro
    audio, rate = synth(Kokoro(*MODEL), text, who, ser)
    audio = resample(np.asarray(audio, dtype=np.float32), rate)
    sf.write(path, audio, SR)
    return audio


def text_width(font, words_size):
    """Return a function measuring text width in px at a size; PIL, then fontTools, then a rough estimate."""
    try:
        from PIL import ImageFont
        return lambda s, size: ImageFont.truetype(font, size).getlength(s)
    except Exception:
        pass
    try:
        from fontTools.ttLib import TTFont
        f = TTFont(font)
        cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
        return lambda s, size: sum(hmtx[cmap.get(ord(c), "space")][0] for c in s) * size / upm
    except Exception:
        return lambda s, size: sum(0.74 if c.isupper() else 0.33 if c in " .,'!" else 0.6 for c in s) * size


def wrap_rows(words, limit=16):
    rows, cur = [], []
    for i, w in enumerate(words):
        if cur and len(" ".join(words[j] for j in cur + [i])) > limit:
            rows.append(cur)
            cur = []
        cur.append(i)
    return rows + ([cur] if cur else [])


def norm(w):
    return "".join(c for c in w.lower() if c.isalnum())


def resolve_shots(J, ep):
    """List of (src_t, focus_y). Falls back to src_t, focus 0.4."""
    raw = J.get("shots")
    if not raw:
        return [(float(J.get("src_t", 0)), 0.4)]
    lines = None
    out = []
    for s in raw[:3]:
        if "line" in s:
            if lines is None:
                lines = json.loads((ep / "hf" / "episode.json").read_text(encoding="utf-8"))["lines"]
            t = float(lines[int(s["line"])]["t0"]) + float(s.get("dt", 0))
        else:
            t = float(s["t"])
        out.append((t, float(s.get("focus_y", 0.4))))
    return out


def cut_times(n, H, starts, hit_flags):
    """n-1 cut times: on hit-word starts when enough exist inside the hook, else equal split."""
    if n < 2:
        return []
    hs = [t for t, h in zip(starts, hit_flags) if h and 0.5 < t < H - 0.5]
    if len(hs) >= n - 1:
        return hs[:n - 1]
    return [H * i / n for i in range(1, n)]


def shot_chain(i, D, fy):
    cy = min(max(fy * H_PX, 768), H_PX - 768)
    y0 = int(round(cy - 768))
    return (f"[{i}:v]setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H_PX}:force_original_aspect_ratio=increase,crop={W}:{H_PX},setsar=1,"
            f"split[s{i}a][s{i}b];[s{i}b]crop={W}:260:0:1410,boxblur=40:4[s{i}c];[s{i}a][s{i}c]overlay=0:1410,"
            f"crop=864:1536:108:{y0},scale={W}:{H_PX}:flags=bicubic,"
            f"scale=w='{W}*(1+0.06*t/{D:.3f})':h=-2:eval=frame,crop={W}:{H_PX}:(iw-{W})/2:(ih-{H_PX})/2,setsar=1,format=yuv420p[sh{i}]")


def build_hook_filter(words, starts, hits, H, font, tmp, shots, cuts):
    """filter_complex string for the hook video; inputs 0..n-1 are the shot clips."""
    measure = text_width(font, None)
    hitset = {norm(h) for h in hits}
    is_hit = [norm(w) in hitset for w in words]
    rows = wrap_rows(words)
    n = len(shots)
    bounds = [0.0] + list(cuts) + [H]
    pre = ";".join(shot_chain(i, bounds[i + 1] - bounds[i], shots[i][1]) for i in range(n))
    pre += ";" + "".join(f"[sh{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[cat];[cat]"
    pulses = list(cuts) + [starts[i] for i in range(len(words)) if is_hit[i]]
    f = ["eq=contrast=1.07:brightness=0.01:saturation=1.02"]
    for t in pulses:
        f.append(f"rgbashift=rh=-9:bh=9:enable='between(t,{t:.3f},{t + 0.1:.3f})'")
    f += ["noise=alls=7:allf=t", "vignette=angle=PI/4"]
    for t in pulses[:len(cuts)]:
        f.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@1:t=fill:enable='between(t,{t:.3f},{t + 0.034:.3f})'")
    chain = pre + ",".join(f)
    # one word at a time
    for i, w in enumerate(words):
        size = 190 if is_hit[i] else 150
        size = int(min(size, 980 / max(measure(w, 1), 0.01)))
        (tmp / f"w{i}.txt").write_text(w, encoding="utf-8")
        col = f"0x{RED}" if is_hit[i] else "white"
        end = starts[i + 1] if i + 1 < len(words) else H
        chain += (f",drawtext=fontfile=font.ttf:textfile=w{i}.txt:fontsize={size}:fontcolor={col}:borderw=8:bordercolor=black"
                  f":shadowx=5:shadowy=6:box=1:boxcolor=0x0b0f14@0.7:boxborderw=26:x=(w-text_w)/2:y=h*0.80-text_h/2:alpha='min(1,(t-{starts[i]:.3f})/0.07)'"
                  f":enable='between(t,{starts[i]:.3f},{end:.3f})'")
    chain += f",format=yuv420p[v]"
    return chain


def make_title(font, tmp, d, series, season, episode, title):
    size = 190
    measure = text_width(font, None)
    while measure(series.upper(), size) > 940 and size > 60:
        size -= 6
    (tmp / "t_series.txt").write_text(series.upper(), encoding="utf-8")
    (tmp / "t_sub.txt").write_text(f"SEASON {season} \u00b7 EPISODE {episode}", encoding="utf-8")
    (tmp / "t_title.txt").write_text(title, encoding="utf-8")
    cx = "(w-text_w)/2"
    jit = "if(lt(t,0.36),34*sin(t*190)*(1-t/0.36),0)"
    yy = "(h*0.42-text_h/2)"

    def layer(col, dx, extra=""):
        return (f"drawtext=fontfile=font.ttf:textfile=t_series.txt:fontsize={size}:fontcolor={col}:x='{cx}+{jit}+({dx})':y='{yy}':"
                f"enable='gte(t,0.1){extra}'")
    f = [f"color=c=0x{INK}:s={W}x{H_PX}:r={FPS}:d={d}", "format=rgb24",
         layer("0xe5484d@0.85", "-12*if(lt(t,0.5),1,0.3)", "*lt(t,0.9)"),
         layer("0x38d6e8@0.8", "12*if(lt(t,0.5),1,0.3)", "*lt(t,0.9)"),
         layer(f"0x{BONE}", "0"),
         f"drawbox=x=(iw-640)/2:y=ih*0.42+{size * 0.62:.0f}:w=640:h=6:color=0x{RED}:t=fill:enable='gte(t,0.5)'",
         f"drawtext=fontfile=font.ttf:textfile=t_sub.txt:fontsize=50:fontcolor=0x{BONE}:x='{cx}':y=h*0.42+{size * 0.62 + 50:.0f}:enable='gte(t,0.75)'",
         f"drawtext=fontfile=font.ttf:textfile=t_title.txt:fontsize=40:fontcolor=0x{BONE}@0.8:x='{cx}':y=h*0.42+{size * 0.62 + 130:.0f}:enable='gte(t,1.0)'",
         "noise=alls=22:allf=t+u", "format=yuv420p"]
    return ",".join(f)




def build_audio(path, voice, H, starts, hit_flags, rnd, cuts=(), title_ticks=None):
    total = H + TITLE_LEN
    buf = np.zeros(int(total * SR), np.float32)
    put(buf, voice, 0.15, 1.0)
    riser = sfx("riser", rnd)
    riser = fade(riser[: int(H * SR)], 0.1, 0.05)
    put(buf, riser, 0.0, 0.35)
    hit = sfx("hit", rnd, 0.9)
    for c in cuts:
        put(buf, fade(hit, 0, 0.1), c, 0.6)
    for s, h in zip(starts, hit_flags):
        if h:
            put(buf, fade(hit, 0, 0.1), s, 0.7)
    rev = sfx("reverse", rnd)
    rev = rev[: int(0.8 * SR)][::-1] if False else rev[: int(0.8 * SR)]
    put(buf, fade(rev, 0.05, 0.02), max(H - 0.8, 0), 0.5)
    boom = sfx("boom", rnd, 1.8)
    put(buf, fade(boom, 0, 0.3), H, 0.9)
    tick = sfx("glitch", rnd, 0.06)
    letters, scan0 = title_ticks if title_ticks else ([0.14, 0.26, 0.4], 0.6)
    for t in letters:  # one key-tick per typed letter of the series name
        put(buf, fade(tick, 0, 0.02), H + t, 0.35)
    put(buf, fade(sfx("whoosh", rnd, 0.5), 0.02, 0.1), H + scan0, 0.6)  # scan bar sweep
    wh = sfx("whoosh", rnd, 0.5)
    put(buf, fade(wh, 0.05, 0.1), H + TITLE_LEN - 0.4, 0.7)
    buf = np.tanh(buf * 0.9)
    sf.write(path, np.stack([buf, buf], axis=1), SR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--video")
    ap.add_argument("--out")
    a = ap.parse_args()
    ep = Path(a.folder).resolve()
    J = json.loads((ep / "hook.json").read_text(encoding="utf-8"))
    nn = f"{int(J['episode']):02d}"
    main_mp4 = ep / f"ep{nn}.mp4"
    body = ep / "out" / "body.mp4"
    if a.video:
        video = Path(a.video)
    elif body.exists():
        video = body
    else:
        video = main_mp4
    marker = ep / "out" / "hooked.json"
    if not a.out and main_mp4.exists():
        st = main_mp4.stat()
        try:
            m = json.loads(marker.read_text(encoding="utf-8"))
            is_hooked = m.get("size") == st.st_size and m.get("mtime") == st.st_mtime
        except Exception:
            is_hooked = False
        if not body.exists() or (not is_hooked and st.st_mtime > body.stat().st_mtime):
            body.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(main_mp4, body)
        if not a.video:
            video = body
    if not video.exists():
        die(f"missing video {video}")
    out = Path(a.out) if a.out else main_mp4
    fp = ep / "hf" / "assets" / "fonts"
    cands = [p for p in (list(fp.glob("*Bold*.ttf")) + list(fp.glob("*Inter*.ttf")) + list(fp.glob("*.ttf"))) if fp.exists()]
    font = cands[0] if cands else Path(r"C:/Windows/Fonts/arialbd.ttf")
    rnd = random.Random(7)
    words = J["line"].split()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        shutil.copy2(font, tmp / "font.ttf")
        voice = kokoro_line(J["line"], J.get("who", "narrator"), tmp / "voice.wav", series_cfg(ep))
        vd = len(voice) / SR
        H = max(3.0, vd + 0.5)
        chars = [len(w) for w in words]
        t0, acc, starts = 0.15, 0, []
        for c in chars:
            starts.append(t0 + vd * acc / sum(chars))
            acc += c
        hitset = {norm(h) for h in J.get("hit_words", [])}
        hit_flags = [norm(w) in hitset for w in words]
        shots = resolve_shots(J, ep)
        cuts = cut_times(len(shots), H, starts, hit_flags)
        vf = build_hook_filter(words, starts, J.get("hit_words", []), H, tmp / "font.ttf", tmp, shots, cuts)
        (tmp / "hook.fg").write_text(vf, encoding="utf-8")
        bounds = [0.0] + cuts + [H]
        ins = []
        for (t, _), b0, b1 in zip(shots, bounds, bounds[1:]):
            ins += ["-ss", f"{t:.3f}", "-t", f"{b1 - b0 + 0.3:.3f}", "-i", video]
        run([*ins, "-/filter_complex", "hook.fg", "-map", "[v]", "-t", f"{H:.3f}",
             "-r", FPS, "-c:v", "libx264", "-crf", 16, "-preset", "veryfast", "-an", "hook.mp4"], cwd=tmp)
        tc = subprocess.run([P["system_python"], "-I", str(Path(__file__).resolve().parent / "title_card.py"), str(tmp / "font.ttf"), str(tmp / "title"),
                             str(TITLE_LEN), J["series"], str(J["season"]), str(J["episode"]), J["title"]], capture_output=True, text=True)
        if tc.returncode:
            die("title_card.py failed: " + tc.stderr[-400:])
        title_ticks = json.loads(tc.stdout.strip().splitlines()[-1])
        run(["-framerate", FPS, "-i", "title/%03d.png", "-t", TITLE_LEN, "-c:v", "libx264", "-crf", 16,
             "-preset", "veryfast", "-pix_fmt", "yuv420p", "-an", "title.mp4"], cwd=tmp)
        build_audio(tmp / "ht_raw.wav", voice, H, starts, hit_flags, rnd, cuts, title_ticks)
        run(["-i", "ht_raw.wav", "-af", f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample={SR}", "-ar", SR, "-ac", 2, "ht.wav"], cwd=tmp)
        norm_v = f"fps={FPS},scale={W}:{H_PX},setsar=1,format=yuv420p"
        fg = (f"[0:v]{norm_v}[a];[1:v]{norm_v}[b];[2:v]{norm_v}[c];[a][b][c]concat=n=3:v=1:a=0[v];"
              f"[3:a]aresample={SR},aformat=channel_layouts=stereo[ha];[4:a]aresample={SR},aformat=channel_layouts=stereo[ba];"
              "[ha][ba]concat=n=2:v=0:a=1[a]")
        (tmp / "final.fg").write_text(fg, encoding="utf-8")
        tmpout = tmp / "final.mp4"
        run(["-i", "hook.mp4", "-i", "title.mp4", "-i", video, "-i", "ht.wav", "-i", video, "-/filter_complex", "final.fg",
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", 18, "-pix_fmt", "yuv420p", "-r", FPS, "-preset", "medium",
             "-c:a", "aac", "-ar", SR, "-ac", 2, "-b:a", "192k", "-movflags", "+faststart", str(tmpout)], cwd=tmp)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmpout, out)
        if not a.out:
            phone = ep / f"ep{nn}-phone.mp4"
            run(["-i", out, "-c:v", "libx264", "-b:v", "3400k", "-maxrate", "3800k", "-bufsize", "7M", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", phone])
            st = out.stat()
            marker.write_text(json.dumps({"size": st.st_size, "mtime": st.st_mtime}), encoding="utf-8")
            if phone.stat().st_size > 30e6:
                print("WARNING: phone copy over 30 MB", phone.stat().st_size)
    print(f"ok {out} hook {H:.2f}s + title {TITLE_LEN}s")


if __name__ == "__main__":
    main()
